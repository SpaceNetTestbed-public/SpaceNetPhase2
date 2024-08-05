# spacenet_network_monitor.py

import netifaces # pip install netifaces; for getting network interface information
import threading # for running the network monitoring in a separate thread
import time # for sleeping between interface polls
import subprocess # for running shell commands



class NetworkMonitor:
    # Event Codes
    NEW_INTF = 1
    INTF_STATUS_CHANGE = 2
    DEL_INTF = 3

    # Interface Status Codes
    INTF_UP = 1
    INTF_DOWN = 0
    INTF_DEL = -1

    def __init__(self, callback, interface_poll_interval=5, verbose=False):
        self.callback = callback
        self.interface_poll_interval = interface_poll_interval
        self.verbose = verbose
        self.monitor_thread = threading.Thread(target=self.monitor_network_interfaces)
        self.monitor_thread.daemon = True
        self.monitor_thread_running = True
        self.monitor_thread.start()
        self.previous_interface_status_dict = {}

    def get_interfaces_status(self, interfaces = None):
        if interfaces is None:
            interfaces = netifaces.interfaces()
        status = {}
        for interface in interfaces:
            try:
                ifaddresses = netifaces.ifaddresses(interface)
            except Exception as e:
                print(f"Could not get ifaddresses for interface {interface}. Error: {e}\n  Skipping.")
                continue
            intf_state = (netifaces.AF_INET in ifaddresses) and self.is_interface_up(interface)
            if intf_state:
                status[interface] = self.INTF_UP
            else:
                status[interface] = self.INTF_DOWN
            # print(f'Interface: {interface}, Status: {status[interface]}')
        return status

    # Main monitoring loop
    def monitor_network_interfaces(self):
        if self.verbose:
            print("Starting network interface monitoring thread...")
        #get_neighbor_intf_ips() # Get the IP addresses of the neighboring interfaces before starting loop
        #print(f"Initial interface poll found {len(all_neigh_dict)} neighbors: {list(all_neigh_dict.keys())}")

        while self.monitor_thread_running:
            time.sleep(self.interface_poll_interval)
            current_interfaces = netifaces.interfaces() # Get list of current interfaces
            if current_interfaces is None:
                if self.verbose:
                    print("Could not get list of interfaces.  Continuing to poll.")
                current_interfaces = []
            if self.previous_interface_status_dict is {}: # No prior interfaces
                new_interfaces_list = current_interfaces
                missing_interfaces_list = []
                changed_interfaces_list = []
            else:
                new_interfaces_list = list(set(current_interfaces) - set(self.previous_interface_status_dict.keys()))
                missing_interfaces_list = list(set(self.previous_interface_status_dict.keys()) - set(current_interfaces))
                changed_interfaces_list = []
                new_interface_status_dict = self.get_interfaces_status(current_interfaces)
                for interface in current_interfaces:
                    if interface in self.previous_interface_status_dict.keys():
                        if self.previous_interface_status_dict[interface] != new_interface_status_dict[interface]:
                            if self.verbose:
                                print(f"(NetworkMonitor.monitor_network_interfaces) Interface {interface} status changed.  Was: {self.previous_interface_status_dict[interface]}, Now: {new_interface_status_dict[interface]}")
                            changed_interfaces_list.append((interface, new_interface_status_dict[interface]))
            
            self.previous_interface_status_dict = self.get_interfaces_status(current_interfaces)

            link_status_code_dict = {}
            if new_interfaces_list: # if there are new interfaces
                if self.verbose:
                    print(f"(NetworkMonitor.monitor_network_interfaces) Discovered new interfaces: {new_interfaces_list}", flush=True)
                for interface in new_interfaces_list:
                    link_status_code_dict[interface] = (self.NEW_INTF, None)
            if missing_interfaces_list:
                if self.verbose:
                    print(f"(NetworkMonitor.monitor_network_interfaces) Discovered missing interfaces: {missing_interfaces_list}", flush=True)
                for interface in missing_interfaces_list:
                    link_status_code_dict[interface] = (self.DEL_INTF, None)
            if changed_interfaces_list:
                if self.verbose:
                    print(f"(NetworkMonitor.monitor_network_interfaces) Discovered changed interfaces: {changed_interfaces_list}", flush=True)
                for interface, status in changed_interfaces_list:
                    link_status_code_dict[interface] = (self.INTF_STATUS_CHANGE, status)
            if len(link_status_code_dict) > 0:
                self.callback(link_status_code_dict) # call callback function with the dictionary of new/missing/changed interfaces

    
    def is_interface_up(self, interface):
        output = subprocess.check_output(f"ip link show {interface}", shell=True).decode()
        return "UP" in output

    def signal_stop(self):
        self.monitor_thread_running = False
        self.monitor_thread.join()