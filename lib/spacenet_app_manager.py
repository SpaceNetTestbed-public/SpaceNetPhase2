#spacenet_app_manager.py

from mininet.cli import CLI
from time import sleep # for sleeping 

class AppManager:
    def __init__(self, totalSatCnt, totalGSCnt, devDict, appRunTime = None, intervalRunTime = None, outputPath = "./", delAppResults = False, net = None, verbose = False): # receive 'global' application parameters
        self.app_list = ["Ping", "Iperf", "CLI"]
        self.app_source_devName = None
        self.app_dest_devName = None
        self.app_selection = None
        self.CLI_start_interval = None
        self.CLI_interval_count = None
        self.del_app_results = delAppResults
        self.total_sat_count = totalSatCnt
        self.total_gs_count = totalGSCnt
        self.appRunTime = appRunTime
        self.intervalRunTime = intervalRunTime
        self.output_path = outputPath
        self.device_dictionary = devDict
        self.net = net
        self.verbose = verbose
        self.app_object = None

    def get_app_source_dest_devNames(self):
        return self.app_source_devName, self.app_dest_devName
    
    def select_app(self, appOptionsDict = None):
        def resolve_keywords(devName):
            if devName == "firstGS":
                return self.total_sat_count
            elif devName == "firstSat":
                return 0
            elif devName == "lastGS":
                return self.total_sat_count + self.total_gs_count - 1
            elif devName == "lastSat":
                return self.total_sat_count - 1
            else:
                return devName
        if appOptionsDict is not None:
            app_name_list = ["Ping", "Iperf", "CLI"]
            selection = appOptionsDict["AppName"]
            app_selected = False
            for app in app_name_list:
                if selection.lower() == app.lower():
                    app_selected = True
                    self.app_selection = app
                    break
            if not app_selected:
                print(f"(spacenet_app_manager:AppManager:select_app) Invalid app selection. Given: {selection}; Acceptable options: {app_name_list}.")
                return
            if self.app_selection == "Ping" or self.app_selection == "Iperf":
                self.app_source_devName = appOptionsDict["SourceDeviceName"]
                self.app_dest_devName = appOptionsDict["DestDeviceName"]
                self.app_source_devName = resolve_keywords(self.app_source_devName)
                if self.app_source_devName < 0 or self.app_source_devName >= self.total_sat_count + self.total_gs_count:
                    print(f"(spacenet_app_manager:AppManager:select_app) Invalid source device selection. Given: {self.app_source_devName}; Acceptable options: 0 - {self.total_sat_count + self.total_gs_count - 1}.")
                    return
                self.app_dest_devName = resolve_keywords(self.app_dest_devName)
                if self.app_dest_devName < 0 or self.app_dest_devName >= self.total_sat_count + self.total_gs_count or self.app_dest_devName == self.app_source_devName:
                    print(f"(spacenet_app_manager:AppManager:select_app) Invalid destination device selection. Given: {self.app_dest_devName}; Acceptable options: 0 - {self.total_sat_count + self.total_gs_count - 1} excluding source device {self.app_source_devName}.")
                    return
                if self.app_dest_devName == self.app_source_devName:
                    print(f"(spacenet_app_manager:AppManager:select_app) Source and destination devices are the same. Please select different devices.")
                    return
                self.app_source_devName = str(self.app_source_devName)
                self.app_dest_devName = str(self.app_dest_devName)
                print(f"(spacenet_app_manager:AppManager:select_app) Running {self.app_selection} from nodes {self.app_source_devName} to {self.app_dest_devName}.")
                print(f"(spacenet_app_manager:AppManager:select_app) Output path: {self.output_path}; Delete app results: {self.del_app_results}; Verbose: {self.verbose}")
                if self.app_selection == "Ping":
                    # Check if Ping should pause during interval changes
                    pause_at_interval_change = False
                    if ("PauseAtIntervalChange" in appOptionsDict):
                        print(f'AppOptionsDict[PauseAtIntervalChange]: {appOptionsDict["PauseAtIntervalChange"]} (type: {type(appOptionsDict["PauseAtIntervalChange"])})')
                        if (appOptionsDict["PauseAtIntervalChange"] == True):
                            pause_at_interval_change = True
                    self.app_object = pingApp(self.device_dictionary, self.app_source_devName, self.app_dest_devName, self.appRunTime, self.intervalRunTime, self.output_path, self.del_app_results, pause_at_interval_change=pause_at_interval_change, verbose=self.verbose)
                elif self.app_selection == "Iperf":
                    self.app_object = iperfApp(self.device_dictionary, self.app_source_devName, self.app_dest_devName, self.appRunTime, self.intervalRunTime, self.output_path, self.del_app_results, self.verbose)
            elif self.app_selection == "CLI":
                self.CLI_start_interval = appOptionsDict["CLIStartInterval"]
                self.CLI_interval_count = appOptionsDict["CLIIntervalCount"]
                # Add source and destination nodes if specified (not required for CLI)
                if "SourceDeviceName" in appOptionsDict:
                    self.app_source_devName = appOptionsDict["SourceDeviceName"]
                    self.app_source_devName = resolve_keywords(self.app_source_devName)
                if "DestDeviceName" in appOptionsDict:
                    self.app_dest_devName = appOptionsDict["DestDeviceName"]
                    self.app_dest_devName = resolve_keywords(self.app_dest_devName)
                print(f"(spacenet_app_manager:AppManager:select_app) Running CLI starting at interval {self.CLI_start_interval} for {self.CLI_interval_count} intervals.")
                if (self.CLI_start_interval < 0) or (self.CLI_interval_count < 1):
                    print(f"(spacenet_app_manager:AppManager:select_app) Invalid CLI interval selection. Starting interval: {self.CLI_start_interval}; Interval count: {self.CLI_interval_count}.")
                    return
                self.app_object = CLIApp(self.net, self.CLI_start_interval, self.CLI_interval_count, self.verbose)
            return self.app_object
        else:
            print("Select an application to run:")
            for i, app in enumerate(self.app_list):
                print(f"{i+1}: {app}")
            selection_loop = True
            while selection_loop:
                try:
                    selection = int(input("Enter the number of the app to run: "))
                    if selection < 1 or selection > len(self.app_list):
                        print("Invalid selection. Please try again.")
                    else:
                        selection_loop = False
                except ValueError:
                    print("Invalid selection. Please try again.")
            self.app_selection = self.app_list[int(selection) - 1]
            if self.app_selection == "Ping" or self.app_selection == "Iperf":
                selection_loop = True
                while selection_loop:
                    try:
                        selection = int(input(f"Enter the number of the source device (0 - {self.total_sat_count + self.total_gs_count - 1}) [{self.total_sat_count}]: ") or self.total_sat_count)
                        if selection < 0 or selection >= self.total_sat_count + self.total_gs_count:
                            print("Invalid selection. Please try again.")
                        else:
                            self.app_source_devName = str(selection)
                            selection_loop = False
                    except ValueError:
                        print("Invalid selection. Please try again.")
                selection_loop = True
                while selection_loop:
                    try:
                        selection = int(input(f"Enter the number of the destination device (0 - {self.total_sat_count + self.total_gs_count - 1}) [{self.total_sat_count + self.total_gs_count - 1}]: ") or (self.total_sat_count + self.total_gs_count - 1))
                        if selection < 0 or selection >= self.total_sat_count + self.total_gs_count or selection == int(self.app_source_devName):
                            print("Invalid selection. Please try again.")
                        else:
                            self.app_dest_devName = str(selection)
                            selection_loop = False
                    except ValueError:
                        print("Invalid selection. Please try again.")
            if self.app_selection == "Ping":
                self.app_object = pingApp(self.device_dictionary, self.app_source_devName, self.app_dest_devName, self.app_run_time, self.intervalRunTime, self.output_path, self.del_app_results, self.verbose)
                return self.app_object
            elif self.app_selection == "Iperf":
                self.app_object = iperfApp(self.device_dictionary, self.app_source_devName, self.app_dest_devName, self.app_run_time, self.intervalRunTime, self.output_path, self.del_app_results, self.verbose)
                return self.app_object

            if self.app_selection == "CLI":
                selection_loop = True
                while selection_loop:
                    try:
                        selection = int(input(f"Enter CLI starting interval [0]: ") or 0)
                        self.CLI_start_interval = selection
                        selection_loop = False
                    except ValueError:
                        print("Invalid selection. Please try again.")
                selection_loop = True
                while selection_loop:
                    try:
                        selection = int(input(f"Enter CLI interval count [1]: ") or 1)
                        self.CLI_interval_count = selection
                        selection_loop = False
                    except ValueError:
                        print("Invalid selection. Please try again.")
                self.app_object = CLIApp(self.net, self.CLI_start_interval, self.CLI_interval_count, self.verbose)
                return self.app_object

    def start_app(self, current_interval):
        if self.app_object == None:
            print("(spacenet_app_manager.AppManager.start_app) No app selected. Please select an app.")
            return
        self.app_object.start(current_interval)

    def stop_app(self):
        if self.app_object == None:
            print("(spacenet_app_manager.AppManager.stop_app) No app selected. Please select an app.")
            return
        self.app_object.stop()

    def update_net(self, net):
        self.net = net
        self.app_object.update_net(self.net)

    def update_app_run_time(self, appRunTime):
        self.app_run_time = appRunTime
        self.app_object.update_app_run_time(appRunTime)

    def get_app_run_time(self):
        return self.app_object.get_app_run_time()
    
    def update_interval_run_time(self, intervalRunTime):
        self.intervalRunTime = intervalRunTime
        self.app_object.update_interval_run_time(intervalRunTime)

    def get_interval_run_time(self):
        return self.get_interval_run_time()

    def app_sleeps(self):
        if self.app_object == None:
            print("(spacenet_app_manager.AppManager.app_sleeps) No app selected. Please select an app.")
            return
        return self.app_object.does_app_sleep()
    
    def rerun_app(self, current_interval):
        if self.app_object == None:
            print("(spacenet_app_manager.AppManager.rerun_app) No app selected. Please select an app.")
            return
        self.app_object.start(current_interval)

    def get_output_file_and_path(self):
        return self.app_object.get_output_file_and_path()
    
    def print_to_output_file(self, output_text):
        self.app_object.print_to_output_file(output_text)

