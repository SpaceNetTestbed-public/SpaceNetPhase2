# spacenet_connectivity_optimizer.py
import datetime
import re # for regex use in filename identification
import os

global_verbose = True
start_color_string = "\033["
end_color_string = "\033[0m"
color_red = "31m"
color_green = "32m"
color_yellow = "33m"
color_blue = "34m"
color_default = "0m"

def load_node_index_dict(nodeIndexFilePath):
    # Returns dictionary of format: {nodeNumber: {'type': nodeType, 'identifier': nodeIdentifier}}
    # Check if file exists at given path
    if not os.path.exists(nodeIndexFilePath):
        print(f"{start_color_string}{color_red}(spacenet_connectivity_optimizer:build_node_index_dict) ERROR: Node Index File not found at path: {nodeIndexFilePath}{end_color_string}")
        return None
    # Build a dictionary of node names and their corresponding indices from the node index file
    nodeIndexDict = {}
    # Each line in the file should be in the format: nodeNumber:nodeName; nodeName is in format: nodeType-nodeIdentifier
    with open(nodeIndexFilePath) as f:
        for line in f:
            line = line.strip() # Remove leading/trailing whitespace
            line = line.replace (' ', '') # Remove spaces (if any)
            try:
                nodeNumber, nodeName = line.split(':')
                nodeType, nodeIdentifier = nodeName.split('-')
            except ValueError:
                print(f"{start_color_string}{color_red}(spacenet_connectivity_optimizer:build_node_index_dict) ERROR: Could not split line into node number, node name, node index, and type: {line}{end_color_string}")
                continue   
            nodeIndexDict[nodeNumber] = {'type': nodeType, 'identifier': nodeIdentifier}
    if global_verbose:
        print(f"(spacenet_connectivity_optimizer:build_node_index_dict) Loaded Node Index Dictionary with {len(nodeIndexDict.keys())} entries.")
    return nodeIndexDict

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
                    print(f"{start_color_string}{color_green}Found{end_color_string}")
                return directory + filename
    print(f" {start_color_string}{color_red}ERROR: Could not find file with date: {prefix}_{target_year}_{target_month}_{target_day}_{target_hour}_{target_minute}_{target_second}{suffix}{end_color_string}")
    return None

