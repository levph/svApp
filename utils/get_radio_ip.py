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

    if dst_ip == '172.20.255.255' and src_ip.startswith('172.20'):
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
    sniff(iface='en5', stop_filter=stop_filter, filter="ip", store=0)
    return radio_ip

