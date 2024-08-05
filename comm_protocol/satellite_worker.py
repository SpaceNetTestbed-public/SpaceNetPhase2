import socket
import time
import subprocess
import threading
import os
import sys
from . import control_mgs_pb2 as ControlMsg
from . import mc_msgs_pb2 as MCMsgs

def get_intf(filename):
    Intf_file = open(filename, 'r')
    lines = Intf_file.readlines()
    list_of_Intf_IPs = []

    for i in range(len(lines)):
        intf, ip = lines[i].strip().split("\t")
        list_of_Intf_IPs.append({"Interface": intf, "IP": ip})

    return list_of_Intf_IPs

def get_all_sat_intf(list_of_Intf_IPs, satname):
    sat_intf = []
    for dct in list_of_Intf_IPs:
        if satname in dct["Interface"]:
            sat_intf.append(dct)

    return sat_intf

def get_network_address(str_ip_address):
    # Assuming /28 subnet mask
    ip_oct1, ip_oct2, ip_oct3, ip_oct4 = str_ip_address.split(".")
    net_add1= int(ip_oct1) & 255
    net_add2= int(ip_oct2) & 255
    net_add3= int(ip_oct3) & 255
    net_add4= int(ip_oct4) & 240

    return str(net_add1)+"."+str(net_add2)+"."+str(net_add3)+"."+str(net_add4)

def connection_establishment(a_mgnt_IP, a_mgnt_port):
    UDPSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPSocket.bind((a_mgnt_IP, a_mgnt_port))
    return UDPSocket

def ip_assignment_msg_handler(message_command, message_receiver, ifconfig_ip, ifconfig_interface):
    # get the satellite name. That will be used later to check if the message is sent to this satellite
    list_of_interfaces = os.listdir('/sys/class/net/')
    satname = ""
    for i in range(0, len(list_of_interfaces)):
        if "eth" in list_of_interfaces[i]:
            satname = list_of_interfaces[i].split("-")[0]

    if satname == message_receiver:
        command = ["ifconfig", ifconfig_interface, ifconfig_ip]
        with open('logs/log-'+satname+'.txt', 'a') as f:
            process = subprocess.Popen(command, stdout=f)

def iperf_msg_handler(message_command, message_receiver, iperf_destination, iperf_time):
    # get the satellite name. That will be used later to check if the message is sent to this satellite
    list_of_interfaces = os.listdir('/sys/class/net/')
    satname = ""
    for i in range(0, len(list_of_interfaces)):
        if "eth" in list_of_interfaces[i]:
            satname = list_of_interfaces[i].split("-")[0]

    if satname == message_receiver:
        command = ["iperf", "-c", iperf_destination, "-t", iperf_time]
        with open('logs/log-'+satname+'.txt', 'a') as f:
            process = subprocess.Popen(command, stdout=f)

def route_update_msg_handler(message_command, message_receiver, route_update_type, route_destination, route_next_hop, route_out_interface):
    # get the satellite name. That will be used later to check if the message is sent to this satellite
    list_of_interfaces = os.listdir('/sys/class/net/')
    satname = ""
    for i in range(0, len(list_of_interfaces)):
        if "eth" in list_of_interfaces[i]:
            satname = list_of_interfaces[i].split("-")[0]

    if satname == message_receiver:
        if route_update_type == 0: #ADD new route
            command = ["ip", "route", "add", route_destination, "via", route_next_hop, "dev", route_out_interface]

        if route_update_type == 1: #DELETE new route
            command = ["ip", "route", "del", route_destination, "via", route_next_hop, "dev", route_out_interface]

        with open('logs/log-'+satname+'.txt', 'a') as f:
            process = subprocess.Popen(command, stdout=f)

def gsl_update_msg_handler(message_command, message_receiver, gsl_update_type, gs_gateway, gs):
    if satname == message_receiver or message_receiver == "all":
        list_of_Intf_IPs = get_intf("constellation_ip_assignment.txt")
        sat_intf = get_all_sat_intf(list_of_Intf_IPs, "sat"+str(gs_gateway))

        for intf in sat_intf:
            ps = subprocess.Popen(("route","-n"),stdout=subprocess.PIPE)
            try:
                output = subprocess.check_output(('grep',get_network_address(str(intf["IP"]))),stdin=ps.stdout)
                ls_output = output.split()
                #['172.16.0.0', '0.0.0.0', '255.255.0.0', 'U', '0', '0', '0', 'enp0s8']
                command = ["ip", "route", "add", gs_ip, "via", route_next_hop_for_GS_Gateway_seen_at_this_sat(output[1]), "dev", route_out_interface_for_GS_Gateway_seen_at_this_sat(output[7])]
            except subprocess.CalledProcessError as e:
                print((e.output))

        # output = subprocess.check_output(('awk','{print $1}'),stdin=ps.stdout)


# def gsl_update_msg_handler(message_command, message_receiver, gs_name, gs_ip, last_hop_satellite_name, last_hop_satellite_ip, change_route_time, connectivity_matrix, num_of_satellites):
#     # get the satellite name. That will be used later to check if the message is sent to this satellite
#     # list_of_interfaces = os.listdir('/sys/class/net/')
#     # satname = ""
#     # for i in range(0, len(list_of_interfaces)):
#     #     if "eth" in list_of_interfaces[i]:
#     #         satname = list_of_interfaces[i].split("-")[0]
#
#     # if satname == message_receiver:
#     start = round(time.time()*1000)
#     G = nx.Graph()
#     for n in range(num_of_satellites+1):  #the last node in the graph is the ground station that propagate the update
#         G.add_node(n)
#
#     G.add_edge(gs_name, last_hop_satellite_name, weight=1)
#     for i in range(len(connectivity_matrix)):
#         for j in range(len(connectivity_matrix[i])):
#             if connectivity_matrix[i][j] == 1:
#                 G.add_edge(i, j, weight=1)
#
#     print len(G.edges())
#     path_length, path_nodes, negative_cycle = bf.bellman_ford(G, source=message_receiver, target=gs_name, weight="weight")
#     print path_nodes, path_length
#     end = round(time.time()*1000)
#     print end-start

