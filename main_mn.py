from mininet.net import Mininet
from mininet.node import Controller
from mininet.node import Host
from mininet.node import Node
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, TCIntf

import json # for JSON encoding/decoding

#from mininet.topo import Topo

import datetime # to help with epoch time management
import ipaddress # to help with IP address management
import time # for sleep
#import deepdiff # for comparing dictionaries
import threading # for threading gRPC server
import signal # for graceful termination of script (currently used only for FIFO loop)
import sys # for command line arguments
import re # for regex use in filename identification
import multiprocessing
import atexit
from resource_monitor.top_logger import TOP_LOGGER

# ===== PYTHON VIRTUAL ENVIRONMENT =====
#import os
# must run the following commands in terminal before running this script:
# source /home/spacenet/mininet_test/mininetEnv/bin/activate
#os.environ['PYTHONPATH'] = '/home/spacenet/mininet_test/mininetEnv/lib/python3.10/site-packages'
# must run the following command in terminal after running this script:
# deactivate

import os # For checking admin priv

pprint = None # Declaring module name in global space so it can be imported in functions

# ~~~~~~~~~~~~~~~~~~ FEATURE ENABLE/DISABLE ~~~~~~~~~~~~~~~~~~
use_node_python_script = False
use_python_virtual_env = False
use_management_net_messaging = False # requires use of node python script and python virtual environment
use_yaml_config = True
use_app_manager = True # Sim currently doesn't work if set to False
use_connectivity_optimizer = False
pre_ping = True # Pre-ping links before starting simulation to attempt ARP table population
dynamic_link_queue_size = False # Calculate netem queue size based on link bandwidth and latency
# ~~~~~~~~~~~~~~~~~~ GENERAL GLOBAL VARIABLES ~~~~~~~~~~~~~~~~~~

# ===== GLOBAL VARIABLES =====
global_verbose = True
del_app_results = False # If True, delete app results files after printing results
pause_before_run = False # If True, pause after building topology but before running the simulation
output_path = "script_output/" # Path to store output files (both node script and app manager)

# ================== Routing Option Variables ==================
routing_files_imply_reverse_routes = True # True indicates that reverse routes are not included in routing files, but are still valid (Don't change unless you're sure)

# ================== Program Flow Variables ==================
main_loop_running = True
simTimeMode = "discrete" # "discrete" or "continuous"; can be specified in config file, 'discrete' is default
contUpdateSkipMargin = 2 # tolerance in seconds to attempt scenario update in continuous mode

# ================== Thread Variables ==================
thread_list = []
stop_event = None # Event to signal threads to stop
update_in_progress = False # Flag to indicate an update is in progress
update_lock = None # Lock to protect 'update_in_progress' flag

# =============== Epoch and Interval Information ===============
starting_interval = 0
CLI_count = 1
current_second = 0

TimeStepCounter = 0
TimeStepDuration = 0
TimeStepCount = None

# =============== Link Variables ==================
r2q = 10 # Default value for r2q parameter in tc commands
default_netem_queue_size = 2000 # Default value for netem queue size when not calculating dynamically
max_netem_queue_size = 20000
# =============== Variables Specific to Network Changes between Intervals ===============
appManager = None
EpochCurrentDateTime = None
fullRoutingDict = {}
net = None

# =============== Tracking Dictionaries ===============
devDict = {} # Will contain: management IP, list of interfaces containing tuples with: interface name, interface IP, distant device name
CurrRoutingDict = {} # Will contain routing information for each device
PrevRoutingDict = {}
AllLinksDict = {}

# =============== Network IP Topology ===============
# Single IP address subnets for each device (/32) (min 5,000 devices): 10.0.0.0 - 10.0.19.255 / 11.0.0.0 - 11.0.19.255
nextSatIP = ipaddress.ip_interface('10.0.0.0/32')
nextGsIP = ipaddress.ip_interface('11.0.0.0/32')

# Two IP address subnets for inter-device networks (/30) (min 5,000 devices with 6 links each): 10.0.20.0 - 10.0.138.255 / 11.0.20.0 - 11.0.138.255
nextSatLinkNetworkIP = ipaddress.IPv4Address('10.0.20.0')
nextGsLinkNetworkIP = ipaddress.IPv4Address('11.0.20.0')

# ~~~~~~~~~~~~~~~~~~ FEATURE GLOBAL VARIABLES AND LIBRARIES ~~~~~~~~~~~~~~~~~~

# =============== Paths and Filenames ===============
if use_node_python_script:
    from lib import spacenet_gRPC_p2p_messaging as spacenet_gRPC_p2p_messaging
    sNode_python_script_filename = "node_scripts/sNode_script.py"
    sats_self_manage_iptables = True

# =============== Python Virtual Environment ===============
if use_python_virtual_env:
    venv_bash_script_filename = "node_scripts/python3_with_venv.sh"
    venv_name = "mininetEnv" # Path and name of Python virtual environment from node script perspective

# =============== Management Network Global Variables ===============
if use_management_net_messaging:
    management_net_messaging_to_all = True # Send management network messages to all devices or just hardware devices
    if not use_node_python_script:
        print("Configuration Error: Management network messaging requires use of node python script; correct and re-run script")
        exit()
    if not use_python_virtual_env:
        print("Configuration Error: Management network messaging requires use of Python virtual environment; correct and re-run script")
        exit()
    from lib import spacenet_fifo_messaging as spacenet_fifo_messaging

    nextManagementNetworkIP = ipaddress.IPv4Address('172.16.0.1') # Using 172.16.0.0/12 for management network
    managementNetDict = {}
    managementSwitchObject = None
    nodeStatusDict = {}

    # ------------------ Controller Node Globals ------------------
    cNode_python_script_filename ="node_scripts/cNode_script.py"
    controller_node_id = -1
    cNode_hostName = 'controller'
    cNodeObject = None
    # ------------------ Controller FIFO Node Messaging ------------------
    cNode_FIFO = 'controller_node_pipe'
    cNode_quit_command = "\!\Q"
    fifo_break_command = "\!\B"
    gRPC_message_port_num = 50051
    monitor_FIFO = 'main_script_pipe'

# =============== Manual Configuration Paths ===============
connectivity_matrix_path = "/home/spacenet/mininet_test/connectivity_matrix/"
routing_file_path = "/home/spacenet/mininet_test/routing/"

# =============== Config file path/name ===============
if use_yaml_config:
    from lib import spacenet_yaml_config as spacenet_yaml_config

    config_file_path = "config_files/"
    config_file_name = "main_mn_config.yaml"
    sat_config_sub_path = "sat_config_files/"

# ================== SpaceNet App Manager ==================
if use_app_manager:
    from lib import spacenet_app_manager as spacenet_app_manager

# Classes

class LinuxRouter( Node ):
    "A Node with IP forwarding enabled."

    # pylint: disable=arguments-differ
    def config( self, **params ):
        super( LinuxRouter, self).config( **params )
        # Enable forwarding on the router
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        self.cmd( 'sysctl net.ipv4.ip_forward=0' )
        super( LinuxRouter, self ).terminate()

# Mininet API method overrides (aka 'Monkey Patches')
# ================== Mininet API Overrides ==================
# Override Mininet TCLink class to add r2q parameter to bwCmds method
print("[[Patching Mininet TCLink class to add r2q parameter to bwCmds method]]")
_original_bwCmds = TCIntf.bwCmds
# "Wraps" original TCIntf.bwCmds to add r2q parameter; method signature derived from Mininet source code (v2.3.0)
def bwCmds_with_r2q(self, bw=None, speedup=0, use_hfsc=False, use_tbf=False, latency_ms=None, enable_ecn=False, enable_red=False):
    global r2q # Use global r2q value - must be modified prior to creating links
    # Call original method with all parameters
    cmds, parent = _original_bwCmds(self, bw=bw, speedup=speedup, use_hfsc=use_hfsc, use_tbf=use_tbf, latency_ms=latency_ms, enable_ecn=enable_ecn, enable_red=enable_red)
    # if r2q is anything other than 10, modify the tc command to include the r2q parameter
    if r2q != 10:
        newCmds = []
        for cmd in cmds:
            # Only patch lines that set 'root handle 5:0 htb default 1' (i.e. the root qdisc)
            if 'htb default 1' in cmd and 'root handle 5:' in cmd:
                replacementString = f"htb r2q {r2q} default 1"
                cmd = cmd.replace('htb default 1', replacementString)
            newCmds.append(cmd)
        cmds = newCmds
        print(f"Modified tc commands to include r2q parameter: {r2q}")
    else:
        print("Using default r2q value of 10; no modification of tc commands")
    return cmds, parent
# Now assign our patched version back to the original Mininet class
TCIntf.bwCmds = bwCmds_with_r2q

# Functions
# ================== Network / IP Functions ==================
def getNextSatIP():
    global nextSatIP
    if nextSatIP.ip == ipaddress.IPv4Address('10.0.19.255'):
        print("Error: No more satellite management IP addresses available")
        return None
    satIP = nextSatIP
    nextSatIP += 1
    return satIP

def getNextGsIP():
    global nextGsIP
    if nextGsIP.ip == ipaddress.IPv4Address('11.0.19.255'):
        print("Error: No more GS management IP addresses available")
        return None
    gsIP = nextGsIP
    nextGsIP += 1
    return gsIP

def getNextSatLinkNetworkIP():
    global nextSatLinkNetworkIP
    if nextSatLinkNetworkIP == ipaddress.IPv4Address('10.0.138.255'):
        print("Error: No more sat-sat link network IP addresses available")
        return None
    satLinkNetworkIP = nextSatLinkNetworkIP
    nextSatLinkNetworkIP += 4
    return satLinkNetworkIP

def getNextGsLinkNetworkIP():
    global nextGsLinkNetworkIP
    if nextGsLinkNetworkIP == ipaddress.IPv4Address('11.0.138.255'):
        print("Error: No more GS-sat link network IP addresses available")
        return None
    gsLinkNetworkIP = nextGsLinkNetworkIP
    nextGsLinkNetworkIP += 4
    return gsLinkNetworkIP

def getNextManagementNetworkIP():
    global nextManagementNetworkIP
    if nextManagementNetworkIP == ipaddress.IPv4Address('17.31.255.255'):
        print("Error: No more management network IP addresses available")
        return None
    managementNetworkIP = nextManagementNetworkIP
    nextManagementNetworkIP += 1
    return managementNetworkIP

