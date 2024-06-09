import socket

# Define the mapping based on the provided table
report_type_mapping = {
    5009: "Begin of RSSI report",
    5010: "Revision number for RSSI report",
    5000: "Raw signal power of first antenna",
    5001: "Raw signal power of second antenna",
    5002: "Raw signal power of third antenna",
    5003: "Raw signal power of fourth antenna",
    5004: "Raw noise power",
    5005: "Sync signal power",
    5006: "Sync noise power",
    5007: "Node ID of the radio",
    5008: "Report sequence number",
    5011: "Node IP",
    5012: "Virtual IP",
    1: "End of report"
}


def decode_data(data):
    decoded_data = []
    index = 0

    while index < len(data):
        # Extract the field identifier (2 bytes)
        field_id = int.from_bytes(data[index:index + 2], byteorder='big')
        index += 2

        # Extract the field length (2 bytes)
        field_length = int.from_bytes(data[index:index + 2], byteorder='big')
        index += 2

        # Extract the field data based on the field length
        field_data = data[index:index + field_length]
        index += field_length

        # Decode the field data as a string (assuming UTF-8 encoding for text data)
        try:
            field_data_str = field_data.decode('utf-8').strip('\x00')
        except UnicodeDecodeError:
            field_data_str = str(field_data)

        # Map the field ID to its description
        field_description = report_type_mapping.get(field_id, f"Unknown field ID {field_id}")

        # Store the decoded field with its description
        decoded_data.append((field_description, field_data_str))

    return decoded_data


def print_decoded_data(decoded_data):
    for field_description, field_data in decoded_data:
        print(f"{field_description}: {field_data}")


def capture_udp_stream(ip: str, port: int):
    # Create a UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind the socket to the specified IP and port
    try:
        udp_socket.bind((ip, port))
        print(f"Listening for UDP packets on {ip}:{port}...")
    except OSError as e:
        print(f"Error binding to {ip}:{port}: {e}")
        return

    while True:
        # Receive data from the socket
        data, addr = udp_socket.recvfrom(1024)  # Buffer size is 1024 bytes
        print(f"Received message from {addr}")
        decoded = decode_data(data)
        print_decoded_data(decoded)


if __name__ == "__main__":
    # Set the IP and port you want to capture
    ip = "172.20.2.3"  # This will listen on all network interfaces
    port = 30000
    capture_udp_stream(ip, port)