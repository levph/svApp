from wsdiscovery.discovery import ThreadedWSDiscovery as WSDiscovery
from wsdiscovery import QName
from onvif import ONVIFCamera
from urllib.parse import urlparse
import cv2
# import vlc
lev=1

def perform_ptz(camera, move, timeout=1):
    """
    Perform a PTZ move command on the camera.

    :param camera: ONVIFCamera object.
    :param move: Dictionary with 'pan', 'tilt', and 'zoom' values.
    :param timeout: Time in seconds for the move to be performed.
    """
    media_service1 = camera.create_media_service()
    ptz_service = camera.create_ptz_service()

    # Get profiles and use the first one
    profiles1 = media_service1.GetProfiles()
    profile_token1 = profiles1[0].token

    # Get PTZ configuration options for the first profile
    ptz_configuration_options = ptz_service.GetConfigurationOptions(
        {'ConfigurationToken': profile_token1.PTZConfiguration.token})

    request = ptz_service.create_type('ContinuousMove')
    request.ProfileToken = profile_token.token
    request.Velocity = ptz_service.create_type('PTZSpeed')

    request.Velocity.PanTilt = {'x': move.get('pan', 0), 'y': move.get('tilt', 0)}
    request.Velocity.Zoom = {'x': move.get('zoom', 0)}

    ptz_service.ContinuousMove(request)
    # Stop movement after 'timeout' seconds
    if timeout:
        import time
        time.sleep(timeout)
        stop = ptz_service.create_type('Stop')
        stop.ProfileToken = profile_token.token
        ptz_service.Stop(stop)


# CAMERA ONVIF DISCOVERY

wsd = WSDiscovery()
wsd.start()

services = wsd.searchServices(types=[QName('http://www.onvif.org/ver10/network/wsdl', 'NetworkVideoTransmitter')])
url = []
for service in services:
    print(f'ONVIF service found at: {service.getXAddrs()[0]}')
    url.append(service.getXAddrs()[0])
chosen = 0
if len(url) > 1:
    print("Found " + str(len(url)) + " cameras")
    response = input("Which would you like to open: ").strip().lower()
    if response in ('1', ''):
        chosen = 0
    else:
        chosen = 1

url = url[chosen]
wsd.stop()

########################

# The IP address, port, and path you got from the discovery
# onvif_service_url = 'http://192.168.1.88:2000/onvif/device_service'
onvif_service_url = url
# Parse the URL to get the components you need


parsed_url = urlparse(onvif_service_url)

# Extract the IP address and port from the URL
ip_address = parsed_url.hostname
port = parsed_url.port
path = parsed_url.path

# Assume default ONVIF username and password, replace with actual if different
username = 'admin'
password = 'admin'

# Path to the WSDL directory, typically provided by the onvif-zeep package or manually downloaded
# wsdl_path = '/path/to/wsdl/'

# Initialize the ONVIF camera
camera = ONVIFCamera(ip_address, port, username, password)

# Create media service
media_service = camera.create_media_service()

# Get the profiles
profiles = media_service.GetProfiles()

# Use the first profile and get the token
profile_token = profiles[0].token

# Get the stream URI
stream_uri = media_service.GetStreamUri(
    {'StreamSetup': {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}}, 'ProfileToken': profile_token})

print(stream_uri.Uri)

# Create an ONVIF camera object


# Create the device management service
devicemgmt_service = camera.create_devicemgmt_service()

# Get device information
device_info = devicemgmt_service.GetDeviceInformation()

print("Manufacturer: ", device_info.Manufacturer)
print("Model: ", device_info.Model)
print("FirmwareVersion: ", device_info.FirmwareVersion)
print("SerialNumber: ", device_info.SerialNumber)
print("HardwareId: ", device_info.HardwareId)

lev = 1

#### VLC SECTION
# # URL of the ONVIF RTSP stream
# stream_url = 'rtsp://192.168.1.88:554/path/to/stream'
#
# # Create a VLC instance
# player_instance = vlc.Instance()
#
# # Create a Media Player object
# player = player_instance.media_player_new()
#
# # Create a new Media object
# media = player_instance.media_new(stream_url)
#
# # Set the media player media
# player.set_media(media)
#
# # Play the media
# player.play()
#
# # Wait for the user to close the stream
# try:
#     while True:
#         time.sleep(1)
# except KeyboardInterrupt:
#     print("\nStream stopped.")

# Replace 'stream_uri' with the actual stream URI obtained in the previous step
cap = cv2.VideoCapture(stream_uri.Uri)

while True:
    # Capture frame-by-frame
    ret, frame = cap.read()
    # Display the resulting frame
    cv2.imshow('frame', frame)
    # Break the loop
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
