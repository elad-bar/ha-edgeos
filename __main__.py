from custom_components.edgeos import EdgeOS

from custom_components.edgeos.const import SCAN_INTERVAL

if __name__ == "__main__":
    instance = EdgeOS(None, "192.168.1.1", "admin", "1234", True, ["eth0"], ["device"], "M", SCAN_INTERVAL, True)



