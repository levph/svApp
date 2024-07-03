"""
This script is sniffing for the silvus discovery message.
finds the IP of the connected radio.

author: lev
"""

from scapy.all import *
from scapy.all import sniff, Ether, get_working_ifaces
import psutil
import socket
from scapy.all import sniff, get_if_addr, get_if_list
import threading

# Lock to control access to radio ip
lock = threading.Lock()

# Condition variable to notify all threads to stop
stop_condition = threading.Condition()

# Define the MAC prefix and IP range
radio_ip = None
version = None
mac_prefix = ["c4:7c:8d"]
ip_range = "172."
broadcast_mac = "ff:ff:ff:ff:ff:ff"
dst_ip_v4 = "172.20.255.255"


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
    global radio_ip, version
    print("Packet!")
    # print("Packet!!!")
    if packet.haslayer(Ether) and packet.haslayer(IP) and packet.haslayer(UDP):
        src_mac = packet[Ether].src
        dst_mac = packet[Ether].dst
        src_ip = packet[IP].src
        dst_ip = packet[IP].dst

        # V4 discovery message
        if dst_ip == dst_ip_v4 and src_ip.startswith(ip_range):
            with lock:
                if radio_ip is None:
                    print(f"Received V4 Silvus discovery message from {src_ip}")
                    radio_ip = src_ip
                    version = 4
                    with stop_condition:
                        stop_condition.notify_all()

        # Check if the packet is a broadcast (V5 discovery message)
        elif dst_mac.lower() == broadcast_mac:
            # Check if the source MAC address matches the prefix and the IP is in the expected range
            if any(src_mac.lower().startswith(prefix) for prefix in mac_prefix) and src_ip.startswith(ip_range):
                with lock:
                    if radio_ip is None:
                        print(f"Received V5 Silvus discovery message from {src_ip}")
                        radio_ip = src_ip
                        version = 5
                        with stop_condition:
                            stop_condition.notify_all()


def get_interface_by_ip(target_ip):
    for iface_name, iface_addrs in psutil.net_if_addrs().items():
        for addr in iface_addrs:
            # print(f"{iface_name} IP is {addr.address}")
            if addr.family == socket.AF_INET and addr.address.startswith(target_ip):
                return iface_name
    return None


def get_iface_name():
    working_ifaces = get_working_ifaces()
    iface_name = [iface.network_name for iface in working_ifaces if iface.ip.startswith("172.20")]
    return iface_name


def sniffer(if_name):
    # sniff(iface=if_name,stop_filter=packet_callback, store=0, timeout=10)
    sniff(iface=if_name, prn=packet_callback, stop_filter=lambda x: radio_ip is not None, timeout=3)


def sniff_target_ip():
    """
    Sniffs the network for a target packet and returns the source IP address
    when the packet is found.
    """
    global radio_ip, version
    radio_ip = version = None

    iface_name = get_iface_name()
    if len(iface_name) == 1:
        sniffer(str(iface_name[0]))
    elif len(iface_name) > 1:
        threads = []
        for iface in iface_name:
            th = threading.Thread(target=sniffer, args=(iface,))
            threads.append(th)
            th.start()

        # Join threads to wait for them to complete
        for thread in threads:
            thread.join()

    print(f"\nRadio IP is {radio_ip}")
    return radio_ip, version


if __name__ == "__main__":
    sniff_target_ip()

# sniff_target_ip()
