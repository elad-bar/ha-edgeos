# EdgeOS
## Description
Provides an integration between EdgeOS (Ubiquiti) routers to Home Assistant.

[Changelog](https://github.com/elad-bar/ha-edgeos/blob/master/CHANGELOG.md)

## How to

#### Installation
Look for "Integration with EdgeOS (Ubiquiti)" and install

#### Requirements
* EdgeRouter User with 'Operator' level access or higher
* Traffic Analysis set to 'Enabled' (both `dpi` and `export` enabled under `system/traffic-analysis`)

#### Setup
To add integration use Configuration -> Integrations -> Add `EdgeOS`
Integration supports  **multiple** EdgeOS devices

Fields name | Type | Required | Default | Description
--- | --- | --- | --- | --- |
Name | Textbox | + | - | Represents the integration name
Host | Textbox | + | - | Hostname or IP address to access EdgeOS device
Username | Textbox | + | - | Username of user with `Operator` level access or higher, better to create a dedicated user for that integration for faster issues identification
Password | Textbox  | + | - | 
Unit | Drop-down | + | Bytes | Unit for sensors, available options are: Bytes, KiloBytes, MegaBytes  
 
###### EdgeOS Device validation errors
Errors |
--- |   
Cannot reach device (404) |
Invalid credentials (403) |
General authentication error (when failed to get valid response from device) |
Could not retrieve device data from EdgeOS Router |
Export (traffic-analysis) configuration is disabled, please enable |
Deep Packet Inspection (traffic-analysis) configuration is disabled, please enable |

###### Password protection
In latest version new capability added to encrypt password before saving integration settings to `.storage` </br>
In order to benefit from that capability, please remove and re-add the integration (after restart of HA between actions) for that capability to work,
As long as the password will remain in clear text saved in integration setting, the following warning log message will appear during restart:
```
EdgeOS password is not encrypted, please remove integration and reintegrate
```

#### Options
*Configuration -> Integrations -> {Integration} -> Options* <br />

Fields name | Type | Required | Default | Description
--- | --- | --- | --- | --- |
Host | Textbox | + | - | Hostname or IP address to access EdgeOS device
Username | Textbox | + | - | Username of user with `Operator` level access or higher, better to create a dedicated user for that integration for faster issues identification
Password | Textbox  | + | - | 
Clear credentials | Check-box | + | Unchecked |  Will reset username and password (Not being stored under options)
Unit | Drop-down | + | Bytes | Unit for sensors, available options are: Bytes, KiloBytes, MegaBytes  
Monitored devices | Drop-down | + | NONE | Devices to monitor using binary_sensor and sensor
Monitored interfaces | Drop-down | + | NONE | Interfaces to monitor using binary_sensor and sensor,
Track | Drop-down | + | NONE | Devices to track using device_trac
Update Interval | Textbox | + | 1 | Number of seconds to update entities
Save debug file | Check-box | + | Unchecked |  Will store debug file, more details below (Not being stored under options)
Log level | Drop-down | + | Default | Changes component's log level (more details below)
Log incoming messages | Check-box | + | Unchecked | Whether to log as DEBUG incoming web-socket messages or not
  
###### Drop-downs work-around
As workaround for UI not allowing submitting the form without all fields with values,
First option in each drop-down is NONE, 
as long as this option is checked, 
it will not allow checking other items

###### Log Level's drop-down
New feature to set the log level for the component without need to set log_level in `customization:` and restart or call manually `logger.set_level` and loose it after restart.

Upon startup or integration's option update, based on the value chosen, the component will make a service call to `logger.set_level` for that component with the desired value,

In case `Default` option is chosen, flow will skip calling the service, after changing from any other option to `Default`, it will not take place automatically, only after restart

###### Save debug file
Will store debug data from the component to HA CONFIG path named `edgeos_data.log`
  
## Components
#### Default
Name | Type | State | Attributes |
--- | --- | --- | --- | 
{Integration Name} System Status | Binary Sensor | Connected or not |  CPU<br /> Memory<br /> Up-time<br /> API Last Update<br /> WS Last Update
{Integration Name} System Uptime | Sensor | Time since restart in seconds | CPU<br /> Memory<br /> Is Alive<br /> API Last Update<br /> WS Last Update
{Integration Name} Unknown Devices | Sensor | Number of unknown devices | Unknown Devices description

#### Monitored Devices 
Name | Type | State | Attributes |
--- | --- | --- | --- | 
{Integration Name} Device {Device Name} | Binary Sensor | Connected or not |  IP<br /> MAC<br /> Name<br /> {Unit}Bytes (Sent)<br /> {Unit}Bytes/ps (Sent)<br />{Unit}Bytes (Received)<br />{Unit}Bytes/ps (Received)<br />Last Activity<br />Last Changed

#### Monitored Interfaces 
Name | Type | State | Attributes |
--- | --- | --- | --- | 
{Integration Name} Interface {Interface Name} | Binary Sensor | Connected or not |  Name<br /> Duplex<br /> Link Speed (Mbps)<br /> address<br /> Packets (Received)<br />Packets (Sent)<br /> Errors (Received)<br />Errors (Sent)<br />Dropped packets (Received)<br />Dropped packets (Sent)<br/>{Unit}Bytes (Received)<br/>{Unit}Bytes (Sent)<br/>{Unit}Bytes/ps (Received)<br/>{Unit}Bytes/ps (Sent)<br />Multicast<br />Last Changed

#### Tracked Devices
Name | Type | State | Attributes |
--- | --- | --- | --- | 
{Integration Name} {Device Name} | Device Tracker | Home or Away |  Host<br /> IP<br /> MAC<br /> Name<br /> Last Activity<br /> Connected

### Setting up the integration

###### Setup integration
![EdgeOS Setup](https://raw.githubusercontent.com/elad-bar/ha-edgeos/master/docs/images/EdgeOS-Setup.PNG)

###### Edit options
![EdgeOS Setup](https://raw.githubusercontent.com/elad-bar/ha-edgeos/master/docs/images/EdgeOS-Options.PNG)
