from skyfield.api import N, W, wgs84, load, EarthSatellite
import time
from multiprocessing import Process, Manager, Pool
import itertools
import math

import sys
sys.path.append("../")
from link.link_utils import *


def calc_max_gsl_length(main_configurations):
    max_gsl_length_m = -1
    if main_configurations["constellation"] == "starlink":
        max_gsl_length_m = 1089686.4181956202;
        return max_gsl_length_m

    else:
        satellite_cone_radius_m = (main_configurations["altitude"])/math.tan(math.radians(main_configurations["elevation_angle"]))
        max_gsl_length_m =  math.sqrt(math.pow(satellite_cone_radius_m, 2) + math.pow(main_configurations["altitude"], 2))
        return max_gsl_length_m

    return max_gsl_length_m

channnel_bandwidth_downlink = 240
channnel_bandwidth_uplink = 60
number_of_users_per_cell = 4.0
density = 1.0/float(number_of_users_per_cell);

def calc_distance_gs_sat_worker(args):
    (
    ground_station,
    satellite,
    sid,
    time_t,
    max_gsl_length_m
    ) = args

    ground_station_satellites_in_range = []
    satellites_in_range = []
    distance_m = distance_between_ground_station_satellite(ground_station, satellite, time_t)
    if distance_m <= max_gsl_length_m:
        satellites_in_range.append((distance_m, sid, ground_station["gid"]))

    ground_station_satellites_in_range.append(satellites_in_range)

    return ground_station_satellites_in_range

def calc_distance_gs_sat_worker_alan(args):
    (
    ground_station,
    satellite,
    sid,
    time_t,
    max_gsl_length_m
    ) = args

    ground_station_satellites_in_range = []
    satellites_in_range = []
    distance_m = distance_between_ground_station_satellite_alan(ground_station, satellite, time_t)
    if distance_m[1] <= max_gsl_length_m:
        satellites_in_range.append((distance_m[0], distance_m[1], distance_m[2], sid, ground_station["gid"]))

    ground_station_satellites_in_range.append(satellites_in_range)

    return ground_station_satellites_in_range

def distance_between_ground_station_satellite(ground_station, satellite, t):
    bluffton = wgs84.latlon(float(ground_station["latitude_degrees_str"]), float(ground_station["longitude_degrees_str"]), ground_station["elevation_m_float"])
    geocentric = satellite.at(t)
    difference = satellite - bluffton
    topocentric = difference.at(t)

    alt, az, distance = topocentric.altaz()

    return distance.m
    #return (az,distance.m, alt)

def distance_between_ground_station_satellite_alan(ground_station, satellite, t):
    bluffton = wgs84.latlon(float(ground_station["latitude_degrees_str"]), float(ground_station["longitude_degrees_str"]), ground_station["elevation_m_float"])
    geocentric = satellite.at(t)
    difference = satellite - bluffton
    topocentric = difference.at(t)

    alt, az, distance = topocentric.altaz()

    # return distance.m
    return (az,distance.m, alt)

def distance_between_two_satellites(satellite1, satellite2, t):
    position1 = satellite1.at(t)
    position2 = satellite2.at(t)
    difference = position2 - position1

    return (position2 - position1).distance().m

def find_nearest_sat_in_adjacent_plane(constellation_planes, sat, key, satellites_by_name, t):
    adj_sat = []
    adj_planes = [-1, -1]
    adj_planes[0], adj_planes[1] = ((key-5)%360), ((key+5)%360)
    sat1 = satellites_by_name[str(sat)]
    for adj_plane in adj_planes:
        closest_sat = -1
        minimum_distance = 1000000000000000
        for sats in constellation_planes[str(adj_plane)]:
            satx = satellites_by_name[str(sats)]
            distance = distance_between_two_satellites(sat1, satx, t)
            if distance < minimum_distance:
                minimum_distance = distance
                closest_sat = sats

        if closest_sat != -1:
            adj_sat.append(closest_sat)

    return adj_sat


def get_differences_in_GSLs_between_iterations(old_list, new_list):
	differences = []
	i = 0;
	for o,n in itertools.izip(old_list,new_list):
		if o != n:
			differences.append((i, o, n))
		i += 1
	return differences

