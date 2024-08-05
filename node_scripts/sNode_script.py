# controller_to_node_worker.py

# This script is run on satellite nodes for one of the following purposes:
# 1. To monitor network interfaces and update routing tables (if applicable)
# 2. To monitor a netfilter queue for packets (if applicable) and a) send them to the controller node or b) dynamically determine route and update routing table
# 3. Use gRPC to communicate with the controller node and/or other satellite nodes

# The script takes the following arguments:
# 1. The current device's satellite number
# 2. The IP address of the controller node (optional)
# 3. Whether to use netfilter queues (currently available - having as argument planned)
# 4. Whether to use verbose output (currently available - having as argument planned)

# The script will:
# 1. Set up iptables to use the loopback IP as the source IP for all traffic from interfaces
# 2. Set up a netfilter queue to monitor traffic received on a specific port (if applicable)
# 3. Monitor network interfaces for changes in status (if applicable)
# 5. Send/Receive messages to the controller node (if applicable)
# 7. Send/Receive messages to other satellite nodes (if applicable)

import netifaces
from lib import spacenet_init_iptables as spacenet_init_iptables
from lib import spacenet_gRPC_p2p_messaging as spacenet_gRPC_p2p_messaging
from lib import spacenet_network_monitor as spacenet_network_monitor
import time # For process sleep and process execution time monitoring
import threading

import scapy.all as scapy

import sys # to run command line
import os # to check for sudo privileges
import signal # for graceful termination of script

import json # for dictionary serialization/deserialization to strings

# ===== GLOBAL VARIABLES =====
global_verbose = True

own_satnum = 0
own_ip = 'localhost'
neigh_satnum_list = []

cNodeIPStr = None

main_loop_running = False

all_neigh_dict = {} # Format all_neigh_dict[satnum] = {"interface_ip": ip, "peer_ip": ip, "status": status}
#neigh_intf_ip_dict = {}
all_neigh_dict_lock = threading.Lock() # Lock for all_neigh_dict to ensure thread safety

current_second = 0

gRPC_server = None
network_monitor = None

# ===== CONFIGURATION VARIABLES =====
use_netfilter = False

# ===== PYTHON VIRTUAL ENVIRONMENT =====
os.environ['PYTHONPATH'] = '/home/spacenet/mininet_test/mininetEnv/lib/python3.10/site-packages'

# ======= IP AND INTERFACE FUNCTIONS =======
def calc_distant_end_ip(ip, netmask):
    # Assuming a /30 subnet
    ip_parts = list(map(int, ip.split('.')))
    netmask_parts = list(map(int, netmask.split('.')))
    for i in range(4):
        if netmask_parts[i] == 255:
            continue
        else:
            # this is the part of the IP that can change
            if ip_parts[i] % 4 == 1:
                ip_parts[i] += 1 # The distant-end IP is the next one
            elif ip_parts[i] % 4 == 2:
                ip_parts[i] -= 1 # The distant-end IP is the previous one
    return '.'.join(map(str, ip_parts))

def get_local_intf_ip_by_neigh_satnum(neigh_satnum):
    print(f"[{current_second}] get_local_intf_ip_by_neigh_satnum({neigh_satnum})", flush=True)
    ip = None
    for interface in netifaces.interfaces():
                if 'lo' in interface:
                    continue # Skip loopback interface
                intf_sat_list = interface.split('_')
                if len(intf_sat_list) != 2:
                    print(f"  [{current_second}] get_local_intf_ip_by_neigh_satnum():  Interface {interface} does not conform to the expected naming convention.  Skipping.")
                    continue
                sat0, sat1 = intf_sat_list
                if sat0 == neigh_satnum or sat1 == neigh_satnum:
                    ifaddresses = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in ifaddresses:
                        ip = ifaddresses[netifaces.AF_INET][0]['addr']
                        break
    return ip

