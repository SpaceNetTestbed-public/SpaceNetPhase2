## code written to read in bandwidth/latency data from simulation

import numpy as np

data = open("iperf_27oct.txt","r")
header = 5
lines = data.readlines()

index = 0
datalength = len(lines)-header

transfer = np.empty((datalength,1))
bandwidth = np.empty((datalength,1))

for line in lines:
	if index>header-1:
		bin1 = line.split(" ")

		transfer[index-header-1,0]=float(bin1[5])
		bandwidth[index-header-1,0]=float(bin1[7])

	elseif index>13:
		bin1 = line.split(" ")

		transfer[index-header-1,0]=float(bin1[4])
		bandwidth[index-header-1,0]=float(bin1[6])

	index = index + 1

avgtransfer = np.mean(transfer) #units of Mbytes
stdtransfer = np.std(transfer)

avgbandwidth = np.mean(bandwidth) #unit of Mbits/sec
stdbandwidth = np.std(bandwidth)

print avgbandwidth
print stdbandwidth
