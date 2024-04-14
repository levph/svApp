from scapy.all import sniff, UDP
from scapy.layers.inet import IP
import time

# Constants
UDP_PORT = 1234  # The port where OPUS packets are sent
OUTPUT_FILE = 'output.opus'  # Output file name
RECORDING_TIME = 5  # Duration to record in seconds
DEST_IP = "239.0.0.190"  # Destination IP address for multicast group

start_time = time.time()


def packet_callback(packet):
    print(time.time() - start_time)
    if time.time() - start_time > RECORDING_TIME:
        return True  # Signal to stop sniffing
    if packet.haslayer(UDP) and packet[UDP].dport == UDP_PORT and packet[IP].dst == DEST_IP:
        # Extract the payload data
        payload = bytes(packet[UDP].payload)
        # Write the payload to the file
        with open(OUTPUT_FILE, 'ab') as f:
            f.write(payload)


print("Starting recording...")
# Start sniffing the network for UDP packets on the specified port and destination IP
sniff(iface='en5',prn=packet_callback, filter=f"udp and dst {DEST_IP} and port {UDP_PORT}", store=0,
      stop_filter=lambda x: packet_callback(x))
