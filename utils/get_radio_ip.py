"""
This script is sniffing for the silvus discovery message.
finds the IP of the connected radio.

author: lev
"""

from scapy.all import *

# Define the MAC prefix and IP range
radio_ip = None
mac_prefix = "c4:7c:8d"
ip_range = "172."
broadcast_mac = "ff:ff:ff:ff:ff:ff"


def packet_callback(packet):
    """
    The packet processing callback for sniff.
    Looking for Silvus discovery message
    From what we've seen it's UDP message, MAC Broadcast
    and source is expected to start with the silvus IP and MAC prefixes defined as global variables
    will stop sniffing once conditions are met.

    :param x: The packet received by sniff.
    :return: True if the packet is the one we're looking for, False otherwise.
    """
    global radio_ip
    if packet.haslayer(Ether) and packet.haslayer(IP) and packet.haslayer(UDP):
        src_mac = packet[Ether].src
        dst_mac = packet[Ether].dst
        src_ip = packet[IP].src
        # Check if the packet is a broadcast
        if dst_mac.lower() == broadcast_mac:
            # Check if the source MAC address matches the prefix and the IP is in the expected range
            if src_mac.lower().startswith(mac_prefix) and src_ip.startswith(ip_range):
                print(f"Received Silvus discovery message from {src_ip}")
                radio_ip = src_ip
                return True
    return False


def sniff_target_ip():
    """
    Sniffs the network for a target packet and returns the source IP address
    when the packet is found.
    """
    # Start sniffing on all interfaces
    sniff(stop_filter=packet_callback, store=0, timeout=10)

    print(f"\nRadio IP is {radio_ip}")
    return radio_ip

# sniff_target_ip()