#!/bin/bash

wget http://10.34.20.13/simulator_data.zip
unzip simulator_data.zip -d ./utils
cd utils/simulator_data
cp -r connectivity_matrix/ routing/ oneweb_tles/ starlink_tles/ ../
cd ../
sudo rm -r simulator_data
cd ../
sudo rm -r simulator_data.zip

echo "---> Done, simulaator data copied"
