import nmap
from nmap import PortScanner
# Create a scanner object
nm = PortScanner()

# Define the IP range to scan
ip_range = '172.16.0.0/12'

# Perform the scan
nm.scan(hosts=ip_range, arguments='-sP')

# Print the results
for host in nm.all_hosts():
    if nm[host].state() == 'up':
        print(f'Host: {host} ({nm[host].hostname()})')
        print(f'IP Address: {nm[host].addresses()}')
