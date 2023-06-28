import socket
import time
import subprocess
import threading
import os
import sys
import control_mgs_pb2 as ControlMsg
import mc_msgs_pb2 as MCMsgs
import networkx as nx

import matplotlib.pyplot as plt
import bellmanford as bf

from socket import *

def main():
    actual_sat_number_to_counter = []
    file3 = open('satellites_num.txt', 'r')
    Lines = file3.readlines()
    for line in Lines:
        actual_sat_number_to_counter.append(line.strip())

    file2 = open('../controller/allnodes.txt', 'r')
    Lines = file2.readlines()[3:]
    prev_sat = [-1 for i in range(100)]
    count, count2 = 0, 0
    current_second = -1
    for line in Lines:
        # print line
        timestamp, gs, sat = line.strip().split("\t")
        if current_second != -1:
            if int((timestamp.split(" ")[1]).split(":")[2]) - current_second == 1 or int((timestamp.split(" ")[1]).split(":")[2]) - current_second == -59:
                current_second =  int((timestamp.split(" ")[1]).split(":")[2])
                # print current_second
                time.sleep(1)
        else:
            current_second =  int((timestamp.split(" ")[1]).split(":")[2])
            # print current_second

        if int(sat) != prev_sat[int(gs)]:
            count +=1
            print timestamp, gs, sat
            prev_sat[int(gs)] = int(sat)
            if "STARLINK-"+str(sat) in actual_sat_number_to_counter and timestamp != "2021-12-01 15:43:58":
                # print timestamp, gs, sat
                msg                     = MCMsgs.mega_constellation_msg()
                msg.message_type            =  3
                msg.message_command         = "ip route"
                msg.message_receiver        = "all"
                msg.gs_name                 = gs
                msg.gs_ip                   = "0.0.0.0"
                msg.last_hop_satellite_name = sat
                msg.last_hop_satellite_ip   = "0.0.0.0"
                msg.change_route_time       = timestamp

                serverAddressPort=("127.0.0.1", 20001)
                UDPClientSocket = socket(family=AF_INET, type=SOCK_DGRAM)
                UDPClientSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                UDPClientSocket.sendto(msg.SerializeToString(), serverAddressPort)
                UDPClientSocket.close()

            else:
                count2 +=1
    print count, count2
main()