def get_neighbor_intf_ips(interface = None):
    # Get the IP address of the current neighboring interfaces
    global all_neigh_dict

    if interface is not None:
        ifaddresses = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in ifaddresses:
            ip = ifaddresses[netifaces.AF_INET][0]['addr']

    for interface in netifaces.interfaces():
        ifaddresses = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in ifaddresses:
            ip = ifaddresses[netifaces.AF_INET][0]['addr'] # Get the IP address of the interface
            netmask = ifaddresses[netifaces.AF_INET][0]['netmask'] # Get the netmask of the interface
            distant_end_ip = calc_distant_end_ip(ip, netmask)
            print(f"Interface: {interface} ({type(interface)}), Local IP: {ip}({type(ip)}), Distant-end IP: {distant_end_ip}({type(distant_end_ip)})")
            # Add to all_neigh_dict
            link_sat_list = interface.split('_')
            if len(link_sat_list) != 2:
                print(f"  get_neighbor_intf_ips():  Interface {interface} does not conform to the expected naming convention.  Skipping.")
                continue
            sat0, sat1 = link_sat_list
            if sat0 != own_satnum:
                neigh_satnum = sat0
            else:
                neigh_satnum = sat1
            neigh_dict = {"interface_ip": ip, "peer_ip": distant_end_ip, "status": True}
            update_all_neigh_dict(neigh_satnum, neigh_dict, True)

# ======= NEIGHBOR TRACKING FUNCTION =======
def add_to_all_neigh_dict(neigh_satnum, update_dict, locking = False):
    global all_neigh_dict, all_neigh_dict_lock
    #print(f"[{current_second}] add_to_all_neigh_dict({neigh_satnum}, {update_dict}, {locking})", flush=True)
    if "interface_ip" not in update_dict.keys():
        ip = get_local_intf_ip_by_neigh_satnum(neigh_satnum)
        if ip is None:
            print(f"[{current_second}] add_to_all_neigh_dict(): Could not find local interface IP for satnum {neigh_satnum}.  Aborting.")
            return
        update_dict["interface_ip"] = ip
    if "peer_ip" not in update_dict:
        neigh_intf_ip_str = calc_distant_end_ip(update_dict["interface_ip"], "255.255.255.252")
        update_dict["peer_ip"] = neigh_intf_ip_str
    update_dict["status"] = True
    print(f'Sat {own_satnum} adding neighbor {neigh_satnum} on local interface IP {update_dict["interface_ip"]} and peer interface IP {update_dict["peer_ip"]} to all_neigh_dict.')
    if locking: all_neigh_dict_lock.acquire()
    all_neigh_dict[neigh_satnum] = update_dict
    if locking: all_neigh_dict_lock.release()
    return

def update_all_neigh_dict(neigh_satnum, update_dict, locking = False):
    global all_neigh_dict, all_neigh_dict_lock
    #print(f"[{current_second}] update_all_neigh_dict({neigh_satnum}, {update_dict}, {locking})", flush=True)
    if neigh_satnum not in all_neigh_dict.keys():
        add_to_all_neigh_dict(neigh_satnum, update_dict, locking)
        return
    if locking: all_neigh_dict_lock.acquire()
    for key, value in update_dict.items():
        all_neigh_dict[neigh_satnum][key] = value # update values provided by update_dict
    if locking: all_neigh_dict_lock.release()

# ======= ROUTING TABLE FUNCTIONS =======
# update_dict format: {neigh_satnum: {"interface_ip": ip, "peer_ip": ip, "status": status}}
def update_routing_table(update_dict):
    #print(f"[{current_second}] update_routing_table({update_dict})", flush=True)
    for interface in update_dict.keys():
        try:
            sat1, sat2 = interface.split('_')
        except:
            print(f"[{current_second}] Interface {interface} does not conform to the expected naming convention.  Skipping.")
            continue
        if sat1 != own_satnum:
            satnum = sat1
        else:
            satnum = sat2
        update_all_neigh_dict(satnum, update_dict[interface], locking = True)

def update_routing_table_entry(interface, code):
    pass

# send routing table to all available neighbors
def publish_routing_table():
    for satnum in all_neigh_dict.keys():
        if all_neigh_dict[satnum]["status"] == spacenet_network_monitor.INTF_UP:
            peer_socket_address = all_neigh_dict[satnum]["peer_ip"] + ':' + str(spacenet_gRPC_p2p_messaging.gRPC_message_port_num)
            print(f"[{current_second}] Sending routing table to neighbor {satnum} at {peer_socket_address}", flush=True)
            spacenet_gRPC_p2p_messaging.send_gRPC_message_to_peer(peer_socket_address, {"message_type": spacenet_gRPC_p2p_messaging.NEIGH_ROUTING_TABLE_UPDATE, "message": all_neigh_dict})
    pass

