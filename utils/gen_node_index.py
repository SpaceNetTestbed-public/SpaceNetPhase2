import argparse
def populate_arg_parser(parser):
    parser.add_argument('-n', type=str, help='Name of the constellation - e.g. STARLINK [required]')
    parser.add_argument('-s', type=int, help='Number of constellation satellites [required]')
    parser.add_argument('-c', type=int, help='Number of customer terminals')
    parser.add_argument('-g', type=int, help='Number of gateway terminals')
    parser.add_argument('-i', type=int, help='Number of Internet Endpoints')
    parser.add_argument('-o', type=str, help='Output file name')
    return parser

def main():
    parser = argparse.ArgumentParser(description='Utility script to generate a node index file after the fact.')
    parser = populate_arg_parser(parser)

    args = parser.parse_args()
    if not args.n or not args.s:
        parser.print_help()
        return

    num_sats = None
    constellation_name = None
    num_cts = 0
    num_gws = 0
    num_ies = 0
    output_file = None

    if args.n:
        constellation_name = args.n
    if args.s:
        num_sats = args.s
    if args.c:
        num_cts = args.c
    if args.g:
        num_gws = args.g
    if args.i:
        num_ies = args.i
    if args.o:
        output_file = args.o
    
    if output_file is None or output_file == "":
        output_file = f"{constellation_name}_node_index_{num_sats}.txt"

    with open(output_file, 'w') as file:
        for i in range(0, num_sats):
            file.write(f"{i}:{constellation_name}-{i+1000}\n")
        
        gs_index = 0
        ct_start = num_sats
        ct_end = num_sats + num_cts
        for j in range(ct_start, ct_end):
            file.write(f"{j}:CT-{gs_index}\n")
            gs_index += 1
        gw_start = ct_end
        gw_end = ct_end + num_gws
        for k in range(gw_start, gw_end):
            file.write(f"{k}:GW-{gs_index}\n")
            gs_index += 1
        
        ie_start = gw_end
        ie_end = gw_end + num_ies
        for l in range(ie_start, ie_end):
            file.write(f"{l}:IE-{gs_index}\n")
            gs_index += 1

    print(f"Node index file {output_file} created.")

if __name__ == '__main__':
    main()