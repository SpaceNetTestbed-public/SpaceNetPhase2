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
                if link_parameters[0] not in ground_stations:
                    ground_stations[link_parameters[0]] = []

                ground_stations[link_parameters[0]].append((timeval, link_parameters[1]))


for gs in ground_stations:
    current_time = previous_time = datetime.datetime(2022,12,5,14,0,0)
    current_sat  = previous_sat  = 0
    for times in sorted(ground_stations[gs], key=lambda x: x[0]):
        if times[0] < datetime.datetime(2022,12,5,14,11,0):
            current_sat = times[1]
            # print current_sat
            if current_sat != previous_sat:
                current_time = times[0]
                time_diff = current_time - previous_time
                print gs, current_time, previous_time, time_diff.total_seconds()
                previous_time = current_time
                previous_sat = current_sat
            # current_time = times
#             time_diff = current_time - previous_time
#             # print gs, current_time, previous_time, time_diff.total_seconds()
#             previous_time = current_time

# a = sorted(ground_stations["1487"], key=lambda x: x[0])
# print a
exit()
for path in os.listdir(dir_path):
    # check if current path is a file
    if os.path.isfile(os.path.join(dir_path, path)):
        # print path
        file = open(dir_path+"/"+path, 'r')
        Lines = file.readlines()

        for line in Lines:
            link_parameters = line.split(",")
            # print link_parameters
            if int(link_parameters[0]) >= number_of_satellites:
                timetext = path.split("_")
                seconds = timetext[6].split(".")[0]
                # print seconds
                timeval = datetime.datetime(int(timetext[1]), int(timetext[2]), int(timetext[3]), int(timetext[4]),int(timetext[5]),int(seconds))
                if link_parameters[0] not in ground_stations:
                    ground_stations[link_parameters[0]] = []
                    current_sat[link_parameters[0]] = ""

                if current_sat[link_parameters[0]] == "" or current_sat[link_parameters[0]] != str(link_parameters[1]):
                    if link_parameters[0] == str(1487):
                        print current_sat[link_parameters[0]], str(link_parameters[1])
                    ground_stations[link_parameters[0]].append(timeval)

print ground_stations["1487"]
current_time = previous_time = datetime.datetime(2022,12,5,14,0,0)
for gs in ground_stations:
    current_time = previous_time = datetime.datetime(2022,12,5,14,0,0)
    for times in sorted(ground_stations[gs]):
        if times < datetime.datetime(2022,12,5,14,11,0):
            current_time = times
            time_diff = current_time - previous_time
            # print gs, current_time, previous_time, time_diff.total_seconds()
            previous_time = current_time

        # print timhere
    # print "----"
# print ground_stations
                # print path, line.strip()