def parallel_ping_links(linkNameList, epochLinksDict, timeout_factor=1):
    """
    Launch a parallel ping -c1 from intf1.node -> intf2.ip 
    for each link in 'links' and collect results.

    :return: A dict { link: retcode } of ping exit codes
    """
    from subprocess import Popen
    from math import ceil

    # Find largest linkDelay
    maxLinkDelay = 0
    maxLinkDelayName = ""
    for linkName in linkNameList:
        linkDelay, _ = epochLinksDict[linkName]
        linkDelay = float(linkDelay)
        if linkDelay > maxLinkDelay:
            maxLinkDelay = linkDelay
            maxLinkDelayName = linkName
    maxTimeout = ceil((2 * (linkDelay/1000)) * timeout_factor)
    if maxTimeout > 10:
        print(f"Warning: Timeout for link {maxLinkDelayName} is {maxTimeout} seconds (linkDelay: {linkDelay}ms and timeout_factor: {timeout_factor}).  May have excessive waiting.")

    ping_procs = {}
    for linkName in linkNameList:
        linkDelay, _ = epochLinksDict[linkName]
        DevAhostName, DevBhostName = linkName.split("_")
        DevAObject = net.get(DevAhostName)
        DevBObject = net.get(DevBhostName)
        link = net.linksBetween(DevAObject, DevBObject)[0]
        #link = net.links(DevAhostName, DevBhostName)[0]
        nodeA = link.intf1.node
        ipB = link.intf2.ip
        # Skip if no IP
        if not ipB:
            continue
        
        timeout = ceil((2 * (float(linkDelay))/1000) * timeout_factor) # Setting timeout to 2x link delay times the timeout factor (linkDelay is in ms)
        cmd = f"ping -c1 -W {timeout} {ipB}"
        proc = nodeA.popen(cmd)
        ping_procs[linkName] = proc

    # Wait for pings to finish and collect retcodes
    results = {}
    numLinks = len(ping_procs)
    cur_link_num = 1
    for linkName, proc in ping_procs.items():
        print(f"Pinging link {cur_link_num}/{numLinks}: {linkName}", end="\r")
        cur_link_num += 1
        try:
            retcode = proc.wait()
        except KeyboardInterrupt:
            print("Caught KeyboardInterrupt: Terminating ping processes...")
            for proc in ping_procs.values():
                proc.terminate()
            abort(net)
        results[linkName] = retcode
    print("\nDone") # Move to next line
    return results

def parallel_ping_neighbors_with_retries(epochLinksDict, max_retries=3, timeout_factor = 1):    
    # Attempt to populate ARP tables by pinging from each link's intf1.node to intf2.ip, retrying up to max_retries times for failures.
    print(f"=== Populating ARP tables by pinging neighbors with {max_retries} retries ===")
    remaining_links = list(epochLinksDict.keys())
    successful_links = set()

    for attempt in range(1, max_retries + 1):
        print(f"=== Attempt {attempt}/{max_retries} ===")
        results = parallel_ping_links(linkNameList=remaining_links, epochLinksDict=epochLinksDict, timeout_factor=timeout_factor)

        # Check for failures
        new_failures = []
        for linkName, retcode in results.items():
            if retcode == 0:
                # success
                successful_links.add(linkName)
            else:
                # failed
                new_failures.append(linkName)

        if not new_failures:
            # everything succeeded
            print("All links succeeded on this attempt!")
            break
        else:
            print(f"{len(new_failures)} links failed in attempt {attempt}.")
            if attempt < max_retries:
                print("Retrying failed links...")
                remaining_links = new_failures  # only re-try failures
            else:
                print("No more retries left.")

    # Print summary
    epoch_links = list(epochLinksDict.keys())
    failed_links = [l for l in epoch_links if l not in successful_links]
    print(f"=== Ping Summary ===")
    print(f"  Succeeded: {len(successful_links)}/{len(epoch_links)}")
    if failed_links:
        print("  Failed links:")
        for l in failed_links:
            DevAhostName, DevBhostName = l.split("_")
            DevAObject = net.get(DevAhostName)
            DevBObject = net.get(DevBhostName)
            link = net.linksBetween(DevAObject, DevBObject)[0]
            #link = net.links(DevAhostName, DevBhostName)[0]
            nodeA = link.intf1.node
            ipB = link.intf2.ip
            print(f"    {nodeA.name} -> {ipB}")

    return failed_links


# ================== Device / Object Functions ==================
def printDevDict():
    global devDict
    print("devDict:")
    for key in devDict:
        _, devManagementIP, devIntfList = devDict[key]
        print(key, ": ", devManagementIP)
        for devIntfTuple in devIntfList:
            DevIntfName, DevIntfIP, DistHostName, DistIntfIP = devIntfTuple
            print("  intf: ", DevIntfName, " - ", DevIntfIP, "\t-> ", DistHostName, " - ", DistIntfIP)

# ================== User Input Functions ==================
def get_constellation_info():
    # Ask user for following constellation details:
    # 1. Number of satellites in constellation
    # 2. Number of ground stations

    TotalSatCnt = int(input("Enter total number of satellites in the constellation: "))
    TotalGSCnt = int(input("Enter total number of ground stations: "))

    return TotalSatCnt, TotalGSCnt

def get_epoch_info():
    # Ask user for following epoch details:
    # 1. Epoch duration (in seconds)
    # 2. Epoch interval (in seconds)
    # 3. Epoch start year
    # 4. Epoch start month
    # 5. Epoch start day
    # 6. Epoch start hour (24 hour format)
    # 7. Epoch start minute
    # 8. Epoch start second
    # Returns: EpochDuration, EpochInterval, StartDateTime (as Python datetime object)
    defaultEpochDuration = "1"
    defaultEpochInterval = "10"
    defaultStartYear = "2023"
    defaultStartMonth = "09"
    defaultStartDay = "13"
    defaultStartHour = "07"
    defaultStartMinute = "45"
    defaultStartSecond = "50"

    EpochDuration = int(input("Enter epoch duration (in seconds) [{}]: ".format(defaultEpochDuration)) or (defaultEpochDuration))
    TimeStepCount = int(input("Enter epoch count [{}]: ".format(defaultEpochInterval)) or (defaultEpochInterval))
    StartYear = int(input("Enter epoch start year [{}]: ".format(defaultStartYear)) or (defaultStartYear))
    StartMonth = int(input("Enter epoch start month [{}]: ".format(defaultStartMonth)) or (defaultStartMonth))
    StartDay = int(input("Enter epoch start day [{}]: ".format(defaultStartDay)) or (defaultStartDay))
    StartHour = int(input("Enter epoch start hour (24 hour format) [{}]: ".format(defaultStartHour)) or (defaultStartHour))
    StartMinute = int(input("Enter epoch start minute [{}]: ".format(defaultStartMinute)) or (defaultStartMinute))
    StartSecond = int(input("Enter epoch start second [{}]: ".format(defaultStartSecond)) or (defaultStartSecond))
    

    return EpochDuration, TimeStepCount, datetime.datetime(StartYear, StartMonth, StartDay, StartHour, StartMinute, StartSecond)

def get_config_info():
    sim_config = {}
    constellation_config = {}
    ConstellationSelection = 0
    while ConstellationSelection not in [1, 2, 3]:
        ConstellationSelection = int(input("Enter constellation selection (1: Starlink, 2: Fakelink, 3: OneFib) [3]: ") or ("3"))
    if ConstellationSelection == 1:
        sim_config["ConstellationName"] = "Starlink"
        constellation_config["ConnectivityMatrixPath"] = connectivity_matrix_path + "starlink/"
        constellation_config["RoutingFilePath"] = routing_file_path + "starlink/"
    elif ConstellationSelection == 2:
        sim_config["ConstellationName"] = "Fakelink"
        constellation_config["ConnectivityMatrixPath"] = connectivity_matrix_path + "fakelink/"
        constellation_config["RoutingFilePath"] = routing_file_path + "fakelink/"
    elif ConstellationSelection == 3:
        sim_config["ConstellationName"] = "OneFib"
        constellation_config["ConnectivityMatrixPath"] = connectivity_matrix_path + "onefib/"
        constellation_config["RoutingFilePath"] = routing_file_path + "onefib/"
    constellation_config["TotalSatCnt"], constellation_config["TotalGSCnt"] = get_constellation_info()

    constellation_config["SimLength"]["TimeStepDuration"], constellation_config["SimLength"]["TimeStepCount"], constellation_config["StartDateTime"] = get_epoch_info()
    
    return sim_config, constellation_config, None

# ================== Connectivity / Routing File Functions ==================
def find_file_in_directory_with_dtg(directory, prefix, suffix, target_datetime):
    # Find the file in the specified directory with the specified prefix and suffix that matches the target date/time
    # Returns the directory+filename if found, None otherwise
    target_year = str(target_datetime.year)
    target_month = str(target_datetime.month).lstrip('0')
    target_day = str(target_datetime.day).lstrip('0')
    target_hour = str(target_datetime.hour).lstrip('0')
    target_minute = str(target_datetime.minute).lstrip('0')
    target_second = str(target_datetime.second).lstrip('0')
    if target_second == '': # If seconds is empty, set it to 0
        target_second = '0'
    if global_verbose:
        print(f"(find_file_in_directory_with_dtg) Looking for file with pattern: {prefix}{target_year}_{target_month}_{target_day}_{target_hour}_{target_minute}_{target_second}{suffix}: ", end="")

    # Define regex pattern to match the date in the filename along with specific prefix and suffix
    file_pattern = re.compile(rf'{prefix}(\d{{1,4}})_(\d{{1,2}})_(\d{{1,2}})_(\d{{1,2}})_(\d{{1,2}})_(\d{{1,2}}){suffix}')

    for filename in os.listdir(directory):
        match = file_pattern.match(filename)
        if match:
            file_year, file_month, file_day, file_hour, file_minute, file_second = match.groups()
            if file_year == target_year and file_month.lstrip('0') == target_month and file_day.lstrip('0') == target_day and file_hour.lstrip('0') == target_hour and file_minute.lstrip('0') == target_minute and file_second.lstrip('0') == target_second.lstrip('0'):
                if global_verbose:
                    #print(f"\t(find_file_in_directory_with_dtg) Found file: {directory + filename}")
                    print(f"\033[32mFound\033[0m")
                return directory + filename
    print(f"(find_file_in_directory_with_dtg) ERROR: Could not find file with date: {prefix}_{target_year}_{target_month}_{target_day}_{target_hour}_{target_minute}_{target_second}{suffix}")
    return None

def parse_connectivity_file(ConnectivityFileName, TotalSatCnt, nodeList = None):
    # Parse the connectivity file and return the connectivity matrix as a list of lists
    LinkDict = {}
    with open(ConnectivityFileName, 'r') as file:
        for line in file:
            NodeAName, NodeBName, LinkDelay, LinkBandwidth = line.split(',')
            if nodeList is not None:
                if NodeAName not in nodeList or NodeBName not in nodeList: # if using minimalNodeList, want only links between nodes in the list
                    #print(f"Skipping link between {NodeAName} and {NodeBName} as one or both are not in the minimal node list", end="\r")
                    continue
            if int(NodeAName) < int(NodeBName):
                LinkName = NodeAName + "_" + NodeBName
            else:
                LinkName = NodeBName + "_" + NodeAName
            if LinkName not in LinkDict:
                if global_verbose:
                    # If either node value is greater than number of satelltes, its a GS
                    if int(NodeAName) >= TotalSatCnt or int(NodeBName) >= TotalSatCnt:
                        if global_verbose: print(f"Adding GS link {LinkName} between Node {NodeAName} and Node {NodeBName} with delay {LinkDelay} and bandwidth {LinkBandwidth}")
                LinkDict[LinkName] = (LinkDelay, LinkBandwidth)
    if global_verbose: print("Read ", len(LinkDict), " links from file")
    
    return LinkDict

