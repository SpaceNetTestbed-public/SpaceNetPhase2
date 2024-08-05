import os
import datetime

# folder path
dir_path = r'./connectivity_matrix/starlink/'
number_of_satellites = 1483
# list to store files
# ground_stations = []

ground_stations = {}
current_sat = {}
# Iterate directory

for path in os.listdir(dir_path):
    if os.path.isfile(os.path.join(dir_path, path)):
        file = open(dir_path+"/"+path, 'r')
        Lines = file.readlines()

        for line in Lines:
            link_parameters = line.split(",")

            if int(link_parameters[0]) >= number_of_satellites:
                timetext = path.split("_")
                seconds = timetext[6].split(".")[0]
                timeval = datetime.datetime(int(timetext[1]), int(timetext[2]), int(timetext[3]), int(timetext[4]),int(timetext[5]),int(seconds))
                # print link_parameters, timeval
                if link_parameters[0] not in ground_stations:
                    ground_stations[link_parameters[0]] = []

                ground_stations[link_parameters[0]].append((timeval, link_parameters[1], link_parameters[2], link_parameters[3].strip()))

# print ground_stations["1484"]
for gs in ground_stations:
    aggregate = str(len(ground_stations[gs]))+"_"
    for values in sorted(ground_stations[gs], key=lambda x: x[0]):
        if values[0] < datetime.datetime(2022,12,5,14,11,0):
            print(values[0], gs, values[2])

    # print gs, aggregate
    # print "------"
