# EdgeOS

## Description

Provides an integration between EdgeOS (Ubiquiti) routers to Home Assistant.

[Changelog](https://github.com/elad-bar/ha-edgeos/blob/master/CHANGELOG.md)

## How to

#### Requirements

- EdgeRouter with at least firmware version 2.0
- EdgeRouter User with 'Operator' level access or higher
- Traffic Analysis set to 'Enabled' (both `dpi` and `export` enabled under `system/traffic-analysis`)
- To enable / disable interfaces an `admin` role is a required

#### Installations via HACS
- In HACS, look for "Ubiquiti EdgeOS Routers" and install and restart
- In Settings  --> Devices & Services - (Lower Right) "Add Integration"

#### Setup

To add integration use Configuration -> Integrations -> Add `EdgeOS`
Integration supports **multiple** EdgeOS devices

| Fields name | Type    | Required | Default | Description                                                                                                                                      |
|-------------|---------|----------|---------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| Host        | Textbox | +        | -       | Hostname or IP address to access EdgeOS device, can hold also port (HOST:PORT), default port is 443                                              |
| Username    | Textbox | +        | -       | Username of user with `Operator` level access or higher, better to create a dedicated user for that integration for faster issues identification |
| Password    | Textbox | +        | -       |                                                                                                                                                  |

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

| Fields name       | Type      | Required | Default   | Description                                                                                                                                      |
|-------------------|-----------|----------|-----------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| Host              | Textbox   | +        | -         | Hostname or IP address to access EdgeOS device, can hold also port (HOST:PORT), default port is 443                                              |
| Username          | Textbox   | +        | -         | Username of user with `Operator` level access or higher, better to create a dedicated user for that integration for faster issues identification |
| Password          | Textbox   | +        | -         |                                                                                                                                                  |
| Clear credentials | Check-box | +        | Unchecked | Will reset username and password (Not being stored under options)                                                                                |

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
| {Router Name} CPU                   | Sensor        | Represents CPU usage                                                      |                                               |
| {Router Name} RAM                   | Sensor        | Represents RAM usage                                                      |                                               |
| {Router Name} Uptime                | Sensor        | Represents last time the EdgeOS was restarted                             |                                               |
| {Router Name} Unknown devices       | Sensor        | Represents number of devices leased by the DHCP server                    | Attributes holds the leased hostname and IPs  |
| {Router Name} Firmware Updates      | Binary Sensor | New firmware available indication                                         | Attributes holds the url and new release name |
| {Router Name} Log incoming messages | Switch        | Sets whether to log WebSocket incoming messages for debugging             |                                               |

*Changing the unit will reload the integration*

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
| Entity Name                                             | Type          | Description                                                                  | Additional information                      |
|---------------------------------------------------------|---------------|------------------------------------------------------------------------------|---------------------------------------------|
| {Router Name} {Interface Name} Status                   | Switch        | Sets whether to interface is active or not                                   | Available only if user level is `admin`     |
| {Router Name} {Interface Name} Status                   | Binary Sensor | Indicates whether interface is active or not                                 | Available only if user level is not `admin` |
| {Router Name} {Interface Name} Connected                | Binary Sensor | Indicates whether interface's port is connected or not                       |                                             |
| {Router Name} {Interface Name} Monitored                | Switch        | Sets whether to monitor interface and create all the components below or not |                                             |
| {Router Name} {Interface Name} Received Rate            | Sensor        | Received Rate per second                                                     | Statistics: Measurement                     |
| {Router Name} {Interface Name} Received Traffic         | Sensor        | Received total traffic                                                       | Statistics: Total Increment                 |
| {Router Name} {Interface Name} Received Dropped Packets | Sensor        | Received packets lost                                                        | Statistics: Total Increment                 |
| {Router Name} {Interface Name} Received Errors          | Sensor        | Received errors                                                              | Statistics: Total Increment                 |
| {Router Name} {Interface Name} Received Packets         | Sensor        | Received packets                                                             | Statistics: Total Increment                 |
| {Router Name} {Interface Name} Sent Rate                | Sensor        | Sent Rate per second                                                         | Statistics: Measurement                     |
| {Router Name} {Interface Name} Sent Traffic             | Sensor        | Sent total traffic                                                           | Statistics: Total Increment                 |
| {Router Name} {Interface Name} Sent Dropped Packets     | Sensor        | Sent packets lost                                                            | Statistics: Total Increment                 |
| {Router Name} {Interface Name} Sent Errors              | Sensor        | Sent errors                                                                  | Statistics: Total Increment                 |
| {Router Name} {Interface Name} Sent Packets             | Sensor        | Sent packets                                                                 | Statistics: Total Increment                 |


_Unit of measurement for `Traffic` and `Rate` are according to the unit settings of the integration_

## Services

### Update configuration
Allows to set:
- Consider away interval - Time to consider a device without activity as AWAY (any value between 10 and 1800 in seconds)
- Log incoming messages - Enable / Disable logging of incoming WebSocket messages for debug
- Store debug data - Enable / Disable store debug data to './storage' directory of HA for API (edgeos.debug.api.json) and WS (edgeos.debug.ws.json) data for faster debugging or just to get more ideas for additional features
- Unit of measurement
- Update API interval - Interval in seconds to update API data
- Update Entities interval - Interval in seconds to update entities

More details available in `Developer tools` -> `Services` -> `edgeos.update_configuration`

```yaml
service: edgeos.update_configuration
data:
  device_id: {Main device ID}
  unit: Bytes
  log_incoming_messages: true
  consider_away_interval: 180
  update_api_interval: 30
  update_entities_interval: 1
```

*Changing the unit will reload the integration*

## Endpoints

| Endpoint Name              | Method | Description                                                                                         |
|----------------------------|--------|-----------------------------------------------------------------------------------------------------|
| /api/edgeos/list           | GET    | List all the endpoints available (supporting multiple integrations), available once for integration |
| /api/edgeos/{ENTRY_ID}/ha  | GET    | JSON of all HA processed data before sent to entities, per integration                              |
| /api/edgeos/{ENTRY_ID}/api | GET    | JSON of all raw data from the EdgeOS API, per integration                                           |
| /api/edgeos/{ENTRY_ID}/ws  | GET    | JSON of all raw data from the EdgeOS WebSocket, per integration                                     |

**Authentication: Requires long-living token from HA**


### Examples

#### List

*Request*
```bash
curl https://ha_url:8123/api/edgeos/list
   -H "Accept: application/json"
   -H "Authorization: Bearer {token}"
```

#### Home Assistant Data

*Request*
```bash
curl https://ha_url:8123/api/edgeos/{ENTRY_ID}/ha
   -H "Accept: application/json"
   -H "Authorization: Bearer {token}"
```

#### WebSockets Data

*Request*
```bash
curl https://ha_url:8123/api/edgeos/{ENTRY_ID}/ws
   -H "Accept: application/json"
   -H "Authorization: Bearer {token}"
```

#### API Data

```bash
curl https://ha_url:8123/api/edgeos/{ENTRY_ID}/api
   -H "Accept: application/json"
   -H "Authorization: Bearer {token}"
```
