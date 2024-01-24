## code

import numpy as np

data = open("ping_27oct_NYtoLondon.txt","r") #w = write, a = apphend
lines = data.readlines()

index = 0

time = np.empty((len(lines)-1,1))

for line in lines:
	if index>0:
		bin1 = line.split(" ")

		bin2 = bin1[6].split("=")

		time[index-1,0]=float(bin2[1])

	index = index + 1

avgtime = np.mean(time)
stdtime = np.std(time)

print(avgtime)
print(stdtime)
