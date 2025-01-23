''''
Network Utility Test Post-Processing

PROJECT: Network Testbed for Small Satellites (NeTSat)

AUTHOR:         Bruce L. Barbour, 2023
                Virginia Tech
EDITED BY:      Jack Downs, 2024
                Virginia Tech


This Python script provides utility functions to perform post-processing of data from the
network utility tests conducted for the SpaceNet testbed simulations.
'''

# =================================================================================== #
# ------------------------------- IMPORT PACKAGES ----------------------------------- #
# =================================================================================== #

import os
import numpy as np
import csv
import yaml
import re
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from tqdm import tqdm

# =================================================================================== #
# ------------------------------ UTILITY FUNCTIONS ---------------------------------- #
# =================================================================================== #

# ----------------------------------------------------- #
# FUNCTION 1 : CHECKS FOR SCALING BASED ON STRING UNITS #
# ----------------------------------------------------- #
def check_unit_scaling(
                            data,
                            unit
                      ):
    """
    Checks the unit of the data and scales the numerical value appropriately.

    Args:
        data (str):     Uncorrected data string
        unit (str):     Unit of the data

    Returns:
        np.float64:     Corrected data converted into NumPy 64-bit float
    """

    # Define reference units to scale from
    ref_units = ['MBytes', 'Mbits/sec', 'ms']

    # x1/100000 unit
    times_oneover1M_unit = ['Bytes', 'bits/sec']

    # x1000 unit
    times_1K_unit = ['GBytes', 's']

    # x1/1000 unit
    times_oneover1K_unit = ['KBytes']

    # Check unit and then scale
    if unit in ref_units:
        return np.float64(data)         # Already at ref unit
    elif unit in times_oneover1M_unit:
        return 1e-6 * np.float64(data)  # Scaled by 1/1000000
    elif unit in times_1K_unit:
        return 1e3 * np.float64(data)   # Scaled by 1000
    elif unit in times_oneover1K_unit:
        return 1e-3 * np.float64(data)  # Scaled by 1/1000


# ----------------------------------------------------- #
# FUNCTION 2 : SEPARATE DATA BY OUTPUT FORMAT           #
# ----------------------------------------------------- #
def separate_content_by_test(
                                file_line,
                                line_index,
                                total_lines,
                                test_type
                            ):
    """
    Separates the contents based on the format of results from the network testing procedure, 
    e.g., ping or iPerf, and outputs it as an NumPy array or NumPy 64-bit float.

    Args:
        file_line (str):    Line of string from file
        line_index (int):   Index of line
        total_lines (int):  Total number of lines in file
        test_type (str):    The specific test used to produce the results,
                                > iPerf - 'iperf'
                                > Ping  - 'ping'

    Returns:
        np.ndarray or np.float64:     If iPerf, extracted data converted into NumPy array
                                      If ping, extracted data converted into NumPy 64-bit float
    """

    # Strip the line into words
    words = file_line.strip().split()

    # Check for the type of test
    if test_type == 'iperf':
        
        # Under iperf, it must contain "sec" to be data
        if 'sec' in words and line_index < total_lines - 1: # Accounts for last line being the sum

            # Reference index
            ref_indx = words.index('sec')

            # Return data
            return np.array([check_unit_scaling(words[ref_indx+1], words[ref_indx+2]), check_unit_scaling(words[ref_indx+3], words[ref_indx+4])])

    elif test_type == 'ping':

        # Under ping, it must contain "from" to be data
        if 'from' in words:

            # Reference index
            ref_indx = words.index('from')

            # Return data
            return check_unit_scaling(list(map(float, re.findall(r"[-+]?\d+(?:\.\d+)?", words[ref_indx+4])))[0], words[ref_indx+5])
    

# ----------------------------------------------------- #
# FUNCTION 3 : READ NETWORK UTILITY TEST OUTPUT         #
# ----------------------------------------------------- #
def read_text_file(
                    path_to_text_file,
                    input_dir,
                    test_type,
                    num_workers
                  ):
    """
    Reads a text file and extracts the contents into a usable list.

    Args:
        path_to_text_file (str):    Text file's location
        input_dir (str):            Specific directory the file is located in
        test_type (str):            The specific test used to produce the results,
                                        > iPerf - 'iperf'
                                        > Ping  - 'ping'
        num_workers (int):          Number of threads to utilize

    Returns:
        list:   Text file contents that are extracted into a list of quantities     
    """

    # Check if a file directory is given and real
    if path_to_text_file and os.path.exists(path_to_text_file) or os.path.exists(os.path.join(input_dir, path_to_text_file)):
        
        # Initialize output
        output = []

        # Read the contents of the file
        with open(path_to_text_file if os.path.exists(path_to_text_file) else os.path.join(input_dir, path_to_text_file), 'r') as file:

            # Length of file
            num_lines = len(open(path_to_text_file if os.path.exists(path_to_text_file) else os.path.join(input_dir, path_to_text_file), 'r').readlines())
           
            # Create Thread pool
            with ThreadPoolExecutor(max_workers=num_workers) as executor:

                # Submit tasks to thread pool
                output = list(tqdm(executor.map(separate_content_by_test,
                                                *list(zip(*[(line, index, num_lines, test_type) for index, line in enumerate(file)]))),
                                                total=num_lines))

        # Shut down thread pool
        executor.shutdown()

        # Filter output and return
        return np.vstack([array for array in output if array is not None])
    
    else:
        raise ValueError("Please provide the correct path to the .txt file!")