def parse_all_connectivity_files(ConnectivityMatrixPath, ConnectivityFilePrefix, ConnectivityFileSuffix, EpochStart, TimeStepCount, TimeStepDuration, TotalSatCnt, nodeList = None):
    # Parse all connectivity files in the specified path
    # Returns a dictionary with epoch number as key and connectivity matrix as value
    ConnectivityDict = {}

    curEpochDateTime = EpochStart
    for _ in range(0, TimeStepCount):
        CurrEpochString = curEpochDateTime.strftime("%Y_%m_%d_%H_%M_%S")
        ConnectivityFileName = find_file_in_directory_with_dtg(ConnectivityMatrixPath, ConnectivityFilePrefix, ConnectivityFileSuffix, curEpochDateTime)
        if ConnectivityFileName is None:
            print("Error: Could not find connectivity file for epoch ", CurrEpochString)
            exit (1)
        print("Processing file: ", ConnectivityFileName)
        ConnectivityDict[CurrEpochString] = parse_connectivity_file(ConnectivityFileName, TotalSatCnt, nodeList)
        curEpochDateTime += datetime.timedelta(seconds=TimeStepDuration)

    return ConnectivityDict

def parse_interval_routing_file_no_implied_routes(RoutingFileName, route = None): # TO DO: Add minimalNodeList functionality!!
    global devDict
    IntervalRoutesDict = {}

    with open(RoutingFileName, 'r') as file:
        for line in file:
            line = line.strip() # Remove leading/trailing whitespace and newlines
            line = line.replace(' ', '') # Remove any remaining spaces
            commaCount = line.count(',')
            if commaCount == 0: # Ignore header line
                pass
            else:
                if commaCount == 1: # target and destination are directly connected
                    sourceDevName, destDevName = line.split(',')
                    if route is not None:
                        if sourceDevName not in route or destDevName not in route: # if we're using a minimal node list, don't create routes for devices not in the route list
                            continue
                    nextHopDevName = destDevName
                else: # at least one interveneing hop between target and destination
                    routingEntry = line.split(',')
                    sourceDevName = routingEntry[0]
                    nextHopDevName = routingEntry[1]
                    destDevName = routingEntry[-1]
                    if route is not None:
                        if sourceDevName not in route or destDevName not in route:
                            continue
                _, _, sourceDevIntfList = devDict[sourceDevName]
                _, destDevManagementIP, _ = devDict[destDevName]
                targetNetworkIP = destDevManagementIP
                for sourceDevIntfTuple in sourceDevIntfList:
                    sourceDevIntfName, _, sourceDevDistHostName, sourceDevDistIntfIP = sourceDevIntfTuple
                    if sourceDevDistHostName == nextHopDevName:
                        nextHopIntfName = sourceDevIntfName
                        nextHopIP = sourceDevDistIntfIP.split('/')[0]
                        break
                # Add routing entry to IntervalRoutesDict
                if sourceDevName not in IntervalRoutesDict:
                    IntervalRoutesDict[sourceDevName] = {}
                IntervalRoutesDict[sourceDevName][targetNetworkIP] = (nextHopIP, nextHopIntfName)
    return IntervalRoutesDict

# Assumes that reverse routes are not included in the routing file but still valid
def parse_interval_routing_file(RoutingFileName, TotalSatCnt, TotalGSCnt, CurrEpochString, route = None):
    if global_verbose:
        print(f"(parse_interval_routing_file) Parsing routing file: {RoutingFileName}, TotalSatCnt: {TotalSatCnt}, TotalGSCnt: {TotalGSCnt}, CurrEpochString: {CurrEpochString}, route: {route}")
    global devDict
    IntervalRoutesDict = {}

    if route:
        print(f"Minimal Node List: {route}")

    with open(RoutingFileName, 'r') as file:
        for line in file:
            line = line.strip() # Remove leading/trailing whitespace and newlines
            line = line.replace(' ', '') # Remove any remaining spaces
            commaCount = line.count(',')
            if commaCount == 0: # Ignore blank line
                pass
            else:
                #if global_verbose:
                #    print("\r\033[K", end="") # Clear line
                #    print(f"\rProcessing line: {line}", end="") # Print current line without trailing newline
                if commaCount == 1: # target and destination are directly connected
                    source1DevName, dest1DevName = line.split(',')
                    if route: # if we're using a minimal node list, don't create routes for devices not in the route list
                        if (source1DevName not in route) or (dest1DevName not in route):
                            continue
                    nextHop1DevName = dest1DevName
                    source2DevName = dest1DevName
                    nextHop2DevName = source1DevName
                    dest2DevName = source1DevName
                else: # at least one intervening hop between target and destination
                    routingEntry = line.split(',')
                    source1DevName = routingEntry[0]
                    dest1DevName = routingEntry[-1]
                    if route: # if we're using a minimal node list, don't create routes for devices not in the route list
                        if (source1DevName not in route) or (dest1DevName not in route):
                            continue
                    nextHop1DevName = routingEntry[1]
                    source2DevName = routingEntry[-1] # Reverse route
                    nextHop2DevName = routingEntry[-2] # Reverse route
                    dest2DevName = routingEntry[0] # Reverse route
                _, _, source1DevIntfList = devDict[source1DevName]
                _, dest1DevManagementIP, _ = devDict[dest1DevName]
                target1NetworkIP = dest1DevManagementIP
                _, _, source2DevIntfList = devDict[source2DevName] # Reverse route
                _, dest2DevManagementIP, _ = devDict[dest2DevName] # Reverse route
                target2NetworkIP = dest2DevManagementIP # Reverse route
                for source1DevIntfTuple in source1DevIntfList:
                    source1DevIntfName, _, source1DevDistHostName, source1DevDistIntfIP = source1DevIntfTuple
                    if source1DevDistHostName == nextHop1DevName:
                        nextHop1IntfName = source1DevIntfName
                        nextHop1IP = source1DevDistIntfIP.split('/')[0]
                        break
                for source2DevIntfTuple in source2DevIntfList: # Reverse route
                    source2DevIntfName, _, source2DevDistHostName, source2DevDistIntfIP = source2DevIntfTuple
                    if source2DevDistHostName == nextHop2DevName:
                        nextHop2IntfName = source2DevIntfName
                        nextHop2IP = source2DevDistIntfIP.split('/')[0]
                        break
                # Add routing entry to IntervalRoutesDict
                if global_verbose:
                    print(f"Adding routing entry for {source1DevName} to {target1NetworkIP} via {nextHop1IP} on interface {nextHop1IntfName}")
                if source1DevName not in IntervalRoutesDict:
                    IntervalRoutesDict[source1DevName] = {}
                try:
                    IntervalRoutesDict[source1DevName][target1NetworkIP] = (nextHop1IP, nextHop1IntfName)
                except UnboundLocalError:
                    print(f"Error: Missing interface information.  source1DevName: {source1DevName}, interfaces: {source1DevIntfList}; looking for link to next hop: {nextHop1DevName}\n")
                    exit(1)
                if source2DevName not in IntervalRoutesDict: # Reverse route
                    IntervalRoutesDict[source2DevName] = {}
                try:
                    IntervalRoutesDict[source2DevName][target2NetworkIP] = (nextHop2IP, nextHop2IntfName)
                except UnboundLocalError:
                    print(f"Error: Missing interface information.  source1DevName: {source2DevName}, interfaces: {source2DevIntfList}; looking for link to next hop: {nextHop2DevName}\n")
                    abort()
                #print("Added routing entry for ", sourceDevName, " to ", targetNetworkIP, " via ", nextHopIP, " on interface ", nextHopIntfName)
    
    if route: # if we're using a minimal node list, don't create routes for devices not in the list, but still need to add GS nodes, if necessary
        gsList = []
        for devName in devDict:
            if int(devName) >= TotalSatCnt:
                if devName in IntervalRoutesDict:  # GS node are already in the route list, so skip
                    break
                gsList.append(devName)
    else:
        if str(TotalSatCnt) not in IntervalRoutesDict: # if GS nodes aren't in the route list [routing files don't have GS nodes in them], add them here
            gsList = [str(i) for i in range(TotalSatCnt, TotalSatCnt + TotalGSCnt)]
        else:
            gsList = []
    print(f"All Links Dictionary for {CurrEpochString}: {AllLinksDict[CurrEpochString]}")
    print(f"Interval Routes Dictionary: {IntervalRoutesDict}")
    for gsName in gsList:
        satName = None
        for linkName in AllLinksDict[CurrEpochString]: # use AllLinksDict to find the satellite connected to the ground station
            if gsName in linkName:
                satName = linkName.split('_')[0] # Sat name will always be listed first in link name due to GS having higher name values
                break
        if satName == None:
            print("Error: Could not find satellite connected to ground station ", gsName)
            continue
        if satName not in route:
            continue
        devList = list(IntervalRoutesDict.keys())
        try: 
            devList.remove(satName) # Remove the satellite from the list of devices
        except ValueError:
            pass # Skip if the satellite is not in the list
        _, gsNetworkIP, _ = devDict[gsName] # Get GS Network IP
        _, satNetworkIP, satIntfList = devDict[satName] # Get Satellite Network IP
        print(devList)
        print(gsName)
        for devName in devList:
            print(devName,satNetworkIP)
            print(f"Interval Routes Dictionary for {devName}: {IntervalRoutesDict[devName]}")
            nextHopIP, nextHopIntfName = IntervalRoutesDict[devName][satNetworkIP]
            IntervalRoutesDict[devName][gsNetworkIP] = (nextHopIP, nextHopIntfName) # Add route to GS
        for satIntfTuple in satIntfList:
            satIntfName, _, distHostName, distIntfIP = satIntfTuple
            if distHostName == gsName:
                nextHopIP = distIntfIP.split('/')[0]
                break
        try:
            IntervalRoutesDict[satName][gsNetworkIP] = (nextHopIP, satIntfName) # Add route for connected sat to GS
        except KeyError:
            print(f"Error: Could not find satellite {satName} in IntervalRoutesDict")
            print(f"IntervalRoutesDict: {IntervalRoutesDict}")
            input("Press Enter to continue...")
            return IntervalRoutesDict
    
    return IntervalRoutesDict

def parse_all_routing_files(RoutingFilePath, RoutingFilePrefix, RoutingFileSuffix, EpochStart, TimeStepCount, TimeStepDuration, TotalSatCnt, TotalGSCnt, routeByIntervalDict = None):
    # Parse all routing files in the specified path
    # Returns a dictionary with epoch number as key and routing information as value
    RoutingDict = {}

    curEpochDateTime = EpochStart
    for i in range(0, TimeStepCount):
        CurrEpochString = curEpochDateTime.strftime("%Y_%m_%d_%H_%M_%S")
        RoutingFileName = find_file_in_directory_with_dtg(RoutingFilePath, RoutingFilePrefix, RoutingFileSuffix, curEpochDateTime)
        if RoutingFileName is None:
            print("Error: Could not find routing file for epoch ", CurrEpochString)
            exit (1)
        print("(parse_all_routing_files) Processing file: ", RoutingFileName)
        if routeByIntervalDict is not None:
            route = routeByIntervalDict[i]
        else:
            route = None
        if routing_files_imply_reverse_routes:
            RoutingDict[CurrEpochString] = parse_interval_routing_file(RoutingFileName, TotalSatCnt, TotalGSCnt, CurrEpochString, route)
        else:
            RoutingDict[CurrEpochString] = parse_interval_routing_file_no_implied_routes(RoutingFileName, route)
        curEpochDateTime += datetime.timedelta(seconds=TimeStepDuration)
        print(curEpochDateTime)
    return RoutingDict

