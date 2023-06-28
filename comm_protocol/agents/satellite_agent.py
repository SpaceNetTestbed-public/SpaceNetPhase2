import socket
import time
import subprocess
import threading
import sys
# sys.path.append('../templates')
import control_mgs_pb2 as ControlMsg


def connection_establishment(a_mgnt_IP, a_mgnt_port):
    UDPSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPSocket.bind((a_mgnt_IP, a_mgnt_port))
    print("The Agent is up and listening")

    return UDPSocket


def handle_commands(cmd, cmd_params):
    full_command = []
    if cmd == "ifconfig":
        full_command.append("ifconfig")
        list_of_interfaces = os.listdir('/sys/class/net/')
        for p in cmd_params:
            full_command.append(p)
            if "eth" in p and p not in list_of_interfaces:
                return
    if cmd == "ping":
    	full_command.append("ping")
    	for p in cmd_params:
    		full_command.append(p)

    print full_command
    with open('log.txt', 'a') as f:
        process = subprocess.Popen(full_command, stdout=f)

def main():
    UDPSocket = connection_establishment("131.227.207.157", 20001)

    while(True):
        bytesAddressPair = UDPSocket.recvfrom(1024)
        recv_msg = ControlMsg.control_msg()
        recv_msg.ParseFromString(bytesAddressPair[0])
        print(recv_msg)

    	param_list = []
    	if recv_msg.cmd_param[0].arg1 != "":
    	    param_list.append(recv_msg.cmd_param[0].arg1)
    	    if recv_msg.cmd_param[0].arg2 != "":
                param_list.append(recv_msg.cmd_param[0].arg2)
                if recv_msg.cmd_param[0].arg3 != "":
                    param_list.append(recv_msg.cmd_param[0].arg3)
                    if recv_msg.cmd_param[0].arg4 != "":
                        param_list.append(recv_msg.cmd_param[0].arg4)
                        if recv_msg.cmd_param[0].arg5 != "":
                            param_list.append(recv_msg.cmd_param[0].arg5)
                            if recv_msg.cmd_param[0].arg6 != "":
                                param_list.append(recv_msg.cmd_param[0].arg6)

    	t = threading.Thread(target=handle_commands, args=(recv_msg.cmd,param_list))
    	t.start()

main()
