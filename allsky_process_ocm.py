#!/usr/bin/env python
import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.pyplot import Circle
import matplotlib.cbook as cbook
from matplotlib import transforms
import matplotlib as mpl
mpl.rcParams['figure.dpi']= 300
from scipy import ndimage
import allsky_shared
import os
import shutil
import cv2
import numpy as np
import time

#OCM customized allsky images
#pwielgor@camk.edu.pl, 8.02.2024

# RAW16 frames: the camera's 16-bit data as FITS, kept RAW_KEEP_DAYS days.
# allsky's own loadimage reads the file with cv2.imread() and gets 8 bits only,
# so the 16-bit file is read here again, before saveimage overwrites it.
RAW_PATH = '/data/misc/allsky_raw/'
RAW_KEEP_DAYS = 7
# FITS card, environment variable from the capture program, type, comment
RAW_CARDS = [
    ('EXPTIME', 'AS_EXPOSURE_US', float, 'exposure [s]'),
    ('AUTOEXP', 'AS_AUTOEXPOSURE', int, 'auto exposure on (1) / off (0)'),
    ('GAIN', 'AS_GAIN', float, 'camera gain setting'),
    ('AUTOGAIN', 'AS_AUTOGAIN', int, 'auto gain on (1) / off (0)'),
    ('CCD-TEMP', 'AS_TEMPERATURE_C', float, 'sensor temperature [C]'),
    ('BINNING', 'AS_BIN', int, 'binning'),
    ('BITDEPTH', 'AS_BIT_DEPTH', int, 'bit depth'),
    ('FLIP', 'AS_FLIP', str, 'image flip'),
    ('CAPMEAN', 'AS_MEAN', float, 'mean from the capture program (auto exposure)'),
    ('DARKFRM', 'AS_DARKFRAME', int, 'dark frame (1) / sky (0)'),
    ('CAPDATE', 'AS_DATE', str, 'exposure start date, RPi local clock'),
    ('CAPTIME', 'AS_TIME', str, 'exposure start time HHMMSS, RPi local clock'),
]

metaData = {
    "name": "AllSKY OCM process pipeline",
    "description": "Cut image add cardinal points and date, download satellite",  
    "events": [
        "day",
        "night"
    ],
    "experimental": "false",
    "module": "allsky_process_ocm",
    "arguments":{
        "directory": "false",
        "grayscale": "false"
    },
    "argumentdetails": {
        "directory" : {
            "required": "false",
            "description": "Save in Documents/allsky instead of NFS (/data/misc/allsky)",
            "help": "The path to the directory where images should be stored",
            "type": {
                "fieldtype": "checkbox"
            }
        },
        "grayscale" : {
            "required": "false",
            "description": "Save in gray scale",
            "help": "Otherwise image is colorful",
            "type": {
                "fieldtype": "checkbox"
            }
        }
        
    }
             
}

#cut image, add cardinal points and date and save to NFS folder /data/misc/allsky/
def process_ocm(params,event):
    gray = True
    documents = False
    #try:
    #    gray = params["grayscale"]
    #    documents = params["directory"]
    #except:
    #    pass
    t = str(datetime.datetime.utcnow()).split(':')
    time = t[0]+':'+t[1]

    folder= t[0].split()[0].split('-')[0]+t[0].split()[0].split('-')[1]+t[0].split()[0].split('-')[2]
    filename = folder+'_'+t[0].split()[1]+t[1]+'.jpg'
    if documents:
        path = '/home/observer/Documents/allsky/'
    else:
        path = '/data/misc/allsky/'

    if not os.access(path+folder,os.R_OK):
        os.mkdir(path+folder)

    try:
        save_raw(folder, filename.replace('.jpg', '.fits'))
    except Exception as e:
        allsky_shared.log(0, 'ERROR: allsky_process_ocm: raw FITS not saved: ' + str(e))

    img = allsky_shared.image[10:990,290:1270]
    if gray:
        img = np.mean(img,axis=2)
        
    # -39.1 puts north straight up (camera model fit on stars, 2026-11-06; -30 left it at -9.1 deg)
    image = ndimage.rotate(img, -39.1, reshape=False)
    fig, ax = plt.subplots()

    ax.cla()
    ax.set_aspect('equal')
    patch = patches.Circle(( 490,490), radius=490, transform=ax.transData)
    ax.text(-30,490,'W',color='red')
    ax.text(990,490,'E',color='red')
    ax.text(490,1010,'S',color='red')
    ax.text(490,-10,'N',color='red')
    ax.text(-10,1010,'UT '+time,color='white',fontsize = 'small')
    ax.text(700,1000,'           Rolf Chini \n Cerro Murphy Observatory',color='green',fontsize = 4)
    if gray:
        im = ax.imshow(image,cmap='gray')
    else:
        im = ax.imshow(image)
        
    im.set_clip_path(patch)


    fig.set_facecolor("black")
    ax.axis('off')

    plt.savefig(path+folder+'/'+filename,bbox_inches='tight')
    try:
        os.system('rm -f '+path+'lastimage4.jpg')
        os.system('mv '+path+'lastimage3.jpg '+path+'lastimage4.jpg')
    except:
        pass
    try:
        os.system('mv '+path+'lastimage2.jpg '+path+'lastimage3.jpg')
    except:
        pass
    try:
        os.system('mv '+path+'lastimage.jpg '+path+'lastimage2.jpg')
    except:
        pass
    plt.savefig(path+'lastimage.jpg',bbox_inches='tight')
    try:
        satellite()
    except:
        pass
    
