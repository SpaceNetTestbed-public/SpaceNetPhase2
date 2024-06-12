# mininet_test
Dependencies:
- gRPC:  Follow instructions in gRPC Virtual Environment Notes.txt
- netfilterqueue: TBD
- netifaces: pip3 install netifaces
- yaml (pip3 install pyyaml | was already installed on SpaceNet VM)
- ???

Uses config files for simulator control (intended to be used as primary method to run)
- main_mn_config.yaml is default config; can specify alternate config files as command line argument
  + main_mn_config.yaml specifies:
    > path for script and app output files
    > whether to delete app output files after simulation stops
    > Name of application to run in simulator (don't have to match case, but preferred if you do)
    > Source and destination of application (Ping and iPerf accepts keywords firstGS, lastGS, firstSat, lastSat
    > Start interval and number of intervals to run application (CLI only)
- Constellation config files: use template file for reference (to include file naming convention)
 

TO DO:
- If management network is being used:
  + have initial routing configured via management network (verify current status/progress)
- Have modules imported only if needed/being used
- Incorporate config files
  + main configuration for simulator
  + seperate configurations for specific constellations
- Mininmum level of documentation
  + dependencies (and how to install)
  + how to run
  + expected output
  + available options
  + how to result RTLINK error manually

Later-on To Do:
- Resolve periodic gRPC transmission errors
- Ensure satellite node python scripts can perform initial routing entries

To Do for Dynamic routing:
- 