def update_and_publish_routing_table(update_dict):
    #print(f"[{current_second}] update_and_publish_routing_table({update_dict})", flush=True)
    update_routing_table(update_dict)
    publish_routing_table()

def process_neigh_routing_table(neigh_routing_table):
    pass

# ======= UTILITY FUNCTIONS =======
def run_bash_command_as_process(command):
    # Run a bash command
    import subprocess
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    return output, error

def make_bash_script_and_run(script_contents):
    # Create a bash script and run it
    import os
    script_file = "temp_script.sh"
    with open(script_file, "w") as file:
        file.write(script_contents)
    os.system(f"chmod +x {script_file}")
    output, error = run_bash_command_as_process(f"./{script_file}")
    if output:
        print(output.decode())
    if error:
        print(error.decode())
    os.system(f"rm {script_file}")
   
def end_main_loop(signum, frame):
    global main_loop_running
    print(f"\nReceived signal to end main loop: {signum}", flush=True)
    main_loop_running = False

def increment_timer():
    global current_second
    while main_loop_running:
        time.sleep(1)
        current_second += 1
        sys.stdout.flush() # Also flush the output buffer to ensure the print statement is displayed

# ======== CALLBACK FUNCTIONS ========
# Callback function for gRPC messaging
# The PeerMessage method is called by the client to connect to the server - will disconnect if this function returns
def PeerMessage_callback(request, context, verbose=False): 
        if verbose:
            print(f"< [{current_second}] Received message from peer {context.peer()}: {request.message}")
        if request.message[0] == '{':
            #print("Converting JSON string message to dict")
            try:
                message_dict = json.loads(request.message)
            except json.JSONDecodeError as exc:
                if verbose:
                    print(f"Error decoding JSON message: {exc}")
                return f"ERROR: Invalid JSON message:{own_satnum}"
            if "message_type" in message_dict:
                if message_dict["message_type"] == spacenet_gRPC_p2p_messaging.NEIGH_DISCV_REQ:
                    if verbose:
                        print(f"  < [{current_second}] Received neighbor discovery request")
                    neigh_satnum, peer_ip = message_dict["message"]
                    local_intf_ip = calc_distant_end_ip(peer_ip, "255.255.255.252")
                    # send neighbor discovery response
                    if verbose:
                        print(f"  > [{current_second}] Sending neighbor discovery response to peer: " + context.peer())
                    neigh_discv_resp_dict = {"message_type": spacenet_gRPC_p2p_messaging.NEIGH_DISCV_RESP, "message": (own_satnum, local_intf_ip)}
                    spacenet_gRPC_p2p_messaging.send_gRPC_message_to_peer(context.peer(), neigh_discv_resp_dict)
                    # update routing table
                    add_to_all_neigh_dict(neigh_satnum, {"interface_ip": local_intf_ip, "peer_ip": peer_ip, "status": True})
                elif message_dict["message_type"] == spacenet_gRPC_p2p_messaging.NEIGH_ROUTING_TABLE_UPDATE:
                    if verbose:
                        print(f"  < [{current_second}] Received neighbor routing table update")
                    # update routing table
                    process_neigh_routing_table(message_dict["message"])
                elif message_dict["message_type"] == spacenet_gRPC_p2p_messaging.MININET_ADD_ROUTES:
                    if verbose:
                        print(f"  < [{current_second}] Received ADD ROUTES from Mininet controller")
                    command = f"ip route add {message_dict['message']}"
                    if verbose:
                        print(f"    [{current_second}] Running command: {command}")
                    cmd_output, cmd_error = run_bash_command_as_process(command) # Add routes to the routing table
                    if cmd_output:
                        if verbose:
                            print(f"  > [{current_second}] Command output: {cmd_output}")
                    if cmd_error:
                        print(f"  > [{current_second}] Command error: {cmd_error}")
                elif message_dict["message_type"] == spacenet_gRPC_p2p_messaging.MININET_ADD_DFLT_ROUTE:
                    if verbose:
                        print(f"  < [{current_second}] Received ADD DEFAULT ROUTE from Mininet controller")
                    command = f"route add default gw {message_dict['message']}"
                    if verbose:
                        print(f"    [{current_second}] Running command: {command}")
                    cmd_output, cmd_error = run_bash_command_as_process(command) # Add default route to the routing table
                    if cmd_output:
                        if verbose:
                            print(f"  > [{current_second}] Command output: {cmd_output}")
                    if cmd_error:
                        print(f"  > [{current_second}] Command error: {cmd_error}")
                elif message_dict["message_type"] == spacenet_gRPC_p2p_messaging.MININET_REMOVE_ROUTES:
                    if verbose:
                        print(f"  < [{current_second}] Received REMOVE ROUTES from Mininet controller")
                    command = f"ip route del {message_dict['message']}"
                    if verbose:
                        print(f"    [{current_second}] Running command: {command}")
                    cmd_output, cmd_error = run_bash_command_as_process(command) # Remove routes from the routing table
                    if cmd_output:
                        if verbose:
                            print(f"  > [{current_second}] Command output: {cmd_output}")
                    if cmd_error:
                        print(f"  > [{current_second}] Command error: {cmd_error}")
                elif message_dict["message_type"] == spacenet_gRPC_p2p_messaging.MININET_CTRL_SHUTDOWN:
                    if verbose:
                        print(f"  < [{current_second}] Received SHUTDOWN COMMAND from Mininet controller", flush=True)
                    end_main_loop(0, None)
                elif message_dict["message_type"] == spacenet_gRPC_p2p_messaging.GENERIC_MESSAGE:
                    if verbose:
                        print(f"  < [{current_second}] Received generic message: {message_dict['message']}")
                    pass
                else: # Unknown message type
                    for key in message_dict:
                        print(f"  < Received unknown message type from peer: {key}, message: {message_dict[key]}")
            else:
                for key in message_dict:
                    print(f"  < Received unknown message from peer: {message_dict[key]}")
        if verbose:
            print(f"  [{current_second}] > Sending acknowledgement to peer: {context.peer()}")
        return f"ACK:{own_satnum}"

