#!/bin/bash

# Check if the script is being run by Bash
if [ -z "$BASH_VERSION" ]
then
    echo "This script must be run with Bash.  Try using the command 'bash $0'"
    exit 1
fi

# Check for sudo permissions
if [ $(id -u) -ne 0 ]
then
	echo "This script must be run with sudo"
	exit 1
fi

mn -c

# Now manually check for any interfaces that weren't cleaned up from the previous command
# Get list of interface names
interfaces=$(ip -o link show | awk -F': ' '{print $2}')

# Loop through the interfaces
for interface in $interfaces
do
	# If the interface name contains '@if'
	if [[ $interface == *@if* ]]
	then
		# Delete the interface
		interface_name=${interface%%@*}
		ip link delete $interface_name
		echo "Deleted interface $interface_name"
		#ip link delete $interface # Doesn't properly delete the interface - once comfortable this code isn't needed, we'll delete
		#echo "Deleted interface $interface"
	fi
done
