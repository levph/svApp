from typing import Optional, List, Tuple, Any
from functools import wraps
import threading
import logging
import time

from scapy.all import sniff, Ether, IP, UDP, conf, get_working_ifaces
from scapy.packet import Packet

from utils.fa_models import DiscoveryResult, RadioDiscoveryError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def retry_on_exception(retries: int = 3, delay: float = 1.0):
    """Decorator for retrying operations that might fail temporarily."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < retries - 1:
                        logging.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds...")
                        time.sleep(delay)
            logging.error(f"All {retries} attempts failed. Last error: {str(last_exception)}")
            raise last_exception

        return wrapper

    return decorator



class RadioIpSniffer:
    """
    A network sniffer for discovering radio devices on specific network interfaces.

    This class implements packet sniffing functionality to discover radio devices
    broadcasting discovery messages on specified network interfaces.
    """

    def __init__(
            self,
            ip_range: str = "172.",
            dst_ips: List[str] = None,
            sniff_timeout: int = 3
    ) -> None:
        """
        Initialize the RadioIpSniffer.

        Args:
            ip_range: IP range prefix to filter source addresses
            dst_ips: List of destination broadcast addresses to monitor
            sniff_timeout: Timeout in seconds for each sniffing attempt
        """
        self.logger = logging.getLogger(__name__)
        self._ip_range = ip_range
        self._dst_ips = dst_ips or ["172.20.255.255", "172.31.255.255"]
        self._sniff_timeout = sniff_timeout

        # Thread-safety mechanisms
        self._lock = threading.Lock()
        self._stop_condition = threading.Condition()

        # Discovery result
        self._discovery_result = DiscoveryResult()

    def _packet_callback(self, packet: Packet) -> None:
        """
        Process captured packets to identify radio discovery messages.

        Args:
            packet: Captured network packet
        """
        try:
            if not (packet.haslayer(Ether) and packet.haslayer(IP) and packet.haslayer(UDP)):
                return

            src_ip = packet[IP].src
            dst_ip = packet[IP].dst

            if (any(dst_ip.lower().startswith(dst) for dst in self._dst_ips) and
                    src_ip.startswith(self._ip_range)):
                with self._lock:
                    if self._discovery_result.ip_address is None:
                        version = 4 if "20" in dst_ip else 5
                        self.logger.info(f"Received V{version} discovery message from {src_ip}")

                        self._discovery_result = DiscoveryResult(
                            ip_address=src_ip,
                            version=version,
                            discovery_time=time.time()
                        )

                        with self._stop_condition:
                            self._stop_condition.notify_all()

        except Exception as e:
            self.logger.error(f"Error processing packet: {str(e)}")

    @retry_on_exception(retries=3, delay=1.0)
    def _get_working_ifaces(self) -> List[str]:
        """
        Get list of working network interfaces matching the target IP range.

        Returns:
            List of working interface names

        Raises:
            RadioDiscoveryError: If no suitable interfaces are found
        """
        try:
            interfaces = []
            working_ifaces = get_working_ifaces()

            for iface in working_ifaces:
                try:
                    # Check if interface has an IP in our target range
                    if hasattr(iface, 'ip') and iface.ip and iface.ip.startswith("172.20"):
                        interfaces.append(iface.name)
                except AttributeError as e:
                    self.logger.debug(f"Skipping interface {iface}: {str(e)}")

            if not interfaces:
                raise RadioDiscoveryError("No suitable network interfaces found")

            return interfaces

        except Exception as e:
            raise RadioDiscoveryError(f"Failed to get working interfaces: {str(e)}")

    def _sniff_interface(self, iface: str) -> None:
        """
        Sniff packets on a specific interface.

        Args:
            iface: Network interface name
        """
        try:
            sniff(
                iface=iface,
                prn=self._packet_callback,
                stop_filter=lambda x: self._discovery_result.ip_address is not None,
                timeout=self._sniff_timeout
            )
        except Exception as e:
            self.logger.error(f"Error sniffing on interface {iface}: {str(e)}")

    def discover_radio(self) -> DiscoveryResult:
        """
        Discover radio device by sniffing network interfaces.

        Returns:
            DiscoveryResult containing the discovered radio IP and version

        Raises:
            RadioDiscoveryError: If discovery fails
        """
        self._discovery_result = DiscoveryResult()

        try:
            iface_names = self._get_working_ifaces()
            self.logger.info(f"Starting discovery on interfaces: {', '.join(iface_names)}")

            if len(iface_names) == 1:
                self._sniff_interface(str(iface_names[0]))
            else:
                threads = []
                for iface in iface_names:
                    thread = threading.Thread(
                        target=self._sniff_interface,
                        args=(iface,),
                        name=f"Sniffer-{iface}"
                    )
                    threads.append(thread)
                    thread.start()

                for thread in threads:
                    thread.join()

            if self._discovery_result.ip_address:
                self.logger.info(
                    f"Radio discovered at {self._discovery_result.ip_address} "
                    f"(Version {self._discovery_result.version})"
                )
            else:
                self.logger.warning("No radio discovered during the scan")

            return self._discovery_result

        except Exception as e:
            raise RadioDiscoveryError(f"Radio discovery failed: {str(e)}")


def main() -> None:
    """Main function to demonstrate RadioIpSniffer usage."""
    try:
        sniffer = RadioIpSniffer()
        result = sniffer.discover_radio()

        if result.ip_address:
            print(f"\nDiscovery successful!")
            print(f"Radio IP: {result.ip_address}")
            print(f"Version: {result.version}")
            print(f"Discovery time: {time.ctime(result.discovery_time)}")
        else:
            print("\nNo radio discovered")

    except RadioDiscoveryError as e:
        print(f"Error during radio discovery: {str(e)}")
    except KeyboardInterrupt:
        print("\nDiscovery interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
    lev=1