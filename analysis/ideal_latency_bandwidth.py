''''

Propagation-Delay Only ISL/GSL Latency & Bandwidth

AUTHOR: Bruce L. Barbour, 2023
        Virginia Tech

This script computes the ideal latency and bandwidth between ground station and satellite nodes in a network 
based solely on propagation delay. It does not consider overhead/processing time.
'''

# =================================================================================== #
# ------------------------------- IMPORT PACKAGES ----------------------------------- #
# =================================================================================== #

from __future__ import annotations
import os
import re
import numpy as np

# =================================================================================== #
# -------------------------------- MAIN FUNCTION ------------------------------------ #
# =================================================================================== #

def calculate_ideal_latency_and_bandwidth(
                                            topology_dir        : str,
                                            optimal_path_file   : str
                                         ):
    """
    Calculates the network latency and bandwidth per timestep of a given simulation run, then 
    provides their average and standard deviation.

    Args:
        topology_dir (str):         Directory of the topology files to be analyzed
        optimal_path_file (str):    File for the optimal routes (per timestep) between source/destination (inclusively)

    Returns:
        np.ndarray:                 Array of latency values per timestep, measured in milliseconds
        np.ndarray:                 Mean and standard deviation of latency
        np.ndarray:                 Array of bandwidth values per timestep, measured in Mbps
        np.ndarray:                 Mean and standard deviation of bandwidth
    """

    # Check the directory of the topology files
    if not os.path.exists(topology_dir):
        raise FileNotFoundError("Please provide the correct path to the topology directory!")
    
    # Check if the optimal path file exists
    if not os.path.exists(optimal_path_file):
        raise FileNotFoundError("Please provide the correct path to the optimal path file!")
    
    # Retrieve the optimal paths from a simulation run
    optimal_paths       = []
    with open(optimal_path_file, 'r') as optimal_file:
        for best_path in optimal_file:
            best_path       = best_path[1:-2]
            nodes_in_path   = best_path.split(", ")
            optimal_paths.append([int(node) for node in nodes_in_path])

    # Collect topology filenames in the directory and sort them in numerical order
    topology_files      = []
    for top_file in os.listdir(topology_dir):
        topology_files.append(top_file)
    topology_files.sort(key=lambda x: tuple(map(int, re.findall(r'\d+', x))))

    # Check if the number of optimal paths is equal to the number of topology files
    if len(optimal_paths) != len(topology_files):
        raise IndexError("There must be the same number of topology files as there are optimal routes!")

    # Arrange the topology data into an array
    topology_hist       = []
    for topology_filename in topology_files:
        link_sequence   = []
        with open(topology_dir+topology_filename, 'r') as topology_file:
            for topology_line in topology_file:
                topology_contents   = topology_line.split(",")
                link_sequence.append([int(val) if indx < 2 else float(val) for indx, val in enumerate(topology_contents)])
        topology_hist.append(link_sequence)

    # Initialize output
    latency_per_timestep    = np.array([0., ] * len(optimal_paths))
    bandwidth_per_timestep  = np.array([0., ] * len(optimal_paths))

    # Iterate optimal paths and topology data to determine ideal latency -------------------------
    for path_indx, path in enumerate(optimal_paths):

        # Extract topology associated with timestep
        topology_at_timestep    = np.array(topology_hist[path_indx])

        # Initialize minimum bandwidth
        min_bandwidth           = float("inf")

        # Iterate over the optimal path at timestep
        for node_indx, _ in enumerate(path):

            # Disregard the final index in the array (only include pairs)
            if node_indx < (len(path) - 1):

                # Determine the subsequent node pair
                node0, node1    = path[node_indx:node_indx+2]

                # Condition to retrieve the node pair link characteristics
                condition       = (topology_at_timestep[:, 0] == node0) & (topology_at_timestep[:, 1] == node1)

                # Find the index of where the node-pair link characteristics exist
                link_char_indx  = np.where(condition)[0]

                # Sum up latency (doubled for round-trip)
                try:
                    latency_per_timestep[path_indx] += topology_at_timestep[link_char_indx, 2][0] * 2
                except:
                    print(node_indx, path_indx, topology_at_timestep[link_char_indx]) 
             
                # Determine lowest bandwidth in optimal path
                if topology_at_timestep[link_char_indx, 3][0] <= min_bandwidth:
                    min_bandwidth   = topology_at_timestep[link_char_indx, 3][0]
        
        # Save the minimum bandwidth
        bandwidth_per_timestep[path_indx]  = min_bandwidth

    # --------------------------------------------------------------------------------------------

    # Compute mean and standard deviation for latency
    mean_latency            = np.mean(latency_per_timestep, axis=0, dtype=np.float64)
    std_latency             = np.std(latency_per_timestep, axis=0, dtype=np.float64)

    # Compute mean and standard deviation for bandwidth
    mean_bandwidth          = np.mean(bandwidth_per_timestep, axis=0, dtype=np.float64)
    std_bandwidth           = np.std(bandwidth_per_timestep, axis=0, dtype=np.float64) 

    # Return output
    return (latency_per_timestep, np.array([mean_latency, std_latency]), 
            bandwidth_per_timestep, np.array([mean_bandwidth, std_bandwidth]))





# Testing Purposes ===============================================================================
if __name__ == "__main__":

    topology_dir    = "/home/mininet/simulator/constellation-simulator-main/utils/connectivity_matrix/starlink/starlink_topology_15s_300/"
    optimal_file    = "/home/mininet/simulator/constellation-simulator-main/analysis/optimal_routes/starlink/best_path_2023_12_04_21_5_285.0.txt"

    latency, latency_mean_std, bandwidth, bandwidth_mean_std = calculate_ideal_latency_and_bandwidth(topology_dir=topology_dir, optimal_path_file=optimal_file)
    print(latency, latency_mean_std)
    print(bandwidth, bandwidth_mean_std)
