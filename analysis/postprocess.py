''''
Network Utility Test Post-Processing

PROJECT: Network Testbed for Small Satellites (NeTSat)

AUTHOR: Bruce L. Barbour, 2023
        Virginia Tech

This Python script provides utility functions to perform post-processing of data from the
network utility tests conducted for the NeTSat/SpaceNet testbed simulations.
'''

# =================================================================================== #
# ------------------------------- IMPORT PACKAGES ----------------------------------- #
# =================================================================================== #

import os
import numpy as np
import yaml
import re
from concurrent.futures import ThreadPoolExecutor
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

    # Base units
    iperf_base_units = ['Bytes', 'bits/sec']
    ping_base_units = ['s']

    # Other units
    iperf_other_unit = ['GBytes']

    # Check unit and then scale
    if unit in ref_units:
        return np.float64(data)         # Already at ref unit
    elif unit in iperf_base_units:
        return 1e-6 * np.float64(data)  # Scaled by 1/1000000
    elif unit in ping_base_units:
        return 1e4 * np.float64(data)   # Scaled by 1000
    elif unit in iperf_other_unit:
        return 1e4 * np.float64(data)   # Scaled by 1000


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
    e.g., ping or iPerf, and outputs it as a list.

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
            return np.float64(check_unit_scaling(list(map(float, re.findall(r'\d+\.\d+', words[ref_indx+4])))[0], words[ref_indx+5]))
    

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
                                                *zip(*[(line, index, num_lines, test_type) for index, line in enumerate(file)])),
                                                total=num_lines))

        # Shut down thread pool
        executor.shutdown()

        # Filter output and return
        return np.vstack([array for array in output if array is not None])
    
    else:
        raise ValueError("Please provide the correct path to the .txt file!")


# ----------------------------------------------------- #
# FUNCTION 4 : COMPUTE MEAN AND STD. DEV. 	        #
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


# =================================================================================== #
# --------------------------------------- RUN --------------------------------------- #
# =================================================================================== #

if __name__ == "__main__":


    # Read config file
    if os.path.exists('postprocess_config.yml'):
        with open('postprocess_config.yml', 'r') as config_file:
            config_data = yaml.safe_load(config_file)

    # Mean and standard deviation
    if config_data['mean_and_stddev']:
        
        # Set main dictionary key
        mstd_key = config_data['mean_and_stddev']

        # Compute mean and std. dev.
        result = compute_mean_and_stddev(path_to_text_file=mstd_key['data_file'], input_dir=mstd_key['input_dir'], 
                                         test_type=mstd_key['test_type'], num_workers=int(mstd_key['threads']))
        
        # Print results
        #os.system('clear')
        print("\nData: " + mstd_key['data_file'])
        if mstd_key['test_type'] == 'iperf':
            print("\nMean:\t\t\t" + str(result[0][1]) + " Mbps\nStd. dev (samp.):\t" + str(result[1][1]) + " Mbps\nStd. dev (pop.):\t" + str(result[2][1]) + " Mbps\n\n")
        elif mstd_key['test_type'] == 'ping':
            print("\nMean:\t\t\t" + str(result[0]) + " ms\nStd. dev (samp.):\t" + str(result[1]) + " ms\nStd. dev (pop.):\t" + str(result[2]) + " ms\n\n")