# ----------------------------------------------------- #
# FUNCTION 4 : COMPUTE MEAN AND STD. DEV. 	            #
# ----------------------------------------------------- #
def compute_mean_and_stddev(
                                path_to_text_file,
                                input_dir,
                                test_type,
                                num_workers
                           ):
    """
    Computes mean and sample/population standard deviation of the dataset.

    Args:
        path_to_text_file (str):    Text file's location
        input_dir (str):            Specific directory the file is located in
        test_type (str):            The specific test used to produce the results,
                                        > iPerf - 'iperf'
                                        > Ping  - 'ping'
        num_workers (int):          Number of threads to utilize

    Returns:
        list:   Mean and standard deviation of the dataset    
    """

    # Read and extract contents from file
    dataset = read_text_file(path_to_text_file=path_to_text_file, input_dir=input_dir,
                             test_type=test_type, num_workers=num_workers)
    
    # Compute and output the list of mean and variance
    if test_type == 'iperf':
        return [np.mean(dataset, axis=0), np.std(dataset, ddof=1, axis=0), np.std(dataset, axis=0)]
    elif test_type == 'ping':
        return [np.mean(dataset), np.std(dataset, ddof=1), np.std(dataset)]
    

# ----------------------------------------------------- #
# FUNCTION 5 : PLOT PING/IPERF PER TIME SEQ. 	        #
# ----------------------------------------------------- #
def plot_network_utility_results(
                                path_to_text_file,
                                main_config,
                                sat_config,
                                input_dir,
                                output_dir,
                                test_type,
                                num_workers
                                ):
    """
    Plots and saves a figure showing either latency vs sequence number or bandwidth vs time

    Args:
        path_to_text_file (str):    Dataset's text file location
        input_dir (str):            Specific directory the file is located in
        output_dir (str):           Specific directory to output the saved figure
        test_type (str):            The specific test used to produce the results,
                                        > iPerf - 'iperf'
                                        > Ping  - 'ping'
        num_workers (int):          Number of threads to utilize

    Returns:
        Matplotlib figure
    """

    # Read and extract contents from file
    dataset = read_text_file(path_to_text_file=path_to_text_file, input_dir=input_dir,
                             test_type=test_type, num_workers=num_workers)

    # Simulation configuration file
    sat_config_file = yaml.safe_load(open(sat_config, 'r'))
    main_config_file = yaml.safe_load(open(main_config, 'r'))

    # Determine the timestep of simulation
    ts = np.float64(sat_config_file['EpochIntervalDuration'])

    # Plot the data
    if test_type == "iperf":

        # Extract dataset to plot
        bandwidth_data = dataset[:, 1]

        # Generate time array
        time_array = [i * ts for i in range(int(len(bandwidth_data)/ts))]

        # Plot the points
        plt.scatter(time_array, bandwidth_data, color='black')

        # Plot the data as connected dots
        plt.plot(time_array, bandwidth_data, color='black', linewidth=0.75)

        # Add a grid to the plot
        plt.grid(visible=True, which='major', axis='both', color='k', linestyle='-', linewidth=0.5)

        # Plot title
        plt.title("IPerf3 Test: " + "gs" + str(main_config_file['SourceDeviceName'] - sat_config_file['TotalSatCnt']) + " - gs" + str(main_config_file['DestDeviceName'] - sat_config_file['TotalSatCnt']) + " Sim Length: " + str(sat_config_file['EpochIntervalDuration'] * sat_config_file['EpochIntervalCount']) + "s")

        # Axis labels
        plt.xlabel('Time (s)')
        plt.ylabel('Bandwidth (Mbps)')

        # Limit x-axis to start at 0
        plt.xlim(0, time_array[-1])


    elif test_type == "ping":

        # Extract dataset to plot
        latency_data = dataset[:, 0]

        # Generate x-axis data
        seq_array = [i for i in range(len(latency_data))]

        # Plot the points
        plt.scatter(seq_array, latency_data, color='black')

        # Plot the data as connected dots
        plt.plot(seq_array, latency_data, color='black', linewidth=0.75)

        # Add a grid to the plot
        plt.grid(visible=True, which='major', axis='both', color='k', linestyle='-', linewidth=0.5)
        
        # Plot title
        plt.title("Ping Test: " + "gs" + str(main_config_file['SourceDeviceName'] - sat_config_file['TotalSatCnt']) + " - gs" + str(main_config_file['DestDeviceName'] - sat_config_file['TotalSatCnt']) + " Sim Length: " + str(sat_config_file['EpochIntervalDuration'] * sat_config_file['EpochIntervalCount']) + "s")

        # Axis labels
        plt.xlabel('ICMP Sequence Number')
        plt.ylabel('Latency (ms)')

        # Limit x-axis to start at 0
        plt.xlim(0, seq_array[-1])

        # Save plot as a .png
        plt.savefig(output_dir+"plots/" + test_type+"_gs" + str(main_config_file['SourceDeviceName'] - sat_config_file['TotalSatCnt']) + "_gs" + str(main_config_file['DestDeviceName'] - sat_config_file['TotalSatCnt'])+'_'+str(sat_config_file['EpochIntervalDuration'] * sat_config_file['EpochIntervalCount'])+'.png')
    

