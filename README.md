# EdgeOS

## Description

Provides an integration between EdgeOS (Ubiquiti) routers to Home Assistant.

[Changelog](https://github.com/elad-bar/ha-edgeos/blob/master/CHANGELOG.md)

## How to

#### Installation

Look for "Integration with EdgeOS (Ubiquiti)" and install

#### Requirements

- EdgeRouter with at least firmware version 2.0
- EdgeRouter User with 'Operator' level access or higher
- Traffic Analysis set to 'Enabled' (both `dpi` and `export` enabled under `system/traffic-analysis`)

#### Setup

To add integration use Configuration -> Integrations -> Add `EdgeOS`
Integration supports **multiple** EdgeOS devices

| Fields name | Type      | Required | Default | Description                                                                                                                                      |
|-------------|-----------|----------|---------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| Name        | Textbox   | +        | -       | Represents the integration name                                                                                                                  |
| Host        | Textbox   | +        | -       | Hostname or IP address to access EdgeOS device                                                                                                   |
| Username    | Textbox   | +        | -       | Username of user with `Operator` level access or higher, better to create a dedicated user for that integration for faster issues identification |
| Password    | Textbox   | +        | -       |                                                                                                                                                  |

###### EdgeOS Device validation errors

| Errors                                                                             |
|------------------------------------------------------------------------------------|
| Cannot reach device (404)                                                          |
| Invalid credentials (403)                                                          |
| General authentication error (when failed to get valid response from device)       |
| Could not retrieve device data from EdgeOS Router                                  |
| Export (traffic-analysis) configuration is disabled, please enable                 |
| Deep Packet Inspection (traffic-analysis) configuration is disabled, please enable |
| Unsupported firmware version                                                       |

###### Encryption key got corrupted

If a persistent notification popped up with the following message:

```
Encryption key got corrupted, please remove the integration and re-add it
```

It means that encryption key was modified from outside the code,
Please remove the integration and re-add it to make it work again.

#### Options

_Configuration -> Integrations -> {Integration} -> Options_ <br />

| Fields name              | Type      | Required | Default   | Description                                                                                                                                      |
|--------------------------|-----------|----------|-----------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| Host                     | Textbox   | +        | -         | Hostname or IP address to access EdgeOS device                                                                                                   |
| Username                 | Textbox   | +        | -         | Username of user with `Operator` level access or higher, better to create a dedicated user for that integration for faster issues identification |
| Password                 | Textbox   | +        | -         |                                                                                                                                                  |
| Clear credentials        | Check-box | +        | Unchecked | Will reset username and password (Not being stored under options)                                                                                |
| Consider away interval   | Textbox   | +        | 180       | Consider away interval in seconds                                                                                                                |
| Update API Interval      | Textbox   | +        | 60        | Number of seconds to update new devices and router settings                                                                                      |
| Update Entities Interval | Textbox   | +        | 1         | Number of seconds to update entities                                                                                                             |

###### Log Level's drop-down

New feature to set the log level for the component without need to set log_level in `customization:` and restart or call manually `logger.set_level` and loose it after restart.

Upon startup or integration's option update, based on the value chosen, the component will make a service call to `logger.set_level` for that component with the desired value,

In case `Default` option is chosen, flow will skip calling the service, after changing from any other option to `Default`, it will not take place automatically, only after restart

###### Save debug file

Will store debug data from the component to `.storage/edgeos.debug.json`

#### Debugging

To set the log level of the component to DEBUG, please set it from the options of the component if installed, otherwise, set it within configuration YAML of HA:

```yaml
logger:
  default: warning
  logs:
    custom_components.edgeos: debug
```

## Components

### System
| Entity Name                         | Type          | Description                                                               | Additional information                        |
|-------------------------------------|---------------|---------------------------------------------------------------------------|-----------------------------------------------|
| {Router Name} Unit                  | Select        | Sets whether to monitor device and create all the components below or not |                                               |
| {Router Name} Unknown devices       | Sensor        | Represents number of devices leased by the DHCP server                    | Attributes holds the leased hostname and IPs  |
| {Router Name} Firmware Updates      | Binary Sensor | New firmware available indication                                         | Attributes holds the url and new release name |
| {Router Name} Log incoming messages | Switch        | Sets whether to log WebSocket incoming messages for debugging             |                                               |
| {Router Name} Store Debug Data      | Switch        | Sets whether to store API and WebSocket latest data for debugging         |                                               |


### Per device
| Entity Name                                  | Type           | Description                                                                     | Additional information      |
|----------------------------------------------|----------------|---------------------------------------------------------------------------------|-----------------------------|
| {Router Name} {Device Name} Monitored        | Sensor         | Sets whether to monitor device and create all the components below or not       |                             |
| {Router Name} {Device Name} Received Rate    | Sensor         | Received Rate per second                                                        | Statistics: Measurement     |
| {Router Name} {Device Name} Received Traffic | Sensor         | Received total traffic                                                          | Statistics: Total Increment |
| {Router Name} {Device Name} Sent Rate        | Sensor         | Sent Rate per second                                                            | Statistics: Measurement     |
| {Router Name} {Device Name} Sent Traffic     | Sensor         | Sent total traffic                                                              | Statistics: Total Increment |
| {Router Name} {Device Name}                  | Device Tracker | Indication whether the device is or was connected over the configured timeframe |                             |


### Per interface
| Entity Name                                             | Type   | Description                                                                  | Additional information      |
|---------------------------------------------------------|--------|------------------------------------------------------------------------------|-----------------------------|
| {Router Name} {Interface Name} Status                   | Switch | Sets whether to interface is active or not                                   |                             |
| {Router Name} {Interface Name} Monitored                | Switch | Sets whether to monitor interface and create all the components below or not |                             |
| {Router Name} {Interface Name} Received Rate            | Sensor | Received Rate per second                                                     | Statistics: Measurement     |
| {Router Name} {Interface Name} Received Traffic         | Sensor | Received total traffic                                                       | Statistics: Total Increment |
| {Router Name} {Interface Name} Received Dropped Packets | Sensor | Received packets lost                                                        | Statistics: Total Increment |
| {Router Name} {Interface Name} Received Errors          | Sensor | Received errors                                                              | Statistics: Total Increment |
| {Router Name} {Interface Name} Received Packets         | Sensor | Received packets                                                             | Statistics: Total Increment |
| {Router Name} {Interface Name} Sent Rate                | Sensor | Sent Rate per second                                                         | Statistics: Measurement     |
| {Router Name} {Interface Name} Sent Traffic             | Sensor | Sent total traffic                                                           | Statistics: Total Increment |
| {Router Name} {Interface Name} Sent Dropped Packets     | Sensor | Sent packets lost                                                            | Statistics: Total Increment |
| {Router Name} {Interface Name} Sent Errors              | Sensor | Sent errors                                                                  | Statistics: Total Increment |
| {Router Name} {Interface Name} Sent Packets             | Sensor | Sent packets                                                                 | Statistics: Total Increment |


_Unit of measurement for `Traffic` and `Rate` are according to the unit settings of the integration_
