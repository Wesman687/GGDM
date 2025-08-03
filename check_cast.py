from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
import time

class ChromecastListener(ServiceListener):
    def __init__(self):
        self.found = []

    def remove_service(self, zeroconf, type, name):
        pass  # We don't care about removals

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info:
            device = {
                "name": name,
                "address": ".".join(str(b) for b in info.addresses[0]),
                "port": info.port,
                "properties": info.properties
            }
            self.found.append(device)
            print(f"🎯 Found Chromecast device: {device['name']} at {device['address']}:{device['port']}")

def scan_chromecast(timeout=5):
    zeroconf = Zeroconf()
    listener = ChromecastListener()
    browser = ServiceBrowser(zeroconf, "_googlecast._tcp.local.", listener)

    print(f"🔍 Scanning for Chromecast devices for {timeout} seconds...")
    time.sleep(timeout)
    zeroconf.close()

    if not listener.found:
        print("❌ No Chromecast devices found. Likely a network/firewall/mDNS issue.")
    else:
        print(f"✅ Found {len(listener.found)} device(s).")

if __name__ == "__main__":
    scan_chromecast()
