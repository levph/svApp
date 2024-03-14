from get_radio_ip import sniff_target_ip
from net_battery_percent import get_batteries

def main():
    try:
        radio_ip = sniff_target_ip()
        if radio_ip:
            print(f"Target IP address found: {radio_ip}")
        else:
            print("Target IP address not found.")

        get_batteries(radio_ip)
    except ValueError as e:
        print(e)



if __name__ == "__main__":
    main()