# ================== Node Routing Functions ==================
def set_GS_default_route(gsName, CurrEpochString, gRPC_message = False):
    satName = None
    for linkName in AllLinksDict[CurrEpochString]: # use AllLinksDict to find the satellite connected to the ground station
        if gsName in linkName:
            satName = linkName.split('_')[0] # Sat name will always be listed first in link name due to GS having higher name values
            break
    if satName == None:
        print("\033[31m(set_GS_default_route) Error: Could not find satellite connected to ground station \033[0m", gsName)
        return -1
    gsIntfList = devDict[gsName][2]
    nextHopIP = None
    for gsIntfTuple in gsIntfList:
        _, _, distHostName, distIntfIP = gsIntfTuple
        if satName.strip() == distHostName.strip():
            nextHopIP = distIntfIP.split('/')[0] # get IP of satellite connected to ground station from GS interface list
            break
    if nextHopIP == None:
        print("Error: Could not find next hop IP for ground station ", gsName)
        return -1
    if gRPC_message:
        return nextHopIP
    cmdString = 'route add default gw ' + nextHopIP
    print(f"[{current_second}] (set_GS_default_route) Executing command on host " + gsName + ": ", cmdString)
    devObject = devDict[gsName][0]
    devObject.cmd(cmdString)
    return 0

# ================== Management Network / Controller Node Functions ==================
# Uses FIFO to send command to controller node script to send message to peer via gRPC
def controller_node_relay_message_to_sat_node(deviceName, message):
    devManagementIP = managementNetDict[deviceName]
    device_socket_address = devManagementIP + ':' + str(gRPC_message_port_num)
    if type(message) is dict:
        #print("Converting dict message to JSON string")
        message = json.dumps(message, ensure_ascii=False)
    command = f"{device_socket_address}^{message}{fifo_break_command}"
    print(f"[{current_second}] Controller Node sending message to peer at {device_socket_address}: {command}")
    cNodeObject.cmd(f"echo '{command}' > {cNode_FIFO}")

def shutdown_controller_node_script():
    command = f'echo \"{cNode_quit_command}\" > {cNode_FIFO}'
    print(f"[{current_second}] Shutting down controller node script with command: {command}")
    cNodeObject.cmd(command)

def monitor_FIFO_callback(message):
    global current_second, nodeStatusDict
    print(f"[{current_second}] (monitor_FIFO_callback) Received command from FIFO")
    if message[0] == '{':
            #print("Converting JSON string message to dict")
            try:
                message_dict = json.loads(message)
            except json.JSONDecodeError as exc:
                if global_verbose:
                    print(f"Error decoding JSON message: {exc}")
                return f"ERROR: Invalid JSON message:{message}"
            if "message_type" in message_dict:
                message_type = message_dict["message_type"]
                if message_type == spacenet_gRPC_p2p_messaging.NODE_RESPONSE_READY:
                    if global_verbose:
                        print(f"Received READY message from peer.")
                    nodeStatusDict[message_dict["message"]] = spacenet_gRPC_p2p_messaging.NODE_RESPONSE_READY
                elif message_type == spacenet_gRPC_p2p_messaging.NODE_RESPONSE_HALTED:
                    if global_verbose:
                        print(f"Received HALTED message from peer.")
                    nodeStatusDict[message_dict["message"]] = spacenet_gRPC_p2p_messaging.NODE_RESPONSE_HALTED
                elif message_type == spacenet_gRPC_p2p_messaging.GENERIC_MESSAGE:
                    if global_verbose:
                        print(f"Received generic message: {message_dict['message']}")
                    pass
            else:
                for key in message_dict:
                    print(f"Received unknown message from peer: {message_dict}")#{message_dict[key]}")
    return


# ================== Program Control Functions ==================
def abort(net):
    info("*** Stopping network")
    net.stop()
    exit()

def end_main_loop(signum, frame):
    global main_loop_running, stop_event
    print(f"\nReceived signal to end main loop: {signum}", flush=True)
    main_loop_running = False
    stop_event.set() if stop_event is not None else None

def increment_timer():
    global current_second
    while main_loop_running:
        time.sleep(1)
        current_second += 1

def wait_on_status_dict(status_dict, status_value, max_wait_time=60):
    global current_second
    wait_time = 0
    while True:
        time.sleep(1)
        wait_time += 1
        if all(entry_val == status_value for entry_val in status_dict.values()):
            print(f"[{current_second}] All devices are ready.")
            break
        if wait_time >= max_wait_time:
            print(f"[{current_second}] Timed out waiting for devices to be ready.")
            break
        print(f"[{current_second}] {list(status_dict.values()).count(status_value)}/{len(status_dict)} devices are ready...", end="\r")

def wait_on_threads():
    global thread_list
    print(f"[{current_second}] (wait_on_threads) Waiting on {len(thread_list)} threads to finish... (10 seconds max)")
    for thread in thread_list:
        thread.join(timeout=10)
        if thread.is_alive():
            print(f"(wait_on_threads) Thread {thread.name} timed out.")
        else:
            print(f"(wait_on_threads) Thread {thread.name} finished.")
    print("(wait_on_threads) All threads finished.")

# ================== Continuous Time Mode Methods ==================
def attempt_scenario_update(): # Tries to perform scenario update when called by timing thread
    global update_in_progress

    # Acquire lock to check/update shared flag
    with update_lock:
        if update_in_progress:
            print(f"[{current_second}] (attempt_scenario_update) >>>WARNING<<< Update already in progress. Skipping interval update.")
            return
        update_in_progress = True

    # Update scenario
    update_interval()

    # Release lock
    with update_lock:
        update_in_progress = False

def interval_update_timing_thread(TimeStepDuration, TimeStepCount): # Attempts to perform updates at specific wall-clock times if using continuous time mode
    start_time = time.monotonic()

    # Precompute all scheduled update times
    update_times = [(i+1) * TimeStepDuration for i in range(TimeStepCount-1)] # Update at the end of each interval, so skip the first interval
    print(f"[{current_second}] (interval_update_timing_thread) Performing interval updates at times: {update_times} seconds.")

    i = 0 # index for update_times
    while i < len(update_times) and not stop_event.is_set():
        elapsed = time.monotonic() - start_time
        print(f"[{current_second}] (interval_update_timing_thread) Checking for update {i+1} (at {update_times[i]:.2f}s) at elapsed time {elapsed:.2f} seconds.")
        

        # Skip any updates we are late for
        while i < len(update_times) and (elapsed >= update_times[i] + contUpdateSkipMargin):
            missed_by = elapsed - update_times[i]
            print(f"[{current_second}] (interval_update_timing_thread) >>>WARNING<<< Skipping update {i+1} (missed by {missed_by:.2f} seconds).")
            i += 1
        
        # If all update times have passed or are told to stop, break out
        if i >= len(update_times) or stop_event.is_set():
            print(f"[{current_second}] (interval_update_timing_thread) Finished all updates.")
            break

        # Calculate time to sleep until next update
        wait_time = update_times[i] - elapsed
        if wait_time > 0:
            print(f"[{current_second}] (interval_update_timing_thread) Sleeping for {wait_time:.2f} seconds until next update.")
            time.sleep(wait_time)

        if stop_event.is_set(): # Check one last time if stop event is set before attempting update
            print(f"[{current_second}] (interval_update_timing_thread) Stop event set. Exiting.")
            break

        # Attempt update (may be skipped if another update is in progress)
        print(f"[{current_second}] (interval_update_timing_thread) Attempting update {i+1} (at {update_times[i]:.2f}s) at {time.monotonic() - start_time:.2f} seconds.")
        attempt_scenario_update()
        i += 1