#def network_monitor_callback(code, message):
def network_monitor_callback(callback_dict):
    #print(f"[{current_second}] network_monitor_callback({callback_dict})", flush=True) # code: {code}, message: {message})
    update_dict = {}
    for interface, status_tuple in callback_dict.items():
        if interface == 'lo': # Skip loopback interface
            continue
        if 's1_' in interface: # Skip management network interface
            continue
        code, status = status_tuple
        if code == spacenet_network_monitor.DEL_INTF:
            print(f'Interface "{interface}" down')
            update_dict[interface] = {"status": spacenet_network_monitor.INTF_DEL}
        elif code == spacenet_network_monitor.NEW_INTF:
            print(f'New interface detected: {interface}')
            update_dict[interface] = {"status": spacenet_network_monitor.INTF_UP}
        elif code == spacenet_network_monitor.INTF_STATUS_CHANGE:
            print(f'Interface "{interface}" status changed to {status}')
            update_dict[interface] = {"status": status}
        else:
            print(f'Unknown code: {code} for interface {interface}')

    update_and_publish_routing_table(update_dict)

def print_callback(message):
    print(f"(print_callback) [{current_second}] Callback function received: {message}")

def print_and_accept_packet(pkt):
    #print(pkt)
    header = scapy.IP(pkt.get_payload())
    # If packet is TCP or UDP
    if header.haslayer(scapy.TCP) or header.haslayer(scapy.UDP):
        dst = header[scapy.IP].dst
        if header.haslayer(scapy.TCP):
            print("TCP Packet with destination: ", dst)
            #print(header.show())
        else:
            print("UDP Packet with destination: ", dst)
            #print(header.show())
    pkt.accept()