def graph_add_ISLs(G, satellites_by_name, actual_sat_number_to_counter, constellation_planes, n_orbits, n_sats_per_orbit, isl_config, t):
    if isl_config == "SAME_ORBIT_AND_GRID_ON_EDGE_SATELLITES_ONLY":
        for i in range(n_orbits):
            for j in range(n_sats_per_orbit):
                sat = i * n_sats_per_orbit + j

                # Link to the next in the orbit
                sat_same_orbit = i * n_sats_per_orbit + ((j + 1) % n_sats_per_orbit)
                G.add_edge(sat, sat_same_orbit, weight=1)

                # Grid for the edge satellites
                if j % n_sats_per_orbit == 0 or j % (n_sats_per_orbit - 1) == 0:
                    sat_adjacent_orbit = ((i + 1) % n_orbits) * n_sats_per_orbit + (j % n_sats_per_orbit)
                    G.add_edge(sat, sat_adjacent_orbit, weight=1)

    if isl_config == "SAME_ORBIT_AND_BASED_ON_DISTANCE_FOR_INTER_ORBIT":
        for i in range(len(constellation_planes.keys())):
            cur_key = constellation_planes.keys()[i]
            for j in range(len(constellation_planes[str(cur_key)])):

                # In the same plane
                satname, adj_satname = constellation_planes[str(cur_key)][j], constellation_planes[str(cur_key)][(j+1)%len(constellation_planes[str(cur_key)])]
                sat_index = actual_sat_number_to_counter.index(str(satname))
                adj_sat_index = actual_sat_number_to_counter.index(str(adj_satname))
                G.add_edge(sat_index, adj_sat_index, weight=1)

                # In the adjacent planes for the edge sats only.
                if j == 0 or j == len(constellation_planes[str(cur_key)])-1:
                    sat_adjacent_orbit = find_nearest_sat_in_adjacent_plane(constellation_planes, str(satname), int(cur_key), satellites_by_name, t)
                    sat_adjacent_orbit_index1 = actual_sat_number_to_counter.index(str(sat_adjacent_orbit[0]))
                    sat_adjacent_orbit_index2 = actual_sat_number_to_counter.index(str(sat_adjacent_orbit[1]))

                    G.add_edge(sat_index, sat_adjacent_orbit_index1, weight=1)
                    G.add_edge(sat_index, sat_adjacent_orbit_index2, weight=1)
    return G

def find_adjacent_orbit_sat(current_plane, current_sat, adj_plane, satellites_sorted_in_orbits, satellites_by_name, t):
    adj_plane_sats = satellites_sorted_in_orbits[adj_plane]
    nearest_sat_in_adj_plane = -1
    min_distance = 1000000000000000

    for i in range(len(adj_plane_sats)):
        distance = distance_between_two_satellites(current_sat, adj_plane_sats[i], t)
        if distance < min_distance:
            min_distance = distance
            nearest_sat_in_adj_plane = adj_plane_sats[i]


    return nearest_sat_in_adj_plane.name.split(" ")[0]

def mininet_add_ISLs(connectivity_matrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, isl_config, t):
    n_orbits = len(satellites_sorted_in_orbits)
    total_sat_now = 0
    if isl_config == "SAME_ORBIT_AND_GRID_ACROSS_ORBITS":
        for i in range(len(satellites_sorted_in_orbits)):
            n_sats_per_orbit = len(satellites_sorted_in_orbits[i])
            for j in range(n_sats_per_orbit):
                sat = total_sat_now + j
                # Link to the next in the orbit
                sat_same_orbit = total_sat_now + ((j + 1) % n_sats_per_orbit)
                # print ("Intra-Orbit connection between ",i,j, total_sat_now, sat, sat_same_orbit)
                connectivity_matrix[sat][sat_same_orbit] = 1
                connectivity_matrix[sat_same_orbit][sat] = 1

                current_sat = satellites_by_index[sat]
                current_sat = satellites_by_name[str(current_sat)]

                # Grid for the edge satellites
                sat_adjacent_orbit_1 = find_adjacent_orbit_sat(i, current_sat, (i+1)%n_orbits, satellites_sorted_in_orbits, satellites_by_name, t)
                sat_adjacent_orbit_1 = satellites_by_index.keys()[satellites_by_index.values().index(str(sat_adjacent_orbit_1))]
                sat_adjacent_orbit_2 = find_adjacent_orbit_sat(i, current_sat, (i-1)%n_orbits, satellites_sorted_in_orbits, satellites_by_name, t)
                sat_adjacent_orbit_2 = satellites_by_index.keys()[satellites_by_index.values().index(str(sat_adjacent_orbit_2))]

                connectivity_matrix[sat][sat_adjacent_orbit_1] = 1
                connectivity_matrix[sat_adjacent_orbit_1][sat] = 1

                connectivity_matrix[sat][sat_adjacent_orbit_2] = 1
                connectivity_matrix[sat_adjacent_orbit_2][sat] = 1

            total_sat_now += n_sats_per_orbit

    return connectivity_matrix