# ----------------------------------------------------- #
# FUNCTION 6 : SAVE RESULTS TO A CSV FILE    	        #
# ----------------------------------------------------- #
def write_to_csv(path_to_text_file,
                 main_config,
                 sat_config,
                 input_dir,
                 output_dir,
                 test_type,
                 num_workers
                 ):
    """
    Saves either the latency or bandwidth data to a .csv file type

    Args:
        path_to_text_file (str):    Dataset's text file location
        input_dir (str):            Specific directory the file is located in
        output_dir (str):           Specific directory to output the saved file
        test_type (str):            The specific test used to produce the results,
                                        > iPerf - 'iperf'
                                        > Ping  - 'ping'
        num_workers (int):          Number of threads to utilize

    Returns:
        CSV file    
    """

    # Simulation configuration file
    sat_config_file = yaml.safe_load(open(sat_config, 'r'))
    main_config_file = yaml.safe_load(open(main_config, 'r'))

    # Read file and extract contents from dataset
    dataset = read_text_file(path_to_text_file=path_to_text_file, input_dir=input_dir,
                             test_type=test_type, num_workers=num_workers)
    latency_data = dataset[:, 0]
    seq_array = [i for i in range(len(latency_data))]
    
    # Ensure both arrays have the same length
    if len(seq_array) != len(latency_data):
        raise ValueError("Arrays must have the same length")
    
    # Define filename and directory
    filename = output_dir+"csv/"+test_type+"_gs" + str(main_config_file['SourceDeviceName'] - sat_config_file['TotalSatCnt']) + "_gs" + str(main_config_file['DestDeviceName'] - sat_config_file['TotalSatCnt'])+'_'+str(sat_config_file['EpochIntervalDuration'] * sat_config_file['EpochIntervalCount'])+'.csv'

    # Open the file in write mode
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        
        # Write the header
        writer.writerow(['Sequence', 'Latency'])
        
        # Write the data rows
        for seq, latency in zip(seq_array, latency_data):
            writer.writerow([seq, latency])

# =================================================================================== #
# --------------------------------------- RUN --------------------------------------- #
# =================================================================================== #

if __name__ == "__main__":


    # Read config file
    if os.path.exists('../analysis/postprocess_config.yml'):
        with open('../analysis/postprocess_config.yml', 'r') as config_file:
            config_data = yaml.safe_load(config_file)

    # Compute mean and std. dev.
    result = compute_mean_and_stddev(path_to_text_file=config_data['data_file'], input_dir=config_data['input_dir'], 
                                         test_type=config_data['test_type'], num_workers=int(config_data['threads']))
        
    # Plot the results
    if config_data['plot']:
        plot = plot_network_utility_results(path_to_text_file=config_data['data_file'], main_config=config_data['main_config'],
                                            sat_config=config_data['sat_config'], input_dir=config_data['input_dir'], 
                                            output_dir=config_data['output_dir'], test_type=config_data['test_type'], 
                                            num_workers=int(config_data['threads']))
        
    # Save the results to a CSV file
    if config_data['csv']:
        write_to_csv(path_to_text_file=config_data['data_file'], main_config=config_data['main_config'],
                     sat_config=config_data['sat_config'], input_dir=config_data['input_dir'], 
                     output_dir=config_data['output_dir'], test_type=config_data['test_type'], 
                     num_workers=int(config_data['threads']))
        
    # Print results
    #os.system('clear')
    print(("\nData: " + config_data['data_file']))
    if config_data['test_type'] == 'iperf':
        print(("\nMean:\t\t\t" + str(result[0][1]) + " Mbps\nStd. dev (samp.):\t" + str(result[1][1]) + " Mbps\nStd. dev (pop.):\t" + str(result[2][1]) + " Mbps\n\n"))
    elif config_data['test_type'] == 'ping':
        print(("\nMean:\t\t\t" + str(result[0]) + " ms\nStd. dev (samp.):\t" + str(result[1]) + " ms\nStd. dev (pop.):\t" + str(result[2]) + " ms\n\n"))
