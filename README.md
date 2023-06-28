# Space Network Emulator
## Mininet-based LEO Mega-constellations Emulator


The Emulator is divided into 5 steps. The main file to run is main_mn.py


### Step.1: Read input files - 
        
##### 1 - Read the TLE files        
```python
satellites = load.tle_file("https://celestrak.com/NORAD/elements/supplemental/starlink.txt")
```
    
##### 2 - Arrange the satellites in the correct orbits
```python
orbital_data = get_orbital_planes_classifications(data_path+"/starlink.txt",1)
```

##### 3 - Sort the satellites within an orbit -- This is important to identify the ISL links latter
```python
satellites_sorted_in_orbits.append(sort_satellites_in_orbit(satellites_in_orbit, actual_time))
```

##### 4- Read the ground stations files:
```python
ground_stations = read_gs("../mobility/ground_stations.txt")
```         

### Step.2: Build Topology and Links - 
#### Build the network topology, specifically, the Inter-Satellites-Links (mininet_add_ISLs) and GroundStation-Satellites-Links (mininet_add_GSLs), compute links charateristics in terms of latency, bandwidth and SNR

##### 1 - Add Inter-Satellites Links (ISLs)      
```python
connectivity_matrix = mininet_add_ISLs(connectivity_matrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, "SAME_ORBIT_AND_GRID_ACROSS_ORBITS", actual_time)
```
    
##### 2 - Add Ground Stations-Satellites Links (GSLs)  
```python
connectivity_matrix = mininet_add_GSLs(connectivity_matrix, satellites_by_name, satellites_by_index, ground_stations, 12, "BASED_ON_DISTANCE_ONLY_MININET", actual_time, 1, GS_SAT_Table)
```

##### 3 - Add Links Charateristics
```python
links_charateristics = calculate_link_charateristics_for_gsls_isls(connectivity_matrix, satellites_by_index, satellites_by_name, ground_stations, actual_time)
```

### Step.3: Routing and Mininet - 
#### Compute the all the routes to all nodes in the topology. We need these routes before we go into mininet to do initial routing table configuration for all nodes in Mininet. We then pass these info to Mininet to create the topology there
        
##### 1 - Static Routing       
```python
TopologyRoutes = get_topology_routes(FreshRun, data_path, num_of_satellites, satellites_by_index, ground_stations, connectivity_matrix, links_charateristics)
```
    
##### 2 - Generate IP Route Commands 
```python
prepare_routing_config_commands(topology, data_path, TopologyRoutes["All_PreConfigured_routes"], topg, list_of_Intf_IPs, satellites_by_index, 20);
```

### Step.4: Iterate


### Step.5: Run the applications