def mininet_add_GSLs(connectivity_matrix, satellites_by_name, satellites_by_index, ground_stations, number_of_threads, association_criteria, t, main_configurations):
    max_gsl_length_m = calc_max_gsl_length(main_configurations)
    if main_configurations["Debug"] == 1:
        print ".......... Maximum GSL links for", main_configurations["constellation"], "Constellation is ", max_gsl_length_m, " meters"

    if max_gsl_length_m == -1:
        if main_configurations["Debug"] == 1:
            print ("[Mininet_add_GSLs] --- check the max GSL length variable ")
            return ;
    # find all satellites in range for each ground station.
    list_args = []
    for ground_station in ground_stations:
        satellites_in_range = []
        for sid in range(len(satellites_by_index)):
            list_args.append((ground_station, satellites_by_name[str(satellites_by_index[sid])], sid, t, max_gsl_length_m))


    # print association_criteria
    if association_criteria == "BASED_ON_DISTANCE_ONLY_MININET" or association_criteria == "BASED_ON_LONGEST_ASSOCIATION_TIME" :
        pool = Pool(number_of_threads)
        ground_station_satellites_in_range_temporary = pool.map(calc_distance_gs_sat_worker, list_args)
        pool.close()
        pool.join()

    if association_criteria == "BASED_ON_DISTANCE_ONLY_MININET_ALAN":
        # print "Im ahere"
        pool = Pool(number_of_threads)
        ground_station_satellites_in_range_temporary = pool.map(calc_distance_gs_sat_worker_alan, list_args)
        pool.close()
        pool.join()

    # Find the best satellite
    if association_criteria == "BASED_ON_DISTANCE_ONLY_MININET":
        return M_gs_sat_association_criteria_BasedOnDistance(connectivity_matrix, ground_station_satellites_in_range_temporary, ground_stations, len(satellites_by_index), t)

    if association_criteria == "BASED_ON_DISTANCE_ONLY_MININET_ALAN":
        return M_gs_sat_no_association_criteria(connectivity_matrix, ground_station_satellites_in_range_temporary, ground_stations, len(satellites_by_index), t, satellites_by_index)

    if association_criteria == "BASED_ON_LONGEST_ASSOCIATION_TIME":
        return M_gs_sat_association_criteria_MaxAssociationTime(connectivity_matrix, ground_station_satellites_in_range_temporary, ground_stations, len(satellites_by_index), satellites_by_index, satellites_by_name, max_gsl_length_m, t)

    return -1


def M_gs_sat_no_association_criteria(connectivity_matrix, all_gs_satellites_in_range, ground_stations, num_of_satellites, t, satellites_by_index):
    ground_station_satellites_in_range = []

    for inrange_sat in all_gs_satellites_in_range:
        if len(inrange_sat[0]) != 0:
            ground_station_satellites_in_range.append(inrange_sat[0][0])

    # for gid in range(len(ground_stations)):
    for (az, distance_m, alt, sid, gr_id) in ground_station_satellites_in_range:
        # if gid == 0:
        # print az, distance_m, alt, sid, gr_id
        connectivity_matrix[sid][num_of_satellites+0] = 1
        connectivity_matrix[num_of_satellites+0][sid] = 1

        # connectivity_matrix[sid][num_of_satellites+1] = 1
        # connectivity_matrix[num_of_satellites+1][sid] = 1
        print "best distance ",0, sid, satellites_by_index[sid], distance_m, az, alt
        # print "best distance ",1, sid, distance_m, az, alt

    return connectivity_matrix

