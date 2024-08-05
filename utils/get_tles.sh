#! /bin/bash

while true
do
	timestamp=$(date +%s)
	echo $timestamp
	wget -O "./starlink_tles/starlink_${timestamp}" https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle
	
	sleep 86400
done
