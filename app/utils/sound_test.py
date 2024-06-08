import os

# Set the DYLD_LIBRARY_PATH for the Opus library
opus_lib_path = "/opt/homebrew/Cellar/opus/1.5.2/lib"
os.environ["DYLD_LIBRARY_PATH"] = f"{opus_lib_path}:{os.environ.get('DYLD_LIBRARY_PATH', '')}"

# Now import the required libraries
from scapy.all import *
import numpy as np
import opuslib
import soundfile as sf

# PTT multicast group and port
multicast_group = '239.0.0.190'  # Replace with actual multicast group if different
multicast_port = 1234

# Audio configuration
sample_rate = 48000  # Opus typically uses 48kHz sample rate
channels = 1
frame_size = 960  # Common frame size for 20 ms of audio at 48 kHz

# Create OPUS decoder
decoder = opuslib.Decoder(sample_rate, channels)

# File to save the recorded audio
output_file = "recorded_audio.wav"
audio_data = []


def record_audio(packet):
    if UDP in packet and packet[UDP].dport == multicast_port:
        print("Packet received")  # Indicate that a packet has been received
        # Extract the payload
        audio_payload = bytes(packet[UDP].payload)
        print(f"Payload length: {len(audio_payload)} bytes")  # Log payload length

        try:
            # Decode OPUS audio
            decoded_audio = decoder.decode(audio_payload, frame_size)
            print(f"Decoded audio length: {len(decoded_audio)} bytes")  # Log decoded audio length

            # Convert byte data to NumPy array
            decoded_audio_np = np.frombuffer(decoded_audio, dtype=np.int16)
            print(f"NumPy array shape: {decoded_audio_np.shape}")  # Log NumPy array shape

            # Append the decoded audio to the list
            audio_data.extend(decoded_audio_np.tolist())
        except Exception as e:
            print(f"Error decoding audio: {e}")


# Specify the network interface to sniff on (e.g., 'en0' for Wi-Fi on macOS)
interface = 'en0'
sniff_duration = 5  # Set the duration for sniffing in seconds

# Use scapy to sniff the multicast traffic
print(f"Listening on {interface} for UDP traffic on port {multicast_port} for {sniff_duration} seconds")
sniff(prn=record_audio, store=0, iface=interface, filter=f'udp port {multicast_port}', timeout=sniff_duration)

# Save the recorded audio to a file
if audio_data:
    audio_array = np.array(audio_data, dtype=np.int16)
    total_samples = len(audio_array)
    duration_in_seconds = total_samples / sample_rate
    print(f"Total samples: {total_samples}, Duration in seconds: {duration_in_seconds}")
    sf.write(output_file, audio_array, sample_rate)
    print(f"Audio recorded and saved to {output_file}")
else:
    print("No audio data recorded")