def last_visible_satellite(ground_station, all_gs_satellites_in_range, number_of_satellites, satellites_by_index, satellites_by_name, max_gsl_length_m, t):

    step = 10       #in seconds

    dt, leap_second = t.utc_datetime_and_leap_second()
    newscs = ((str(dt).split(" ")[1]).split(":")[2]).split("+")[0]
    date, timeN, zone = t.utc_strftime().split(" ")
    year, month, day = date.split("-")
    hour, minute, second = timeN.split(":")
    loggedTime = str(year)+","+str(month)+","+str(day)+","+str(hour)+","+str(minute)+","+str(newscs)


    ts = load.timescale()
    loop_t = ts.utc(int(year), int(month), int(day), int(hour), int(minute), float(newscs))

    # print loop_t

    visible_sats = []
    for entry in all_gs_satellites_in_range:
        for val in entry:
            if len(val) > 0:
                if int(ground_station["gid"]) == int(val[0][2]):
                    visible_sats.append(val[0][1])

    number_of_visible_sats = len(visible_sats)

    cnt = 0
    while number_of_visible_sats > 1:
        loop_t = ts.utc(int(year), int(month), int(day), int(hour), int(minute), float(newscs)+cnt)
        number_of_visible_sats = 0
        new_visible_sats = []
        for sat in visible_sats:
            satellite_name = satellites_by_index[sat]
            distance = distance_between_ground_station_satellite(ground_station, satellites_by_name[satellite_name], loop_t)
            if distance <= max_gsl_length_m:
                number_of_visible_sats += 1
                new_visible_sats.append(sat)

        visible_sats = new_visible_sats[:]
        cnt += step

    if len(visible_sats) == 1:
        ground_station["next_update"] = loop_t.tt
        return (satellites_by_index[visible_sats[0]], visible_sats[0])

    return -1

def M_gs_sat_association_criteria_MaxAssociationTime(connectivity_matrix, ground_station_satellites_in_range_temporary, ground_stations, num_of_satellites, satellites_by_index, satellites_by_name, max_gsl_length_m, t):
    for gs in ground_stations:
        if t.tt > gs["next_update"] or gs["next_update"] == "":
            chosen_satellite = last_visible_satellite(gs, ground_station_satellites_in_range_temporary, num_of_satellites, satellites_by_index, satellites_by_name, max_gsl_length_m, t)
            if chosen_satellite != -1:
                print "....... Current time = ", t.tt," GS#", gs["gid"], " is associated with SAT#", chosen_satellite[0]," which is named as ", chosen_satellite[1], ". The next uupdate time will be ", gs["next_update"]
                connectivity_matrix[num_of_satellites+gs["gid"]][chosen_satellite[1]] = 1
                connectivity_matrix[chosen_satellite[1]][num_of_satellites+gs["gid"]] = 1
            else:
                print gs["gid"], -1
        else:
            print "....... No updates = ", t.tt
            continue

    return connectivity_matrix


def M_gs_sat_association_criteria_BasedOnDistance(connectivity_matrix, all_gs_satellites_in_range, ground_stations, num_of_satellites, t):
    gsl_snr = [0 for i in range(len(ground_stations))]
    gsl_latency = [0 for i in range(len(ground_stations))]
    ground_station_satellites_in_range = []

    for inrange_sat in all_gs_satellites_in_range:
        if len(inrange_sat[0]) != 0:
            ground_station_satellites_in_range.append(inrange_sat[0][0])

    # USE CASE 1 -- REMOVE for general run
    # chosen_sid_forAlan = -1
    # ######################################
    for gid in range(len(ground_stations)):
        chosen_sid = -1
        best_distance_m = 1000000000000000
        for (distance_m, sid, gr_id) in ground_station_satellites_in_range:
            # print t.utc_strftime(), az, distance_m, alt, sid, gr_id
            if gid == gr_id:
                # if gid != 1: # USE CASE 1 -- REMOVE for general run
                if distance_m < best_distance_m:
                    chosen_sid = sid
                    best_distance_m = distance_m
                # USE CASE 1 -- REMOVE for general run
                # if gid == 1:
                #     if sid == chosen_sid_forAlan:
                #         chosen_sid = sid
                #         best_distance_m = distance_m
                ######################################
        if chosen_sid != -1:
            # USE CASE 1 -- REMOVE for general run
            #if gid == 0:
            #    chosen_sid_forAlan = chosen_sid
            ######################################

            connectivity_matrix[chosen_sid][num_of_satellites+gid] = 1
            connectivity_matrix[num_of_satellites+gid][chosen_sid] = 1
            # if gid == 1:
            #     chosen_sid = chosen_sid_forAlan
            #     connectivity_matrix[chosen_sid][num_of_satellites+gid] = 1
            #     connectivity_matrix[num_of_satellites+gid][chosen_sid] = 1

            #print "best distance ",gid, chosen_sid, best_distance_m
            gsl_snr[gid] = calc_gsl_snr_given_distance(best_distance_m)
            gsl_latency[gid] = best_distance_m/299792458            #speed of light
            # print "best distance ",gid, chosen_sid, best_distance_m, gsl_latency[gid]

    return connectivity_matrix

