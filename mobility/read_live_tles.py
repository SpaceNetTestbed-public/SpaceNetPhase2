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
from mobility_utils import *

def get_orbital_planes(tle_filename, shell_num):
    orbital_data = {}
    tle_file = open(tle_filename, 'r')
    Lines = tle_file.readlines()

    # each iteration we read three lines at once
    for i in range(0,len(Lines),3):
        tle_second_line = list(filter(None, Lines[i+2].strip("\n").split(" ")))

        if shell_num == 1:
            if float(tle_second_line[2]) < 53.2: #Inclination of shell 1 should be 53.0 degrees
                orbital_num = math.floor(float(tle_second_line[3])/5.0)
                orbital_data[Lines[i].strip()] = (tle_second_line[2], tle_second_line[3], orbital_num) #Satellite name: (Inclination, Longitude of the ascending node, orbital number)
                # print Lines[i].strip(), (tle_second_line[2], tle_second_line[3], orbital_num)
    return orbital_data

def get_orbital_planes_classifications(tle_filename, shell_num):

    data_orbits                 = {}
    number_of_orbits            = 72
    number_of_sats_per_orbits   = 22

    dump_orbital_data           = {"Satellites": [], "Inclination": [], "Longitude of the ascending node": [], "Mean anomaly": [], "elec": [], "argu": []}

    print tle_filename
    tle_file = open(tle_filename, 'r')
    Lines = tle_file.readlines()

    # First, we dump the TLE files into the dump_orbital_data variable
    # We read the three lines by three lines, and save satellite names, inclination and Longitude of the ascending node
    for i in range(0,len(Lines),3):
        tle_second_line = list(filter(None, Lines[i+2].strip("\n").split(" ")))
        # print tle_second_line

        if shell_num == 1:
            if float(tle_second_line[2]) < 53.1: #Inclination of shell 1 should be 53.0 degrees
                dump_orbital_data["Satellites"].append(Lines[i].strip())
                dump_orbital_data["Inclination"].append(tle_second_line[2])
                dump_orbital_data["Longitude of the ascending node"].append(tle_second_line[3])
                dump_orbital_data["elec"].append(tle_second_line[4])
                dump_orbital_data["argu"].append(tle_second_line[5])
                dump_orbital_data["Mean anomaly"].append(tle_second_line[6])

    list_of_values = [-1 for c in range(len(dump_orbital_data["Longitude of the ascending node"]))]
    for i in range(0, len(dump_orbital_data["Longitude of the ascending node"])):
        list_of_values[i] = float(dump_orbital_data["Longitude of the ascending node"][i])

    print len(dump_orbital_data["Longitude of the ascending node"])
    breaks = jenkspy.jenks_breaks(list_of_values, nb_class=number_of_orbits)
    totalsatellites = 0
    for b in range(1, len(breaks)):
        upperBound_of_class = float(breaks[b])
        lowerBound_of_class = float(breaks[b-1])
        class_num = b-1
        # print "Class -------------------- "+str(class_num)
        count_sats_per_orbit = 0

        for i,j in itertools.izip(range(len(dump_orbital_data["Satellites"])), range(len(dump_orbital_data["Longitude of the ascending node"]))):
            if b == 1:
                if float(dump_orbital_data["Longitude of the ascending node"][j]) <= upperBound_of_class and float(dump_orbital_data["Longitude of the ascending node"][j]) >= lowerBound_of_class:
                    # print dump_orbital_data["Satellites"][i], dump_orbital_data["Longitude of the ascending node"][j]
                    data_orbits[dump_orbital_data["Satellites"][i]] = ("53.0", dump_orbital_data["Longitude of the ascending node"][j], class_num, class_num, dump_orbital_data["elec"][j], dump_orbital_data["argu"][j], dump_orbital_data["Mean anomaly"][j])#Satellite name: (Inclination, Longitude of the ascending node, orbital number)
                    count_sats_per_orbit += 1
            else:
                if float(dump_orbital_data["Longitude of the ascending node"][j]) <= upperBound_of_class and float(dump_orbital_data["Longitude of the ascending node"][j]) > lowerBound_of_class:
                    data_orbits[dump_orbital_data["Satellites"][i]] = ("53.0", dump_orbital_data["Longitude of the ascending node"][j], class_num, dump_orbital_data["elec"][j], dump_orbital_data["argu"][j], dump_orbital_data["Mean anomaly"][j])#Satellite name: (Inclination, Longitude of the ascending node, orbital number)
                    count_sats_per_orbit += 1
        # print "Num of Sats ----------------", count_sats_per_orbit
        totalsatellites += count_sats_per_orbit

    print totalsatellites

    return data_orbits

