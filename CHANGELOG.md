# Changelog

## 2.1.0

Major refactor:

- Code cleanup
- Fix thread safe issues
- Fix typos
- Improve performance
- Add util for translations
- Removed service of update configuration

New components:

- Consider Away Interval - Number
- Update API Interval - Number
- Update Entities Interval - Number
- Log Incoming Messages - Switch

TODO:

- Data processors not retrieving HOSTNAME
- Devices are not loaded
- Check ignored interfaces
- Monitored state doesn't control which entities to open
- Configuration update without reloading integration

## 2.0.32

- Ignore interfaces that were removed

## 2.0.31

- Replaced soon (2025) to get deprecated SUPPORT\_\* constant with SourceType

## 2.0.30

_Minimum HA Version: 2024.1.0b0_

- Set minimum HA version for component to 2024.1.0b0

## 2.0.29

_Minimum HA Version: 2024.1.0_

- Adjust code to HA 2024.1.0
- Update pre-commit packages

## 2.0.28

- Fix 'TOTAL_INCREASING' for rate sensors by [@Dude4Linux](https://github.com/Dude4Linux)

## 2.0.27

Configuration breaking change

- Adopt Unit of Data & Information from HA Core [#90](https://github.com/elad-bar/ha-edgeos/issues/90) [#84](https://github.com/elad-bar/ha-edgeos/issues/84)

  Changing the units will be available per entity instead of maintaining it with select component, native unit is bytes - B (information) or B/s (traffic)

## 2.0.26

Configuration breaking change

- Change units from Bytes, KBytes and MBytes to B, KB and MB, if the configured unit was other than Bytes, please re-configure it
- Last activity as seconds to return without milliseconds
- Upgrade pre-commit-configuration by [@tetienne](https://github.com/tetienne) [PR #91](https://github.com/elad-bar/ha-edgeos/pull/91)
- Fix integration reload after changing configuration

## 2.0.25

- Add support for Home Assistant integration and device diagnostics
- Removed debug API
- Avoid sending ping when no active WebSockets connection
- Fix warning message regarding of invalid unit's translation
- Fix units format [#90](https://github.com/elad-bar/ha-edgeos/issues/90)
- Fix last restart sensor, switched to uptime in seconds [#94](https://github.com/elad-bar/ha-edgeos/issues/94)

## 2.0.24

- Change log level of warning to debug level for session closed on HA restart
- Core fix: remove session close request, being handled by HA

## 2.0.23

- Add test file to run locally (requires environment variables)
- Cleaner code to resolve URLs
- Remove unused constants
- Core feature: BaseAPI to handle session initialization and termination
- Core fix: wrongfully reported logs of entities getting updated when no update perform

## 2.0.22

- Fix issue with new Select options

## 2.0.21

**Version requires HA v2022.11.0 and above**

- Aligned _Core Select_ according to new HA _SelectEntityDescription_ object

## 2.0.20

- Additional validation for WebSockets disconnection with more logging
- Documentation for API
- Core alignment

## 2.0.19

- Improved logic to identify interface types correctly and present all

## 2.0.18

- Removed configuration and service parameter of `store debug data`

## 2.0.17

- Fix missing switch for monitoring
- Non admin user INFO message that prevents interface switch to turn on / off will be logged once

## 2.0.16

- Add interface line connected binary sensor

## 2.0.15

- Fix unhandled WS session disconnection
- Add support for special interfaces (vtun, switch, pppoe, openvpn)

**Please note:**
For now, special interface do not support to turn on / off

## 2.0.14

**Debugging became easier (less IO and Disk Space)**

- Removed `Store Debug Data` switch (Moved to the API endpoints below)
- Removed WebSocket messages sensors (Moved to the API endpoints below)
- Add endpoints to expose the data was previously stored to files and the messages counters

| Endpoint Name              | Method | Description                                                                                         |
| -------------------------- | ------ | --------------------------------------------------------------------------------------------------- |
| /api/edgeos/list           | GET    | List all the endpoints available (supporting multiple integrations), available once for integration |
| /api/edgeos/{ENTRY_ID}/ha  | GET    | JSON of all HA processed data before sent to entities including messages counters, per integration  |
| /api/edgeos/{ENTRY_ID}/api | GET    | JSON of all raw data from the EdgeOS API, per integration                                           |
| /api/edgeos/{ENTRY_ID}/ws  | GET    | JSON of all raw data from the EdgeOS WebSocket, per integration                                     |

**Authentication: Requires long-living token from HA**

## 2.0.13

- Add support for all interfaces but `loopback` [#76](https://github.com/elad-bar/ha-edgeos/issues/76)
- Improve WS connection management
- Fix WS ping message
- Change interval of ping message
- Add WS connection compression to support deflate
- Add 3 sensors for WS messages - Received, Ignored and Error

## 2.0.12

- Fix wrong parameters for service validation [#77](https://github.com/elad-bar/ha-edgeos/issues/77)

## 2.0.11

- Fix core wrong reference

## 2.0.10

- Update core to latest

## 2.0.9

- Fix configuration migration process

## 2.0.8

- Removed port from configuration as it's not being used

## 2.0.7

- Add service data validation
- Fix binary sensor of interface status

## 2.0.6

- Fix configuration load, save and import processes

## 2.0.5

- Since user with operator role cannot update interface status, non-admin user will have binary sensor for status of interface instead of switch, in addition, an INFO log message will explain it

## 2.0.4

- Add IP address to status switch of its interface [#71](https://github.com/elad-bar/ha-edgeos/issues/71)
- Constants clean up
- Add ability to set the interval to update data and entities separately, to update use the `edgeos.update_configuration` service and set the number of seconds per `update_api_interval` and/or `update_entities_interval` parameters, defaults are API: 30 seconds, Entities: 1 second
- Improved logic of service `edgeos.update_configuration`
- Add to store debug data HA data that is being used to generate HA components
- Add openvpn as supported interface type

## 2.0.3

- Fix wrong parameter for CPU [#70](https://github.com/elad-bar/ha-edgeos/issues/70)
- Another fix json serialization when saving debug data

## 2.0.2

- Fix json serialization when saving debug data

## 2.0.1

- Fix missing validation of entry

## 2.0.0

Component refactored to allow faster future integration for additional features.

New features:

- Enable / Disable interface (Ethernet / Bridge) using a new switch per interface
- Enable / Disable interface monitoring for received and sent data / rate / errors / packets and dropped packets using a switch per interface
- Enable / Disable device monitoring for received and sent data and rate (including device tracker) using a switch per interface
- Enable / Disable store debug data to `./storage` directory of HA for API (`edgeos.debug.api.json`) and WS (`edgeos.debug.ws.json`) data for faster debugging or just to get more ideas for additional features
- Firmware Update binary sensor including link to the new firmware
- Warning when prerequisites of traffic analysis (DPI and Export) are not turned on
- Asynchronous data updates of API and WebSocket to handle disconnection better
- New service: `Update configuration` allows to edit configuration of unit, store debug data, log incoming messages and consider away interval

**Breaking Changes!**

- Most of the configurations moved to be regular components of HA (Log incoming messages, Unit of measurement, Store debug data)
- Configuration UI will hold EdgeOS URL and credentials only:
  - Hostname
  - Port
  - Username
  - Password

**System**

| Entity Name                         | Type          | Description                                                               | Additional information                        |
| ----------------------------------- | ------------- | ------------------------------------------------------------------------- | --------------------------------------------- |
| {Router Name} Unit                  | Select        | Sets whether to monitor device and create all the components below or not |                                               |
| {Router Name} Unknown devices       | Sensor        | Represents number of devices leased by the DHCP server                    | Attributes holds the leased hostname and IPs  |
| {Router Name} CPU                   | Sensor        | Represents CPU usage                                                      | Attributes holds the leased hostname and IPs  |
| {Router Name} RAM                   | Sensor        | Represents RAM usage                                                      | Attributes holds the leased hostname and IPs  |
| {Router Name} Last Restart          | Sensor        | Represents last time the EdgeOS was restarted                             | Attributes holds the leased hostname and IPs  |
| {Router Name} Firmware Updates      | Binary Sensor | New firmware available indication                                         | Attributes holds the url and new release name |
| {Router Name} Log incoming messages | Switch        | Sets whether to log WebSocket incoming messages for debugging             |                                               |
| {Router Name} Store Debug Data      | Switch        | Sets whether to store API and WebSocket latest data for debugging         |                                               |

**Per device**

| Entity Name                                  | Type           | Description                                                                     | Additional information      |
| -------------------------------------------- | -------------- | ------------------------------------------------------------------------------- | --------------------------- |
| {Router Name} {Device Name} Monitored        | Sensor         | Sets whether to monitor device and create all the components below or not       |                             |
| {Router Name} {Device Name} Received Rate    | Sensor         | Received Rate per second                                                        | Statistics: Measurement     |
| {Router Name} {Device Name} Received Traffic | Sensor         | Received total traffic                                                          | Statistics: Total Increment |
| {Router Name} {Device Name} Sent Rate        | Sensor         | Sent Rate per second                                                            | Statistics: Measurement     |
| {Router Name} {Device Name} Sent Traffic     | Sensor         | Sent total traffic                                                              | Statistics: Total Increment |
| {Router Name} {Device Name}                  | Device Tracker | Indication whether the device is or was connected over the configured timeframe |                             |

**Per interface**

| Entity Name                                             | Type   | Description                                                                  | Additional information      |
| ------------------------------------------------------- | ------ | ---------------------------------------------------------------------------- | --------------------------- |
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

## 1.2.6

- Restore value exception handling for WebSocket

## 1.2.5

- Add Brazilian Portuguese Translation [\#66](https://github.com/elad-bar/ha-edgeos/pull/66) by [@LeandroIssa](https://github.com/LeandroIssa)

## 1.2.4

- Add line number to WebSocket error log messages
- Add more log messages for WebSocket

## 1.2.3

- Device and Entity registry - `async_get_registry` is deprecated, change to `async_get`

## 1.2.2

- Hotfix for `Handled %` before first message is being received (division by zero)

## 1.2.1

- Fixed incorrect lookup value for Rate (Sent / Received) per device
- Improved message parsing
- Added web socket messages counters to status binary sensor (Received, Ignored, Handled %)

## 1.2.0

BREAKING CHANGES!

- Added for each interface multiple statistics sensors instead of attributes under the main binary sensor of the interface
- Added for each device multiple statistics sensors instead of attributes under the main binary sensor of the device
- Removed: Uptime sensor, uptime in seconds will be part of the status binary sensor
- Removed: Store debug file from the integration's options
- New service: Generate Debug File to `.storage/edgeos.debug.json`

## 1.1.8

- Removed entity / device delete upon restarting HA

## 1.1.7

- Added support for long term statistics

## 1.1.6

- Upgraded code to support breaking changes of HA v2012.12.0

## v1.1.5

- Fixed integration fails to load with EdgeOS version older than 2.0.9 [\#53](https://github.com/elad-bar/ha-edgeos/pull/53)

## v1.1.4

- Prevent the component to get installed or run with EdgeOS Firmware v1

## v1.1.3

- Fixed monitored_devices appear as disconnected [\#32](https://github.com/elad-bar/ha-edgeos/pull/32) by [@shlomki](https://github.com/shlomki)
- Added documentation of how to set manually log level as debug

## v1.1.2

- Fixed hassfest error (missing iot_class)

## 2020-10-24

**Fixed bugs:**

- Fixed interface parameter that should indicate whether an interface connected or not (l1up vs. up) [\#34](https://github.com/elad-bar/ha-edgeos/pull/34)

## 2020-09-17

**Fixed bugs:**

- Integration setup errors caused by invalid credentials (User input malformed / Unknown error occurred)

## 2020-07-23

**Implemented enhancements:**

- Moved encryption key of component to .storage directory
- Removed support for non encrypted password (**Breaking Change**)

**Fixed bugs:**

- Better handling of password parsing

## 2020-07-21

**Fixed bugs:**

- Don't block startup of Home Assistant [\#36](https://github.com/elad-bar/ha-edgeos/pull/36)

## 2020-07-22

**Implemented enhancements:**

- Support MDI icons for HA 0.113 and above
- Removed NONE option from drop-down, NONE was workaround for a validation issue in Integration's Options and fixed as part of HA v0.112.0

## 2020-07-03

**Fixed bugs:**

- Fix error message on load due to duplicate entities being created - Entity id already exists - ignoring: \*. Platform edgeos does not generate unique IDs

## 2020-06-23

**Fixed bugs:**

- Error fix on failed attempt to access the router

## 2020-06-20

**Fixed bugs:**

- Re-run pre-commit
- Handle closing HA session better to avoid stuck upon restart
- Avoid closing manually sessions opened by HA

## 2020-06-12

**Fixed bugs:**

- Fix logic of reconnect to avoid HA core getting stuck during restart

## 2020-05-29

**Fixed bugs:**

- Fix `Entity id already exists` warning log message on startup

## 2020-05-17

**Fixed bugs:**

- Fix incorrect error message displayed when WebSocket or API request failed
- Fix retry mechanism of API requests
- Fix integration's options error when device or interface list is empty

## 2020-05-14

**Implemented enhancements:**

- Integration's options - Renamed `Update interval` to `Update entities interval` (will reset the value to default in the first run)
- Integration's options - Added `Update API interval` to set the interval in seconds of the component to access EdgeOS API to get new devices and router settings, default=60 [\#27](https://github.com/elad-bar/ha-edgeos/issues/27)
- Improved the logic of heartbeat to take place every 30 seconds for both WebSocket and API connections

**Fixed bugs:**

- Fix API disconnection that causes "Failed to load devices data" errors [\#29](https://github.com/elad-bar/ha-edgeos/issues/29)
- Fix error message on HA termination

## 2020-05-08 #2

**Fixed bugs:**

- Fix redundant calculation of bits to bytes as data is already bytes

## 2020-05-08 #1

**Implemented enhancements:**

- Consider away interval can be modified in integration's options, interval is in seconds, default=180

**Fixed bugs:**

- Fix default value of unit in integration's options

## 2020-05-06

**Fixed bugs:**

- Fix WebSocket disconnections [\#26](https://github.com/elad-bar/ha-edgeos/issues/26)

## 2020-05-02

**Implemented enhancements:**

- Improved device tracker is home logic to consider traffic instead of just DPI report
- Version validation upon adding new integration (Required at least v1.10)

## 2020-05-01

**Fixed bugs:**

- Fix device_tracker didn't work correctly. It is always displayed not home

**Implemented enhancements:**

- More enhancements to options, ability to change setup details
- Support new translation format of HA 0.109.0
- Added **main**.py to root directory for debugging

## 2020-04-28 #3

**Fixed bugs:**

- Invalid credentials to EdgeOS Router when using IP [\#25](https://github.com/elad-bar/ha-edgeos/issues/25)

## 2020-04-28 #2

**Fixed bugs:**

- Async login without sleep 1 second

## 2020-04-28 #1

**Fixed bugs:**

- Fix disabled entity check throws an exception in logs

## 2020-04-27

**Fixed bugs:**

- Fix disabled entities still being triggered for updates

## 2020-04-26

**Fixed bugs:**

- Fix disabled entities are getting enabled after periodic update (update interval)

## 2020-04-25

**Implemented enhancements:**

- Simplified the way calculating whether device is connected or not, based on report of traffic analysis instead of calculating amount of traffic (bps) over the last 3 minutes [\#24](https://github.com/elad-bar/ha-edgeos/issues/24)
- Moved service `edgeos.save_debug_data` to Integration -> Options as configuration (that being reset after doing the action once)
- Moved service `edgeos.log_events` to Integration -> Options as configuration to toggle upon need
- Added ability to configure the log level of the component from Integration - Options, more details in README

## 2020-04-20 #2

**Fixed bugs:**

- Fix connection maximum attempts and added keep-alive WS message every 30 seconds [\#21](https://github.com/elad-bar/ha-edgeos/issues/21)

## 2020-04-20 #1

**Fixed bugs:**

- Missing resource for update interval field [\#19](https://github.com/elad-bar/ha-edgeos/issues/19)

## 2020-04-18

**Implemented enhancements:**

- Added changelog
- Added ability to configure update entities interval in seconds (Integrations -> Integration Name -> Options) [\#19](https://github.com/elad-bar/ha-edgeos/issues/19) [\#15](https://github.com/elad-bar/ha-edgeos/issues)
- Added instructions how to install in HACS [\#16](https://github.com/elad-bar/ha-edgeos/issues/16)
- Added password encryption upon saving the integration settings
- Improved drop-down logic to choose device trackers, monitored devices and interfaces [\#9](https://github.com/elad-bar/ha-edgeos/issues/9)
- Moved code to new file structure
- More logs added for easier debugging

**Fixed bugs:**

- Login failure initiated reconnect mechanism instead of die gracefully
