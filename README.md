# allsky
additional script to reprocess allsky images


To run allsky camera (our is Alcor ALPHEA 6CW based on ZWO ASI178MC) download the repository from https://github.com/AllskyTeam/allsky.git and install following the instructions there. Then copy the script allsky_process_ocm.py to ./allsky/scripts/modules/.

You should install NFS to have the access to /data/misc/allsky/ directory.

Your allsky is accessible under the link http://ip_address/public.php . Go to Module manager and select (by moving to the selected modules) the module ALLSKY OCM process pipeline and enable it. Data should be written to /data/misc/allsky.

The script will also download latest GOES satellite images for OCM and save in the /data/misc/satellite directory.

TBD: after the internet lost module is automatically disabled (timeout limit), it should be fixed somehow.