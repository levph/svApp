"""
This script is sniffing for the silvus discovery message.
finds the IP of the connected radio.

author: lev
"""

from scapy.all import *
from scapy.all import sniff, Ether, get_working_ifaces
import psutil
import socket



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
    # print("Packet!!!")
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


def get_interface_by_ip(target_ip):
    for iface_name, iface_addrs in psutil.net_if_addrs().items():
        for addr in iface_addrs:
            # print(f"{iface_name} IP is {addr.address}")
            if addr.family == socket.AF_INET and addr.address.startswith(target_ip):
                return iface_name
    return None

def get_iface_name():
    # name = get_interface_by_ip("172.")
    working_ifaces = get_working_ifaces()
    iface_name = [iface.network_name for iface in working_ifaces if iface.ip.startswith("172.")]
    return iface_name

def sniff_target_ip():
    """
    Sniffs the network for a target packet and returns the source IP address
    when the packet is found.
    """
    iface_name = get_iface_name()

    sniff(iface=iface_name,stop_filter=packet_callback, store=0, timeout=10)

    print(f"\nRadio IP is {radio_ip}")
    return radio_ip


if __name__ == "__main__":
    ip = sniff_target_ip()

    
sniff_target_ip()