class pingApp:
    def __init__(self, devDict, app_source_devName, app_dest_devName, ApplicationRunTime, intervalRunTime, output_path, del_app_results, pause_at_interval_change = False, verbose = False):
        self.devDict = devDict
        self.app_source_devName = app_source_devName
        self.app_dest_devName = app_dest_devName
        self.app_run_time = ApplicationRunTime
        self.interval_run_time = intervalRunTime
        self.output_path = output_path
        self.del_app_results = del_app_results
        self.pause_at_interval_change = pause_at_interval_change
        self.verbose = verbose
        
        self.app_source_object = None
        self.app_source_ip = None
        self.app_dest_object = None
        self.app_dest_ip = None
        self.output_filename = "ping_results.txt"
        self.app_sleeps = True
        self.running = False
        self.use_bash_script = True
        self.bash_script = "ping_for_duration.sh"

        # Initialization tasks:
        print(f"(spacenet_app_manager:pingApp:init) Pausing at interval change: {self.pause_at_interval_change}")
        # If output path directory doesn't exist, create it
        import os
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
        # Delete the output file if it already exists
        import os
        if os.path.exists(f"{self.output_path}{self.output_filename}"):
            print(f"(spacenet_app_manager.startPing) Deleting existing output file {self.output_path}{self.output_filename}")
            os.remove(f"{self.output_path}{self.output_filename}")

    def start(self, current_interval = None):
        if self.running: # This indicates the app is already running and shouldn't be started again
            return
        if not self.pause_at_interval_change:
            self.running = True # If running for duration of simulation, prevent it from being re-run at each time interval (probably a better way to do this)
            appRunTime = self.app_run_time
        else:
            appRunTime = self.interval_run_time
        # Now that the device dictionary should be populated, get the source and destination devices and IPs
        self.app_source_object, self.app_source_ip, _ = self.devDict[self.app_source_devName]
        self.app_source_ip = self.app_source_ip.split('/')[0]
        self.app_dest_object, self.app_dest_ip, _ = self.devDict[self.app_dest_devName]
        self.app_dest_ip = self.app_dest_ip.split('/')[0]

        if self.verbose:
            print("*** Running Ping\n")
            print(f"Pinging from {self.app_source_ip} to {self.app_dest_ip}")
            print(f"self.app_run_time = {appRunTime} (type: {type(appRunTime)})")
            print(f"self.pause_at_interval_change = {self.pause_at_interval_change}")
        if self.use_bash_script:
            #cmdString = f"bash {self.bash_script} {self.app_dest_ip} {str(12)} >> {self.output_path}{self.output_filename} 2>&1 &"
            cmdString = f"bash {self.bash_script} {self.app_dest_ip} {str(appRunTime)} >> {self.output_path}{self.output_filename} 2>&1 &"
        else:
            #cmdString = f"ping {self.app_dest_ip} -v -O -w {str(12)} >> {self.output_path}{self.output_filename} 2>&1 &"
            cmdString = f"ping {self.app_dest_ip} -v -O -w {str(appRunTime)} >> {self.output_path}{self.output_filename} 2>&1 &"
        if self.verbose:
            print(f"{self.app_source_devName}: {cmdString}")
        self.app_source_object.popen(cmdString, shell=True) # Have to use popen to run in background; cmd hangs on subsequent commands
        if self.verbose:
            print(f"(spacenet_app_manager.startPing) Ping started in background", flush=True)

    def stop(self):
        if self.verbose:
            print("*** (spacenet_app_manager.pingApp.stop) Stopping Ping\n")
        self.app_source_object.cmd('kill %1')
        sleep(1)
        command = f"cat {self.output_path}{self.output_filename}"
        retVal = self.app_source_object.cmd(command)
        print(f"(spacenet_app_manager.pingApp.stop) Ping test results:\n{retVal}", flush=True)
        if self.del_app_results:
            command = f"rm -f {self.output_path}{self.output_filename}"
            self.app_source_object.cmd(command)
        self.running = False

    def update_net(self):
        pass

    def update_app_run_time(self, appRunTime):
        if not self.pause_at_interval_change:
            self.app_run_time = appRunTime

    def get_app_run_time(self):
        if self.pause_at_interval_change:
            return self.get_interval_run_time()
        return self.app_run_time

    def update_interval_run_time(self, intervalRunTime):
        self.interval_run_time = intervalRunTime

    def get_interval_run_time(self):
        return self.interval_run_time

    def does_app_sleep(self):
        return self.app_sleeps
    
    def get_output_file_and_path(self):
        if self.output_path and self.output_filename:
            return self.output_path+self.output_filename
        return None
    
    def print_to_output_file(self, output_text):
        output_path_and_filename = self.get_output_file_and_path()
        if output_path_and_filename and self.app_source_object:
            cmdString = f"echo {output_text} >> {output_path_and_filename}"
            self.app_source_object.popen(cmdString, shell=True)
            if self.verbose:
                print(f"(spacenet_app_manager.print_to_output_file) Printed {output_text} to {output_path_and_filename}")

