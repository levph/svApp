from wsdiscovery.discovery import ThreadedWSDiscovery as WSDiscovery
from wsdiscovery import QName, Scope
from onvif import ONVIFCamera
from urllib.parse import urlparse


# CAMERA ONVIF DISCOVERY
def check_valid(cam):
    dev_mgmt_service = cam.create_devicemgmt_service()

    device_info = dev_mgmt_service.GetDeviceInformation()

    # TODO: make sure its the correct field
    return device_info.HardwareId == 'IPCamera'


def camera_finder():
    """
    This method scans the network for ONVIF services
    and finds cameras in network.
    :return:
    rtsp_main_stream: url string list of rtsp streams
    """
    # initialize discovery
    wsd = WSDiscovery()
    wsd.start()

    # look for ONVIF services
    services = wsd.searchServices(types=[QName('http://www.onvif.org/ver10/network/wsdl', 'NetworkVideoTransmitter')])

    url = []
    for service in services:
        print(f'ONVIF service found at: {service.getXAddrs()[0]}')
        url.append(service.getXAddrs()[0])

    wsd.stop()

    # parse camera URLs
    parsed_urls = [urlparse(u) for u in url]

    rtsp_main_stream = []

    username = 'admin'
    pw = 'admin'
    for pu in parsed_urls:
        ip_address = pu.hostname
        port = pu.port
        path = pu.path

        camera = ONVIFCamera(ip_address, port, username, pw)

        # check if it's an IP Camera or other ONVIF service
        v = check_valid(camera)
        if not v:
            continue

        # Create media service
        media_service = camera.create_media_service()

        # Get the profiles
        profiles = media_service.GetProfiles()

        # Use the first profile and get the token
        profile_token = profiles[0].token

        # Get the stream URI
        stream_uri = media_service.GetStreamUri(
            {'StreamSetup': {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}},
             'ProfileToken': profile_token})

        rtsp_main_stream.append(stream_uri.Uri)

    return rtsp_main_stream[0]
