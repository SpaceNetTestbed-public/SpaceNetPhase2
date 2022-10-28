import wget

import sys
import schedule
import time

def get_new_TLEs():
	print("Learning Python Is Fun...Sometimes!")

schedule.every(10).seconds.do(do_nothing)

while 1:
	schedule.run_pending()
	time.sleep(1)
    

def get_new_TLEs(startDateTime, interval, constellations):
