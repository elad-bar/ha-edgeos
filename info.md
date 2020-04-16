# EdgeOS
### Description
Provides an integration between EdgeOS (Ubiquiti) routers to Home Assistant.

### How to set it up:

#### Installation
Please install in HACS, look for "Integration with EdgeOS (Ubiquiti)"

#### Requirements
* EdgeRouter User with 'Operator' level access or higher
* Traffic Analysis set to 'Enabled' (both `dpi` and `export` enabled under `system/traffic-analysis`)

#### Basic configuration
* Configuration should be done via Configuration -> Integrations.
* In case you are already using that integration with YAML Configuration - please remove it
* Integration supports **multiple** devices 
* In the setup form, the following details are mandatory:
  * Name - Unique
  * Host (or IP)
  * Username (It's better to create a unique user to identify issues related to the integration)
  * Password 
  * Unit (Bytes, Kilobytes, Megabytes) 
* Upon submitting the form of creating an integration login to the EdgeOS device will take place and will cause failure in case:
  * Cannot reach device (404)
  * Invalid credentials (403)
  * General authentication error (when failed to get valid response from device)
  * Could not retrieve device data from EdgeOS Router
  * Export (traffic-analysis) configuration is disabled, please enable
  * Deep Packet Inspection (traffic-analysis) configuration is disabled, please enable

#### Monitoring interfaces, devices and track devices
*Configuration -> Integrations -> {Integration} -> Options* <br />

Form will open at the first time with 3 multiple selection drop-downs:
* Monitored devices
* Monitored interfaces
* Track 

First option in each drop-down is NONE, as long as this option is checked, it will not allow checking other items
  
### By default, following entities will be generated 
###### Binary Sensor
```
Binary Sensor
Name: {Integration Name} System Status
State: Connected
Attributes
    API Last Update
    WS Last Update
    cpu
    mem
    uptime
```

###### Sensors
```
Name: {Integration Name} System Uptime
State: Up time in seconds
Attributes
    API Last Update
    WS Last Update
    cpu
    mem
    is alive
```
```
Name: {Integration Name} Unknown Devices
State: # of devices connected not set as static IPs
Attributes
    Unknown Devices
```

#### Following components will be generated upon options configuration of the integration:
More details available after this section
 
###### Binary Sensor (Per monitored interface)
```
Name: {Integration Name} Interface {Interface Name}
State: Connected
Attributes
    Duplex
    Link Speed (Mbps)
    MAC
    addresses
    Packets (Sent / Received)
    Errors (Sent / Received)
    Dropped Packets (Sent / Received)
    *Bytes (Sent / Received)
    *Bytes/ps (Sent / Received)
    Multicast
```

###### Binary Sensor (Per monitored device)
```
Name: {Integration Name} Device {Device Name}
State: Connected
Attributes
    IP
    MAC
    *Bytes/ps (Sent / Received)
    *Bytes (Sent / Received)
```

###### Device Tracker (Per tracked device)
```
Name: {Integration Name} {Device Name}
State: Home / Not home
Attributes
    host
    ip
    mac
    Connected
    Last Activity
```

### Setting up the integration

###### Setup integration
![EdgeOS Setup](https://raw.githubusercontent.com/elad-bar/ha-edgeos/master/docs/images/EdgeOS-Setup.PNG)

###### Edit options
![EdgeOS Setup](https://raw.githubusercontent.com/elad-bar/ha-edgeos/master/docs/images/EdgeOS-Options.PNG)
