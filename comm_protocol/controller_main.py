
from socket import *
import subprocess
import time
import sys
import control_mgs_pb2 as ControlMsg
import c_m_update_topology_pb2 as updateTopologyMsg
import string

#serverAddressPort   = ("172.16.255.255", 20001)
bufferSize          = 1024

def establish_connection():
    UDPClientSocket = socket(family=AF_INET, type=SOCK_DGRAM)
    UDPClientSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    #UDPClientSocket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    print ("Controller - Agent Socket is open")

    return UDPClientSocket

def create_message_to_nodes(name, to, command, args_list):
    send_msg             = ControlMsg.control_msg()
    send_msg.cmd_name    = name
    send_msg.cmd_receiver= to
    send_msg.cmd         = command
    parameters           = send_msg.cmd_param.add()
    for i in range(len(args_list)):
        if i==0:parameters.arg1 = args_list[i]
        if i==1:parameters.arg2 = args_list[i]
        if i==2:parameters.arg3 = args_list[i]
        if i==3:parameters.arg4 = args_list[i]
        if i==4:parameters.arg5 = args_list[i]
        if i==5:parameters.arg6 = args_list[i]

    return send_msg.SerializeToString()

def create_message_to_mininet(command, node1, node2):
    send_msg            = updateTopologyMsg.c_m_update_topology()
    send_msg.command    = command
    send_msg.node1_name = node1
    send_msg.node2_name = node2

    return send_msg.SerializeToString()

def send_command(message_to_send, serverAddressPort):
    # print serverAddressPort
    UDPClientSocket = socket(family=AF_INET, type=SOCK_DGRAM)
    UDPClientSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

    try:
    	UDPClientSocket.sendto(message_to_send, serverAddressPort)
        UDPClientSocket.close()
    except error as e:
        print e
        UDPClientSocket.close()

#UDPClientSocket = establish_connection()
#msg = create_message("Assign IP", "h1", "ifconfig", ["sat-eth1", "12.16.0.15/16"])
#msg = create_message("check connectivity", "sat1", "ping", ["172.16.0.11"])
#send_command(msg, ("172.16.5.197", 20001))
#time.sleep(10)
