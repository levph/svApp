### FIND IP OF CONNECTED SILVUS ###
"""
This script finds the IP of Silvus radio directly connected to computer/tablet,
while automatically determining LAN Interface.

Main assumption - using CSMA (3GPP2 A11 protocol) broadcasts as discovery mechanism.
"""

import netifaces
from scapy.all import sniff
from scapy.layers.inet import IP

radio_ip = ""


def get_active_lan_interface():
    """
    Returns the name of the active LAN interface, excluding loopback and Wi-Fi.
    It checks for the presence of an IPv4 address that falls within typical LAN
    address ranges and is not a link-local address.

    :return: Name of the active LAN interface or None if not found.
    """
    return 'en5'
    # ... TBD ...


def stopfilter(x):
    """
    The packet processing callback for sniff.
     If packet is a broadcast to 172.20.255.255 coming from an address in same subnet,
     store source IP as IP of Silvus connected to tablet, and stop sniffing.

    :param x: The packet received by sniff.
    :return: True if the packet is the one we're looking for, False otherwise.
    """
    global radio_ip
    src_ip = x[IP].src
    dst_ip = x[IP].dst

    if dst_ip == '172.20.255.255' and src_ip.startswith('172.20'):
        radio_ip = src_ip
        return True
    else:
        return False


# Usage instructions or main block
if __name__ == '__main__':
    print("Looking for IP")
    # Specify the interface where packets are being received
    interface = get_active_lan_interface()
    sniff(iface='en5', stop_filter=stopfilter, filter="ip", store=0)

    print("radio IP is " + radio_ip)