def get_orbital_planes_ML(tle_filename, shell_num):
    data_orbits                 = {}
    orbits                      = {}
    number_of_classes           = 0
    unclassified_sats           = []
    number_of_orbits            = 72
    number_of_sats_per_orbits   = 22
    difference_allowance        = 2
    dump_orbital_data           = {"Satellites": [], "Inclination": [], "Longitude of the ascending node": []}

    tle_file = open(tle_filename, 'r')
    Lines = tle_file.readlines()

    # First, we dump the TLE files into the dump_orbital_data variable
    # We read the three lines by three lines, and save satellite names, inclination and Longitude of the ascending node
    for i in range(0,len(Lines),3):
        tle_second_line = list(filter(None, Lines[i+2].strip("\n").split(" ")))

        if shell_num == 1:
            if float(tle_second_line[2]) < 53.1: #Inclination of shell 1 should be 53.0 degrees
                dump_orbital_data["Satellites"].append(Lines[i].strip())
                dump_orbital_data["Inclination"].append(tle_second_line[2])
                dump_orbital_data["Longitude of the ascending node"].append(tle_second_line[3])

    satellites_in_class         = [[] for c in range(len(dump_orbital_data["Satellites"]))]
    classes_data                = [[] for c in range(len(dump_orbital_data["Satellites"]))]

    for v in dump_orbital_data["Longitude of the ascending node"]:
        print v

    print "\n"
    print "len of sats:,", len(dump_orbital_data["Satellites"])

    # Second, we start to group satellites based on their Longitude of the ascending node values
    # Satellites with Longitude of the ascending node values close to each others are grouped in a similar group (we name that class)
    #
    for i in range(len(dump_orbital_data["Longitude of the ascending node"])):
        visit = False
        diffr_arry = []
        for j in range(len(dump_orbital_data["Longitude of the ascending node"])):
            diffr = abs(float(dump_orbital_data["Longitude of the ascending node"][i])-float(dump_orbital_data["Longitude of the ascending node"][j]))
            if diffr < difference_allowance:
                diffr_arry.append((dump_orbital_data["Satellites"][i], dump_orbital_data["Satellites"][j], float(dump_orbital_data["Longitude of the ascending node"][i]), float(dump_orbital_data["Longitude of the ascending node"][j]), diffr))

        for k in range(len(diffr_arry)):
            min_val = 10000000
            min_indx = -1
            for q in range(len(diffr_arry)):
                if float(diffr_arry[q][4]) < min_val:
                    min_val = float(diffr_arry[q][4])
                    min_indx = q

            if min_indx != -1:
                addthisValue = diffr_arry[min_indx]
                in_the_list1 = any(addthisValue[0] in sublist for sublist in satellites_in_class)
                if in_the_list1 == False and len(satellites_in_class[number_of_classes]) < number_of_sats_per_orbits:
                    satellites_in_class[number_of_classes].append(addthisValue[0])
                    classes_data[number_of_classes].append(addthisValue[2])
                    visit = True

                in_the_list2 = any(addthisValue[1] in sublist for sublist in satellites_in_class)
                if in_the_list2 == False and len(satellites_in_class[number_of_classes]) < number_of_sats_per_orbits:
                    satellites_in_class[number_of_classes].append(addthisValue[1])
                    classes_data[number_of_classes].append(addthisValue[3])
                    visit = True

                diffr_arry.remove(addthisValue)

        if visit == True:
            number_of_classes += 1

    counter_for_classes = 0

    # Third, we sort the groups(classes) based on the average Longitude of the ascending node value for lowest to highest
    # data_orbits is the output of this function, and it is a dict with satellite names as index and values are tuple of:
    # Satellite name: (Inclination, Longitude of the ascending node, orbital number, mean longitude, std_longtiude)
    # orbits is another dict that has tuple values of (list of satellites in this orbit, list of Longitude of the ascending node values for these satellites
    # , statistics.mean(Longitude of the ascending node values), statistics.stdev(Longitude of the ascending node values)

    for v,m in itertools.izip(satellites_in_class, classes_data):
        min_list = []
        min_list_mean = []
        min_val = 10000000
        min_indx = -1
        vist = False
        cmt = 0
        for v,m in itertools.izip(satellites_in_class, classes_data):
            if len(v) > 5:
                for i in range(0, len(m)):
                    m[i] = float(m[i])
                if statistics.mean(m) < min_val:
                    min_list = v
                    min_list_mean = m
                    min_val = statistics.mean(m)
                    min_indx = cmt
                    vist = True
            else:
                for i in range(0, len(v)):
                    if v[i] not in unclassified_sats:
                        unclassified_sats.append(v[i])

            cmt +=1

        if vist == True:
            for i in range(len(min_list)):
                data_orbits[min_list[i]] = ("53.0", min_list_mean[i], counter_for_classes, statistics.mean(min_list_mean), statistics.stdev(min_list_mean))#Satellite name: (Inclination, Longitude of the ascending node, orbital number, mean longitude, std_longtiude)

            orbits[counter_for_classes] = (min_list, min_list_mean, statistics.mean(min_list_mean), statistics.stdev(min_list_mean))

            counter_for_classes += 1
            satellites_in_class.pop(min_indx)
            classes_data.pop(min_indx)

    print "Number of classes (orbits) extracted from the TLE", counter_for_classes
    print "Number of Unclassified Satellites = ", len(unclassified_sats)

    if counter_for_classes > number_of_orbits:
        print "Info: Number of extracted orbits ("+str(counter_for_classes)+") > number of configured orbits ("+str(number_of_orbits)+") - that will be fixed now ..."
        # for nd, orbit in enumerate(orbits.values()):
        #     for va in (orbit[0]):
        #         print va
        #     print "--------->", nd, orbit[2],orbit[3], len(orbit[0])
        #
        # print "----------------------------------------------------------------------------------------------------------------------------------------------------------------"
        merge_potential = []
        merge_potential_index = []
        for nd, orbit in enumerate(orbits.values()):
            if len(orbit[0]) < 10:
                merge_potential.append(orbit)
                merge_potential_index.append(nd)

        print len(merge_potential)
        for mg in merge_potential:
            min_difference = 100000
            min_index = -1
            for nd, orbit in enumerate(orbits.values()):
                if abs(orbit[2] - mg[2]) < min_difference and abs(orbit[2] - mg[2]) != 0:
                    min_difference = abs(orbit[2] - mg[2])
                    min_index = nd

            if min_index != -1:
                # print min_difference
                for vals1, vals2 in itertools.izip(mg[0], mg[1]):
                    orbits[min_index][0].append(vals1)
                    orbits[min_index][1].append(vals2)
                    temp_list = orbits[min_index][1]
                    for i in range(0, len(temp_list)):
                        temp_list[i] = float(temp_list[i])

                    data_orbits[vals1] = ("53.0", vals2, min_index, statistics.mean(temp_list), statistics.stdev(temp_list))

                temp_list = orbits[min_index][1]
                for i in range(0, len(temp_list)):
                    temp_list[i] = float(temp_list[i])

                orbits[min_index] = (orbits[min_index][0], orbits[min_index][1], statistics.mean(temp_list), statistics.stdev(temp_list))

        for inds in merge_potential_index:
            orbits.pop(inds)

        for i,j in itertools.izip(range(number_of_orbits), orbits.keys()):
            orbits[i] = orbits.pop(j)
            # print i, j, orbits[i]
            # if i not in orbits:

        # This is for debug purposes:
        allsats = 0
        for nd, orbit in enumerate(orbits.values()):
            for sats in orbit[0]:
                print sats

            print "--------->", nd, orbit[2],orbit[3], len(orbit[0])
            allsats += len(orbit[0])

        print "total_sats = ",allsats

        # exit()

    # print orbits.keys()
    # exit()
    print unclassified_sats
    # Lastly, we use the orbit dict to classify the remaining unclassified satellites to their closest orbit.
    for satellites in unclassified_sats:
        index = dump_orbital_data["Satellites"].index(satellites)
        print "satellite: ", satellites, "Long: ", dump_orbital_data["Longitude of the ascending node"][index]
        minVal = 100000
        minIndx = -1
        for ind, orbi in enumerate(orbits.values()):
            mean_Longitude = orbi[2]
            if abs(float(mean_Longitude) - float(dump_orbital_data["Longitude of the ascending node"][index])) < minVal:
                minVal = abs(float(mean_Longitude) - float(dump_orbital_data["Longitude of the ascending node"][index]))
                minIndx = ind
                # print minVal, minIndx, orbi[0], satellites

        if minIndx != -1:
            orbits[minIndx][0].append(satellites)
            orbits[minIndx][1].append(dump_orbital_data["Longitude of the ascending node"][index])
            temp_list = orbits[minIndx][1]
            for i in range(0, len(temp_list)):
                temp_list[i] = float(temp_list[i])

            data_orbits[satellites] = ("53.0", dump_orbital_data["Longitude of the ascending node"][index], minIndx, statistics.mean(temp_list), statistics.stdev(temp_list))#Satellite name: (Inclination, Longitude of the ascending node, orbital number, mean longitude, std_longtiude)

    # This is for debug purposes:
    # allsats = 0
    # for nd, orbit in enumerate(orbits.values()):
    #     for sats in orbit[0]:
    #         print sats
    #
    #     print "--------->", nd, orbit[2],orbit[3], len(orbit[0])
    #     allsats += len(orbit[0])
    #
    # print "total_sats = ",allsats

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