# ================== Logic for all updates that occur during interval changes ==================
# 
def update_interval():
    global TimeStepDuration, TimeStepCounter, TimeStepCount, EpochCurrentDateTime, continuousTimeTotal
    global current_second, global_verbose, simTimeMode
    global appManager, net
    global nodeIndexDict, devDict, AllLinksDict, fullRoutingDict
    print(f"[{current_second}] (update_interval)  Updating to Interval Number {TimeStepCounter}")
    appManager.print_to_output_file(f"[{current_second}] Change to Interval Number {TimeStepCounter}")
    # Update epoch time to next interval
    EpochPreviousDateTime = EpochCurrentDateTime
    PrevEpochString = EpochPreviousDateTime.strftime("%Y_%m_%d_%H_%M_%S")
    EpochCurrentDateTime += datetime.timedelta(seconds=TimeStepDuration)
    CurrEpochString = EpochCurrentDateTime.strftime("%Y_%m_%d_%H_%M_%S")
    info("[" + str(current_second) + "] (update_interval) ~Setting conditions at epoch " + CurrEpochString + "~\n")

    info("*** Updating link states\n")
    try:
        prevLinkNameList = list(AllLinksDict[PrevEpochString].keys())
        currLinkNameList = list(AllLinksDict[CurrEpochString].keys())
    except KeyError:
        print(f"[{current_second}] Error: Could not find link information for epoch {PrevEpochString} or {CurrEpochString} (Epochs in AllLinksDict: {list(AllLinksDict.keys())})")
        abort(net)
    linksToDisableList = set(prevLinkNameList) - set(currLinkNameList)
    linksToEnableList = set(currLinkNameList) - set(prevLinkNameList)
    linksToContinueList = set(prevLinkNameList) & set(currLinkNameList)

    info("*** Disabling links\n")
    for linkName in linksToDisableList:
        DevAhostName, DevBhostName = linkName.split("_")
        DevAObject = net.get(DevAhostName)
        DevBObject = net.get(DevBhostName)
        cmdString = 'ip link set ' + linkName + ' down'
        if global_verbose:
            print(f"[{current_second}] Executing command on hosts ", DevAhostName, ", ", DevBhostName, ": ", cmdString)
        DevAObject.cmd(cmdString)
        DevBObject.cmd(cmdString)
        if global_verbose:
            print("  - Link ", linkName, " disabled")

    info("*** Enabling links\n")
    DevAObject, DevBObject = None, None # Initialize variables so they persist outside of loops
    linkList = None
    for linkName in linksToEnableList:
        DevAhostName, DevBhostName = linkName.split("_")
        DevAObject = net.get(DevAhostName)
        DevBObject = net.get(DevBhostName)
        cmdString = 'ip link set ' + linkName + ' up'
        if global_verbose:
            print(f"[{current_second}] Executing command on hosts ", DevAhostName, ", ", DevBhostName, ": ", cmdString)
        DevAObject.cmd(cmdString)
        DevBObject.cmd(cmdString)
        # Set link delay and bandwidth
        linkDelay, linkBandwidth = AllLinksDict[CurrEpochString][linkName]
        linkList = net.linksBetween(DevAObject, DevBObject)
        linkList[0].intf1.config(delay=str(linkDelay)+'ms', bw=float(linkBandwidth)) # bandwidth is in Mbps (I think)
        linkList[0].intf2.config(delay=str(linkDelay)+'ms', bw=float(linkBandwidth))
        if global_verbose:
            print("  - Link ", linkName, " enabled with delay ", linkDelay, " and bandwidth ", linkBandwidth)

    info("*** Verifying continuing links\n")
    for linkName in linksToContinueList:
        if AllLinksDict[PrevEpochString][linkName] != AllLinksDict[CurrEpochString][linkName]:
            # Set link delay and bandwidth
            linkDelay, linkBandwidth = AllLinksDict[CurrEpochString][linkName]
            DevAhostName, DevBhostName = linkName.split("_")
            DevAObject = net.get(DevAhostName)
            DevBObject = net.get(DevBhostName)
            linkList = net.linksBetween(DevAObject, DevBObject)
            if linkList == []:
                print(f"[{current_second}] (update_interval)  Error: Could not find link between {DevAhostName} and {DevBhostName}")
                abort(net)
            linkList[0].intf1.config(delay=str(linkDelay)+'ms', bw=float(linkBandwidth)) # bandwidth is in Mbps (I think)
            linkList[0].intf2.config(delay=str(linkDelay)+'ms', bw=float(linkBandwidth))
            if global_verbose:
                print(f"  [{current_second}] - Link ", linkName, " modified with delay ", linkDelay, " and bandwidth ", linkBandwidth)
    #info("  Links available in current epoch: ", str(linksToEnableList) + str(linksToContinueList) + "\n")
    currentLinks = linksToEnableList | linksToContinueList
    print(f"  Links available in current epoch: {str(sorted(currentLinks))}")

    info("*** Configuring routing\n")
    if global_verbose:
        print(f"  [{current_second}] Routing Dict for epoch {CurrEpochString}:")
        pprint.pprint(fullRoutingDict[CurrEpochString])
    #dictionary of format {epochString: {deviceName: {targetNetworkIP: (nextHopIP, nextHopIntfName)}}}
    prevRoutingDict = fullRoutingDict[PrevEpochString]
    currRoutingDict = fullRoutingDict[CurrEpochString]
    #gsRoutesIncluded = False
    if global_verbose:
        print(f"Checking for routes to remove")
    for deviceName in prevRoutingDict:
        if deviceName not in currRoutingDict: # if this device is not in the current epoch's routing dictionary, so remove all of its routes and any routes that other devices had to it
            print(f"  [{current_second}] Removing routes for device {deviceName}")
            for targetNetworkIP in prevRoutingDict[deviceName]:
                prevNextHopIp, prevNextHopIntfName = prevRoutingDict[deviceName][targetNetworkIP]
                devObject = net.get(deviceName)
                if not use_node_python_script:
                    cmdString = 'ip route del ' + targetNetworkIP + ' via ' + prevNextHopIp + ' dev ' + prevNextHopIntfName
                    if global_verbose:
                        print(f"[{current_second}] Executing command on host " + deviceName + ": ", cmdString)
                    devObject.cmd(cmdString)
                elif use_management_net_messaging and not management_net_messaging_to_all:
                    pass # TO DO:  IMPLEMENT METHOD TO SEND VIA gRPC ONLY TO HARDWARE NODES
                elif use_management_net_messaging and management_net_messaging_to_all:
                    gRPC_command = f"{targetNetworkIP} via {prevNextHopIp} dev {prevNextHopIntfName}"
                    message = {"message_type": spacenet_gRPC_p2p_messaging.MININET_REMOVE_ROUTES, "message": gRPC_command}
                    controller_node_relay_message_to_sat_node(deviceName, message)
            deviceNetworkIP = devDict[deviceName][1]
            for otherDeviceName in currRoutingDict: # for each device in the current epochs routing dictionary
                if deviceNetworkIP in currRoutingDict[otherDeviceName]:
                    nextHopIp, nextHopIntfName = currRoutingDict[otherDeviceName][deviceNetworkIP]
                    devObject = net.get(otherDeviceName)
                    if not use_node_python_script:
                        cmdString = 'ip route del ' + deviceNetworkIP + ' via ' + nextHopIp + ' dev ' + nextHopIntfName
                        if global_verbose:
                            print(f"[{current_second}] Executing command on host " + otherDeviceName + ": ", cmdString)
                        devObject.cmd(cmdString)
                    elif use_management_net_messaging and not management_net_messaging_to_all:
                        pass # TO DO:  IMPLEMENT METHOD TO SEND VIA gRPC ONLY TO HARDWARE NODES
                    elif use_management_net_messaging and management_net_messaging_to_all:
                        gRPC_command = f"{deviceNetworkIP} via {nextHopIp} dev {nextHopIntfName}"
                        message = {"message_type": spacenet_gRPC_p2p_messaging.MININET_REMOVE_ROUTES, "message": gRPC_command}
                        controller_node_relay_message_to_sat_node(otherDeviceName, message)   
    if global_verbose:
        print(f"Checking for routes to add/update")
    for deviceName in currRoutingDict: # for each device in the current epochs routing dictionary
        for targetNetworkIP in currRoutingDict[deviceName]:
            nextHopTuple = currRoutingDict[deviceName][targetNetworkIP]
            devHasPrevRoute = False
            prevRouteNeedsChange = False
            if deviceName in prevRoutingDict: # if this device was in the previous epoch's routing dictionary, check if the route has changed
                devHasPrevRoute = True
                if (targetNetworkIP in prevRoutingDict[deviceName]) and (nextHopTuple != prevRoutingDict[deviceName][targetNetworkIP]): # Had a route in the previous epoch and it has changed
                    prevRouteNeedsChange = True
                    # Remove old route
                    if global_verbose:
                        print(f"  [{current_second}] Removing old route for device {deviceName} to target network {targetNetworkIP}; changed to {nextHopTuple}")
                    devObject = net.get(deviceName)
                    if targetNetworkIP in prevRoutingDict[deviceName]:
                        prevNextHopIp, prevNextHopIntfName = prevRoutingDict[deviceName][targetNetworkIP]
                        if not use_node_python_script: # if sending commands via Mininet API
                            cmdString = 'ip route del ' + targetNetworkIP + ' via ' + prevNextHopIp + ' dev ' + prevNextHopIntfName
                            if global_verbose:
                                print(f"[{current_second}] Executing command on host " + deviceName + ": ", cmdString)
                            retval = devObject.cmd(cmdString + " 2> error.tmp")
                            #if (retval != 0):
                            #    print(f"Error: Could not remove route for device {deviceName} to target network {targetNetworkIP}. Details:")
                            #    error = devObject.cmdPrint('cat error.tmp')
                            #    if 'Cannot find device' in error:
                            #        devObject.cmdPrint('ip link show')
                        elif use_management_net_messaging and not management_net_messaging_to_all: # if sending commands via gRPC (TO DO: implement method to send via gRPC only to hardware nodes)
                            pass # TO DO:  IMPLEMENT METHOD TO SEND VIA gRPC ONLY TO HARDWARE NODES
                        elif use_management_net_messaging and management_net_messaging_to_all: # if sending commands to all nodes via gRPC
                            gRPC_command = f"{targetNetworkIP} via {prevNextHopIp} dev {prevNextHopIntfName}"
                            message = {"message_type": spacenet_gRPC_p2p_messaging.MININET_REMOVE_ROUTES, "message": gRPC_command}
                            controller_node_relay_message_to_sat_node(deviceName, message)
            # Now add new route if needed
            if not devHasPrevRoute or prevRouteNeedsChange:
                nextHopIP, nextHopIntfName = nextHopTuple
                if not use_node_python_script: # if sending commands via Mininet API
                    devObject = net.get(deviceName)
                    cmdString = 'ip route add ' + targetNetworkIP + ' via ' + nextHopIP + ' dev ' + nextHopIntfName
                    if global_verbose:
                        print(f"[{current_second}] Executing command on host " + deviceName + ": ", cmdString)
                    retval = devObject.cmd(cmdString + " 2> error.tmp")
                    #if (retval != 0):
                    #    print(f"Error: Could not add route for device {deviceName} to target network {targetNetworkIP}. Details:")
                    #    error = devObject.cmdPrint('cat error.tmp')
                    #    if 'Cannot find device' in error:
                    #        devObject.cmdPrint('ip link show')
                elif use_management_net_messaging and not management_net_messaging_to_all: # if sending commands via gRPC (TO DO: implement method to send via gRPC only to hardware nodes)
                    pass # TO DO:  IMPLEMENT METHOD TO SEND VIA gRPC ONLY TO HARDWARE NODES
                elif use_management_net_messaging and management_net_messaging_to_all: # if sending commands via gRPC (TO DO: implement method to send via gRPC only to hardware nodes)
                    gRPC_command = f"{targetNetworkIP} via {nextHopIP} dev {nextHopIntfName}"
                    message = {"message_type": spacenet_gRPC_p2p_messaging.MININET_ADD_ROUTES, "message": gRPC_command}
                    controller_node_relay_message_to_sat_node(deviceName, message)
        #if int(deviceName) >= TotalSatCnt: # if this is a ground station
        #    gsRoutesIncluded = True
    potentialDefaultGatewayNodes = [devName for devName in devDict.keys() if devName not in currRoutingDict.keys()]
    if nodeIndexDict is not None:
        potentialDefaultGatewayNodes = [devName for devName in potentialDefaultGatewayNodes if nodeIndexDict[devName]['type'] == 'CT'] # If using connectivity optimizer, only include nodes that are customer terminals
    defaultGatewayNodeList = []
    for devName in potentialDefaultGatewayNodes: # check if the device has only a single active interface
        devObject, _, devIntfList = devDict[devName]
        # Get list of all interface names for this device
        devIntfNameList = [devIntfTuple[0] for devIntfTuple in devIntfList] # devIntfTupe format: (intfName, intfIPandCDR, distHostName, distIntfIP)
        currLinksUp = [linkName for linkName in devIntfNameList if linkName in AllLinksDict[CurrEpochString].keys()]
        if len(currLinksUp) > 4: # if the device has more than four active interfaces
            print(f"\033[33m\tWARNING: Device {devName} is not in routing table but has more than one active interface this time interval. Skipping default route setup.\033[0m")
            continue
        defaultGatewayNodeList.append(devName)
    if global_verbose: print(f"\033[34mList of nodes to use default routes: {defaultGatewayNodeList}\033[0m")
    prevLinkNameList = list(AllLinksDict[PrevEpochString].keys())
    currLinkNameList = list(AllLinksDict[CurrEpochString].keys())
    for nodeName in defaultGatewayNodeList:
        linkNameFound = False
        for prevLinkName in prevLinkNameList: # find name of link to this node in previous epoch
            if nodeName in prevLinkName:
                linkNameFound = True
                break
        if linkNameFound: # if the node was not connected to a satellite in the previous epoch, check if link has changed and needs to be removed/updated
            if prevLinkName not in currLinkNameList:
                if global_verbose: print(f"  [{current_second}] \033[34mChange in connected sat for ground station {nodeName}\033[0m")
                try:
                    gsObject = net.get(nodeName)
                except KeyError:
                    print(f"\033[31mError: Ground station {nodeName} not found in Mininet\033[0m")
                    exit(-1)
                # Remove previous default route from GS
                if (not use_node_python_script) or (not use_management_net_messaging): # if sending commands via Mininet API
                    command = 'ip route del 0/0'
                    if global_verbose:
                        print(f"[{current_second}] Executing command on ground station {nodeName}: {command}")
                    gsObject.cmd(command)
                    retVal = set_GS_default_route(nodeName, CurrEpochString) # Set default route
                    if retVal == -1:
                        print(f"\033[31mError setting default route for {nodeName}.\033[0m")
                elif use_management_net_messaging and management_net_messaging_to_all: # if sending commands via gRPC (TO DO: implement method to send via gRPC only to hardware nodes)
                    message = {"message_type": spacenet_gRPC_p2p_messaging.MININET_REMOVE_ROUTES, "message": "0/0"}
                    controller_node_relay_message_to_sat_node(nodeName, message)
                    nextHopIP = set_GS_default_route(nodeName, CurrEpochString, gRPC_message = True)
                    message = {"message_type": spacenet_gRPC_p2p_messaging.MININET_ADD_DFLT_ROUTE, "message": f"{nextHopIP}"}
                    controller_node_relay_message_to_sat_node(nodeName, message)
    """
    if not gsRoutesIncluded: # if the routing file does not contain routes for GS's, set default routes for GS and routes for connected satellites, if needed
        prevLinkNameList = list(AllLinksDict[PrevEpochString].keys())
        currLinkNameList = list(AllLinksDict[CurrEpochString].keys())
        if use_connectivity_optimizer:
            gsList = [source_devName, dest_devName]
        else:
            gsList = [str(i) for i in range(TotalSatCnt, TotalSatCnt + TotalGSCnt)]
        for gsName in gsList:
            for prevLinkName in prevLinkNameList:
                if gsName in prevLinkName:
                    break # find name of link to GS in previous epoch
            if prevLinkName not in currLinkNameList: # GS no longer connected to previous satellite
                if global_verbose:
                    print(f"  [{current_second}] Change in connected sat for ground station {gsName}")
                try:
                    gsObject = net.get(gsName)
                except KeyError:
                    print(f"Error: Ground station {gsName} not found in Mininet")
                    exit(-1)
                # Remove previous default route from GS
                if (not use_node_python_script) or (not use_management_net_messaging): # if sending commands via Mininet API
                    command = 'ip route del 0/0'
                    if global_verbose:
                        print(f"[{current_second}] Executing command on ground station {gsName}: {command}")
                    gsObject.cmd(command) # Remove previous default route
                    retVal = set_GS_default_route(gsName, CurrEpochString)
        
                elif use_management_net_messaging and management_net_messaging_to_all: # if sending commands via gRPC (TO DO: implement method to send via gRPC only to hardware nodes)
                    message = {"message_type": spacenet_gRPC_p2p_messaging.MININET_REMOVE_ROUTES, "message": "0/0"}
                    controller_node_relay_message_to_sat_node(gsName, message)
                    nextHopIP = set_GS_default_route(gsName, CurrEpochString, gRPC_message = True)
                    message = {"message_type": spacenet_gRPC_p2p_messaging.MININET_ADD_DFLT_ROUTE, "message": f"{nextHopIP}"}
                    controller_node_relay_message_to_sat_node(gsName, message)
                # Remove routes to GS from satellites
    """

    if use_app_manager:
        appManager.rerun_app(TimeStepCounter) # Rerun app if needed (ie, CLI app)

    # End of loop
    TimeStepCounter += 1 
    if simTimeMode == "continuous":
        print(f"[{current_second}] (update_interval)  ~~~Interval update complete ({TimeStepCounter}/{TimeStepCount})~~~")
    else: # Discrete time mode (default)
        if use_app_manager and appManager.app_sleeps(): # Interval duration skipped for CLI app
            sleepTime = TimeStepDuration+10
            print(f"[{current_second}] ~~~Sleeping for {sleepTime} seconds ({TimeStepCounter}/{TimeStepCount})~~~")
            time.sleep(sleepTime)
