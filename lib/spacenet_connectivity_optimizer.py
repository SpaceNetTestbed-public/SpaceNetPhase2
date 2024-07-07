# spacenet_connectivity_optimizer.py
import datetime
import re # for regex use in filename identification
import os

global_verbose = True

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
        print(f"(spacenet_connectivity_optimizer:find_file_in_directory_with_dtg) Looking for file with pattern: {prefix}{target_year}_{target_month}_{target_day}_{target_hour}_{target_minute}_{target_second}{suffix}: ", end="")

    # Define regex pattern to match the date in the filename along with specific prefix and suffix
    file_pattern = re.compile(rf'{prefix}(\d{{1,4}})_(\d{{1,2}})_(\d{{1,2}})_(\d{{1,2}})_(\d{{1,2}})_(\d{{1,2}}){suffix}')

    for filename in os.listdir(directory):
        match = file_pattern.match(filename)
        if match:
            file_year, file_month, file_day, file_hour, file_minute, file_second = match.groups()
            if file_year == target_year and file_month.lstrip('0') == target_month and file_day.lstrip('0') == target_day and file_hour.lstrip('0') == target_hour and file_minute.lstrip('0') == target_minute and file_second.lstrip('0') == target_second.lstrip('0'):
                if global_verbose:
                    print(f"OK")
                return directory + filename
    print(f" ERROR: Could not find file with date: {prefix}_{target_year}_{target_month}_{target_day}_{target_hour}_{target_minute}_{target_second}{suffix}")
    return None

def parse_connectivity_files_for_connected_sats(connectivityFileTuple, epochTuple, endpointTuple):
    if global_verbose:
        print(f"(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) connectivityFileTuple: {connectivityFileTuple}, epoch details: {epochTuple}, endpoint details: {endpointTuple}")
    ConnectivityMatrixPath, ConnectivityFilePrefix, ConnectivityFileSuffix = connectivityFileTuple
    EpochStart, EpochIntervalCount, EpochIntervalDuration = epochTuple
    sourceGS, destinationGS = endpointTuple
    # Parse all connectivity files to identify all sat nodes connected to source and destination GS nodes
    sourceSatList = []
    destinationSatList = []
    endpointSatDict = {}
    for i in range(EpochIntervalCount):
        connectivityFile = find_file_in_directory_with_dtg(ConnectivityMatrixPath, ConnectivityFilePrefix, ConnectivityFileSuffix, EpochStart + datetime.timedelta(seconds=(i * EpochIntervalDuration)))
        if connectivityFile is None:
            print(f"(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) ERROR: Could not find connectivity file for epoch {i} at {EpochStart + datetime.timedelta(seconds=(i * EpochIntervalDuration))}")
            return None, None
        found_source = False
        found_destination = False
        with open(connectivityFile) as f:
            lines = f.readlines()
            for line in reversed(lines): # Reverse the lines so we find the last occurrence of the source and destination GS nodes without having to parse the entire file
                if not found_source and line.startswith(sourceGS):
                    sourceSatConnectivity = line.split(',')
                    sourceGSConnectingSat = sourceSatConnectivity[1]
                    if global_verbose:
                        print(f"Found Source {sourceGS} connecting to sat: {sourceGSConnectingSat}")
                    if sourceGSConnectingSat not in sourceSatList:
                        sourceSatList.append(sourceGSConnectingSat)
                    found_source = True
                if not found_destination and line.startswith(destinationGS):
                    destinationSatConnectivity = line.split(',')
                    destinationGSConnectingSat = destinationSatConnectivity[1]
                    if global_verbose:
                        print(f"Found Destination {destinationGS} connecting to sat: {destinationGSConnectingSat}")
                    if destinationGSConnectingSat not in destinationSatList:
                        destinationSatList.append(destinationGSConnectingSat)
                    found_destination = True
                if found_source and found_destination:
                    break
            if not found_source or not found_destination:
                print(f"(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) ERROR: Could not find source or destination GS nodes in connectivity file {connectivityFile}.  Source Node: {sourceGS}, Destination Node: {destinationGS}; SourceSatList={sourceSatList}, DestinationSatList={destinationSatList}.")
                return None, None
            endpointSatDict[i] = (sourceGSConnectingSat, destinationGSConnectingSat)
    if global_verbose:
        print(f"Source Satellites: {sourceSatList}")
        print(f"Destination Satellites: {destinationSatList}")
        print(f"Endpoint Satellite Dictionary: {endpointSatDict}")
    return endpointSatDict
    #return sourceSatList, destinationSatList

