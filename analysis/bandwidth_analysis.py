## code written to read in bandwidth/latency data from simulation

import numpy as np

data = open("iperf_27oct_NYtoLondon.txt","r")
header = 6
lines = data.readlines()

index = 0
datalength = len(lines)-header

transfer = np.empty((datalength,1))
bandwidth = np.empty((datalength,1))

for line in lines:
	if index>header-1 and index<=14:
		bin1 = line.split(" ")
#		print bin1
		transfer[index-header-1,0]=float(bin1[5])
		if bin1[7]== '':
			bandwidth[index-header-1,0]=float(bin1[7+1])
		else:
			bandwidth[index-header-1,0]=float(bin1[7])
	elif index>14:
		if index == len(lines)-1:
			break
		else:
			bin1 = line.split(" ")
#			print bin1

			transfer[index-header-1,0]=float(bin1[4])

			if bin1[6]== "":
				bandwidth[index-header-1,0]=float(bin1[7])
			else:
				bandwidth[index-header-1,0]=float(bin1[6])

	index = index + 1

avgtransfer = np.mean(transfer) #units of Mbytes
stdtransfer = np.std(transfer)

avgbandwidth = np.mean(bandwidth) #unit of Mbits/sec
stdbandwidth = np.std(bandwidth)

print(avgbandwidth)
print(stdbandwidth)