# End of update_interval function

# ================== Main Function ==================
def main():
    if os.geteuid() != 0:
        print("ERROR - Mininet must be run as root. Aborting...", flush=True)
        return
    
    if len(sys.argv) > 1:
        global config_file_path, config_file_name
        config_file_path, config_file_name = os.path.split(sys.argv[1])
        if config_file_path == "":
            config_file_path = "./"
        else:
            config_file_path += "/" # returning the trailing slash to the path
        print(f"Using config file: {config_file_name}")

    global devDict, CurrRoutingDict, PrevRoutingDict
    global AllLinksDict, IntervalLinksDict, fullRoutingDict
    global thread_list
    global TimeStepCounter, TimeStepCount, TimeStepDuration, EpochCurrentDateTime
    global appManager
    global net
    global nodeIndexDict
    global simTimeMode, r2q, pre_ping, dynamic_link_queue_size
    nodeIndexDict = None

    if use_yaml_config:
        sim_config, constellation_config = spacenet_yaml_config.load_sim_and_constellation_config_file(config_file_path, config_file_name, sat_config_sub_path)
        if sim_config is None or constellation_config is None:
            print("Error loading configuration files.")
            return
        global del_app_results, output_path, global_verbose
        del_app_results = bool(sim_config["DeleteAppResults"])
        output_path = sim_config["ResultsFilePath"]
        global_verbose = bool(sim_config["Verbose"])
    else:
        sim_config, constellation_config = get_config_info()

    if global_verbose:
        global pprint
        import pprint

    constellationName = sim_config["ConstellationName"]
    use_connectivity_optimizer = sim_config["Optimize"]
    run_resource_logger = sim_config["MonitorResource"] if "MonitorResource" in sim_config else False
    simTimeMode = sim_config["SimTimeMode"] if "SimTimeMode" in sim_config else "discrete"
    r2q = sim_config["R2Q"] if "R2Q" in sim_config else r2q # use default value if not in config file
    dynamic_link_queue_size = sim_config["DynamicLinkQueueSize"] if "DynamicLinkQueueSize" in sim_config else dynamic_link_queue_size # use default value if not in config file
    pre_ping = sim_config["PrePing"] if "PrePing" in sim_config else pre_ping # use default value if not in config file 
    TotalSatCnt = int(constellation_config["TotalSatCnt"])
    TotalGSCnt = int(constellation_config["TotalGSCnt"])
    ConnectivityMatrixPath = sim_config["Phase1FilePath"]+"connectivity/starlink/"
    RoutingFilePath = sim_config["Phase1FilePath"]+"routing/starlink/"
    TimeStepDuration = int(constellation_config["SimLength"]["TimeStepDuration"])
    TimeStepCount = int(constellation_config["SimLength"]["TimeStepCount"])
    StartDateTime = constellation_config["StartDateTime"]
    EpochCurrentDateTime = StartDateTime
    TimeStepCounter = 0
    if simTimeMode == "continuous":
        global stop_event, update_lock, continuousTimeTotal
        continuousTimeTotal = TimeStepDuration * TimeStepCount
        stop_event = threading.Event()
        update_lock = threading.Lock()
    print("Config values:")
    print("  Constellation Name: ", constellationName)
    print("  Total satellites: ", TotalSatCnt)
    print("  Total ground stations: ", TotalGSCnt)
    print("  Connectivity Matrix Path: ", ConnectivityMatrixPath)
    print("  Routing File Path: ", RoutingFilePath)
    print("  Epoch Interval Duration: ", TimeStepDuration)
    print("  Epoch Interval Count: ", TimeStepCount)
    print("  Epoch Start Date/Time: ", StartDateTime)
    print("  Sim Time Mode: ", simTimeMode)
    if simTimeMode == "continuous":
        print("    Continuous Time Total: ", continuousTimeTotal)
    print("  R2Q: ", r2q)
    print("  Dynamic Link Queue Size: ", dynamic_link_queue_size)
    print("  Pre-Ping: ", pre_ping)
    print("  Verbose: ", global_verbose)

    ConnectivityFilePrefix = "topology_"
    ConnectivityFileSuffix = ".0.txt"
    RoutingFilePrefix = "routes_"
    RoutingFileSuffix = ".0.txt"

    if run_resource_logger:
        print("\n.......... Initiating resource logger")
        resource_log_process = multiprocessing.Process(target=TOP_LOGGER, args=(1, r"script_output/", 'mn_1584_10_10'))
        resource_log_process.start()
        atexit.register(lambda: os.kill(resource_log_process.pid, signal.SIGTERM))
        time.sleep(10)

    t0_mn = time.perf_counter_ns()

    # =================================================================
    net = Mininet(controller=None)
    # =================================================================

    # Select application to run in simulation (needs to be performed after net is declared)
    if use_app_manager:
        if use_yaml_config:
            appOptionsDict = {}
            appOptionsDict["AppName"] = sim_config["AppName"]
            appOptionsDict["SourceDeviceName"] = sim_config["SourceDeviceName"]
            appOptionsDict["DestDeviceName"] = sim_config["DestDeviceName"]
            appOptionsDict["CLIStartInterval"] = sim_config["CLIStartInterval"]
            appOptionsDict["CLIIntervalCount"] = sim_config["CLIIntervalCount"]
            if "PauseAtIntervalChange" in sim_config:
                appOptionsDict["PauseAtIntervalChange"] = sim_config["PauseAtIntervalChange"]
        else:
            appOptionsDict = None
        appRunTime = TimeStepCount * TimeStepDuration # Default application run time
        appManager = spacenet_app_manager.AppManager(totalSatCnt = TotalSatCnt, 
                                                     totalGSCnt = TotalGSCnt, 
                                                     devDict = devDict, 
                                                     appRunTime = appRunTime, 
                                                     intervalRunTime= TimeStepDuration, 
                                                     outputPath = output_path, 
                                                     delAppResults = del_app_results, 
                                                     net = net, 
                                                     verbose = global_verbose)
        appManager.select_app(appOptionsDict)
    else: # TO DO: Add support for other app managers
        print("No App Manager selected. Exiting...")
        exit()

    # Build topology with all satellites, ground stations, and links (then disable links as needed)
    if use_connectivity_optimizer:
        # Create ephemeral variants of the connectivity and routing files using only nodes that are part of the selected app
        # Must ensure node names remain consistent between the original and ephemeral files
        from lib import spacenet_connectivity_optimizer as spacenet_connectivity_optimizer
        source_devName, dest_devName = appManager.get_app_source_dest_devNames()
        if source_devName == None or dest_devName == None:
            print("Could not get source/dest device names from app manager; defaulting to first/second GS nodes")
            source_devName = str(TotalSatCnt)
            dest_devName = str(TotalSatCnt + 1)
        if type(source_devName) is not str:
            source_devName = str(source_devName)
        if type(dest_devName) is not str:
            dest_devName = str(dest_devName)
        print('..............................................................................................', constellation_config)
        nodeIndexFilePath = sim_config["Phase1FilePath"]+"node_indices/starlink/nodeindex_"+str(constellation_config["Sim_Date_Time"]["StartYear"])+"_"+str(constellation_config["Sim_Date_Time"]["StartMonth"])+"_"+str(constellation_config["Sim_Date_Time"]["StartDay"])+"_"+str(constellation_config["Sim_Date_Time"]["StartHour"])+"_"+str(constellation_config["Sim_Date_Time"]["StartMinute"])+"_"+str(float(constellation_config["Sim_Date_Time"]["StartSecond"]))+".txt"
        nodeIndexDict = spacenet_connectivity_optimizer.load_node_index_dict(nodeIndexFilePath)
        minimalNodeList, routeByIntervalDict = spacenet_connectivity_optimizer.find_minimal_node_list((ConnectivityMatrixPath, ConnectivityFilePrefix, ConnectivityFileSuffix), (RoutingFilePath, RoutingFilePrefix, RoutingFileSuffix), (StartDateTime, TimeStepCount, TimeStepDuration), (source_devName, dest_devName), nodeIndexDict)
        if global_verbose:
            print("Minimal node list: ", minimalNodeList)
        if minimalNodeList == None:
            print("Error: Using connectivity optimizer but could not find minimal node list! Exiting...")
            exit(-1)
    else:
        minimalNodeList = None
        routeByIntervalDict = None

    # Create nodes
    info("*** Creating nodes\n")
    if minimalNodeList:
        print(minimalNodeList)
        for nodeName in minimalNodeList: # Sats and GSs are included in minimalNodeList
            hostName = nodeName
            if int(hostName) >= TotalSatCnt: # GS
                hostIP = str(getNextGsIP())
                nodeType = "ground station"
            else: # Sat
                hostIP = str(getNextSatIP())
                nodeType = "satellite"
            hostObject = net.addHost(hostName, cls=LinuxRouter, ip=hostIP)
            devDict[hostName] = (hostObject, hostIP, [])
            print(f"Added {nodeType}: {hostName}, with management IP {hostIP}")
    else:
        for i in range(0, TotalSatCnt):
            hostName = str(i)
            hostIP = str(getNextSatIP())
            hostObject = net.addHost(hostName, cls=LinuxRouter, ip=hostIP)
            devDict[hostName] = (hostObject, hostIP, [])
            print("Added satellite: ", hostName, " with management IP: ", hostIP)
        for i in range(TotalSatCnt, TotalSatCnt + TotalGSCnt):
            hostName = str(i)
            hostIP = str(getNextGsIP())
            hostObject = net.addHost(hostName, cls=LinuxRouter, ip=hostIP)
            devDict[hostName] = (hostObject, hostIP, [])
            print("Added ground station: ", hostName, " with management IP: ", hostIP)

    # Compile links
    info("*** Compiling links from files\n")
    # AllLinksDict will contain all link statuses at every epoch
    # link_tracker will contain all links that have been created in the topology
    # We create all links before starting the network, then dynamically bring links up/down as needed
    AllLinksDict = parse_all_connectivity_files(ConnectivityMatrixPath, ConnectivityFilePrefix, ConnectivityFileSuffix, StartDateTime, TimeStepCount, TimeStepDuration, TotalSatCnt, minimalNodeList) # Returns dictionary of format {epochString: {linkName: (linkDelay, linkBandwidth)}}    
    # Create links
    info("*** Creating links\n")
    link_tracker = []
    for epochString in AllLinksDict:
        epochLinksDict = AllLinksDict[epochString]
        for linkName in epochLinksDict:
            linkDelay, linkBandwidth = epochLinksDict[linkName] # ??Where does linkBandwidth get incorporated?
            if linkName not in link_tracker: # if this link hasn't yet been created in the topology
                DevAhostName, DevBhostName = linkName.split("_")
                DevAObject, _, _ = devDict[DevAhostName]
                DevBObject, _, _ = devDict[DevBhostName]
                if (int(DevAhostName) >= TotalSatCnt) or (int(DevBhostName) >= TotalSatCnt): # Identify whether this is a link to a GS
                    LinkNetworkIP = getNextGsLinkNetworkIP()
                else:
                    LinkNetworkIP = getNextSatLinkNetworkIP()
                DevAIntfName = DevAhostName + '_' + DevBhostName
                DevBIntfName = DevAhostName + '_' + DevBhostName
                DevAIntfIP = str(ipaddress.ip_interface(str(LinkNetworkIP + 1) + '/30')) # Get IP for DevA interface
                DevBIntfIP = str(ipaddress.ip_interface(str(LinkNetworkIP + 2) + '/30')) # Get IP for DevB interface
                # Estimate necessary queue limit size based on bandwidth and delay
                max_segment_size = 1500 # default estimate
                if dynamic_link_queue_size:
                    computed_link_queue_size = (float(linkDelay) / 1000) * (float(linkBandwidth) * 1000000) / (8 * max_segment_size) # linkDelay is in ms; bandwidth is in Mbps
                    if computed_link_queue_size > max_netem_queue_size:
                        print(f"[[ Warning]] : Estimated link queue size for link {linkName} is {int(computed_link_queue_size):,} packets!! Setting to {max_netem_queue_size:,} packets.")
                    link_queue_size = int(max(1000, min(computed_link_queue_size, 20000))) # limit to 1000-20000 packets; larger values may cause Mininet to hang
                    if global_verbose:
                        print(f"  [{current_second}] Setting link queue size for link {linkName} to {link_queue_size} packets (bandwidth: {linkBandwidth} Mbps, delay: {linkDelay} ms)")
                else:
                    link_queue_size = default_netem_queue_size
                net.addLink(DevAhostName, DevBhostName, intfName1=DevAIntfName, intfName2=DevBIntfName, params1={'ip':DevAIntfIP}, params2={'ip':DevBIntfIP}, cls=TCLink, delay=linkDelay, max_queue_size=link_queue_size) # Add link to Mininet topology (where does bandwidth get used?)
                link_tracker.append(linkName)
                devDict[DevAhostName][2].append((DevAIntfName, DevAIntfIP, DevBhostName, DevBIntfIP)) # add link to device A interface list
                devDict[DevBhostName][2].append((DevBIntfName, DevBIntfIP, DevAhostName, DevAIntfIP)) # add link to device B interface list
    print(devDict) 
    # Compile Routes
    info("\n*** Compiling routes from files\n")
    fullRoutingDict = parse_all_routing_files(RoutingFilePath, RoutingFilePrefix, RoutingFileSuffix, StartDateTime, TimeStepCount, TimeStepDuration, TotalSatCnt, TotalGSCnt, routeByIntervalDict) # Returns dictionary of format {epochString: {deviceName: {targetNetworkIP: (nextHopIP, nextHopIntfName)}}}

    # Create management network
    if use_management_net_messaging:
        global managementNetDict, managementSwitchObject, cNodeObject
        info("*** Creating management node\n")
        hostIP = str(getNextManagementNetworkIP())
        cNodeObject = net.addHost(cNode_hostName, cls=LinuxRouter, ip=hostIP)
        if cNodeObject == None:
            print("Error: Could not create controller node")
            return -1
        managementNetDict[cNode_hostName] = hostIP

        info("*** Creating management switch\n")
        managementSwitchObject = net.addSwitch('s1')
        if managementSwitchObject == None:
            print("Error: Could not create management switch")
            return -1

        info("*** Creating link from controller node to management switch\n")
        linkName = 's1_' + cNode_hostName
        linkDelay = '0ms'
        #linkBandwidth = '1000'
        intfName = 's1_' + cNode_hostName
        intfIP = str(ipaddress.ip_interface(hostIP + '/12'))
        net.addLink('s1', cNode_hostName, intfName1=intfName, intfName2=intfName, params2={'ip':intfIP}, cls=TCLink, delay=linkDelay)#, bw=linkBandwidth)

        if management_net_messaging_to_all:
            # Create links from each satellite to the management switch
            info("*** Creating links from satellites to management switch\n")
            for devName in devDict.keys():
                linkName = 's1_' + devName
                linkDelay = '0ms'
                #linkBandwidth = '1000'
                managementIP = getNextManagementNetworkIP()
                intfName = 's1_' + devName
                intfIP = str(ipaddress.ip_interface(str(managementIP) + '/12'))
                print(f"  [{current_second}] Creating link from {devName} to management switch with IP {intfIP} and name {intfName}")
                net.addLink('s1', devName, intfName1=intfName, intfName2=intfName, params2={'ip':intfIP}, cls=TCLink, delay=linkDelay)#, bw=linkBandwidth)
                managementNetDict[devName] = str(managementIP)
        else:
            pass # TO DO:  Add links for just hardware nodes

    info("*** Starting network\n")
    if pause_before_run:
        input("Press Enter to start network...")
    net.start()

    if use_management_net_messaging:
        # Specify normal behavior for the switch (forward all packets - must be done after net.start() is called)
        managementSwitchObject.cmd('ovs-ofctl add-flow s1 action=normal')
        # Start thread to monitor FIFO for commands
        fifo_thread = threading.Thread(target=spacenet_fifo_messaging.monitor_fifo_for_commands, args=(monitor_FIFO, monitor_FIFO_callback, cNode_quit_command, fifo_break_command, global_verbose))
        fifo_thread.daemon = True
        fifo_thread.start()
        thread_list.append(fifo_thread)
        # Register FIFO loopbacks for specific signals to terminate FIFO loop
        signal.signal(signal.SIGINT, spacenet_fifo_messaging.end_fifo_loop) # Can only be done from main thread
        signal.signal(signal.SIGTERM, spacenet_fifo_messaging.end_fifo_loop) # Can only be done from main thread

    # =================================================================
    info ("*** Configuring hosts\n")

    # Correcting eth0 interface IP addresses - Mininet automatically assigns the host IP address to the first interface, so we need to correct them
    info("*** Correcting initial interface IP addresses\n") 
    for DeviceName in devDict:
        devObject, devManagementIP, devIntfList = devDict[DeviceName]
        # Assume the first interface in devIntfList is the interface that needs it's IP address corrected
        if len(devIntfList) == 0:
            print("Error: No interfaces found for device ", DeviceName)
            continue
        devIntfTuple = devIntfList[0]
        currIntfName, currIntfIPandCDR, _, _ = devIntfTuple
        currIntfIP = currIntfIPandCDR.split('/')[0]
        cmdString = 'ifconfig ' + currIntfName + ' ' + currIntfIP + ' netmask 255.255.255.252'
        print("Executing command on host " + DeviceName + ": ", cmdString)
        devObject.cmd(cmdString)

    # Creating loopback interface IP addresses
    info("*** Creating loopback interfaces\n")
    for key in devDict:
        devObject, devManagementIP, _ = devDict[key]
        cmdString = 'ifconfig lo ' + devManagementIP
        devObject.cmd(cmdString)
        print("Executing command on host " + key + ": ", cmdString)

    # disabling reverse path filtering based on Mohamed's code
    info ("*** Disabling reverse path filtering\n")
    for key in devDict:
        devObject, _, _ = devDict[key]
        ifacelist = devObject.cmd('ls /proc/sys/net/ipv4/conf').split()
        for iface in ifacelist:
            if iface != 'lo':
                devObject.cmd('sysctl -w net.ipv4.conf.'+iface+'.rp_filter=0')
    
    if (not use_node_python_script) or (not sats_self_manage_iptables): # Following code now done on client side using Python script, but can execute here if not using Python script on clients 
        # Set up iptables rule to modify source ip of all packets originating from a satellite to the satellite's lo int ip
        info ("*** Adding iptable rule for packets to use management IP as source instead of interface IP\n")
        for key in devDict:
            devObject, devManagementIP, devIntfList = devDict[key]
            for devIntfTuple in devIntfList: # for each interface on the device
                _, devIntfIP, _, _ = devIntfTuple
                cmdString = 'iptables -t nat -A POSTROUTING -s ' + devIntfIP.split('/')[0] + ' -j SNAT --to-source ' + devManagementIP.split('/')[0] # change the source IP from the interface IP to the management IP
                if global_verbose:
                    print("Executing command on host " + key + ": ", cmdString)
                devObject.cmd(cmdString)

    # =================================================================
    CurrEpochString = EpochCurrentDateTime.strftime("%Y_%m_%d_%H_%M_%S")
    info("*** Setting initial conditions at epoch ", CurrEpochString, "\n")

    info("*** Setting initial link states\n")
    # Set initial link states based on first epoch
    # AllLinksDict is dictionary of format {epochString: {linkName: (linkDelay, linkBandwidth)}}
    CurrTopoLinks = AllLinksDict[CurrEpochString] 
    for linkName in link_tracker:
            DevAhostName, DevBhostName = linkName.split("_")
            DevAObject = net.get(DevAhostName)
            DevBObject = net.get(DevBhostName)
            if linkName not in CurrTopoLinks: # link is not available in current epoch so disable it    
                #net.configLinkStatus(DevAObject, DevBObject, 'down') # This doesn't work
                cmdString = 'ip link set ' + linkName + ' down'
                print("Executing command on hosts ", DevAhostName, ", ", DevBhostName, ": ", cmdString)
                DevAObject.cmd(cmdString)
                DevBObject.cmd(cmdString)
                if global_verbose:
                    print(f"- Link {linkName} disabled")
            else:
                # Ensure link is enabled
                cmdString = 'ip link set ' + linkName + ' up'
                print("Executing command on hosts ", DevAhostName, ", ", DevBhostName, ": ", cmdString)
                DevAObject.cmd(cmdString)
                DevBObject.cmd(cmdString)
                # Set link delay and bandwidth
                linkDelay, linkBandwidth = AllLinksDict[CurrEpochString][linkName]
                linkList = net.linksBetween(DevAObject, DevBObject) # Get the link between the two hosts
                linkList[0].intf1.config(delay=str(linkDelay)+'ms', bw=float(linkBandwidth), max_queue_size=link_queue_size) # bandwidth is in Mbps
                linkList[0].intf2.config(delay=str(linkDelay)+'ms', bw=float(linkBandwidth), max_queue_size=link_queue_size)
                if global_verbose:
                    print("- Link ", linkName, " enabled with delay ", linkDelay, " and bandwidth ", linkBandwidth, " Mbps")

    print("Starting administrative timer thread") # Used to keep track of administrative time only - not used for simulation time
    timer_thread = threading.Thread(target=increment_timer)
    timer_thread.daemon = True
    timer_thread.start()
    thread_list.append(timer_thread)
    
    # ==== NODE PYTHON SCRIPT EXECUTION ====
    # Controller node (if using management network messaging)
    if use_management_net_messaging:
        # Start controller node with Python script - still needs sudo for iptables
        if use_python_virtual_env:
            cmdString = f"sudo bash {venv_bash_script_filename} {venv_name} {cNode_python_script_filename} {cNode_hostName} > {output_path}{cNode_python_script_filename.split('.')[0]}_output.txt 2>&1 &"
        else:
            cmdString = f"sudo python3 {cNode_python_script_filename} {cNode_hostName} > {output_path}{cNode_python_script_filename.split('.')[0]}_output.txt 2>&1 &"
        print(f"[{current_second}] Executing command on host {cNode_hostName} : {cmdString}")
        cNodeObject.popen(cmdString, shell=True) # Have to use popen to run in background; cmd hangs on subsequent commands

    # Satellite nodes
    if use_node_python_script:
        # Having each node run node python script
        info("*** Hosts running Python script\n")
        global sNode_python_script_filename, nodeStatusDict
        # Start all satellite nodes with Python scripts - sudo needed for NetFilter queues
        for hostName in devDict.keys():
            if use_python_virtual_env:
                #cmdString = f"sudo bash {venv_bash_script_filename} {venv_name} {sNode_python_script_filename} {hostName} > {output_path}{sNode_python_script_filename.split('.')[0]}_output_{hostName}.txt 2>&1 &"
                cmdPrefix = f"sudo bash {venv_bash_script_filename} {venv_name} {sNode_python_script_filename} {hostName}"
            else:
                #cmdString = f"sudo python3 {sNode_python_script_filename} {hostName} > {output_path}{sNode_python_script_filename.split['.'][0]}_output_{hostName}.txt 2>&1 &"
                cmdPrefix = f"sudo python3 {sNode_python_script_filename} {hostName}"
            if use_management_net_messaging:
                cmdPrefix += f" {managementNetDict[cNode_hostName]}"
            cmdSuffix = f" > {output_path}{sNode_python_script_filename.split('.')[0]}_output_{hostName}.txt 2>&1 &"
            cmdString = cmdPrefix + cmdSuffix
            print(f"[{current_second}] Executing command on host {hostName} : {cmdString}")
            devObject, _, _ = devDict[hostName]
            devObject.popen(cmdString, shell=True) # Have to use popen to run in background; cmd hangs on subsequent commands
            nodeStatusDict[hostName] = None

    # TO DO:  Allow this to be done via management network!!!
    #    Factors:  Nodes receiving this via management network must already be running their scripts
    info("*** Setting initial routing statements\n")
    if global_verbose:
        print(f"Routing dict for epoch {CurrEpochString}:")
        pprint.pprint(fullRoutingDict[CurrEpochString])
    #dictionary of format {epochString: {deviceName: {targetNetworkIP: (nextHopIP, nextHopIntfName)}}}
    #gsRoutesIncluded = False
    for deviceName in fullRoutingDict[CurrEpochString]: # for each device in the current epochs routing dictionary
        for targetNetworkIP in fullRoutingDict[CurrEpochString][deviceName]: # for each target network in the current devices routing dictionary
            nextHopIP, nextHopIntfName = fullRoutingDict[CurrEpochString][deviceName][targetNetworkIP]
            devObject, _, _ = devDict[deviceName]
            cmdString = 'ip route add ' + targetNetworkIP + ' via ' + nextHopIP + ' dev ' + nextHopIntfName
            print("Executing command on host " + deviceName + ": ", cmdString)
            devObject.cmd(cmdString)
            ## also send message via gRPC -- Can't send these yet as clients haven't run their Python scripts yet
            #devIP = devDict[deviceName][1].split('/')[0]
            #device_socket_address = devIP + ':' + str(gRPC_message_port_num)
            #message = {"message_type": MININET_ADD_ROUTES, "message": "test"}
            #send_gRPC_message_to_peer(device_socket_address, message)
        #if int(deviceName) >= TotalSatCnt: # if this is a ground station
        #    gsRoutesIncluded = True    
            
    # Get list of deviceNames from devDict that are not in fullRoutingDict[CurrEpochString]
    potentialDefaultGatewayNodes = [devName for devName in devDict.keys() if devName not in fullRoutingDict[CurrEpochString].keys()]
    if nodeIndexDict is not None:
        potentialDefaultGatewayNodes = [devName for devName in potentialDefaultGatewayNodes if nodeIndexDict[devName]['type'] == 'CT'] # If using connectivity optimizer, only include nodes that are customer terminals
    defaultGatewayNodeList = []
    for devName in potentialDefaultGatewayNodes: # check if the device has only a single active interface
        devObject, _, devIntfList = devDict[devName]
        # Get list of all interface names for this device
        devIntfNameList = [devIntfTuple[0] for devIntfTuple in devIntfList] # devIntfTupe format: (intfName, intfIPandCDR, distHostName, distIntfIP)
        currLinksUp = [linkName for linkName in devIntfNameList if linkName in AllLinksDict[CurrEpochString].keys()]
        if len(currLinksUp) > 4: # if the device has more than four active interfaces
            print(f"\033[33m\tWARNING: Device {devName} is not in routing table but has more than one active interface this time interval. Skipping default route setup.\033[0m")
            continue
        defaultGatewayNodeList.append(devName)
    if global_verbose: print(f"\033[34mDefault gateway nodes: {defaultGatewayNodeList}\033[0m")
    for nodeName in defaultGatewayNodeList:
        retVal = set_GS_default_route(nodeName, CurrEpochString)
        if retVal == -1:
            print(f"\033[31mError setting default route for {nodeName}.\033[0m")
    
    if use_node_python_script:
        if use_management_net_messaging:
            print(f"  [{current_second}] ~~Waiting for all nodes to report ready~~\n")
            wait_on_status_dict(nodeStatusDict, spacenet_gRPC_p2p_messaging.NODE_RESPONSE_READY, 60) # wait for all nodes to report ready
        else:
            print(f"  [{current_second}] ~~Sleeping for 10 seconds to allow python scripts to start running~~\n")
            time.sleep(10) # wait for the python scripts to start running
    # =================================================================
    # Attempt to populate ARP tables for all devices
    if pre_ping:
        parallel_ping_neighbors_with_retries(epochLinksDict=epochLinksDict, max_retries=4, timeout_factor=3)
    # =================================================================
    # If running simulation in continuous mode, start the update timing thread
    if simTimeMode == "continuous":
        print(f"[{current_second}] Starting continuous time mode update timing thread")
        update_timing_thread = threading.Thread(target=interval_update_timing_thread, args=(TimeStepDuration, TimeStepCount))
        update_timing_thread.daemon = True
        update_timing_thread.start()
        thread_list.append(update_timing_thread)

    # =================================================================
    if use_app_manager:
        # Application start
        #ApplicationRunTime = (TimeStepCount * TimeStepDuration)# - 5 # 5 second buffer
        print(f"[{current_second}] Starting application and running for {appManager.get_app_run_time()} seconds")
        #appManager.update_app_run_time(ApplicationRunTime)
        appManager.start_app(TimeStepCounter)
        t0_app = time.perf_counter_ns()

    # =================================================================
    TimeStepCounter += 1
    if global_verbose:
        print(f"[{current_second}] Simulating {len(devDict)} nodes")
    
    if simTimeMode == "continuous":
        print(f"[{current_second}] Starting continuous time mode main loop")
        start_time = time.time()

        while not stop_event.is_set():
            # Check every second for updates
            time.sleep(1)

            # Stop if we've exceeded our total run time
            if (time.time() - start_time) > continuousTimeTotal:
                break
    else: # Discrete mode (default)
        if appManager.app_sleeps(): # Does the app put the control script to sleep for interval duration? (Interval duration skipped for CLI app)
            sleepTime = TimeStepDuration+10
            print(f"[{current_second}] ~~~Sleeping for {sleepTime} seconds ({TimeStepCounter}/{TimeStepCount})~~~")
            time.sleep(sleepTime) # Wait initial interval duration before starting main program loop

        # Start of Loop
        while (TimeStepCounter < TimeStepCount):
            update_interval()
    
    # Application stop
    if use_app_manager:
        print(f"[{current_second}] Stopping application")
        tf_app = time.perf_counter_ns()
        appManager.stop_app()
    
    # Shutdown topology and services
    if use_management_net_messaging:
        print(f"[{current_second}] Signalling shutdown to all nodes")
        for deviceName in devDict.keys():
            message = {"message_type": spacenet_gRPC_p2p_messaging.MININET_CTRL_SHUTDOWN, "message": ""}
            controller_node_relay_message_to_sat_node(deviceName, message)
        print(f"[{current_second}] Waiting for all nodes to report halted")
        wait_on_status_dict(nodeStatusDict, spacenet_gRPC_p2p_messaging.NODE_RESPONSE_HALTED, 60)
        print(f"[{current_second}] All nodes halted")
        # Shutdown controller node
        print(f"[{current_second}] Shutting down controller node script")
        shutdown_controller_node_script()
        print(f"[{current_second}] Waiting for controller node to halt")
        wait_on_status_dict({cNode_hostName: None}, spacenet_gRPC_p2p_messaging.NODE_RESPONSE_HALTED, 10)
        print(f"[{current_second}] Controller node halted")
    
        spacenet_fifo_messaging.end_fifo_loop(0, None, global_verbose)

    print("Signalling shutdown to any running threads")
    end_main_loop(0, None)
    wait_on_threads()


    info("*** Stopping network")
    net.stop()

    if run_resource_logger:
        os.kill(resource_log_process.pid, signal.SIGTERM)

    print("EMU RUNTIME: " + str((time.perf_counter_ns() - t0_mn)*1e-9))
    print(f"APP TIME: {(tf_app-t0_app)*1e-9} seconds")

    exit()


if __name__ == '__main__':
    setLogLevel('info')
    main()
