import argparse
import re
import time
import os
import numpy as np
import datetime

import threading
import queue
from copy import copy, deepcopy

import networkx as nx
import matplotlib.pyplot as plt
import bellmanford as bf
import itertools
from multiprocessing import Process, Manager, Pool

import socket
import time
import subprocess
import threading
import wget
import shutil

import sys
sys.path.append("../")
from mobility.read_real_tles import *
from mobility.read_live_tles import *
from mobility.mobility_utils import *
from mobility.read_gs import *
from routing.routing_utils import *
from routing.constellation_routing import *
from comm_protocol.controller_main import *

gs_p0 = {
    "gid": 0,
    "name": "P0",
    "latitude_degrees_str": "55.951636",
    "longitude_degrees_str": "-3.191072",
    "elevation_m_float": 0.0,
    "cartesian_x": float(3573755.613),
    "cartesian_y": float(-199245.349),
    "cartesian_z": float(5261429.146),
}

gs_p1 = {
    "gid": 1,
    "name": "P1",
    "latitude_degrees_str": "55.941315",
    "longitude_degrees_str": "-3.237200",
    "elevation_m_float": 0.0,
    "cartesian_x": float(3574544.613),
    "cartesian_y": float(-202176.227),
    "cartesian_z": float(5260785.66),
}

gs_p2 = {
    "gid": 2,
    "name": "P2",
    "latitude_degrees_str": "55.931342",
    "longitude_degrees_str": "-3.281723",
    "elevation_m_float": 0.0,
    "cartesian_x": float(3575304.793),
    "cartesian_y": float(-205006.506),
    "cartesian_z": float(5260163.71),
}

gs_p3 = {
    "gid": 3,
    "name": "P3",
    "latitude_degrees_str": "55.934268",
    "longitude_degrees_str": "-3.374547",
    "elevation_m_float": 0.0,
    "cartesian_x": float(3574698.569),
    "cartesian_y": float(-210782.645),
    "cartesian_z": float(5260346.202),
}

gs_p4 = {
    "gid": 4,
    "name": "P4",
    "latitude_degrees_str": "55.920873",
    "longitude_degrees_str": "-3.465150",
    "elevation_m_float": 0.0,
    "cartesian_x": float(3575593.903),
    "cartesian_y": float(-216509.792),
    "cartesian_z": float(5259510.656),
}

gs_p5 = {
    "gid": 5,
    "name": "P5",
    "latitude_degrees_str": "55.899919",
    "longitude_degrees_str": "-3.548423",
    "elevation_m_float": 0.0,
    "cartesian_x": float(3577203.87),
    "cartesian_y": float(-221825.87),
    "cartesian_z": float(5258203.023),
}

gs_p6 = {
    "gid": 6,
    "name": "P6",
    "latitude_degrees_str": "55.898606",
    "longitude_degrees_str": "-3.642133",
    "elevation_m_float": 0.0,
    "cartesian_x": float(3576957.087),
    "cartesian_y": float(-227683.949),
    "cartesian_z": float(5258121.062),
}

gs_p7 = {
    "gid": 7,
    "name": "P7",
    "latitude_degrees_str": "55.887851",
    "longitude_degrees_str": "-3.727215",
    "elevation_m_float": 0.0,
    "cartesian_x": float(3577604.435),
    "cartesian_y": float(-233059.791),
    "cartesian_z": float(5257449.602),
}
ground_stations = [gs_p0, gs_p1, gs_p2, gs_p3, gs_p4, gs_p5, gs_p6, gs_p7]

number_of_orbits = 72

print(ground_stations)

satellites = load.tle_file("https://celestrak.com/NORAD/elements/starlink.txt")
satellites_by_name = {sat.name: sat for sat in satellites}
satellites_by_index = {}


# tle_url = "https://celestrak.com/NORAD/elements/supplemental/starlink.txt"
# tle_file = wget.download(tle_url, out = "./")

orbital_data = get_orbital_planes_classifications("./starlink.txt",1)

ts = load.timescale()
t = ts.now()
print(t.utc_strftime())

dt, leap_second = t.utc_datetime_and_leap_second()
newscs = ((str(dt).split(" ")[1]).split(":")[2]).split("+")[0]
date, timeN, zone = t.utc_strftime().split(" ")
year, month, day = date.split("-")
hour, minute, second = timeN.split(":")
loggedTime = str(year)+","+str(month)+","+str(day)+","+str(hour)+","+str(minute)+","+str(newscs)
t2 = ts.utc(int(year), int(month), int(day), int(hour), int(minute), float(newscs))
print(t2.tt)


satellites_sorted_in_orbits = []        #carry satellites names according to STARLINK naming conversion
for i in range(number_of_orbits):
    satellites_in_orbit = []
    cn = 0
    for data in orbital_data:
        if i == int(orbital_data[str(data)][2]):
            satellites_in_orbit.append(satellites_by_name[str(data)])
            print(i, data, orbital_data[str(data)])
            cn +=1
    print(i, cn)

    satellites_sorted_in_orbits.append(sort_satellites_in_orbit(satellites_in_orbit, t))

sat_index = -1
for orbit in satellites_sorted_in_orbits:
    for i in range(len(orbit)):
        sat_index += 1
        satellites_by_index[sat_index] = orbit[i].name
        print(sat_index, orbit[i].name)

num_of_satellites = len(orbital_data)
num_of_ground_stations = len(ground_stations)
GS_SAT_Table = [[] for i in range(num_of_satellites)]

print(num_of_satellites, num_of_ground_stations)

print(t)
print(t.utc_strftime())
dt, leap_second = t.utc_datetime_and_leap_second()
print(dt)
conn_mat_size = num_of_satellites + num_of_ground_stations

addthis = 0
while 1:
    ts = load.timescale()
    t = ts.now()
    addthis += 60
    t = ts.utc(int(2022), int(3), int(4), int(12), int(47), float(0)+addthis)
    print(t.utc_strftime())
    # print t.utc_strftime()
    connectivity_matrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]
    connectivity_matrix = mininet_add_GSLs(connectivity_matrix, satellites_by_name, satellites_by_index, ground_stations, 12, "BASED_ON_DISTANCE_ONLY_MININET", t, 1, GS_SAT_Table)