# def gsl_update_msg_handler_trial(satname, message_command, message_receiver, gs_name, gs_ip, last_hop_satellite_name, last_hop_satellite_ip, change_route_time, connectivity_matrix, num_of_satellites):
#
#     if satname == message_receiver or message_receiver == "all":
#         gs = int(gs_name)+num_of_satellites
#         # print ("I am heree")
#         start = round(time.time()*1000)
#         G = nx.Graph()
#         for n in range(num_of_satellites+100):  #the last node in the graph is the ground station that propagate the update
#             G.add_node(n)
#
#         # print last_hop_satellite_name
#         G.add_edge(gs, int(last_hop_satellite_name), weight=1)
#         for i in range(len(connectivity_matrix)):
#             for j in range(len(connectivity_matrix[i])):
#                 if connectivity_matrix[i][j] == 1:
#                     G.add_edge(i, j, weight=1)
#
#         print len(G.edges())
#         # path_length, path_nodes, negative_cycle = bf.bellman_ford(G, source=int(satname), target=gs, weight="weight")
#         path = nx.dijkstra_path(G, int(satname), int(gs))
#         end = round(time.time()*1000)
#         # print("["+str(satname)+"]["+str(change_route_time)+"] Best route to ", str(gs_name), path_nodes, path_length, " --> it takes ", str(end-start)+" ms")
#         print("["+str(satname)+"]["+str(change_route_time)+"] Best route to ", str(gs_name), len(path), " --> it takes ", str(end-start)+" ms")
#
#         # print end-start

def main():
    UDPSocket = connection_establishment(str(sys.argv[1]), 20001)
    # file1 = open('connectivity_matrix.txt', 'r')
    # Lines = file1.readlines()
    #
    # conn_mat_size = 1451+100
    # connectivity_matrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]
    #
    # for line in Lines:
    #     i, j, conn = line.split("\t")
    #     connectivity_matrix[int(i)][int(j)] = int(conn)

    # actual_sat_number_to_counter = []
    # file3 = open('satellites_num.txt', 'r')
    # Lines = file3.readlines()
    # for line in Lines:
    #     actual_sat_number_to_counter.append(line.strip())
    #
    # file2 = open('gsl_changes.txt', 'r')
    # Lines = file2.readlines()
    # prev_sat = -1
    # for line in Lines:
    #     timed, satellite_num = line.strip().split("\t")
    #     # print satellite_num
    #     if int(satellite_num) != prev_sat:
    #         print timed, satellite_num
    #         prev_sat = int(satellite_num)
    #         if "STARLINK-"+str(satellite_num) in actual_sat_number_to_counter:
    #             val = actual_sat_number_to_counter.index("STARLINK-"+str(satellite_num))
    #             t = threading.Thread(target=gsl_update_msg_handler, args=("ip route", 10, 1+1451, "recv_msg.gs_ip", val, "last_hop_satellite_ip", timed, connectivity_matrix, 1451))
    #             t.start()
    #             t.join()
    #         else:
    #             print "STARLINK-"+str(satellite_num)+" is not in the list"
    while(True):
        bytesAddressPair = UDPSocket.recvfrom(1024)
        recv_msg = MCMsgs.mega_constellation_msg()
        recv_msg.ParseFromString(bytesAddressPair[0])
        print("Received "+str(recv_msg.message_type)+" for "+str(recv_msg.message_receiver))

        if recv_msg.message_type == 0: # IP_ASSIGNMENT
            t = threading.Thread(target=ip_assignment_msg_handler, args=(recv_msg.message_command, recv_msg.message_receiver, recv_msg.ifconfig_ip, recv_msg.ifconfig_interface))

        if recv_msg.message_type == 1: # TRAFFIC_GEN
            t = threading.Thread(target=iperf_msg_handler, args=(recv_msg.message_command, recv_msg.message_receiver, recv_msg.iperf_destination, recv_msg.iperf_time))

        if recv_msg.message_type == 2: # ROUTE_UPDATE
            t = threading.Thread(target=route_update_msg_handler, args=(recv_msg.message_command, recv_msg.message_receiver, recv_msg.route_update_type, recv_msg.route_destination, recv_msg.route_next_hop, recv_msg.route_out_interface))
            t.start()

        if recv_msg.message_type == 3: # GSL_UPDATE
            t = threading.Thread(target=gsl_update_msg_handler_trial, args=(sys.argv[1], recv_msg.message_command, recv_msg.message_receiver, recv_msg.gs_name, recv_msg.gs_ip, recv_msg.last_hop_satellite_name, recv_msg.last_hop_satellite_ip, recv_msg.change_route_time, connectivity_matrix, 1451))
            t.start()

        if recv_msg.message_type == 5: # CONN_TEST -- PING
            t = threading.Thread(target=ping_msg_handler, args=(recv_msg.message_command, recv_msg.message_receiver, recv_msg.ping_ip, recv_msg.ping_duration))


main()