def main():
    # Check for root privileges - for iptables and netfilter queue
    if os.geteuid() != 0:
        print("ERROR - This script must be run as root. Aborting...", flush=True)
        return
    if len(sys.argv) > 1:
        global own_satnum
        own_satnum = sys.argv[1]
        if len(sys.argv) > 2:
            global cNodeIPStr
            cNodeIPStr = sys.argv[2]
            print(f"Reporting to Controller node with IP: {cNodeIPStr}")
    else:
        print("No satellite number provided.  Aborting.", flush=True)
        return

    global current_second, gRPC_server, network_monitor
    print(f"Running {sys.argv[0]} with satellite number {own_satnum}", flush=True)

    # Set Up
    print("Configuring IP tables...")
    spacenet_init_iptables.initialize_ip_tables_and_nfqueue(use_loopback_as_source = True, use_netfilter = use_netfilter, nfqueue_base_port_num = 55555, nfqueue_admin_queue_num = 1, nfqueue_unknown_queue_num = 99, admin_traffic_callback=print_and_accept_packet, unknown_traffic_callback=print_and_accept_packet, verbose = global_verbose)

    print("Starting gRPC server...")
    gRPC_server_manager = spacenet_gRPC_p2p_messaging.gRPCServerManager(callback=PeerMessage_callback, own_satnum=own_satnum, port_num=spacenet_gRPC_p2p_messaging.gRPC_server_port_num, max_connections=spacenet_gRPC_p2p_messaging.max_connections_from_peers, verbose=global_verbose)
    #gRPC_server = spacenet_gRPC_p2p_messaging.run_gRPC_server(callback=PeerMessage_callback, own_satnum=own_satnum, port_num = 50051, max_connections = 10, verbose=global_verbose)
    gRPC_server_manager.start_gRPC_server()

    print("Monitoring network interfaces...")
    #network_monitor = NetworkMonitor(network_monitor_callback, interface_poll_interval = 2) # Poll interfaces every 2 seconds
    network_monitor = spacenet_network_monitor.NetworkMonitor(print_callback, interface_poll_interval = 2) # Poll interfaces every 2 seconds
    
    # Report ready status if cNodeIPStr is provided
    if cNodeIPStr is not None:
        print(f"Sending ready status to controller node at {cNodeIPStr}:{str(spacenet_gRPC_p2p_messaging.gRPC_server_port_num)}")
        spacenet_gRPC_p2p_messaging.send_gRPC_message_to_peer(cNodeIPStr + ':' + str(spacenet_gRPC_p2p_messaging.gRPC_server_port_num), {"message_type": spacenet_gRPC_p2p_messaging.NODE_RESPONSE_READY, "message": own_satnum})
    
    # Do the things
    global main_loop_running
    main_loop_running = True

    print("Starting timer thread")
    timer_thread = threading.Thread(target=increment_timer)
    timer_thread.daemon = True
    timer_thread.start()

    # Listening for SIGINT/SIGTERM to end main loop
    signal.signal(signal.SIGINT, end_main_loop)
    signal.signal(signal.SIGTERM, end_main_loop)
    try:
        while main_loop_running:
            time.sleep(1)
    except Exception as e:
        print(f"Exception: {e}. Exiting...")

    # Clean up
    print(f"  [{current_second}] Signalling network monitor to stop...")
    network_monitor.signal_stop()

    if use_netfilter:
        print(f"[{current_second}] Stopping netfilter queue...")
        spacenet_init_iptables.stop_netfilterqueue()

    print(f"[{current_second}] Stopping gRPC server...")
    time.sleep(2) # Short wait to allow for any final messages to be sent
    if cNodeIPStr is not None:
        # Report HALT status to cNode
        spacenet_gRPC_p2p_messaging.send_gRPC_message_to_peer(cNodeIPStr + ':' + str(spacenet_gRPC_p2p_messaging.gRPC_server_port_num), {"message_type": spacenet_gRPC_p2p_messaging.NODE_RESPONSE_HALTED, "message": own_satnum})
        #spacenet_gRPC_p2p_messaging.stop_gRPC_server(gRPC_server, blocking=False)
    gRPC_server_manager.stop_gRPC_server(blocking=False)

    print(f"[{current_second}] Verifying any running threads received shutdown signal")
    end_main_loop(0, None)

    print(f"[{current_second}] Done.", flush=True)

if __name__ == "__main__":
    main()