def parse_connectivity_files_for_connected_sats(connectivityFileTuple, epochTuple, endpointTuple, nodeIndexDict):
    if global_verbose:
        print(f"(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) connectivityFileTuple: {connectivityFileTuple}, epoch details: {epochTuple}, endpoint details: {endpointTuple}")
    ConnectivityMatrixPath, ConnectivityFilePrefix, ConnectivityFileSuffix = connectivityFileTuple
    EpochStart, EpochIntervalCount, EpochIntervalDuration = epochTuple
    sourceNode, destinationNode = endpointTuple
    nonConnectingNodeTypeList = ['CT']# , 'IE'] # List of node types that are not connected to more than one node at a time (e.g. Customer Terminals) thus may not be in the routing files
    sourceNodeConnectingNodeList = []
    destinationNodeConnectingNodeList = []
    sourceRequiresVariableConnection = True
    destinationRequiresVariableConnection = True
    # TROUBLESHOOTING
    if sourceNode not in nodeIndexDict.keys():
        print(f"{start_color_string}{color_red}(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) ERROR: Source Node {sourceNode} not found in node index dictionary.{end_color_string}")
        print(f"(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) Node Index Dictionary: {nodeIndexDict}")
        return None
    if destinationNode not in nodeIndexDict.keys():
        print(f"{start_color_string}{color_red}(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) ERROR: Destination Node {destinationNode} not found in node index dictionary.{end_color_string}")
        print(f"(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) Node Index Dictionary: {nodeIndexDict}")
        return None
    # END TROUBLESHOOTING
    if global_verbose: 
        try:
            print(f"(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) Source Node: {sourceNode} (type: {nodeIndexDict[sourceNode]['type']}), Destination Node: {destinationNode} (type: {nodeIndexDict[destinationNode]['type']})")
        except KeyError:
            print(f"{start_color_string}{color_yellow}(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) WARNING: Could not find source or destination node in node index dictionary.  Source Node: {sourceNode}, Destination Node: {destinationNode}{end_color_string}")
    if nodeIndexDict[sourceNode]['type'] not in nonConnectingNodeTypeList:
        if global_verbose: print(f"{start_color_string}{color_green}(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) Source node {sourceNode} is directly connected to the network.{end_color_string}")
        sourceNodeConnectingNodeList.append(sourceNode)
        sourceRequiresVariableConnection = False
    if nodeIndexDict[destinationNode]['type'] not in nonConnectingNodeTypeList:
        if global_verbose: print(f"{start_color_string}{color_green}(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) Destination node {destinationNode} is directly connected to the network.{end_color_string}")
        destinationNodeConnectingNodeList.append(destinationNode)
        destinationRequiresVariableConnection = False
    intervalConnectingNodeDict = {}
    if not sourceRequiresVariableConnection and not destinationRequiresVariableConnection:
        if global_verbose: 
            print(f"{start_color_string}{color_green}(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) Source and Destination nodes are already connected to the network.  No need to parse connectivity files.{end_color_string}")
        for intervalNum in range(EpochIntervalCount): # set the same connecting nodes for all intervals as sats and gateways are included in routing files
            intervalConnectingNodeDict[intervalNum] = (sourceNodeConnectingNodeList, destinationNodeConnectingNodeList)
        if global_verbose: print(f"(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) Interval Connecting Node Dictionary: {intervalConnectingNodeDict}")
        return intervalConnectingNodeDict

    # If source or destination nodes are not sats or gateways, parse all connectivity files to identify all nodes connected to source and destination nodes
    for intervalNum in range(EpochIntervalCount):
        connectivityFile = find_file_in_directory_with_dtg(ConnectivityMatrixPath, ConnectivityFilePrefix, ConnectivityFileSuffix, EpochStart + datetime.timedelta(seconds=(intervalNum * EpochIntervalDuration)))
        if connectivityFile is None:
            print(f"{start_color_string}{color_red}(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) ERROR: Could not find connectivity file for epoch {intervalNum} at {EpochStart + datetime.timedelta(seconds=(intervalNum * EpochIntervalDuration))}{end_color_string}")
            return None, None
        # These flags reset for each simulation interval
        foundSourceConnection = False
        foundDestinationConnection = False
        foundSourceConnectionList = False
        foundDestinationConnectionList = False
        sourceNodeNeedingConnection = sourceNode
        destinationNodeNeedingConnection = destinationNode

        with open(connectivityFile) as f:
            lines = f.readlines()
        lines = reversed(lines) # Reverse the lines so we find the last occurrence of the source and destination GS nodes without having to parse the entire file (as CTs, gateways, and IEs are at the end of the files)
        while (sourceRequiresVariableConnection and not foundSourceConnectionList) or (destinationRequiresVariableConnection and not foundDestinationConnectionList): # Keep parsing the file until we find all the connecting nodes for the source and destination nodes
            for line in lines: 
                if sourceRequiresVariableConnection and not foundSourceConnectionList and line.startswith(sourceNodeNeedingConnection):
                    sourceNodeConnectivity = line.split(',')
                    sourceNodeConnectingNode = sourceNodeConnectivity[1]
                    if global_verbose:
                        print(f"{start_color_string}{color_green}(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) Found Source {sourceNode} connecting to sat: {sourceNodeConnectingNode}{end_color_string}")
                    if sourceNodeConnectingNode not in sourceNodeConnectingNodeList:
                        sourceNodeConnectingNodeList.append(sourceNodeConnectingNode)
                    foundSourceConnection = True
                    if nodeIndexDict[sourceNodeConnectingNode]['type'] not in nonConnectingNodeTypeList:
                        foundSourceConnectionList = True
                if destinationRequiresVariableConnection and not foundDestinationConnectionList and line.startswith(destinationNodeNeedingConnection):
                    destinationNodeConnectivity = line.split(',')
                    destinationNodeConnectingNode = destinationNodeConnectivity[1]
                    if global_verbose:
                        print(f"{start_color_string}{color_green}Found Destination {destinationNode} connecting to sat: {destinationNodeConnectingNode}{end_color_string}")
                    if destinationNodeConnectingNode not in destinationNodeConnectingNodeList:
                        destinationNodeConnectingNodeList.append(destinationNodeConnectingNode)
                    foundDestinationConnection = True
                    if nodeIndexDict[destinationNodeConnectingNode]['type'] not in nonConnectingNodeTypeList:
                        foundDestinationConnectionList = True
                if foundSourceConnectionList and foundDestinationConnectionList:
                    break
            if (sourceRequiresVariableConnection and not foundSourceConnectionList and not foundSourceConnection) or (destinationRequiresVariableConnection and not foundDestinationConnectionList and not foundDestinationConnection):
                print(f"{start_color_string}{color_red}(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) ERROR: Could not find source or destination GS nodes in connectivity file {connectivityFile}.  Source Node: {sourceNode}, Destination Node: {destinationNode}; SourceSatList={sourceNodeConnectingNodeList}, DestinationSatList={destinationNodeConnectingNodeList}.{end_color_string}")
                return None, None
        intervalConnectingNodeDict[intervalNum] = (sourceNodeConnectingNodeList, destinationNodeConnectingNodeList)
        if global_verbose: print(f"(spacenet_connectivity_optimizer:parse_connectivity_files_for_connected_sats) Interval {intervalNum} Connecting Node Dictionary: {intervalConnectingNodeDict[intervalNum]}")
        sourceNodeConnectingNodeList = [] # Now reset the connecting node lists for the next time increment
        destinationNodeConnectingNodeList = []
    if global_verbose:
        print(f"Source Node Connecting List: {sourceNodeConnectingNodeList}")
        print(f"Destination Node Connecting List: {destinationNodeConnectingNodeList}")
        print(f"Interval Connecting Node Dictionary: {intervalConnectingNodeDict}")
    return intervalConnectingNodeDict
    #return sourceSatList, destinationSatList

