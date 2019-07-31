<h1>EdgeOS</h1>
<h2>Requirements</h2>
<ul>
<li>EdgeRouter User with 'Operator' level access or higher</li>
<li>Traffic Analysis set to 'Hosts only' or 'Enabled'</li>
    </ul>
<h2>Description</h2>
Provides an integration between EdgeOS (Ubiquity) routers to Home Assistant,
Creates the following components:
<li> Binary Sensor - per monitored device whether it's connected, attributes: IP, MAC, Bytes / Bps (Sent / Received)</li>
<li> Binary Sensor - per interface - whether its connected, attributes: MAC, Duplex, Link Speed (Mbps), Addresses, Packets / Bytes / Errors / Dropped Packets / Bps (Sent / Received)</li>
<li> Sensor - System up-time, attributes: CPU, Memory, API Last Update, WS Last Update</li>
<li> Sensor - Number of Unknown Devices (Not part of DHCP Static Address), attributes - IP of devices</li>

When setting device_tracker domain it will add per host device tracker, "unsee" command takes place after 1 hour due to EdgeOS late update

<h2>Example</h2>
<pre>
configuration: 
    edgeos:
        #Hostname / IP
        host: !secret edge_os_host
        #Supports SSL (true/false) - should be true
        ssl: !secret edge_os_ssl
        #Username of EdgeOS
        username: !secret edge_os_username
        #Password of EdgeOS
        password: !secret edge_os_password
        #Path to the certificate (full-chain)
        cert_file: !secret ssl_certificate	
        #List of interfaces
        monitored_interfaces: 				
            - eth0
        #List of network devices to monitor
        monitored_devices:
            - PC1
            - PC2
        #Optional - Allowed values:
        #  '' - represents bytes
        #  'K' - represents Kilobytes
        #  'M' - represents Megabytes
        unit: 'M'

    device_tracker:
      - platform: edgeos
        #List of network devices to treat as device tracker
        hosts:
          - MOBILE-PHONE
</pre>

<h2>Custom_updater</h2>
<pre>
custom_updater:
  track:
    - components
  component_urls:
    - https://raw.githubusercontent.com/elad-bar/ha-edgeos/master/edgeos.json
</pre>
