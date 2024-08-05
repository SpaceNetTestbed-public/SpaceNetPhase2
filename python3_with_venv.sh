#!/bin/bash

# Check for command line argument specifying the virtual environment name and python script filename
if [ $# -lt 3 ] || [ $# -gt 4 ]
then
    echo "Usage: $0 <virtual env name> <python script filename> <python script argument> (<python script argument>)"
    exit 1
fi
venv_name=$1
python_script=$2

# Start virtual environment
source $1/bin/activate
echo "Python virtual environment activated"

# Start Python Script
if [ $# -eq 3 ]
then
    python3 $2 $3
    exit 0
else
    python3 $2 $3 $4
    exit 0
fi

# Deactivate virtual environment
deactivate
echo "Python virtual environment deactivated"