#def parse_routing_files_for_minimal_node_list(routingFileTuple, epochTuple, sourceSatList, destinationSatList):
def parse_routing_files_for_minimal_node_list(routingFileTuple, epochTuple, endpointConnectingNodeByIntervalDict, endpointTuple):
    if global_verbose:
        #print(f"(spacenet_connectivity_optimizer:parse_routing_files_for_minimal_node_list): {routingFileTuple}, epoch details: {epochTuple}, source satellites: {sourceSatList}, destination satellites: {destinationSatList}")
        print(f"(spacenet_connectivity_optimizer:parse_routing_files_for_minimal_node_list): {routingFileTuple}, epoch details: {epochTuple}, endpoint connecting nodes by interval: {endpointConnectingNodeByIntervalDict}")
    RoutingFilePath, RoutingFilePrefix, RoutingFileSuffix = routingFileTuple
    EpochStart, EpochIntervalCount, EpochIntervalDuration = epochTuple
    # Parse all routing files to identify the minimal set of nodes that need to be connected to route between source and destination
    #minimalNodeList = sourceSatList + destinationSatList
    #minimalNodeList = []
    #for key in endpointSatDict:
    #    sourceSat, destinationSat = endpointSatDict[key]
    #    if sourceSat not in minimalNodeList:
    #        minimalNodeList.append(sourceSat)
    #    if destinationSat not in minimalNodeList:
    #        minimalNodeList.append(destinationSat)
    #if global_verbose:
    #    print(f"(spacenet_connectivity_optimizer:parse_routing_files_for_minimal_node_list) Initial Minimal Node List: {minimalNodeList}")
    routeByIntervalDict = {}
    for epochIntervalNum in range(EpochIntervalCount):
        routingFile = find_file_in_directory_with_dtg(RoutingFilePath, RoutingFilePrefix, RoutingFileSuffix, EpochStart + datetime.timedelta(seconds=(epochIntervalNum * EpochIntervalDuration)))
        if routingFile is None:
            print(f"{start_color_string}{color_red}(spacenet_connectivity_optimizer:parse_routing_files_for_minimal_node_list) ERROR: Could not find routing file for epoch {epochIntervalNum} at {EpochStart + datetime.timedelta(seconds=(epochIntervalNum * EpochIntervalDuration))}{end_color_string}")
            return None
        sourceConnectingNodeList, destinationConnectingNodeList = endpointConnectingNodeByIntervalDict[epochIntervalNum]
        if len(sourceConnectingNodeList) > 0:
            sourceConnectingNode = sourceConnectingNodeList[-1]  # The last node in the list is the one that connects to the routed network (all prior nodes are intermediate between connecting node and source node)
        else:
            sourceConnectingNode = None
        if len(destinationConnectingNodeList) > 0:
            destinationConnectingNode = destinationConnectingNodeList[-1] # The last node in the list is the one that connects to the routed network (all prior nodes are intermediate between connecting node and destination node)
        else:
            destinationConnectingNode = None
        sourceNode, destinationNode = endpointTuple
        candidate_pairs_list = []
        if sourceConnectingNode is not None:
            candidate_pairs_list.append((sourceConnectingNode, destinationNode))
        if destinationConnectingNode is not None:
            candidate_pairs_list.append((sourceNode, destinationConnectingNode))
        if sourceConnectingNode is not None and destinationConnectingNode is not None:
            candidate_pairs_list.append((sourceConnectingNode, destinationConnectingNode))
        best_route = None
        best_route_len = float("inf") # Initialize to infinity so that any route found will be shorter
        with open(routingFile) as f:
            for line in f: # First check whether an entry in the file is a direct route
                line = line.strip() # Remove leading/trailing whitespace
                line = line.replace(' ','') # Remove spaces (if any)
                commaCount = line.count(',')
                if commaCount == 0: #Ignore header line
                    continue # move to next line
                lineElements = line.split(',')
                routeSourcenode = lineElements[0]
                routeDestnode = lineElements[-1]
                if (routeSourcenode == sourceNode and routeDestnode == destinationNode) or (routeDestnode == sourceNode and routeSourcenode == destinationNode): # Route between source and destination nodes explicitly included in routing file
                    best_route = lineElements # Store the route for this interval
                    break
                # If not a direct route, check if it is a candidate pair
                for candidate_pair in candidate_pairs_list:
                    if (routeSourcenode == candidate_pair[0] and routeDestnode == candidate_pair[1]) or (routeSourcenode == candidate_pair[1] and routeDestnode == candidate_pair[0]):
                        if len(lineElements) < best_route_len:
                            best_route = lineElements
                            best_route_len = len(lineElements)

        if not best_route:
            print(f"{start_color_string}{color_red}(spacenet_connectivity_optimizer:parse_routing_files_for_minimal_node_list) ERROR: Could not find route between {sourceConnectingNode} and {destinationConnectingNode} in routing file {routingFile}{end_color_string}")
            return None
        routeByIntervalDict[epochIntervalNum] = best_route
        if global_verbose: 
            print(f"{start_color_string}{color_green}(spacenet_connectivity_optimizer:parse_routing_files_for_minimal_node_list) Found route between {sourceConnectingNode} and {destinationConnectingNode} in routing file {routingFile}: {routeByIntervalDict[epochIntervalNum]}{end_color_string}")
    return routeByIntervalDict