def save_raw(folder, filename):
    """
    Save the current frame with its full bit depth as a FITS file.

    Reads allsky's current image file again with cv2.IMREAD_UNCHANGED. Only a
    16-bit frame (camera Image Type RAW16, file name *.png) is saved; an 8-bit
    frame (jpg mode) is skipped. The data are written as the camera gives them
    (the Bayer mosaic, not debayered), Rice compressed, to
    RAW_PATH/<folder>/<filename>, with the capture values (exposure, gain,
    sensor temperature, ...) in the header. Day folders older than
    RAW_KEEP_DAYS are deleted.

    Parameters
    ----------
    folder : str
        Day folder, YYYYMMDD (UT), the same as in the jpg archive.
    filename : str
        File name, YYYYMMDD_HHMM.fits (UT), the same as the archive jpg.
    """
    from astropy.io import fits

    raw = cv2.imread(allsky_shared.CURRENTIMAGEPATH, cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise ValueError('cannot read ' + allsky_shared.CURRENTIMAGEPATH)
    if raw.dtype != np.uint16:
        return

    hdr = fits.Header()
    hdr['DATE-UT'] = (folder + '_' + filename[9:13], 'UT of processing, YYYYMMDD_HHMM')
    hdr['ORIGFILE'] = (os.path.basename(allsky_shared.CURRENTIMAGEPATH), 'allsky image file')
    for card, var, kind, comment in RAW_CARDS:
        value = os.environ.get(var)
        if value is None:
            continue
        value = kind(value)
        if card == 'EXPTIME':
            value = value / 1e6
        hdr[card] = (value, comment)

    os.makedirs(RAW_PATH + folder, exist_ok=True)
    out = RAW_PATH + folder + '/' + filename
    hdu = fits.CompImageHDU(raw, header=hdr, compression_type='RICE_1')
    fits.HDUList([fits.PrimaryHDU(), hdu]).writeto(out + '.tmp', overwrite=True)
    os.replace(out + '.tmp', out)

    oldest = (datetime.datetime.utcnow() - datetime.timedelta(days=RAW_KEEP_DAYS)).strftime('%Y%m%d')
    for d in os.listdir(RAW_PATH):
        if len(d) == 8 and d.isdigit() and d < oldest:
            shutil.rmtree(RAW_PATH + d)


#download GOES-16 satellite images of South America from https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR/ssa/GEOCOLOR/ for last 3 hours and edit them
	
def edit_images(images,dates):
    sites_dic={
        "OCA":[270,270,"*","red"],
        "Antofagasta":[250,180,"s","magenta"],
        "Tal-Tal":[240,330,"s","yellow"],
        "Llullaillaco":[430,270,"^","green"],
        "Copiapo":[250,530,"s","cyan"]
    }
    circles_dict = {
        "Clouds alt = 20km @ 35°": [270,270,27,"red"],  # r = 27px ≈ 31km (≈ 20km / tan(35°))
    }
	
		
    #with imageio.get_writer('satellite.gif', mode='I',duration=500) as writer:
    try:
    #if True:
        for j,image in enumerate(images):
            mpl.pyplot.figure(figsize=(10,10))
            im = mpl.pyplot.imread(image)
            mpl.pyplot.clf()
            mpl.pyplot.imshow(im[1000:1600,2100:2700])
            for i,site in enumerate(sites_dic):
                (x,y,marker,color) = sites_dic[site]
                mpl.pyplot.plot(x,y,marker,color=color,markersize=10)
                mpl.pyplot.text(x-70,y,site,c=color)
            for txt, (x,y,r,color) in circles_dict.items():
                mpl.pyplot.gca().add_patch(Circle((x,y),r,edgecolor=color,facecolor='none', lw=1))
                mpl.pyplot.text(x,y - r - 4, txt, c=color)

            mpl.pyplot.text(20,580,'UT: '+dates[j],c='red',fontsize='x-large')
            mpl.pyplot.text(500,580,'GOES-16 satellite',c='yellow')
            frame = mpl.pyplot.gca()
            frame.axes.xaxis.set_ticklabels([])
            frame.axes.yaxis.set_ticklabels([])
            frame.axes.get_xaxis().set_ticks([])
            frame.axes.get_yaxis().set_ticks([])
            mpl.pyplot.tight_layout()
            mpl.pyplot.savefig(image.replace('7200x4320.jpg','600x600.jpg',1))
    except:
        pass	
		

		

def satellite():
    dr = '/data/misc/GOES_satellite/'
    image_suffix = '_GOES19-ABI-ssa-GEOCOLOR-7200x4320.jpg'
    image_suffix_2 = '_GOES19-ABI-ssa-GEOCOLOR-600x600.jpg'
    minutes = ['00','10','20','30','40','50']
    czas = time.strftime('%Y/%m/%d %H:%M:%S',time.gmtime())
    night = czas.split(' ')[0].replace('/','',2)
    day_of_year = str(datetime.datetime.utcnow().timetuple().tm_yday)#day of year now
    day_of_year_1 = str((datetime.datetime.utcnow()-datetime.timedelta(hours=1)).timetuple().tm_yday)#day of year one hour ago
    #day_of_year_2 = str((datetime.datetime.utcnow()-datetime.timedelta(hours=2)).timetuple().tm_yday)#day of year two hours ago

    if int(day_of_year) < 10:
        day_of_year='00'+day_of_year

    elif int(day_of_year) < 100:
        day_of_year='0'+day_of_year
		
    if int(day_of_year_1) < 10:
        day_of_year_1='00'+day_of_year_1
		
    elif int(day_of_year_1) < 100:
        day_of_year_1='0'+day_of_year_1
		
    #if int(day_of_year_2)  < 100:
        #day_of_year_2='0'+day_of_year_2
		
    hour = datetime.datetime.utcnow()#hour now
    hour_1 = hour - datetime.timedelta(hours=1)#hour 1 hour ago
    #hour_2 = hour - datetime.timedelta(hours=2)#hour 2 hours ago
    date_to_display = hour.strftime('%D %H')#change format (YYYY:HH)
    date_to_display_1 = hour_1.strftime('%D %H')
    #date_to_display_2 = hour_2.strftime('%D %H')
    hour = hour.strftime('%Y%H')#change format (YYYY:HH)
    hour_1 = hour_1.strftime('%Y%H')
    #hour_2 = hour_2.strftime('%Y%H')
    date = hour[:4]+day_of_year+hour[4:]#change format(YYYYDDDHH)
    date_1 = hour_1[:4]+day_of_year_1+hour_1[4:]
    #date_2 = hour_2[:4]+day_of_year_2+hour_2[4:]

	
    good_files = []
    for minute in minutes:
        good_files.append(dr+date+minute+image_suffix)
        good_files.append(dr+date+minute+image_suffix_2)
        good_files.append(dr+date_1+minute+image_suffix)
        good_files.append(dr+date_1+minute+image_suffix_2)
        #good_files.append(dr+date_2+minute+image_suffix)
        #good_files.append(dr+date_2+minute+image_suffix_2)
	
	
	
    files = os.popen('ls '+dr+'*.jpg*').read().split('\n')[:-1]
    for i,pl in enumerate(files):
        if pl not in good_files:
            os.system('rm -f '+pl)
	
    for minute in minutes:
        if not (os.access(dr+date+minute+image_suffix,os.R_OK)):
            cmd='wget --timeout=5 -t 1 -P \"'+dr+'\" https://cdn.star.nesdis.noaa.gov/GOES19/ABI/SECTOR/ssa/GEOCOLOR/'+date+minute+image_suffix 
            os.system(cmd)
        if (os.access(dr+date+minute+image_suffix,os.R_OK)):
            edit_images([dr+date+minute+image_suffix],[date_to_display+':'+minute])
        '''if not (os.access(dr+date_1+minute+image_suffix,os.R_OK)):
            cmd='wget --timeout=5 -t 1 -P \"'+dr+'\" https://cdn.star.nesdis.noaa.gov/GOES19/ABI/SECTOR/ssa/GEOCOLOR/'+date_1+minute+image_suffix 
            os.system(cmd)
        if (os.access(dr+date_1+minute+image_suffix,os.R_OK)):
            edit_images([dr+date_1+minute+image_suffix],[date_to_display_1+':'+minute])
        if not (os.access(dr+date_2+minute+image_suffix,os.R_OK)):
            cmd='wget --timeout=10 -t 1 -P \"'+dr+'\" https://cdn.star.nesdis.noaa.gov/GOES19/ABI/SECTOR/ssa/GEOCOLOR/'+date_2+minute+image_suffix 
            os.system(cmd)
        if (os.access(dr+date_2+minute+image_suffix,os.R_OK)):
            edit_images([dr+date_2+minute+image_suffix],[date_to_display_2+':'+minute])'''