#def parse_routing_files_for_minimal_node_list(routingFileTuple, epochTuple, sourceSatList, destinationSatList):
def parse_routing_files_for_minimal_node_list(routingFileTuple, epochTuple, endpointSatDict):
    if global_verbose:
        #print(f"(spacenet_connectivity_optimizer:parse_routing_files_for_minimal_node_list): {routingFileTuple}, epoch details: {epochTuple}, source satellites: {sourceSatList}, destination satellites: {destinationSatList}")
        print(f"(spacenet_connectivity_optimizer:parse_routing_files_for_minimal_node_list): {routingFileTuple}, epoch details: {epochTuple}, endpoint satellites: {endpointSatDict}")
    RoutingFilePath, RoutingFilePrefix, RoutingFileSuffix = routingFileTuple
    EpochStart, EpochIntervalCount, EpochIntervalDuration = epochTuple
    # Parse all routing files to identify the minimal set of nodes that need to be connected to route between source and destination
    #minimalNodeList = sourceSatList + destinationSatList
    minimalNodeList = []
    for key in endpointSatDict:
        sourceSat, destinationSat = endpointSatDict[key]
        if sourceSat not in minimalNodeList:
            minimalNodeList.append(sourceSat)
        if destinationSat not in minimalNodeList:
            minimalNodeList.append(destinationSat)
    if global_verbose:
        print(f"(spacenet_connectivity_optimizer:parse_routing_files_for_minimal_node_list) Initial Minimal Node List: {minimalNodeList}")
    oldMinimalNodeListLen = 0
    while len(minimalNodeList) != oldMinimalNodeListLen: # Continue until no new nodes are added; we loop to make sure we get all routes between intervening nodes as well
        oldMinimalNodeListLen = len(minimalNodeList)
        for i in range(EpochIntervalCount):
            routingFile = find_file_in_directory_with_dtg(RoutingFilePath, RoutingFilePrefix, RoutingFileSuffix, EpochStart + datetime.timedelta(seconds=(i * EpochIntervalDuration)))
            if routingFile is None:
                print(f"(spacenet_connectivity_optimizer:parse_routing_files_for_minimal_node_list) ERROR: Could not find routing file for epoch {i} at {EpochStart + datetime.timedelta(seconds=(i * EpochIntervalDuration))}")
                return None
            sourceSat, destinationSat = endpointSatDict[i]
            with open(routingFile) as f:
                for line in f:
                    line = line.strip() # Remove leading/trailing whitespace
                    line = line.replace (' ', '') # Remove spaces (if any)
                    commaCount = line.count(',')
                    if commaCount == 0: # Ignore header line
                        continue
                    lineElements = line.split(',')
                    routeSourcenode = lineElements[0]
                    routeDestnode = lineElements[-1]
                    #if routeSourcenode in (sourceSatList + destinationSatList) and routeDestnode in (sourceSatList + destinationSatList):
                    if routeSourcenode == sourceSat and routeDestnode == destinationSat:
                    #if routeSourcenode in minimalNodeList and routeDestnode in minimalNodeList:
                    #if (lineElements[0] == 'Source' and lineElements[-1] == 'Destination') or (lineElements[0] == 'Destination' and lineElements[-1] == 'Source'): # Have to check both ways because the order of the nodes can be reversed
                        # Add intervening nodes to minimalNodeList if not already present
                        for node in lineElements[1:-1]: # For all intervening nodes between source and destination nodes
                            if node not in minimalNodeList:
                                minimalNodeList.append(node)
                                if global_verbose:
                                    print(f"(spacenet_connectivity_optimizer:parse_routing_files_for_minimal_node_list) Adding node {node} to minimal node list", end="\r")
    if global_verbose:
        print(f"(spacenet_connectivity_optimizer:parse_routing_files_for_minimal_node_list) Final Minimal Node List: {minimalNodeList}")
    return minimalNodeList

# Items needed: source sat for all intervals, destination sat for all intervals, EpochStart, EpochIntervalCount, EpochIntervalDuration
# Files needed: All connectivity files, all routing files
# Receive items as:
#  connectivity files: tuple: (ConnectivityMatrixPath, ConnectivityFilePrefix, ConnectivityFileSuffix)
#  routing files: tuple: (RoutingFilePath, RoutingFilePrefix, RoutingFileSuffix)
#  epoch details: tuple: (EpochStart, EpochIntervalCount, EpochIntervalDuration)
#  endpoint details: tuple: (sourceGS, destinationGS)
# NOTE:  Currently assumes both source and destination are GS nodes - will need to adjust logic if otherwise
def find_minimal_node_list(connectivityFileTuple, routingFileTuple, epochTuple, endpointTuple):
    if global_verbose:
        print(f"(spacenet_connectivity_optimizer:find_minimal_node_list) connectivity files: {connectivityFileTuple}, routing files: {routingFileTuple}, epoch details: {epochTuple}, endpoint details: {endpointTuple}")
    #sourceSatList, destinationSatList = parse_connectivity_files_for_connected_sats(connectivityFileTuple, epochTuple, endpointTuple)
    endpointSatDict = parse_connectivity_files_for_connected_sats(connectivityFileTuple, epochTuple, endpointTuple)
    #if sourceSatList is None or destinationSatList is None:
    #    return None
    #minimalNodeList = parse_routing_files_for_minimal_node_list(routingFileTuple, epochTuple, sourceSatList, destinationSatList)
    minimalNodeList = parse_routing_files_for_minimal_node_list(routingFileTuple, epochTuple, endpointSatDict)
    if minimalNodeList is None:
        return None
    sourceNode, destNode = endpointTuple
    if sourceNode not in minimalNodeList:
        minimalNodeList.append(sourceNode)
    if destNode not in minimalNodeList:
        minimalNodeList.append(destNode)
    minimalNodeList.sort()
    if global_verbose:
        print(f"(spacenet_connectivity_optimizer:find_minimal_node_list) Minimal Node List Length: {len(minimalNodeList)}")
        print(f"(spacenet_connectivity_optimizer:find_minimal_node_list) Minimal Node List: {minimalNodeList}")
    return minimalNodeList, endpointSatDict
    
