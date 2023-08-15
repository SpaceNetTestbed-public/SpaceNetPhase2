from skyfield.api import N, W, wgs84, load, EarthSatellite
from multiprocessing import Process, Manager, Pool
import time
import networkx as nx
import matplotlib.pyplot as plt
import bellmanford as bf
import itertools
import copy
import collections
import math
import wget
import os
import statistics
import jenkspy

import sys
from .mobility_utils import *

def get_orbital_planes(tle_filename, shell_num):
    orbital_data = {}
    tle_file = open(tle_filename, 'r')
    Lines = tle_file.readlines()

    # each iteration we read three lines at once
    for i in range(0,len(Lines),3):
        tle_second_line = list([_f for _f in Lines[i+2].strip("\n").split(" ") if _f])

        if shell_num == 1:
            if float(tle_second_line[2]) < 53.2: #Inclination of shell 1 should be 53.0 degrees
                orbital_num = math.floor(float(tle_second_line[3])/5.0)
                orbital_data[Lines[i].strip()] = (tle_second_line[2], tle_second_line[3], orbital_num) #Satellite name: (Inclination, Longitude of the ascending node, orbital number)
                # print Lines[i].strip(), (tle_second_line[2], tle_second_line[3], orbital_num)
    return orbital_data

def get_orbital_planes_classifications(tle_filename, constellation, number_of_orbits, number_of_sats_per_orbits, orbits_inclination):

    data_orbits                 = {}
    dump_orbital_data           = {"Epoch": [], "Satellites": [], "Inclination": [], "RAAN": [], "Mean anomaly": [], "ecc": [], "aop": [], "Mean motion": []}

    print(tle_filename)
    tle_file = open(tle_filename, 'r')
    Lines = tle_file.readlines()

    # First, we dump the TLE files into the dump_orbital_data variable
    # We read the three lines by three lines, and save satellite names, inclination and RAAN
    for i in range(0,len(Lines),3):
        tle_first_line = list([_f for _f in Lines[i+1].strip("\n").split(" ") if _f])
        tle_second_line = list([_f for _f in Lines[i+2].strip("\n").split(" ") if _f])

        if constellation == "starlink":
            if float(tle_second_line[2]) < (orbits_inclination+0.1) and float(tle_second_line[2]) >= (orbits_inclination): #Inclination of Starlink shell 1 should be 53.0 degrees
                dump_orbital_data["Epoch"].append(tle_first_line[3])
                dump_orbital_data["Satellites"].append(Lines[i].strip())
                dump_orbital_data["Inclination"].append(tle_second_line[2])
                dump_orbital_data["RAAN"].append(tle_second_line[3])
                dump_orbital_data["ecc"].append(tle_second_line[4])
                dump_orbital_data["aop"].append(tle_second_line[5])
                dump_orbital_data["Mean anomaly"].append(tle_second_line[6])
                dump_orbital_data["Mean motion"].append(tle_second_line[7])
        else:
            if float(tle_second_line[2]) < (orbits_inclination+1) and float(tle_second_line[2]) >= (orbits_inclination): #Inclination of Starlink shell 1 should be 53.0 degrees
                dump_orbital_data["Epoch"].append(tle_first_line[3])
                dump_orbital_data["Satellites"].append(Lines[i].strip())
                dump_orbital_data["Inclination"].append(tle_second_line[2])
                dump_orbital_data["RAAN"].append(tle_second_line[3])
                dump_orbital_data["ecc"].append(tle_second_line[4])
                dump_orbital_data["aop"].append(tle_second_line[5])
                dump_orbital_data["Mean anomaly"].append(tle_second_line[6])
                dump_orbital_data["Mean motion"].append(tle_second_line[7])


    list_of_values = [-1 for c in range(len(dump_orbital_data["RAAN"]))]
    for i in range(0, len(dump_orbital_data["RAAN"])):
        list_of_values[i] = float(dump_orbital_data["RAAN"][i])

    print(len(dump_orbital_data["RAAN"]))
    breaks = jenkspy.jenks_breaks(list_of_values, n_classes=number_of_orbits)
    totalsatellites = 0
    for b in range(1, len(breaks)):
        upperBound_of_class = float(breaks[b])
        lowerBound_of_class = float(breaks[b-1])
        class_num = b-1
        # print "Class -------------------- "+str(class_num)
        count_sats_per_orbit = 0

        for i,j in zip(list(range(len(dump_orbital_data["Satellites"]))), list(range(len(dump_orbital_data["RAAN"])))):
            if b == 1:
                if float(dump_orbital_data["RAAN"][j]) <= upperBound_of_class and float(dump_orbital_data["RAAN"][j]) >= lowerBound_of_class:
                    # print dump_orbital_data["Satellites"][i], dump_orbital_data["RAAN"][j]
                    data_orbits[dump_orbital_data["Satellites"][i]] = (class_num, dump_orbital_data["Epoch"][j], str(orbits_inclination), dump_orbital_data["RAAN"][j], dump_orbital_data["ecc"][j], dump_orbital_data["aop"][j], dump_orbital_data["Mean anomaly"][j], dump_orbital_data["Mean motion"][j])#Satellite name: (Inclination, RAAN, orbital number)
                    count_sats_per_orbit += 1
            else:
                if float(dump_orbital_data["RAAN"][j]) <= upperBound_of_class and float(dump_orbital_data["RAAN"][j]) > lowerBound_of_class:
                    data_orbits[dump_orbital_data["Satellites"][i]] = (class_num, dump_orbital_data["Epoch"][j], str(orbits_inclination), dump_orbital_data["RAAN"][j], dump_orbital_data["ecc"][j], dump_orbital_data["aop"][j], dump_orbital_data["Mean anomaly"][j], dump_orbital_data["Mean motion"][j])#Satellite name: (Inclination, RAAN, orbital number)
                    count_sats_per_orbit += 1
        # print "Num of Sats ----------------", count_sats_per_orbit
        totalsatellites += count_sats_per_orbit

    print(totalsatellites)

    return data_orbits

def sort_satellites_in_orbit(satellites_in_orbit, t):
    visited_sats = []
    sorted_sats = []

    first_sat = satellites_in_orbit[0]
    sorted_sats.append(first_sat)
    visited_sats.append(first_sat.name)
    for i in range(len(satellites_in_orbit)):
        next_hop = -1
        min_distance = 1000000000000000
        for sat in satellites_in_orbit:
            if sat.name not in visited_sats:
                distance = distance_between_two_satellites(first_sat, sat,t)
                if distance < min_distance:
                    next_hop = sat
                    min_distance = distance

        if next_hop != -1:
            first_sat = next_hop
            visited_sats.append(first_sat.name)
            sorted_sats.append(first_sat)

    return sorted_sats
