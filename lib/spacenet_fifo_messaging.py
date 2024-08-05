#spacenet_fifo_messaging.py

import os # to use FIFO
#import signal # for graceful termination of script
import errno # for error handling
#import threading # for running the network monitoring in a separate thread
#import traceback # for printing exceptions

quit_command = "\!\Q"
fifo_break_command = "\!\B"


fifo_loop_running = True

def end_fifo_loop(signum, frame, verbose=False):
    global fifo_loop_running
    if verbose:
        print(f"(spacenet_fifo_messaging.end_fifo_loop) Received signal to end FIFO loop: {signum}", flush=True)
    fifo_loop_running = False

def monitor_fifo_for_commands(FIFO, callback_function, quit_command="\!\Q", fifo_break_command="\!\B", verbose=False):
    global fifo_loop_running
    if verbose:
        print(f"(spacenet_fifo_messaging.monitor_fifo_for_commands) Creating FIFO '{FIFO}'...")
    try:
        os.mkfifo(FIFO)
    except OSError as oe:
        if oe.errno != errno.EEXIST:
            raise
    
    # Listening for SIGINT/SIGTERM to end main loop
    #if threading.current_thread() is threading.main_thread():
    #    signal.signal(signal.SIGINT, end_fifo_loop) # Can only be done from main thread
    #    signal.signal(signal.SIGTERM, end_fifo_loop) # Can only be done from main thread
    #else:
    #    print("(spacenet_fifo_messaging.monitor_fifo_for_commands) WARNING: Signal handlers can only be set from the main thread")
    #    print("(spacenet_fifo_messaging.monitor_fifo_for_commands) Call stack:")
    #    traceback.print_stack()
    try:
        while fifo_loop_running:
            with open(FIFO, 'r') as fifo:
                if verbose:
                    print(f"(spacenet_fifo_messaging.monitor_fifo_for_commands) FIFO '{FIFO}' opened")
                while True:
                    raw_data = fifo.read()
                    if len(raw_data) == 0:
                        if verbose:
                            print(f'(spacenet_fifo_messaging.monitor_fifo_for_commands) Writer closed')
                        break
                    #data = data.strip() # Remove leading/trailing whitespace and any newline characters
                    # Process string to ensure we account for multiple commands in a single message
                    raw_data = raw_data.replace('\n', '').replace('\r', '') # Remove any potential newline characters
                    #replaced_data = raw_data.replace(fifo_break_command, '#') # Replace break command with hash to allow for split
                    #data_list = replaced_data.split('#')
                    data_list = raw_data.split(fifo_break_command)
                    data_list = [data for data in data_list if data] # Remove any potential empty strings
                    for data in data_list:
                        if verbose:
                            print(f"  (spacenet_fifo_messaging.monitor_fifo_for_commands) FIFO received message: {data}")
                        if quit_command in data:
                            if verbose:
                                print("(spacenet_fifo_messaging.monitor_fifo_for_commands) Received quit command.  Quitting...")
                            fifo_loop_running = False
                            break
                        else:
                            callback_function(data)
    except Exception as e:
        print(f"(spacenet_fifo_messaging.monitor_fifo_for_commands) Error - exception: {e}. Exiting...")