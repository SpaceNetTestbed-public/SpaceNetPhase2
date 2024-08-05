# controller_to_node_cNode_script.py

# Script to monitor FIFO for commands to send to nodes via gRPC

from lib import spacenet_gRPC_p2p_messaging as spacenet_gRPC_p2p_messaging
from lib import spacenet_fifo_messaging as spacenet_fifo_messaging

import netifaces # For getting IP addresses of interfaces used during IP tables setup
import time # For process sleep and process execution time monitoring
import threading

#import netfilterqueue 
import scapy.all as scapy

import sys # to run command line
import os # to use FIFO
import signal # for graceful termination of script
import errno # for error handling
import json # for JSON encoding/decoding

main_loop_running = True
global_verbose = True

own_hostName = 0
own_ip = 'localhost'

#max_connections_from_peers = 10
#gRPC_port_num = 50051

current_second = 0

gRPC_server = None
thread_list = []

# ===== PYTHON VIRTUAL ENVIRONMENT =====
os.environ['PYTHONPATH'] = '/home/spacenet/mininet_test/mininetEnv/lib/python3.10/site-packages'

# FIFO
FIFO_IN = 'controller_node_pipe'
CONTROLLER_FIFO = 'main_script_pipe'
quit_command = spacenet_fifo_messaging.quit_command
fifo_break_command = spacenet_fifo_messaging.fifo_break_command

message_id = 0 # Used to track message IDs for gRPC messages for debugging


def gRPC_callback(request, context, verbose=False): # The PeerMessage method is called by the client to connect to the server - will disconnect if this function returns
        if verbose:
            print(f"(gRPC_callback) < [{current_second}] Received message from peer {context.peer()}: {request.message}")
        if request.message[0] == '{':
            #print("Converting JSON string message to dict")
            try:
                message_dict = json.loads(request.message)
            except json.JSONDecodeError as exc:
                print(f"  (gRPC_callback) < Error decoding JSON message from peer: {exc}")
                return f"ERROR decoding JSON message:{own_hostName}"
            if "message_type" in message_dict:
                if message_dict["message_type"] == spacenet_gRPC_p2p_messaging.NODE_RESPONSE_READY:
                    if verbose:
                        print(f"  (gRPC_callback) < [{current_second}] Received READY message from peer {message_dict['message']}.")
                    send_fifo_message(CONTROLLER_FIFO, message_dict)
                elif message_dict["message_type"] == spacenet_gRPC_p2p_messaging.NODE_RESPONSE_HALTED:
                    if verbose:
                        print(f"  (gRPC_callback) < [{current_second}] Received HALTED message from peer {message_dict['message']}.")
                    send_fifo_message(CONTROLLER_FIFO, message_dict)
                elif message_dict["message_type"] == spacenet_gRPC_p2p_messaging.GENERIC_MESSAGE:
                    if verbose:
                        print(f"  (gRPC_callback) < [{current_second}] Received generic message: {message_dict['message']}")
                    pass
            else:
                for key in message_dict:
                    print(f"  (gRPC_callback) < Received unknown message from peer: {message_dict[key]}")
        if verbose:
            print("  (gRPC_callback) > Sending acknowledgement to peer: " + context.peer())
        return f"ACK:{own_hostName}"

def get_message_id():
    global message_id
    message_id += 1
    return message_id

def print_callback(message):
    print(f"(print_callback) Callback function received: {message}")

def end_main_loop(signum, frame):
    global main_loop_running
    print(f"\n(end_main_loop) Received signal to end main loop: {signum}", flush=True)
    main_loop_running = False

def wait_on_threads():
    global thread_list
    print(f"[{current_second}] (wait_on_threads) Waiting on {len(thread_list)} threads to finish...")
    for thread in thread_list:
        thread.join()
    print("(wait_on_threads) All threads finished.")

def send_fifo_message(fifo, message):
    if type(message) is dict:
        message = json.dumps(message)
    with open(fifo, 'w') as fifo_file:
        fifo_file.write(message + spacenet_fifo_messaging.fifo_break_command)
        fifo_file.write('\n') # Ensure message is sent

def send_command_to_node(command):
    try:
        socket_address, message = command.split('^', 1)
    except ValueError:
        print(f"(send_command_to_node) Invalid command: {command}")
        return
    message_type_str = message.split(',', 1)[0]
    message_type = int(message_type_str.split(':', 1)[1])
    message_id = get_message_id()
    try:
        validation_test = json.loads(message)
    except json.JSONDecodeError as exc:
        print(f"[{current_second}] (send_command_to_node) Error decoding JSON message [ID: {message_id}]: {exc}")
        print(f"  Message: {message}")
        return
    print(f"[{current_second}](send_command_to_node) Sending {spacenet_gRPC_p2p_messaging.decode_gRPC_message_code(message_type)} message to {socket_address} [ID {message_id}]: {message}")
    spacenet_gRPC_p2p_messaging.send_gRPC_message_to_peer(socket_address, message, message_id, verbose=global_verbose)

def increment_timer():
    global current_second, main_loop_running
    while main_loop_running:
        time.sleep(1)
        current_second += 1
        sys.stdout.flush() # Flush buffer to ensure print is immediate

def main():
    # Check for root privileges - for iptables
    if os.geteuid() != 0:
        print("ERROR - This script must be run as root. Aborting...", flush=True)
        return
    if len(sys.argv) > 1:
        global own_hostName
        own_hostName = sys.argv[1]
    else:
        print("No satellite number provided.  Aborting.", flush=True)
        return

    global current_second, gRPC_server
    print(f"(main) Running {sys.argv[0]} with host name {own_hostName}", flush=True)

    # Set Up
    print("(main) Starting gRPC server...")
    #gRPC_server = spacenet_gRPC_p2p_messaging.run_gRPC_server(callback=gRPC_callback, own_satnum=own_hostName, port_num=gRPC_port_num, max_connections=max_connections_from_peers, verbose=global_verbose)
    gRPC_server_manager = spacenet_gRPC_p2p_messaging.gRPCServerManager(callback=gRPC_callback, own_satnum = own_hostName, port_num=spacenet_gRPC_p2p_messaging.gRPC_server_port_num, max_connections=spacenet_gRPC_p2p_messaging.max_connections_from_peers, verbose=global_verbose)
    gRPC_server_manager.start_gRPC_server()

    print("(main) Starting timer thread")
    global thread_list
    timer_thread = threading.Thread(target=increment_timer)
    timer_thread.daemon = True
    timer_thread.start()
    thread_list.append(timer_thread)

    print(f"[{current_second}] (main) Starting FIFO monitoring loop")
    spacenet_fifo_messaging.monitor_fifo_for_commands(FIFO_IN, send_command_to_node, quit_command=quit_command, fifo_break_command=fifo_break_command, verbose=global_verbose)

    # Clean up
    print(f"[{current_second}] (main) Stopping gRPC server...")
    time.sleep(2) # Short wait to allow for any final messages to be sent
    #spacenet_gRPC_p2p_messaging.stop_gRPC_server(gRPC_server, blocking=False)
    gRPC_server_manager.stop_gRPC_server(blocking=False)

    print(f"[{current_second}] (main) Verifying any running threads received shutdown signal")
    end_main_loop(0, None)
    wait_on_threads()

    # Report own HALT status to main script
    send_fifo_message(CONTROLLER_FIFO, {"message_type": spacenet_gRPC_p2p_messaging.NODE_RESPONSE_HALTED, "message" : own_hostName})

    print(f"[{current_second}] Done.", flush=True)

if __name__ == "__main__":
    main()