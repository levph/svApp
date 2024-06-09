from wsdiscovery.discovery import ThreadedWSDiscovery as WSDiscovery
from wsdiscovery import QName, Scope
from onvif import ONVIFCamera
from urllib.parse import urlparse
# import vlc
import time


def find_cameras():
    # CAMERA ONVIF DISCOVERY
    wsd = WSDiscovery()
    wsd.start()
    services = wsd.searchServices(types=[QName('http://www.onvif.org/ver10/network/wsdl', 'NetworkVideoTransmitter')])
    url = []

    for service in services:
        # print(f'ONVIF service found at: {service.getXAddrs()[0]}')
        url.append(service.getXAddrs()[0])

    wsd.stop()

    ########################

    # Assume default ONVIF username and password, replace with actual if different
    username = 'admin'
    password = 'admin'

    camera_ips = []
    # check for each ONVIF service found if it's an IPCamera
    for u in url:
        parsed_url = urlparse(u)

        # Extract the IP address and port from the URL
        ip_address = parsed_url.hostname
        port = parsed_url.port
        path = parsed_url.path

        # Path to the WSDL directory, typically provided by the onvif-zeep package or manually downloaded
        # wsdl_path = '/path/to/wsdl/'

        # Initialize the ONVIF camera
        camera = ONVIFCamera(ip_address, port, username, password)

        # Create the device management service
        devicemgmt_service = camera.create_devicemgmt_service()

        # Get device information
        device_info = devicemgmt_service.GetDeviceInformation()

        if device_info.HardwareId == 'IPCamera':
            camera_ips.append(ip_address)

    return camera_ips
