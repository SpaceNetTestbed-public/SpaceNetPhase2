#! /bin/bash

while true
do
	timestamp=$(date +%s)
	echo $timestamp
	wget -O "./starlink_tles/starlink_${timestamp}" https://celestrak.com/NORAD/elements/supplemental/starlink.txt
	wget -O "./oneweb_tles/oneweb_${timestamp}" https://celestrak.com/NORAD/elements/supplemental/oneweb.txt
	sleep 86400
done