# Items needed: source sat for all intervals, destination sat for all intervals, EpochStart, EpochIntervalCount, EpochIntervalDuration
# Files needed: All connectivity files, all routing files
# Receive items as:
#  connectivity files: tuple: (ConnectivityMatrixPath, ConnectivityFilePrefix, ConnectivityFileSuffix)
#  routing files: tuple: (RoutingFilePath, RoutingFilePrefix, RoutingFileSuffix)
#  epoch details: tuple: (EpochStart, EpochIntervalCount, EpochIntervalDuration)
#  endpoint details: tuple: (sourceGS, destinationGS)
# NOTE:  Currently assumes both source and destination are GS nodes - will need to adjust logic if otherwise
def find_minimal_node_list(connectivityFileTuple, routingFileTuple, epochTuple, endpointTuple, nodeIndexDict):
    if global_verbose:
        print(f"(spacenet_connectivity_optimizer:find_minimal_node_list) connectivity files: {connectivityFileTuple}, routing files: {routingFileTuple}, epoch details: {epochTuple}, endpoint details: {endpointTuple}")
    #sourceSatList, destinationSatList = parse_connectivity_files_for_connected_sats(connectivityFileTuple, epochTuple, endpointTuple)
    endpointConnectingNodeByIntervalDict = parse_connectivity_files_for_connected_sats(connectivityFileTuple, epochTuple, endpointTuple, nodeIndexDict)
    if endpointConnectingNodeByIntervalDict is None:
        return None, None
    #if sourceSatList is None or destinationSatList is None:
    #    return None
    #minimalNodeList = parse_routing_files_for_minimal_node_list(routingFileTuple, epochTuple, sourceSatList, destinationSatList)
    routeByIntervalDict = parse_routing_files_for_minimal_node_list(routingFileTuple, epochTuple, endpointConnectingNodeByIntervalDict, endpointTuple)
    if routeByIntervalDict is None:
        return None, None
    sourceNode, destinationNode = endpointTuple
    minimalNodeList = [sourceNode, destinationNode]
    for interval in routeByIntervalDict.keys():
        route = routeByIntervalDict[interval]
        #DEBUG
        print(f"{start_color_string}{color_red}routeByIntervalDict[{interval}]: {route}{end_color_string}")
        #END DEBUG
        for node in route:
            if node not in minimalNodeList:
                minimalNodeList.append(node)
    # DEBUG
    print(f"{start_color_string}{color_yellow}Raw minimalNodeList: {minimalNodeList}{end_color_string}")
    # END DEBUG
    minimalNodeList = list(set(minimalNodeList)) # to ensure no duplicate nodes
    if global_verbose:
        print(f"{start_color_string}{color_green}(spacenet_connectivity_optimizer:find_minimal_node_list) Minimal Node List: {minimalNodeList}{end_color_string}")
        print(f"{start_color_string}{color_green}(spacenet_connectivity_optimizer:find_minimal_node_list) Route by Interval Dictionary: {routeByIntervalDict}{end_color_string}")
    return minimalNodeList, routeByIntervalDict
    
