import socket
import subprocess
import time
sys.path.append('../templates')
import control_mgs_pb2 as ControlMsg

serverAddressPort   = ("131.227.207.157", 20001)
bufferSize          = 1024

def establish_connection():
    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

def create_message(name, to, command, args_list):
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

def send_command(message_to_send):
    UDPClientSocket.sendto(message_to_send, serverAddressPort)