def M_gs_sat_association_criteria_BasedOnDistance_alan(connectivity_matrix, all_gs_satellites_in_range, ground_stations, num_of_satellites, t):
    gsl_snr = [0 for i in range(len(ground_stations))]
    gsl_latency = [0 for i in range(len(ground_stations))]
    ground_station_satellites_in_range = []

    for inrange_sat in all_gs_satellites_in_range:
        if len(inrange_sat[0]) != 0:
            ground_station_satellites_in_range.append(inrange_sat[0][0])

    # USE CASE 1 -- REMOVE for general run
    chosen_sid_forAlan = -1
    # ######################################
    for gid in range(len(ground_stations)):
        chosen_sid = -1
        best_distance_m = 1000000000000000
        for (distance_m, sid, gr_id) in ground_station_satellites_in_range:
            # print t.utc_strftime(), az, distance_m, alt, sid, gr_id
            if gid == gr_id:
                if gid != 1: # USE CASE 1 -- REMOVE for general run
                    if distance_m < best_distance_m:
                        chosen_sid = sid
                        best_distance_m = distance_m
                # USE CASE 1 -- REMOVE for general run
                if gid == 1:
                    if sid == chosen_sid_forAlan:
                        chosen_sid = sid
                        best_distance_m = distance_m
                ######################################
        if chosen_sid != -1:
            # USE CASE 1 -- REMOVE for general run
            if gid == 0:
               chosen_sid_forAlan = chosen_sid
            ######################################

            connectivity_matrix[chosen_sid][num_of_satellites+gid] = 1
            connectivity_matrix[num_of_satellites+gid][chosen_sid] = 1
            if gid == 1:
                chosen_sid = chosen_sid_forAlan
                connectivity_matrix[chosen_sid][num_of_satellites+gid] = 1
                connectivity_matrix[num_of_satellites+gid][chosen_sid] = 1

            #print "best distance ",gid, chosen_sid, best_distance_m
            gsl_snr[gid] = calc_gsl_snr_given_distance(best_distance_m)
            gsl_latency[gid] = best_distance_m/299792458            #speed of light
            # print "best distance ",gid, chosen_sid, best_distance_m, gsl_latency[gid]

    return connectivity_matrix

# def M_gs_sat_association_criteria_MaxAssoTime(ground_station, satellites, tles, simulation_time, step, bestSatPerInterval):
#
# 	"""
# 	Ground station, Satellite selection criteria function based on maximizing
# 	the association time.
#
# 	The GS will associate with a satellite once it appears in Horizon and will
# 	remain attached to the same satellites until it disappear (no Line of Sight)
#
# 	Param:
# 	- ground_station: The actual ground station to which the best satellite will be identified
# 	- satellites: List of all satellites in the constellation
# 	- Tles: Used to get the epoch in the tles files
# 	- simulation_time: For how long the best satellite should be estimated (in seconds)
# 	- step: the frequency of calculating satellites in range (in seconds)
# 	- bestSatPerInterval: The list of all GS and Best satellites at any time
# 	"""
# 	satellites_in_range = []
# 	satellites_timeAvailability = []
# 	for i in range(0, simulation_time, step):
# 		date_str = tles["epoch"] + 0.000000115*i*100		#100*0.000000115 corresponds to one second change
# 		for sid in range(len(satellites)):
# 			distance_m = distance_m_ground_station_to_satellite(ground_station, satellites[sid], str(tles["epoch"]), str(date_str))
# 			if distance_m <= max_gsl_length_m:
# 				satellites_in_range.append((i, sid, distance_m))
#
# 	# Out of all the satellites_in_range, find the longest attached satellite for each time step
#
# 	for i in range(len(satellites)):
# 		min_time = 10000000
#                 max_time = 0
#                 distance_AtMinTime = 0
#                 distance_AtMaxTime = 0
#                 availabilityCount = 0
#
# 		for (time_step, sat, distance, elevation) in satellites_in_range:
# 			if sat == i:
#                                 availabilityCount += 1
#                                 if time_step < min_time:
#                                         min_time = time_step
#                                         distance_AtMinTime = distance
#                                 if time_step > max_time:
#                                         max_time = time_step
#                                         distance_AtMaxTime = distance
#
#                 satellites_timeAvailability.append((i, min_time, max_time, distance_AtMinTime, distance_AtMaxTime, availabilityCount))
#
# 	for i in range (0, simulation_time, step):
#                 satMaxTime = 0
#                 appearCnt = 0
#                 distance_AtMin = 0
#                 distance_AtMax = 0
#                 bestSat = 0
#                 for (sat, min_t, max_t, d_AtMin, d_AtMax, avaCnt) in satellites_timeAvailability:
#                         if i == min_t:
#                                 if max_t > satMaxTime and (max_t-min_t)/step == avaCnt-1:
#                                         satMaxTime = max_t
#                                         appearCnt = avaCnt
#                                         distance_AtMin = d_AtMin
#                                         distance_AtMax = d_AtMax
#                                         bestSat = sat
#
#                 bestSatPerInterval.append((ground_station["gid"], i, bestSat, satMaxTime, appearCnt, distance_AtMin, distance_AtMax))
# 		print ground_station["gid"], i, bestSat, satMaxTime, appearCnt, distance_AtMin, distance_AtMax
#
# 	return bestSatPerInterval


