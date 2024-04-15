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
import numpy as np
import time

#OCM customized allsky images
#pwielgor@camk.edu.pl, 8.02.2024

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
    
    img = allsky_shared.image[10:990,290:1270]
    if gray:
        img = np.mean(img,axis=2)
        
    image = ndimage.rotate(img, -30, reshape=False)
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
    image_suffix = '_GOES16-ABI-ssa-GEOCOLOR-7200x4320.jpg'
    image_suffix_2 = '_GOES16-ABI-ssa-GEOCOLOR-600x600.jpg'
    minutes = ['00','10','20','30','40','50']
    czas = time.strftime('%Y/%m/%d %H:%M:%S',time.gmtime())
    night = czas.split(' ')[0].replace('/','',2)
    day_of_year = str(datetime.datetime.utcnow().timetuple().tm_yday)#day of year now
    day_of_year_1 = str((datetime.datetime.utcnow()-datetime.timedelta(hours=1)).timetuple().tm_yday)#day of year one hour ago
    #day_of_year_2 = str((datetime.datetime.utcnow()-datetime.timedelta(hours=2)).timetuple().tm_yday)#day of year two hours ago
    if int(day_of_year) < 100:
        day_of_year='0'+day_of_year
		
    if int(day_of_year_1) < 100:
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
            cmd='wget --timeout=5 -t 1 -P \"'+dr+'\" https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR/ssa/GEOCOLOR/'+date+minute+image_suffix 
            os.system(cmd)
        if (os.access(dr+date+minute+image_suffix,os.R_OK)):
            edit_images([dr+date+minute+image_suffix],[date_to_display+':'+minute])
        '''if not (os.access(dr+date_1+minute+image_suffix,os.R_OK)):
            cmd='wget --timeout=5 -t 1 -P \"'+dr+'\" https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR/ssa/GEOCOLOR/'+date_1+minute+image_suffix 
            os.system(cmd)
        if (os.access(dr+date_1+minute+image_suffix,os.R_OK)):
            edit_images([dr+date_1+minute+image_suffix],[date_to_display_1+':'+minute])
        if not (os.access(dr+date_2+minute+image_suffix,os.R_OK)):
            cmd='wget --timeout=10 -t 1 -P \"'+dr+'\" https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR/ssa/GEOCOLOR/'+date_2+minute+image_suffix 
            os.system(cmd)
        if (os.access(dr+date_2+minute+image_suffix,os.R_OK)):
            edit_images([dr+date_2+minute+image_suffix],[date_to_display_2+':'+minute])'''