class iperfApp:
    def __init__(self, devDict, app_source_devName, app_dest_devName, ApplicationRunTime, output_path, del_app_results, verbose = False):
        self.devDict = devDict
        self.app_source_devName = app_source_devName
        self.app_dest_devName = app_dest_devName
        self.app_run_time = ApplicationRunTime
        self.output_path = output_path
        self.del_app_results = del_app_results
        self.verbose = verbose

        self.app_source_object = None
        self.app_source_ip = None
        self.app_dest_object = None
        self.app_dest_ip = None
        self.server_output_filename = "iperf_server_results.txt"
        self.client_output_filename = "iperf_client_results.txt"
        self.app_sleeps = True
        self.running = False

        # Initialization tasks:
        # If output path directory doesn't exist, create it
        import os
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

    def start(self, current_interval = None):
        if self.running:
            return
        self.running = True
        # Now that the device dictionary should be populated, get the source and destination devices and IPs
        self.app_source_object, self.app_source_ip, _ = self.devDict[self.app_source_devName]
        self.app_source_ip = self.app_source_ip.split('/')[0]
        self.app_dest_object, self.app_dest_ip, _ = self.devDict[self.app_dest_devName]
        self.app_dest_ip = self.app_dest_ip.split('/')[0]

        if self.verbose:
            print("*** Running Iperf\n")
        if self.verbose:
            print("Iperf from ", self.app_source_ip, " to ", self.app_dest_ip)
        cmdString = f"iperf -s -p 5201 > {self.output_path}{self.server_output_filename} &"
        if self.verbose:
            print(f"{self.app_dest_devName}: {cmdString}")
        self.app_dest_object.cmd(cmdString)
        cmdString = f"iperf -c {self.app_dest_ip} -p 5201 -t {str(self.app_run_time)} -i 1 > {self.output_path}{self.client_output_filename} &"
        if self.verbose:
            print(f"{self.app_source_devName}: {cmdString}")
        self.app_source_object.cmd(cmdString)

    def stop(self):
        if self.verbose:
            print(f"*** (spacenet_app_manager.iperfApp.stop) Stopping Iperf\n")
        self.app_source_object.cmd('kill %1')
        self.app_dest_object.cmd('kill %1')
        sleep(1) # Wait a second for processes to end
        retVal = self.app_source_object.cmd(f"cat {self.output_path}{self.client_output_filename}")
        print('iPerf client results:\n', retVal)
        retVal = self.app_dest_object.cmd(f"cat {self.output_path}{self.server_output_filename}")
        print('iPerf server results:\n', retVal)
        if self.del_app_results:
            self.app_source_object.cmd(f"rm {self.output_path}{self.client_output_filename} -f")
            self.app_dest_object.cmd(f"rm {self.output_path}{self.server_output_filename} -f")
        self.running = False
    
    def update_net(self):
        pass

    def update_app_run_time(self, appRunTime):
        self.app_run_time = appRunTime

    def get_app_run_time(self):
        return self.app_run_time

    def update_interval_run_time(self, intervalRunTime):
        self.interval_run_time = intervalRunTime

    def get_interval_run_time(self):
        return self.interval_run_time

    def does_app_sleep(self):
        return self.app_sleeps
    
    def get_output_file_and_path(self):
        # Returns two filenames and paths
        server_output_file_and_path = None
        client_output_file_and_path = None
        if self.output_path: 
            if self.server_output_filename:
                server_output_file_and_path = self.output_path+self.server_output_filename
            if self.client_output_filename:
                client_output_file_and_path = self.output_path+self.client_output_filename
        return server_output_file_and_path, client_output_file_and_path

    def print_to_output_file(self, output_text):
        server_output_file_and_path, client_output_file_and_path = self.get_output_file_and_path()
        if server_output_file_and_path and client_output_file_and_path and self.app_source_object and self.app_dest_object:
            dest_cmdString = f"echo {output_text} >> {server_output_file_and_path}"
            source_cmdString = f"echo {output_text} >> {client_output_file_and_path}"
            self.app_dest_object.cmd(dest_cmdString)
            self.app_source_object.cmd(source_cmdString)
            if self.verbose:
                print(f"(spacenet_app_manager.print_to_output_file) Printed {output_text} to {server_output_file_and_path and {client_output_file_and_path}}")
