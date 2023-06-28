import socket
import time
import subprocess
import threading
import os
import sys
# sys.path.append('../templates')
import control_mgs_pb2 as ControlMsg


def connection_establishment(a_mgnt_IP, a_mgnt_port):
    print a_mgnt_IP
    UDPSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPSocket.bind((a_mgnt_IP, a_mgnt_port))
    # print("The Agent is up and listening")

    return UDPSocket

def check_message(cmd_receiver, cmd_param, cmd):
    list_of_interfaces = os.listdir('/sys/class/net/')
    satname = ""
    for i in range(0, len(list_of_interfaces)):
        if "eth" in list_of_interfaces[i]:
            satname = list_of_interfaces[i].split("-")[0]

    if cmd_receiver == satname:
        param_list = []
        if cmd_param[0].arg1 != "":
            param_list.append(cmd_param[0].arg1)
            if cmd_param[0].arg2 != "":
                param_list.append(cmd_param[0].arg2)
                if cmd_param[0].arg3 != "":
                    param_list.append(cmd_param[0].arg3)
                    if cmd_param[0].arg4 != "":
                        param_list.append(cmd_param[0].arg4)
                        if cmd_param[0].arg5 != "":
                            param_list.append(cmd_param[0].arg5)
                            if cmd_param[0].arg6 != "":
                                param_list.append(cmd_param[0].arg6)
        handle_commands(cmd,param_list,satname)

def handle_commands(cmd, cmd_params,satname):
    full_command = []
    if cmd == "ifconfig":
        full_command.append("ifconfig")
        list_of_interfaces = os.listdir('/sys/class/net/')
        for p in cmd_params:
            full_command.append(p)
            # if "eth" in p and p not in list_of_interfaces:
            #     return
    if cmd == "ping":
    	full_command.append("ping")
    	for p in cmd_params:
    		full_command.append(p)

    #print full_command
    with open('logs/log-'+satname+'.txt', 'a') as f:
        process = subprocess.Popen(full_command, stdout=f)

def main():
    UDPSocket = connection_establishment(str(sys.argv[1]), 20001)
    #print "hello"
    while(True):
        bytesAddressPair = UDPSocket.recvfrom(1024)
        # print bytesAddressPair
        recv_msg = ControlMsg.control_msg()
        recv_msg.ParseFromString(bytesAddressPair[0])
        print "Received "+recv_msg.cmd+" for "+recv_msg.cmd_receiver
        t = threading.Thread(target=check_message, args=(recv_msg.cmd_receiver, recv_msg.cmd_param, recv_msg.cmd))
    	t.start()

        #print(recv_msg)

        # list_of_interfaces = os.listdir('/sys/class/net/')
        # satname = ""
        # for i in range(0, len(list_of_interfaces)):
        #     if "eth" in list_of_interfaces[i]:
        #         satname = list_of_interfaces[i].split("-")[0]
        #
        # if recv_msg.cmd_receiver != satname:
        #     #print ("The command is not fot this satellite: "+satname+". It is for satellite: "+recv_msg.cmd_receiver)
        #     continue
        #
    	# param_list = []
    	# if recv_msg.cmd_param[0].arg1 != "":
    	#     param_list.append(recv_msg.cmd_param[0].arg1)
    	#     if recv_msg.cmd_param[0].arg2 != "":
        #         param_list.append(recv_msg.cmd_param[0].arg2)
        #         if recv_msg.cmd_param[0].arg3 != "":
        #             param_list.append(recv_msg.cmd_param[0].arg3)
        #             if recv_msg.cmd_param[0].arg4 != "":
        #                 param_list.append(recv_msg.cmd_param[0].arg4)
        #                 if recv_msg.cmd_param[0].arg5 != "":
        #                     param_list.append(recv_msg.cmd_param[0].arg5)
        #                     if recv_msg.cmd_param[0].arg6 != "":
        #                         param_list.append(recv_msg.cmd_param[0].arg6)
        #
    	# t = threading.Thread(target=handle_commands, args=(recv_msg.cmd,param_list,satname))
    	# t.start()

main()
