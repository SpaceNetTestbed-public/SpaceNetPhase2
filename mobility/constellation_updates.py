import wget

import sys
sys.path.append("../")

from mobility.read_live_tles import *
from mobility.mobility_utils import *

def extract_starlink_shells(tle_filename, satelliteName):
    tle_file = open(tle_filename, 'r')
    Lines = tle_file.readlines()

    for i in range(0,len(Lines),3):
        tle_first_line = list([_f for _f in Lines[i].strip("\n").split(" ") if _f])[0]
        if satelliteName == tle_first_line:
            tle_second_line = list([_f for _f in Lines[i+2].strip("\n").split(" ") if _f])

            if float(tle_second_line[2]) < 53.2 and float(tle_second_line[2]) >= 53: #Inclination of Starlink shell 1 should be 53.0 degrees
                return 1
            if float(tle_second_line[2]) < 53.5 and float(tle_second_line[2]) >= 53.2: #Inclination of Starlink shell 4 should be 53.2 degrees
                return 4
            if float(tle_second_line[2]) < 71 and float(tle_second_line[2]) >= 70: #Inclination of Starlink shell 2 should be 70.0 degrees
                return 2
            if float(tle_second_line[2]) < 97.9 and float(tle_second_line[2]) >= 97.6: #Inclination of Starlink shell 3 and 5 should be 97.6 degrees
                return 3
    return 0

def constellation_updates(tle_url, ground_stations, running_time):
    satellites = load.tle_file(tle_url)
    temp_list = []

    for gs in ground_stations:
        for sat in satellites:
            d = distance_between_ground_station_satellite_alan(gs, sat, running_time)
            if d[1] <= 1089686.4181956202:
                shellnum = extract_starlink_shells("./starlink.txt", sat.name)
                dt, leap_second = running_time.utc_datetime_and_leap_second()
                newscs = ((str(dt).split(" ")[1]).split(":")[2]).split("+")[0]
                date, timeN, zone = running_time.utc_strftime().split(" ")
                year, month, day = date.split("-")
                hour, minute, second = timeN.split(":")
                loggedTime = str(year)+","+str(month)+","+str(day)+","+str(hour)+","+str(minute)+","+str(newscs)
                temp_list.append([loggedTime, d[1], d[0], d[2], gs["name"], sat.name, shellnum])

    a = sorted(temp_list, key=lambda x: x[1])
    for aa in a:
        print(aa)


def main():
    print("run this main ..")
    ts = load.timescale()
    actual_time = ts.now()
    print(actual_time.utc_strftime())
    gs_Alan = {
        "gid": 0,
        "name": "Alan-Starlink",
        "latitude_degrees_str": "51.52132683544218",
        "longitude_degrees_str": "-1.7868832746954848",
        "elevation_m_float": 0.0,
        "cartesian_x": float(3974857.483),
        "cartesian_y": float(-124004.072),
        "cartesian_z": float(4969839.203),
    }
    gs_gw = {
	"gid": 1,
	"name": "UK-Gateway",
	"latitude_degrees_str": "51.614596",
	"longitude_degrees_str": "-0.574415",
	"elevation_m_float": 0.0,
	"cartesian_x": float(3968463.039),
        "cartesian_y": float(-39786.893),
        "cartesian_z": float(4976289.428),
    }
    ground_stations = [gs_Alan, gs_gw]
    total_duration_in_seconds=1*60*60
    j = 0
    for i in range(total_duration_in_seconds):
        # j = i/float(100.0)
        j += 1
        # print j,i
        t = ts.utc(int(2022), int(11), int(2), int(12), int(24), float(8)+j)
        constellation_updates("https://celestrak.org/NORAD/elements/supplemental/starlink.txt", ground_stations, t)
        print("----------------------------------------------------------------------------------------")

main()
