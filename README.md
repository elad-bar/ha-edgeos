# EdgeOS
## Description
Provides an integration between EdgeOS (Ubiquity) routers to Home Assistant,
Creates the following components:
* Binary Sensor - per monitored device whether it's connected, attributes: IP, MAC, Bytes / Bps (Sent / Received)
* Binary Sensor - per interface - whether its connected, attributes: MAC, Duplex, Link Speed (Mbps), Addresses, Packets / Bytes / Errors / Dropped Packets / Bps (Sent / Received)
* Sensor - System up-time, attributes: Is Alive, CPU, Memory, API Last Update, WS Last Update
* Sensor - Number of Unknown Devices (Not part of DHCP Static Address), attributes - IP of devices
* Binary Sensor - System Status, attributes: up-time, CPU, Memory, API Last Update, WS Last Update

When setting device_tracker domain it will add per host device tracker, "unsee" command takes place after 1 hour due to EdgeOS late update

## Requirements
* EdgeRouter User with 'Operator' level access or higher
* Traffic Analysis set to 'Hosts only' or 'Enabled'

## Example configuration.yaml
```
edgeos:
    host: !secret edge_os_host #Hostname / IP
    ssl: !secret edge_os_ssl #Supports SSL (true/false) - should be true
    username: !secret edge_os_username #Username of EdgeOS
    password: !secret edge_os_password #Password of EdgeOS
    cert_file: !secret ssl_certificate #Path to the certificate (full-chain)
    monitored_interfaces: #List of interfaces
        - eth0
    monitored_devices: #List of network devices to monitor
        - my-iPhone
        - PC1
        - PC2
    unit: 'M' #Optional - Allowed values: '' - represents bytes, 'K' - Kilobytes, 'M' - Megabytes

device_tracker:
  - platform: edgeos
    hosts: #List of network devices to treat as device tracker
      - my-iPhone
```

## Custom_updater
```
custom_updater:
  track:
    - components
  component_urls:
    - https://raw.githubusercontent.com/elad-bar/ha-edgeos/master/edgeos.json
```