# def main():
#     satellites = load.tle_file("https://celestrak.com/NORAD/elements/starlink.txt")
#     satellites_by_name = {sat.name: sat for sat in satellites}
#
#     if os.path.isfile("./starlink.txt"):
#         os.remove("./starlink.txt")
#
#     tle_url = "https://celestrak.com/NORAD/elements/supplemental/starlink.txt"
#     tle_file = wget.download(tle_url)
#
#     dump_orbital_data = get_orbital_planes("starlink.txt",1)
#     number_of_orbits = 72
#
#     ts = load.timescale()
#     t = ts.now()
#
#     satellites_sorted_in_orbits = []
#     for i in range(number_of_orbits):
#         satellites_in_orbit = []
#         for data in dump_orbital_data:
#             if i == int(data.values()[0][2]):
#                 satellites_in_orbit.append(satellites_by_name[str(data.keys()[0])])
#
#         satellites_sorted_in_orbits.append(sort_satellites_in_orbit(satellites_in_orbit, t))
#
#     satellites_by_index = []
#     sat_index = -1
#     for orbit in satellites_sorted_in_orbits:
#         for i in range(len(orbit)):
#             sat_index += 1
#             satellites_by_index.append({sat_index: orbit[i]})
#             print sat_index, orbit[i].name
#
#     print satellites_by_index
# # main()