class CLIApp:
    def __init__(self, net, starting_interval, CLI_count, verbose = False):
        self.net = net
        self.starting_interval = starting_interval
        self.CLI_count = CLI_count
        self.verbose = verbose

        self.app_sleeps = False

    def start(self, current_interval = None):
        if self.net == None:
            print("(spacenet_app_manager.CLIApp.start) No Mininet network provided. Please use CLIApp.update_net to provide a Mininet network.")
            return
        if current_interval == None:
            print("(spacenet_app_manager.CLIApp.start) No current interval provided. Please provide a current interval.")
            return
        if current_interval >= self.starting_interval and current_interval < self.starting_interval + self.CLI_count:
            if self.verbose:
                print("*** (spacenet_app_manager.CLIApp.start) Running CLI\n")
            try:
                CLI(self.net)
            except KeyboardInterrupt: # doesn't work
                print("CLI interrupted. Exiting...")
                self.net.stop()

    def stop(self):
        pass
    
    def update_app_run_time(self, appRunTime):
        self.app_run_time = appRunTime

    def get_app_run_time(self):
        return self.app_run_time

    def update_net(self, net): # used in the event of app selection prior to Mininet net creation
        self.net = net

    def does_app_sleep(self):
        return self.app_sleeps
    
    def get_output_file_and_path(self):
        return None # There is no output file
    
    def print_to_output_file(self, output_text):
        return # No output file to print to
