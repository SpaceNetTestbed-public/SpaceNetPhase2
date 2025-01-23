#!/usr/bin/env python3

import argparse
import subprocess
import time
import os
import sys
import signal
import threading
import math

def parse_size(size_str):
    """Parse human-readable file size strings into bytes."""
    size_str = size_str.strip().upper()
    if size_str.endswith('G'):
        return int(float(size_str[:-1]) * 1024 ** 3)
    elif size_str.endswith('M'):
        return int(float(size_str[:-1]) * 1024 ** 2)
    elif size_str.endswith('K'):
        return int(float(size_str[:-1]) * 1024)
    else:
        return int(size_str)

def run_server(port, protocol):
    """Run netcat server."""
    nc_protocol = '-u' if protocol == 'udp' else ''
    nc_options = ['-l', '-p', str(port)]
    if protocol == 'tcp':
        nc_options.insert(0, '-k') # Keep listening for multiple connections
    cmd = ['nc'] + nc_options + [nc_protocol]
    cmd = [arg for arg in cmd if arg] # Removes any empty arguments
    print(f"Running command: {' '.join(cmd)}")
    with subprocess.Popen(cmd, stdout=subprocess.DEVNULL) as proc:
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()

def generate_test_file(file_name, size):
    """Generate a test file of the specified size."""
    with open(file_name, 'wb') as f:
        f.write(os.urandom(size))

def delete_test_file(file_name):
    """Delete the test file."""
    os.remove(file_name)

def send_file(file_name, host, port, protocol):
    """Send a file using netcat."""
    nc_protocol = '-u' if protocol == 'udp' else ''
    nc_options = ['-v', '-N'] # Verbose output, no DNS resolution #['-N'] # no DNS resolution
    if protocol == 'udp':
        nc_options.extend(['-w', '1']) # Set timeout to 1 second for UDP so it exits after sending
    else:
        nc_options.extend(['-q', '0']) # Set timeout to 0 for TCP after EOF on stdin (if supported)
    cmd = ['nc'] + nc_options + [nc_protocol, host, str(port)]
    cmd = [arg for arg in cmd if arg] # Removes any empty arguments
    print(f"Running command: {' '.join(cmd)}")
    
    with open(file_name, 'rb') as f:
        proc = subprocess.Popen(cmd, stdin=f, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        exit_code = proc.returncode
        if exit_code != 0:
            print(f"Error: netcat exited with code {exit_code}")
            if stdout:
                print(f"stdout: {stdout.decode('utf-8')}")
            if stderr:
                print(f"stderror: {stderr.decode('utf-8')}")
            sys.exit(1)

def throughput_test(args):
    """Perform the throughput test."""
    total_bytes = args.size * args.num_files
    if args.unit == 'Mbps':
        total_bits = total_bytes * 8
        unit_divisor = 1_000_000
        unit_name = 'Mbps'
    elif args.unit == 'Kbps':
        total_bits = total_bytes * 8
        unit_divisor = 1_000
        unit_name = 'Kbps'
    durations = []

    for trial in range(1, args.trials + 1):
        print(f"Trial {trial}/{args.trials}")
        file_list = []
        for i in range(args.num_files):
            file_name = f"testfile_{trial}_{i}.dat"
            generate_test_file(file_name, args.size)
            file_list.append(file_name)

        start_time = time.time()

        # Send files using netcat
        for file_name in file_list:
            send_file(file_name, args.host, args.port, args.protocol)

        end_time = time.time()
        duration = end_time - start_time
        durations.append(duration)

        # Delete test files
        for file_name in file_list:
            delete_test_file(file_name)

        print(f"Duration: {duration:.2f} seconds")
        throughput = (total_bytes * 8 / unit_divisor) / duration
        print(f"Throughput: {throughput:.2f} {unit_name}\n")

    avg_duration = sum(durations) / len(durations)
    avg_throughput = (total_bytes * 8 / unit_divisor) / avg_duration
    stddev_duration = math.sqrt(sum((d - avg_duration) ** 2 for d in durations) / len(durations))
    stddev_throughput = (stddev_duration / avg_duration) * avg_throughput

    print("=== Test Results ===")
    print(f"Average Duration: {avg_duration:.2f} seconds")
    print(f"Average Throughput: {avg_throughput:.2f} {unit_name}")
    print(f"Throughput Standard Deviation: {stddev_throughput:.2f} {unit_name}")

def main():
    parser = argparse.ArgumentParser(description='Throughput Test using netcat', allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='mode', required=True)

    # Server mode
    server_parser = subparsers.add_parser('server', help='Run in server mode')
    server_parser.add_argument('-p', '--port', type=int, default=5000, help='Port number (default: 5000)')
    server_parser.add_argument('-t', '--protocol', choices=['tcp', 'udp'], default='tcp', help='Protocol (default: tcp)')

    # Client mode
    client_parser = subparsers.add_parser('client', help='Run in client mode')
    client_parser.add_argument('-H', '--host', required=True, help='Server host')
    client_parser.add_argument('-p', '--port', type=int, default=5000, help='Port number (default: 5000)')
    client_parser.add_argument('-P', '--protocol', choices=['tcp', 'udp'], default='tcp', help='Protocol (default: tcp)')
    client_parser.add_argument('-n', '--num-files', type=int, default=1, help='Number of test files (default: 1)')
    client_parser.add_argument('-s', '--size', type=parse_size, default=parse_size('1M'), help='Size of each test file (default: 1M)')
    client_parser.add_argument('-r', '--trials', type=int, default=1, help='Number of trials to run (default: 10)')
    client_parser.add_argument('-u', '--unit', choices=['Mbps', 'Kbps'], default='Mbps', help='Unit for throughput (default: Mbps)')

    args = parser.parse_args()
    print(f"Using arguments:")
    for arg in vars(args):
        print(f"  {arg}: {getattr(args, arg)}")
    if args.mode == 'server':
        print(f"Running in server mode on port {args.port} using {args.protocol.upper()} protocol.")
        print("Press Ctrl+C to stop the server.")
        run_server(args.port, args.protocol)
    elif args.mode == 'client':
        print(f"Running in client mode, connecting to {args.host}:{args.port} using {args.protocol.upper()} protocol.")
        print(f"Number of files: {args.num_files}, File size: {args.size} bytes, Trials: {args.trials}")
        print(f"Throughput unit: {args.unit}")
        throughput_test(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
