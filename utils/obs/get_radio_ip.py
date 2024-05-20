from scapy.all import sniff
from scapy.layers.inet import IP
import psutil

radio_ip = ""


def get_active_lan_interface():
    """
    Returns the name of the active LAN interface, excluding loopback and Wi-Fi.
    It checks for the presence of an IPv4 address that falls within typical LAN
    address ranges and is not a link-local address.

    :return: Name of the active LAN interface or None if not found.
    """
    """
    Returns the name of the active LAN interface.
    """
    """
       Returns the name of the active Ethernet LAN interface.
       """
    interfaces = psutil.net_if_addrs()
    ethernet_interfaces = []

    for interface, addrs in interfaces.items():
        for addr in addrs:
            if addr.family == psutil.AF_LINK:
                # Skip loopback and Wi-Fi interfaces
                if interface == 'lo' or interface.startswith(
                        'lo') or 'wifi' in interface.lower() or 'wlan' in interface.lower() or 'wl' in interface.lower():
                    continue
                # Check if the interface is up and store Ethernet interfaces
                if psutil.net_if_stats()[interface].isup and (
                        interface.startswith('eth') or interface.startswith('en')):
                    ethernet_interfaces.append(interface)

    # Return the first active Ethernet interface if found
    if ethernet_interfaces:
        return ethernet_interfaces[0]

    # If no Ethernet interface is found, check for any other active interface (GOOD FOR OKETZ, needs testing...)
    for interface, addrs in interfaces.items():
        for addr in addrs:
            if addr.family == psutil.AF_LINK:
                if interface == 'lo' or interface.startswith('lo'):
                    continue
                if psutil.net_if_stats()[interface].isup:
                    return interface

    return None


def stop_filter(x):
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

    if dst_ip == '172.31.255.255' and src_ip.startswith('172.20'):
        radio_ip = src_ip
        return True
    else:
        return False


def sniff_target_ip():
    """
    Sniffs the network for a target packet and returns the source IP address
    when the packet is found.
    """
    active_lan_interface = get_active_lan_interface()
    if not active_lan_interface:
        raise ValueError("No active LAN interface found.")
    # The sniff function now returns the IP address from the packet_handler
    print(f"Found interface {active_lan_interface}")
    sniff(iface=active_lan_interface, stop_filter=stop_filter, filter="ip", store=0, timeout=6)

    return radio_ip

