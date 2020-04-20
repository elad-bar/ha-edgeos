# Changelog

## 2020-04-20

**Fixed bugs:**

- Missing resource for update interval field [\#19](https://github.com/elad-bar/ha-edgeos/issues/19)

## 2020-04-18

**Implemented enhancements:**

- Added changelog
- Added ability to configure update entities interval in seconds (Integrations -> Integration Name -> Options)  [\#19](https://github.com/elad-bar/ha-edgeos/issues/19) [\#15](https://github.com/elad-bar/ha-edgeos/issues)
- Added instructions how to install in HACS [\#16](https://github.com/elad-bar/ha-edgeos/issues/16)
- Added password encryption upon saving the integration settings
- Improved drop-down logic to choose device trackers, monitored devices and interfaces [\#9](https://github.com/elad-bar/ha-edgeos/issues/9)
- Moved code to new file structure
- More logs added for easier debugging

**Fixed bugs:**

- Login failure initiated reconnect mechanism instead of die gracefully 