def calculate_link_charateristics_for_gsls_isls(connectivity_matrix, satellites_by_index, satellites_by_name, ground_stations, t):
    matrix_size = len(satellites_by_index)+len(ground_stations)
    latency_matrix = [[0.0 for c in range(matrix_size)] for r in range(matrix_size)]
    throughput_matrix = [[0.0 for c in range(matrix_size)] for r in range(matrix_size)]

    for i in range(len(connectivity_matrix)):
        for j in range(len(connectivity_matrix[i])):
            # print i, j
            # print satellites_by_index[i], satellites_by_index[j]
            if connectivity_matrix[i][j] == 1 and i < len(satellites_by_index) and j < len(satellites_by_index):
                distance_meters             = distance_between_two_satellites(satellites_by_name[str(satellites_by_index[i])], satellites_by_name[str(satellites_by_index[j])], t)
                latency_matrix[i][j]        = ((distance_meters)/299792458.0)*1000                                           #speed of light
                throughput_matrix[i][j]     = 500            #20Gbps

            if connectivity_matrix[i][j] == 1 and i >= len(satellites_by_index) and j < len(satellites_by_index):
                distance_meters             = distance_between_ground_station_satellite(ground_stations[i-len(satellites_by_index)], satellites_by_name[str(satellites_by_index[j])], t)
                latency_matrix[i][j]        = ((distance_meters)/299792458.0)*1000            #speed of light
                # snr                         = calc_gsl_snr_given_distance(distance_meters)
                snr                         = calc_gsl_snr(satellites_by_name[str(satellites_by_index[j])], ground_stations[i-len(satellites_by_index)], t, distance_meters, "uplink")
                channel_width               = channnel_bandwidth_downlink
                throughput_matrix[i][j]     = channel_width*(math.log(1+snr)/math.log(2))

                if i-len(satellites_by_index) == 1:
                    snr                         = calc_gsl_snr(satellites_by_name[str(satellites_by_index[j])], ground_stations[i-len(satellites_by_index)], t, distance_meters, "downlink")
                    channel_width               = channnel_bandwidth_downlink
                    throughput_matrix[i][j]     = channel_width*(math.log(1+snr)/math.log(2))
                    # print "inside if ", snr, throughput_matrix[i][j], latency_matrix[i][j], distance_meters, i, j

                # print "Uplink", snr, throughput_matrix[i][j], latency_matrix[i][j], distance_meters, i, j

            if connectivity_matrix[i][j] == 1 and i < len(satellites_by_index) and j >= len(satellites_by_index):
                distance_meters             = distance_between_ground_station_satellite(ground_stations[j-len(satellites_by_index)], satellites_by_name[str(satellites_by_index[i])], t)
                latency_matrix[i][j]        = ((distance_meters)/299792458.0)*1000            #speed of light
                # snr                         = calc_gsl_snr_given_distance(distance_meters)
                snr                         = calc_gsl_snr(satellites_by_name[str(satellites_by_index[i])], ground_stations[j-len(satellites_by_index)], t, distance_meters, "downlink")
                throughput_matrix[i][j]     = channnel_bandwidth_downlink*(math.log(1+snr)/math.log(2))
                # print "Donwlink", snr, throughput_matrix[i][j], latency_matrix[i][j], distance_meters, i, j

    return {
                "latency_matrix": latency_matrix,
                "throughput_matrix": throughput_matrix
            }

###################################################
###################################################
