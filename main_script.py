import os

from utils.obs.get_radio_ip import sniff_target_ip
from utils.net_battery_percent import get_batteries, node_labels, save_node_label, list_devices, net_status
from utils.list_cameras import find_cameras
from utils.fa_models import BasicSettings
from utils.change_label import change_label


def open_url_if_agreed(ip):
    url = f"http://{ip}/#"
    # url = "http://172.20.245.48/#"
    response = input("Would you like to open the URL? [Y/n]: ").strip().lower()
    if response in ('y', 'yes', ''):  # Default to 'Yes' if enter key is pressed
        if os.system(f"open {url}") != 0:  # Using macOS 'open' command
            print("Failed to open URL.")
        else:
            print("URL opened.")
    else:
        print("URL not opened.")


def main():
    try:
        radio_ip = sniff_target_ip()
        if radio_ip:
            print(f"Target IP address found: {radio_ip}")
        else:
            print("Target IP address not found.")
        # Example usage
        open_url_if_agreed(str(radio_ip))
        # res = get_version(radio_ip)
        [ips, network_ids, _] = list_devices(radio_ip)

        status= net_status(radio_ip, network_ids)
        print(status)

        result = get_batteries(ips)
        print("saving")
        settings = BasicSettings
        settings.set_net_flag = 0
        settings.netID = "yosi"
        settings.frequency = "2490"
        settings.bw = "5"
        settings.powerdBm = "15"

        # set_basic_settings(radio_ip, network_ids, settings)

        print("New settings set.")

        new_name = "name1"
        iid = network_ids[0]
        change_label(radio_ip, iid, new_name)
        print(f"Label of {ips[0]} changed to {new_name}")

        print(f"Radios in network:")
        print(ips)

        print(f"Cameras in network:")
        print(find_cameras())


        # Example usage
        open_url_if_agreed(str(radio_ip))

        get_batteries(ips)
        # change_led(radio_ip)

        # root = tk.Tk()
        # root.withdraw()

        # Open a file chooser dialog and get the selected file path
        # file_path = filedialog.askopenfilename()

        # upload_settings(radio_ip, file_path)

        labels = node_labels(radio_ip)

        save_node_label(radio_ip)

        lev = 1
        # do we need time of flight?

    except ValueError as e:
        print(e)


if __name__ == "__main__":
    main()
