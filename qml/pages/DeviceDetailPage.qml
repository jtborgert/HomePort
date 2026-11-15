import QtQuick 2.0
import Sailfish.Silica 1.0

Page {
    id: page
    allowedOrientations: defaultAllowedOrientations

    property string deviceId: ""
    property string deviceName: ""
    property string deviceClass: ""
    property string zoneName: ""
    property var capabilities: []
    property var capabilitiesObj: ({})
    property var state: ({})

    property int updateTrigger: 0

    property bool isFavorite: {
        updateTrigger
        if (typeof appWindow !== "undefined" && appWindow.isDeviceFavorite) {
            return appWindow.isDeviceFavorite(deviceId)
        }
        return false
    }

    Connections {
        target: typeof appWindow !== "undefined" ? appWindow : null
        onDeviceCapabilityChanged: {
            if (deviceId === page.deviceId) {
                page.updateTrigger++
            }
        }
        onFavoriteChanged: {
            if (deviceId === page.deviceId) {
                page.updateTrigger++
            }
        }
        onDevicesUpdated: {
            page.updateTrigger++
        }
    }

    // Find current device from appWindow devicesMap or devicesModel
    function getDevice() {
        updateTrigger
        if (typeof appWindow !== "undefined" && appWindow.getDevice) {
            var d = appWindow.getDevice(deviceId)
            if (d) return d
        }
        if (typeof devicesModel !== "undefined") {
            for (var i = 0; i < devicesModel.count; i++) {
                if (devicesModel.get(i).id === deviceId) {
                    return devicesModel.get(i)
                }
            }
        }
        return null
    }

    function getDeviceCapabilities() {
        updateTrigger
        var dev = getDevice()
        if (dev && dev.capabilities) {
            var c = dev.capabilities
            if (Array.isArray(c)) return c
            if (typeof c === "string") {
                return c.split(",").map(function(s) { return s.trim(); }).filter(function(s) { return s.length > 0; })
            }
            if (c.count !== undefined) {
                var arr = []
                for (var i = 0; i < c.count; i++) {
                    var itm = c.get(i)
                    arr.push(typeof itm === "string" ? itm : (itm.id || itm.value || itm.name || ""))
                }
                if (arr.length > 0) return arr
            }
        }
        if (page.capabilities) {
            if (Array.isArray(page.capabilities)) return page.capabilities
            if (typeof page.capabilities === "string") {
                return page.capabilities.split(",").map(function(s) { return s.trim(); }).filter(function(s) { return s.length > 0; })
            }
            if (page.capabilities.count !== undefined) {
                var arr2 = []
                for (var j = 0; j < page.capabilities.count; j++) {
                    var itm2 = page.capabilities.get(j)
                    arr2.push(typeof itm2 === "string" ? itm2 : (itm2.id || itm2.value || itm2.name || ""))
                }
                if (arr2.length > 0) return arr2
            }
        }
        return []
    }

    function hasCapability(capId) {
        var caps = getDeviceCapabilities()
        return caps.indexOf(capId) !== -1
    }

    function getCapValue(capId) {
        updateTrigger
        var dev = getDevice()
        if (dev) {
            if (dev.state && dev.state[capId] !== undefined && dev.state[capId] !== null) {
                return dev.state[capId]
            }
            if (dev.capabilitiesObj && dev.capabilitiesObj[capId] && dev.capabilitiesObj[capId].value !== undefined && dev.capabilitiesObj[capId].value !== null) {
                return dev.capabilitiesObj[capId].value
            }
            if (capId === "onoff" && dev.onoff !== undefined && dev.onoff !== null) {
                return dev.onoff
            }
            if (capId === "dim" && dev.dim !== undefined && dev.dim !== null) {
                return dev.dim
            }
        }
        if (page.state && page.state[capId] !== undefined && page.state[capId] !== null) {
            return page.state[capId]
        }
        var capObj = getCapObj(capId)
        if (capObj && capObj.value !== undefined && capObj.value !== null) {
            return capObj.value
        }
        return null
    }

    function getCapObj(capId) {
        updateTrigger
        var dev = getDevice()
        if (dev && dev.capabilitiesObj && dev.capabilitiesObj[capId]) {
            return dev.capabilitiesObj[capId]
        }
        if (page.capabilitiesObj && page.capabilitiesObj[capId]) {
            return page.capabilitiesObj[capId]
        }
        return null
    }

    function getCapTitle(capId) {
        var capObj = getCapObj(capId)
        if (capObj && capObj.title) {
            return capObj.title
        }
        var titles = {
            "onoff": qsTr("Power"),
            "dim": qsTr("Brightness"),
            "volume_set": qsTr("Volume"),
            "volume_mute": qsTr("Mute"),
            "speaker_playing": qsTr("Playback"),
            "speaker_next": qsTr("Next Track"),
            "speaker_prev": qsTr("Previous Track"),
            "light_temperature": qsTr("Color Temperature"),
            "light_hue": qsTr("Color Hue"),
            "light_saturation": qsTr("Color Saturation"),
            "light_mode": qsTr("Light Mode"),
            "target_temperature": qsTr("Target Temperature"),
            "windowcoverings_set": qsTr("Covering Position"),
            "windowcoverings_state": qsTr("Covering State"),
            "locked": qsTr("Lock"),
            "measure_temperature": qsTr("Temperature"),
            "measure_humidity": qsTr("Humidity"),
            "measure_power": qsTr("Power Consumption"),
            "meter_power": qsTr("Total Energy"),
            "measure_battery": qsTr("Battery"),
            "measure_pressure": qsTr("Atmospheric Pressure"),
            "measure_luminance": qsTr("Luminance"),
            "measure_co2": qsTr("CO2 Level"),
            "measure_co": qsTr("CO Level"),
            "measure_pm25": qsTr("PM2.5"),
            "measure_voltage": qsTr("Voltage"),
            "measure_current": qsTr("Current"),
            "meter_water": qsTr("Water Meter"),
            "meter_gas": qsTr("Gas Meter"),
            "measure_rain": qsTr("Rain Rate"),
            "measure_wind_strength": qsTr("Wind Speed"),
            "measure_wind_angle": qsTr("Wind Direction"),
            "measure_noise": qsTr("Noise Level"),
            "measure_gust_strength": qsTr("Gust Speed"),
            "alarm_motion": qsTr("Motion Alarm"),
            "alarm_contact": qsTr("Contact Sensor"),
            "alarm_smoke": qsTr("Smoke Alarm"),
            "alarm_water": qsTr("Water Leak Alarm"),
            "alarm_tamper": qsTr("Tamper Alarm"),
            "alarm_co": qsTr("Carbon Monoxide Alarm"),
            "alarm_co2": qsTr("CO2 Alarm"),
            "alarm_heat": qsTr("Heat Alarm"),
            "alarm_battery": qsTr("Battery Alarm"),
            "alarm_generic": qsTr("Generic Alarm"),
            "alarm_night": qsTr("Night Alarm")
        }
        if (titles[capId]) return titles[capId]
        var name = capId.replace("measure_", "").replace("meter_", "").replace("alarm_", "").replace(/_/g, " ")
        return name.charAt(0).toUpperCase() + name.slice(1)
    }

    function getCapUnits(capId) {
        var capObj = getCapObj(capId)
        if (capObj && capObj.units) {
            return capObj.units
        }
        var unitsMap = {
            "measure_temperature": "°C",
            "target_temperature": "°C",
            "measure_humidity": "%",
            "measure_power": "W",
            "meter_power": "kWh",
            "measure_battery": "%",
            "measure_pressure": "mbar",
            "measure_luminance": "lx",
            "measure_co2": "ppm",
            "measure_co": "ppm",
            "measure_pm25": "µg/m³",
            "measure_voltage": "V",
            "measure_current": "A",
            "meter_water": "m³",
            "meter_gas": "m³",
            "measure_rain": "mm/h",
            "measure_wind_strength": "m/s",
            "measure_wind_angle": "°",
            "measure_noise": "dB",
            "measure_gust_strength": "m/s"
        }
        return unitsMap[capId] || ""
    }

    function formatSensorValue(capId) {
        var val = getCapValue(capId)
        if (val === null || val === undefined) return "-"
        var units = getCapUnits(capId)
        if (typeof val === "number") {
            var numStr = Number.isInteger(val) ? val.toString() : val.toFixed(1)
            return units ? (numStr + " " + units) : numStr
        }
        if (typeof val === "boolean") {
            return val ? qsTr("Active") : qsTr("Inactive")
        }
        return units ? (val + " " + units) : val.toString()
    }

    function formatAlarmValue(capId) {
        var val = getCapValue(capId)
        if (capId === "alarm_motion") return val ? qsTr("Motion Detected!") : qsTr("Clear")
        if (capId === "alarm_contact") return val ? qsTr("Open") : qsTr("Closed")
        if (capId === "alarm_smoke") return val ? qsTr("SMOKE DETECTED!") : qsTr("Clear")
        if (capId === "alarm_water") return val ? qsTr("LEAK DETECTED!") : qsTr("Clear")
        if (capId === "alarm_tamper") return val ? qsTr("Tampered!") : qsTr("Clear")
        if (capId === "alarm_co") return val ? qsTr("CO DETECTED!") : qsTr("Clear")
        if (capId === "alarm_co2") return val ? qsTr("CO2 Level High!") : qsTr("Clear")
        if (capId === "alarm_heat") return val ? qsTr("HEAT DETECTED!") : qsTr("Clear")
        if (capId === "alarm_battery") return val ? qsTr("Low Battery!") : qsTr("OK")
        return val ? qsTr("Triggered!") : qsTr("Clear")
    }

    function formatOtherValue(capId) {
        var val = getCapValue(capId)
        if (val === null || val === undefined) return "-"
        var units = getCapUnits(capId)
        if (typeof val === "boolean") {
            return val ? qsTr("Yes / Active") : qsTr("No / Inactive")
        }
        if (typeof val === "number") {
            var numStr = Number.isInteger(val) ? val.toString() : val.toFixed(1)
            return units ? (numStr + " " + units) : numStr
        }
        return units ? (val + " " + units) : val.toString()
    }

    function hasControls() {
        var controlCaps = [
            "onoff", "dim", "volume_set", "volume_mute", "speaker_playing",
            "speaker_next", "speaker_prev", "light_temperature", "light_hue",
            "light_saturation", "target_temperature", "windowcoverings_set",
            "windowcoverings_state", "locked"
        ]
        for (var i = 0; i < controlCaps.length; i++) {
            if (hasCapability(controlCaps[i])) return true
        }
        return false
    }

    function hasSensors() {
        var caps = getDeviceCapabilities()
        for (var i = 0; i < caps.length; i++) {
            var c = caps[i]
            if (c.indexOf("measure_") === 0 || c.indexOf("meter_") === 0) {
                return true
            }
        }
        return false
    }

    function hasAlarms() {
        var caps = getDeviceCapabilities()
        for (var i = 0; i < caps.length; i++) {
            if (caps[i].indexOf("alarm_") === 0) return true
        }
        return false
    }

    function hasOtherCapabilities() {
        return getOtherCapabilitiesList().length > 0
    }

    function getSensorList() {
        var caps = getDeviceCapabilities()
        var list = []
        for (var i = 0; i < caps.length; i++) {
            var c = caps[i]
            if (c.indexOf("measure_") === 0 || c.indexOf("meter_") === 0) {
                list.push(c)
            }
        }
        return list
    }

    function getAlarmList() {
        var caps = getDeviceCapabilities()
        var list = []
        for (var i = 0; i < caps.length; i++) {
            if (caps[i].indexOf("alarm_") === 0) {
                list.push(caps[i])
            }
        }
        return list
    }

    function getOtherCapabilitiesList() {
        var caps = getDeviceCapabilities()
        var controlCaps = [
            "onoff", "dim", "volume_set", "volume_mute", "speaker_playing",
            "speaker_next", "speaker_prev", "light_temperature", "light_hue",
            "light_saturation", "light_mode", "target_temperature", "windowcoverings_set",
            "windowcoverings_state", "locked"
        ]
        var list = []
        for (var i = 0; i < caps.length; i++) {
            var c = caps[i]
            if (controlCaps.indexOf(c) === -1 &&
                c.indexOf("measure_") !== 0 &&
                c.indexOf("meter_") !== 0 &&
                c.indexOf("alarm_") !== 0) {
                list.push(c)
            }
        }
        return list
    }

    SilicaFlickable {
        anchors.fill: parent
        contentHeight: contentCol.height + Theme.paddingLarge

        PullDownMenu {
            MenuItem {
                text: qsTr("Refresh device")
                onClicked: appWindow.refreshDevices()
            }
            MenuItem {
                text: page.isFavorite ? qsTr("Remove from favorites") : qsTr("Add to favorites")
                onClicked: appWindow.toggleFavorite(deviceId)
            }
        }

        Column {
            id: contentCol
            width: page.width
            spacing: Theme.paddingMedium

            PageHeader {
                title: deviceName
            }

            DetailItem {
                label: qsTr("Zone / Room")
                value: zoneName ? zoneName : qsTr("Unassigned")
            }

            DetailItem {
                label: qsTr("Class")
                value: deviceClass
            }

            DetailItem {
                label: qsTr("Device ID")
                value: deviceId
            }

            DetailItem {
                label: qsTr("Favorite Device")
                value: page.isFavorite ? qsTr("Starred (Favorite)") : qsTr("No")
            }

            // -----------------------------------------------------------------
            // Controls Section (shown only when device has controllable features)
            // -----------------------------------------------------------------
            SectionHeader {
                text: qsTr("Controls")
                visible: hasControls()
            }

            // On / Off Switch (lights, sockets, generic switches)
            TextSwitch {
                visible: hasCapability("onoff")
                text: qsTr("Power")
                description: checked ? qsTr("Device is On") : qsTr("Device is Off")
                checked: getCapValue("onoff") === true
                onClicked: appWindow.setDeviceCapability(deviceId, "onoff", !checked)
            }

            // Dimming / Brightness (lights)
            Slider {
                visible: hasCapability("dim")
                width: parent.width
                label: qsTr("Brightness")
                minimumValue: 0.0
                maximumValue: 1.0
                stepSize: 0.05
                value: getCapValue("dim") !== null ? getCapValue("dim") : 0.0
                valueText: Math.round(value * 100) + "%"
                onReleased: appWindow.setDeviceCapability(deviceId, "dim", value)
            }

            // Speaker Volume (speakers, media players)
            Slider {
                visible: hasCapability("volume_set")
                width: parent.width
                label: qsTr("Volume")
                minimumValue: 0.0
                maximumValue: 1.0
                stepSize: 0.05
                value: getCapValue("volume_set") !== null ? getCapValue("volume_set") : 0.0
                valueText: Math.round(value * 100) + "%"
                onReleased: appWindow.setDeviceCapability(deviceId, "volume_set", value)
            }

            // Speaker Mute Switch
            TextSwitch {
                visible: hasCapability("volume_mute")
                text: qsTr("Mute")
                description: checked ? qsTr("Muted") : qsTr("Unmuted")
                checked: getCapValue("volume_mute") === true
                onClicked: appWindow.setDeviceCapability(deviceId, "volume_mute", !checked)
            }

            // Speaker Playback (Play / Pause)
            TextSwitch {
                visible: hasCapability("speaker_playing")
                text: qsTr("Playback")
                description: checked ? qsTr("Playing") : qsTr("Paused / Stopped")
                checked: getCapValue("speaker_playing") === true
                onClicked: appWindow.setDeviceCapability(deviceId, "speaker_playing", !checked)
            }

            // Speaker Track Controls (Next / Previous)
            Row {
                visible: hasCapability("speaker_prev") || hasCapability("speaker_next")
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Theme.paddingLarge

                Button {
                    visible: hasCapability("speaker_prev")
                    text: qsTr("Previous Track")
                    onClicked: appWindow.setDeviceCapability(deviceId, "speaker_prev", true)
                }

                Button {
                    visible: hasCapability("speaker_next")
                    text: qsTr("Next Track")
                    onClicked: appWindow.setDeviceCapability(deviceId, "speaker_next", true)
                }
            }

            // Light Color Temperature (Warm <-> Cold) - ONLY for color temp lights
            Slider {
                visible: hasCapability("light_temperature")
                width: parent.width
                label: qsTr("Color Temperature (Warm <-> Cold)")
                minimumValue: 0.0
                maximumValue: 1.0
                stepSize: 0.05
                value: getCapValue("light_temperature") !== null ? getCapValue("light_temperature") : 0.5
                valueText: Math.round(value * 100) + "%"
                onReleased: appWindow.setDeviceCapability(deviceId, "light_temperature", value)
            }

            // Light Color Hue - ONLY for RGB lights
            Slider {
                visible: hasCapability("light_hue")
                width: parent.width
                label: qsTr("Color Hue")
                minimumValue: 0.0
                maximumValue: 1.0
                stepSize: 0.02
                value: getCapValue("light_hue") !== null ? getCapValue("light_hue") : 0.0
                valueText: Math.round(value * 360) + "°"
                onReleased: appWindow.setDeviceCapability(deviceId, "light_hue", value)
            }

            // Light Saturation - ONLY for RGB lights
            Slider {
                visible: hasCapability("light_saturation")
                width: parent.width
                label: qsTr("Color Saturation")
                minimumValue: 0.0
                maximumValue: 1.0
                stepSize: 0.05
                value: getCapValue("light_saturation") !== null ? getCapValue("light_saturation") : 1.0
                valueText: Math.round(value * 100) + "%"
                onReleased: appWindow.setDeviceCapability(deviceId, "light_saturation", value)
            }

            // Target Temperature - ONLY for thermostats
            Slider {
                visible: hasCapability("target_temperature")
                width: parent.width
                label: qsTr("Target Temperature")
                minimumValue: getCapObj("target_temperature") && getCapObj("target_temperature").min !== undefined ?
                              getCapObj("target_temperature").min : 4.0
                maximumValue: getCapObj("target_temperature") && getCapObj("target_temperature").max !== undefined ?
                              getCapObj("target_temperature").max : 35.0
                stepSize: getCapObj("target_temperature") && getCapObj("target_temperature").step !== undefined ?
                          getCapObj("target_temperature").step : 0.5
                value: getCapValue("target_temperature") !== null ? getCapValue("target_temperature") : 20.0
                valueText: value.toFixed(1) + " °C"
                onReleased: appWindow.setDeviceCapability(deviceId, "target_temperature", value)
            }

            // Window Coverings / Blinds Position
            Slider {
                visible: hasCapability("windowcoverings_set")
                width: parent.width
                label: qsTr("Covering Position")
                minimumValue: 0.0
                maximumValue: 1.0
                stepSize: 0.05
                value: getCapValue("windowcoverings_set") !== null ? getCapValue("windowcoverings_set") : 0.0
                valueText: Math.round(value * 100) + "%"
                onReleased: appWindow.setDeviceCapability(deviceId, "windowcoverings_set", value)
            }

            // Window Coverings State Buttons (Up / Idle / Down)
            Row {
                visible: hasCapability("windowcoverings_state")
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Theme.paddingMedium

                Button {
                    text: qsTr("Up")
                    onClicked: appWindow.setDeviceCapability(deviceId, "windowcoverings_state", "up")
                }
                Button {
                    text: qsTr("Stop")
                    onClicked: appWindow.setDeviceCapability(deviceId, "windowcoverings_state", "idle")
                }
                Button {
                    text: qsTr("Down")
                    onClicked: appWindow.setDeviceCapability(deviceId, "windowcoverings_state", "down")
                }
            }

            // Lock Control
            TextSwitch {
                visible: hasCapability("locked")
                text: qsTr("Lock")
                description: checked ? qsTr("Locked") : qsTr("Unlocked")
                checked: getCapValue("locked") === true
                onClicked: appWindow.setDeviceCapability(deviceId, "locked", !checked)
            }

            // -----------------------------------------------------------------
            // Sensor Readings Section (dynamically rendered from real device sensors)
            // -----------------------------------------------------------------
            SectionHeader {
                text: qsTr("Sensor Readings")
                visible: hasSensors()
            }

            Repeater {
                model: getSensorList()
                delegate: DetailItem {
                    label: getCapTitle(modelData)
                    value: formatSensorValue(modelData)
                }
            }

            // -----------------------------------------------------------------
            // Alarms Section (dynamically rendered from real device alarms)
            // -----------------------------------------------------------------
            SectionHeader {
                text: qsTr("Alarms")
                visible: hasAlarms()
            }

            Repeater {
                model: getAlarmList()
                delegate: DetailItem {
                    label: getCapTitle(modelData)
                    value: formatAlarmValue(modelData)
                }
            }

            // -----------------------------------------------------------------
            // Other Capabilities Section
            // -----------------------------------------------------------------
            SectionHeader {
                text: qsTr("Other Information")
                visible: hasOtherCapabilities()
            }

            Repeater {
                model: getOtherCapabilitiesList()
                delegate: DetailItem {
                    label: getCapTitle(modelData)
                    value: formatOtherValue(modelData)
                }
            }
        }
    }
}
