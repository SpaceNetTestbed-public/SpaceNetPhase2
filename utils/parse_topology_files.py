import os
import datetime

# folder path
dir_path = r'./connectivity_matrix_longest_assoication/starlink/'
number_of_satellites = 1483
# list to store files
# ground_stations = []

ground_stations = {}
# Iterate directory
for path in os.listdir(dir_path):
    # check if current path is a file
    if os.path.isfile(os.path.join(dir_path, path)):
        # print path
        file = open(dir_path+"/"+path, 'r')
        Lines = file.readlines()

        for line in Lines:
            link_parameters = line.split(",")
            if int(link_parameters[0]) >= number_of_satellites:
                timetext = path.split("_")
                seconds = timetext[6].split(".")[0]
                # print seconds
                timeval = datetime.datetime(int(timetext[1]), int(timetext[2]), int(timetext[3]), int(timetext[4]),int(timetext[5]),int(seconds))
                if link_parameters[0] not in ground_stations:
                    ground_stations[link_parameters[0]] = []

                ground_stations[link_parameters[0]].append(timeval)

current_time = previous_time = datetime.datetime(2022,12,5,14,0,0)
for gs in ground_stations:
    current_time = previous_time = datetime.datetime(2022,12,5,14,0,0)
    for times in sorted(ground_stations[gs]):
        if times < datetime.datetime(2022,12,5,14,11,0):
            current_time = times
            time_diff = current_time - previous_time
            print(gs, current_time, previous_time, time_diff.total_seconds())
            previous_time = current_time

        # print timhere
    # print "----"
# print ground_stations
                # print path, line.strip()
