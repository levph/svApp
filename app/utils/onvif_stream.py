from valkka.discovery import *

a = runWSDiscovery()
# --> returns a list of tuples (ip, port)
b = runARPScan(exclude_list = [], exclude_interfaces = [], max_time_per_interface=10)
# performs a combination of arp-scan and "rtsp options" probes
# --> returns a list of ArpRTSPScanResult objects
ip=3
c = ARPIP2Mac(ip)
# maps ip address to a mac address
# --> returns ArpRTSPScanResult object
# --> to get most recent ip address -> mac address mapping, you should run
getARPCache(update=True)