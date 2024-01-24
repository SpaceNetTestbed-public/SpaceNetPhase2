import threading
import os
from .utils import *
# from datetime import *
import time

import sys
sys.path.append("../")
from mobility.read_live_tles import *
from mobility.mobility_utils import *
from mobility.read_gs import *
from routing.routing_utils import *
from routing.constellation_routing import *


def main():
    # 1 - Read configurations
    main_configurations = parse_config_file_yml(".","../controller/oneweb_config.yml")

    # 2 - Get current time
    ts = load.timescale()
    inc = 0
    time_resolution_in_seconds = 1
    y,mon,d,h,min,s = main_configurations["simulation"]["start_time"].split(",")[0],main_configurations["simulation"]["start_time"].split(",")[1],main_configurations["simulation"]["start_time"].split(",")[2],main_configurations["simulation"]["start_time"].split(",")[3],main_configurations["simulation"]["start_time"].split(",")[4],main_configurations["simulation"]["start_time"].split(",")[5]
    time_utc = ts.utc(int(y), int(mon), int(d), int(h), int(min), float(s))
    time_timestamp = convert_time_utc_to_unix(time_utc)
    print(time_utc, time_timestamp)

    # 3 - Choose the recent TLE and load satellites
    path_of_recent_TLE = get_recent_TLEs_using_timestamp("./", time_timestamp, main_configurations["constellation"]["operator"])
    print(path_of_recent_TLE)
    tle_timestamp = path_of_recent_TLE.split("_")[2]
    satellites = load.tle_file(path_of_recent_TLE)
    satellites_by_name = {sat.name.split(" ")[0]: sat for sat in satellites}
    satellites_by_index = {}

    # 4 - Read ground stations file
    ground_stations = read_gs(main_configurations["ground_stations"]["gs_file"])

    # 5 - Arrange satellites in the orbits
    orbital_data  = get_orbital_planes_classifications(path_of_recent_TLE, main_configurations["constellation"]["operator"], main_configurations["constellation"]["shell1"]["orbits"], main_configurations["constellation"]["shell1"]["sat_per_orbit"], main_configurations["constellation"]["shell1"]["inclination"])
    arranged_sats = arrange_satellites("./", orbital_data, satellites_by_name, main_configurations, time_utc ,satellites_by_index, tle_timestamp)
    satellites_by_index = arranged_sats["satellites by index"]
    satellites_sorted_in_orbits = arranged_sats["sorted satellite in orbits"]

    num_of_satellites = len(orbital_data)
    num_of_ground_stations = len(ground_stations)
    if main_configurations["simulation"]["debug"] == 1:
        print(".......... total number of satellites = ", num_of_satellites)
        print(".......... total number of ground_stations = ", num_of_ground_stations)


    if main_configurations["simulation"]["debug"] == 1:
        print("..... Phase-1: Build Topology")

    conn_mat_size = num_of_satellites + num_of_ground_stations

    old_connectivity_matrix = [[-1 for c in range(conn_mat_size)] for r in range(conn_mat_size)]
    # 6 - Loop, update the topology and save it in a file.
    while 1:
        inc += time_resolution_in_seconds
	sec = float(s)+inc
	if (sec)%60 == 0:
            min=int(min)+1
            s = 0.0
	    inc = 0
	    sec = 0.0

	if (int(min))%60 == 0 and int(min) != 0:
            h=int(h)+1
            s = 0.0
            inc = 0
            sec = 0.0
	    min = 0

        time_utc_inc = ts.utc(int(y), int(mon), int(d), int(h), int(min), sec)
        time_timestamp = convert_time_utc_to_unix(time_utc_inc)

        new_file = get_recent_TLEs_using_timestamp("./", time_timestamp, main_configurations["constellation"]["operator"])
        if  new_file != path_of_recent_TLE:
            path_of_recent_TLE = new_file
            reloaded_vars = reload_tles(path_of_recent_TLE, main_configurations)
            satellites_sorted_in_orbits = reloaded_vars["satellites_sorted_in_orbits"]
            satellites_by_name = reloaded_vars["satellites_by_name"]
            satellites_by_index = reloaded_vars["satellites_by_index"]
            num_of_satellites = reloaded_vars["num_of_satellites"]

        conn_mat_size = num_of_satellites + num_of_ground_stations
        if main_configurations["simulation"]["debug"] == 1:
            print("..... Time: ", time_utc_inc.utc_strftime())
        start = round(time.time()*1000)
        connectivity_matrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]
        if main_configurations["constellation"]["operator"] == "oneweb":
            connectivity_matrix = mininet_add_ISLs(connectivity_matrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, "SAME_ORBIT_AND_GRID_ACROSS_ORBITS_ONEWEB", time_utc_inc)
        else:
            connectivity_matrix = mininet_add_ISLs(connectivity_matrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, "SAME_ORBIT_AND_GRID_ACROSS_ORBITS", time_utc_inc)

        connectivity_matrix = mininet_add_GSLs_parallel(connectivity_matrix, satellites_by_name, satellites_by_index, ground_stations, 20, main_configurations["constellation"]["topology"]["association_criteria_GSL"], time_utc_inc, main_configurations)
        links_charateristics = calculate_link_charateristics_for_gsls_isls(connectivity_matrix, satellites_by_index, satellites_by_name, ground_stations, time_utc_inc)

        save_topology(connectivity_matrix, links_charateristics, main_configurations, str(y)+"_"+str(mon)+"_"+str(d)+"_"+str(h)+"_"+str(min)+"_"+str(sec))
        end = round(time.time()*1000)
        if main_configurations["simulation"]["debug"] == 1:
            print(".......... Connectivity Matrix for", main_configurations["constellation"]["operator"], "Constellation is created in", (end-start)/1000, "secs")


        # topology_changes = check_changes_in_topology(old_connectivity_matrix, connectivity_matrix)
        # gsl_changes = 0
        # isl_changes = 0
        # for tp_change in topology_changes:
        #    if tp_change[0] >= num_of_satellites or  tp_change[1] >= num_of_satellites:
        #        gsl_changes += 1
        #    else:
        #        isl_changes +=1
        #
        # print ".......... changes at ", time_utc_inc.utc_strftime(), len(topology_changes), gsl_changes, isl_changes
        # print len(topology_changes), gsl_changes, isl_changes
        # old_connectivity_matrix = connectivity_matrix[:]

main()
