"""
The methods in this script convert node IDs to node IPs in Software version 5,
where node IDs are 20 bits instead of 16

author: lev
"""


def node_id_to_ip(nodelist):
    """
    This method converts node ids to node ips in SW V5
    The network base address is 172.16.0.0.
    node ID is corresponding to last 20 bits of the IP.
    Node IP essentialy = base_ip + nodeID

    :param nodelist: list of integers indicating network node IDs
    :return: ips: list of corresponding node IPs
    """
    base_ip = "172.16.0.0"
    ips = []

    for node_id in nodelist:
        # Ensure node_id is within the valid range for a 20-bit number
        if node_id < 0 or node_id >= (1 << 20):
            raise ValueError("Node ID must be a 20-bit number (0 to 1048575).")

        # Convert base IP to binary and extract the network part
        base_ip_octets = [int(octet) for octet in base_ip.split('.')]
        base_ip_bin = ''.join(format(octet, '08b') for octet in base_ip_octets)

        # Extract the network prefix (first 12 bits)
        network_prefix = base_ip_bin[:12]

        # Convert node ID to a 20-bit binary string
        node_id_bin = format(node_id, '020b')

        # Combine the network prefix and the node ID
        ip_bin = network_prefix + node_id_bin

        # Split the 32-bit binary string into four 8-bit segments
        octets = [ip_bin[i:i + 8] for i in range(0, 32, 8)]

        # Convert each 8-bit segment to a decimal number
        ip_address = '.'.join(str(int(octet, 2)) for octet in octets)

        ips.append(ip_address)

    return ips


