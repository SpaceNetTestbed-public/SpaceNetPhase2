import wget

import sys
sys.path.append("../")

from mobility.read_live_tles import *
from mobility.read_gs import *
from mobility.mobility_utils import *

def parse_config_file(filepath, filename):
    configurations = {"simulation_time(second)":0, "mode":0, "simulation_step(second)":0, "Fresh_run":False, "ground_stations":"./", "inclination":0, "constellation":"starlink", "tle_file":"", "number_of_orbits":0, "number_of_sat_per_orbit":0, "altitude":0, "elevation_angle":0, "experiment":2, "constellation_ip_range":"" , "False_run_archieve_path_foldername":"" ,"Debug":1}
    configFile = open(filepath+"/"+filename, 'r')
    configs = configFile.readlines()

    for config in configs:
        config_parameters = config.split("=")
        if config_parameters[1].strip().isdigit():
            configurations[str(config_parameters[0])]=int(config_parameters[1].strip())
        elif config_parameters[1].strip() == "False" or config_parameters[1].strip() == "True":
            if config_parameters[1].strip() == "False":
                configurations[str(config_parameters[0])] = False
            elif config_parameters[1].strip() == "True":
                configurations[str(config_parameters[0])] = True
        else:
            configurations[str(config_parameters[0])]=config_parameters[1].strip()

    return configurations

def main():
    print("run this main ..")
    satellites = load.tle_file("https://celestrak.org/NORAD/elements/supplemental/starlink.txt")


    ts = load.timescale()
    actual_time = ts.now()
    print(actual_time.utc_strftime())

    satellites_by_name = {sat.name.split(" ")[0]: sat for sat in satellites}
    satellites_by_index = {}

    data_path = "."
    number_of_orbits = 72
    number_of_sats_per_orbits = 22
    orbital_data = get_orbital_planes_classifications(data_path+"/"+"starlink"+".txt", "starlink", number_of_orbits, number_of_sats_per_orbits, 53)

    main_configurations = parse_config_file("../controller/","starlink_config.txt")

    f = open(data_path+"/sorted_satellites_within_orbit.txt", "a")
    satellites_sorted_in_orbits = []        #carry satellites names according to STARLINK naming conversion (list of lists)
    for i in range(number_of_orbits):
        sorted = []
        satellites_in_orbit = []
        cn = 0
        for data in orbital_data:
            if i == int(orbital_data[str(data)][2]):
                satellites_in_orbit.append(satellites_by_name[str(data.split(" ")[0])])
                cn +=1
        print(".......... Orbit no.    "+str(i)+"    ->  "+str(cn)+" satellites")

        sorted = sort_satellites_in_orbit(satellites_in_orbit, actual_time)
        satellites_sorted_in_orbits.append(sorted)

        for s in sorted:
            write_this = str(i)+" "+str(s.name)+" "+str(orbital_data[str(s.name)])+"\n"
            f.write(write_this)

    f.close()

# Update the satellite_by_index
    sat_index = -1
    for orbit in satellites_sorted_in_orbits:
        for i in range(len(orbit)):
            sat_index += 1
            satellites_by_index[sat_index] = orbit[i].name.split(" ")[0]

####
    ground_stations = read_gs("ground_stations_small.txt")
    num_of_satellites = len(orbital_data)
    num_of_ground_stations = len(ground_stations)

    print(".......... total number of satellites = ", num_of_satellites)
    print(".......... total number of ground_stations = ", num_of_ground_stations)
    conn_mat_size = num_of_satellites + num_of_ground_stations
    
    addthis = 0
    while 1:
        ts = load.timescale()
        t = ts.now()
        addthis += 1
        t = ts.utc(int(2022), int(7), int(25), int(15), int(15), float(0)+addthis)
        print(t.utc_strftime())
        # print t.utc_strftime()
        connectivity_matrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]
        connectivity_matrix = mininet_add_GSLs(connectivity_matrix, satellites_by_name, satellites_by_index, ground_stations, 12, "BASED_ON_LONGEST_ASSOCIATION_TIME", t, main_configurations)


main()
