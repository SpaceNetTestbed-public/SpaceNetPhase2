# for i in range(0, 1548):

file1 = open('stat_r.sh', 'r')
Lines = file1.readlines()

count = 0
for line in Lines:
    command = line.strip().split(" ")
    # print command[0]
    file = open("./cmd_files/"+command[0]+"_routes.sh", 'a')
    string_to_write = ""
    for i in range(1,len(command)):
        string_to_write += command[i]+" "

    file.writelines(string_to_write+"\n")
    file.close()
