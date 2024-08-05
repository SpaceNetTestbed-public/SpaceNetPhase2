import sys
sys.path.append("../")
from mobility.read_live_tles import *
from mobility.mobility_utils import *
from mobility.read_gs import *
from utils.utils import *

TopologyFile="/home/mininet/simulator/constellation-simulator-main/utils/connectivity_matrix/starlink/topology_2023_06_28_13_2_26.0.txt"

print(TopologyFile)


ts = load.timescale()
path_of_recent_TLE = get_recent_TLEs_using_datetime("../utils/", "2023,06,28,13,2,26", "starlink")
orbital_data = get_orbital_planes_classifications(path_of_recent_TLE, "starlink", 72, 22, 53)
ground_stations = read_gs("../mobility/ground_stations_experiments.txt")
num_of_satellites = len(orbital_data)
num_of_ground_stations = len(ground_stations)


time_utc_inc= ts.utc(int(2023), int(06), int(28), int(13), int(2), float(26)+0) 
conn_mat_size = num_of_satellites + num_of_ground_stations
topology_path = "../utils/connectivity_matrix/starlink/"

# satnat_topology_change  = parse_connectivity_matrix_n_charateristics(time_utc_inc, conn_mat_size,topology_path)


time_components = convert_time_utc_to_ymdhms(time_utc_inc)
topology_file_found = 0
connectivity_matrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]
links_latency           = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]
links_capacity          = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]

for filename in os.listdir(topology_path):
        f = os.path.join(topology_path, filename)
        if os.path.isfile(f):
            if int(time_components[0]) == int(filename.split("_")[1]) and int(time_components[1]) == int(filename.split("_")[2]) and int(time_components[2]) == int(filename.split("_")[3]) and int(time_components[3]) == int(filename.split("_")[4]) and int(time_components[4]) == int(filename.split("_")[5]) and int(time_components[5]) == int(float(filename.split("_")[6][:-4])):
                topology_file_found = 1
                topology_file = open(f, 'r')
                lines = topology_file.readlines()
                for line in lines:
                    link_config                                                     = line.split(",")
                    connectivity_matrix[int(link_config[0])][int(link_config[1])]   = 1
                    connectivity_matrix[int(link_config[1])][int(link_config[0])]   = 1

                    links_latency[int(link_config[0])][int(link_config[1])]         = round(float(link_config[2]),0)
                    links_latency[int(link_config[1])][int(link_config[0])]         = round(float(link_config[2]),0)
                    links_capacity[int(link_config[0])][int(link_config[1])]        = round(float(link_config[3]),0)
                    links_capacity[int(link_config[1])][int(link_config[0])]        = round(float(link_config[3]),0)
                break
if topology_file_found == 0:
     print("[Error] No Topology file available ... check the simulation step resolution")
#    return -1

 #   return {
 #           "connectivity_matrix": connectivity_matrix,
 #           "links_latency":       links_latency,
 #           "links_capacity":      links_capacity
 #           }




# if satnat_topology_change == -1:
#	print ("[Error] Check the parse_connectivity_matrix_n_characteristics function")
#	exit()

