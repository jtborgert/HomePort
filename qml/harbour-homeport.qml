import QtQuick 2.0
import Sailfish.Silica 1.0
import io.thp.pyotherside 1.5
import "pages"

ApplicationWindow {
    id: appWindow

    initialPage: Qt.resolvedUrl("pages/MainPage.qml")
    cover: Qt.resolvedUrl("cover/CoverPage.qml")
    allowedOrientations: defaultAllowedOrientations

    // Global application properties
    property bool isConnected: false
    property string activeHomeyName: "Homey Pro"
    property string activeHomeyUrl: ""
    property string connectionStatusText: "Connecting..."
    property int lightsOnCount: 0
    property int totalDevicesCount: 0

    // Saved credentials & settings
    property string savedEmail: ""
    property string savedUsername: ""
    property string savedClientId: ""
    property string savedClientSecret: ""
    property string savedSessionToken: ""
    property string savedDirectBaseUrl: ""

    // Raw device data map (preserves nested JavaScript arrays and objects)
    property var devicesMap: ({})

    // Global signals for device and favorite updates
    signal devicesUpdated()
    signal deviceCapabilityChanged(string deviceId, string capabilityId, var value)
    signal favoriteChanged(string deviceId, bool isFavorite)

    // Data models exposed as properties
    property alias devicesModel: devicesModel
    property alias zonesModel: zonesModel
    property alias flowsModel: flowsModel
    property alias homeysModel: homeysModel
    property alias py: py

    ListModel { id: devicesModel }
    ListModel { id: zonesModel }
    ListModel { id: flowsModel }
    ListModel { id: homeysModel }

    // PyOtherSide Bridge
    Python {
        id: py

        onError: console.log("PyOtherSide error: " + traceback)

        Component.onCompleted: {
            // Add python module search paths
            addImportPath(Qt.resolvedUrl("../src"))
            addImportPath("/usr/share/harbour-homeport/src")
            addImportPath("/usr/share/harbour-homeport/python")

            setHandler("oauth_success", function(homeys) {
                homeysModel.clear()
                for (var i = 0; i < homeys.length; i++) {
                    homeysModel.append(homeys[i])
                }
                connectionStatusText = "Athom account connected"
                refreshDevices()
            })

            setHandler("oauth_error", function(err) {
                connectionStatusText = "OAuth Error: " + err
            })

            setHandler("login_success", function(data) {
                appWindow.isConnected = true
                appWindow.activeHomeyName = data.name || "Homey Pro"
                appWindow.activeHomeyUrl = data.baseUrl || ""
                if (data.baseUrl) appWindow.savedDirectBaseUrl = data.baseUrl
                appWindow.connectionStatusText = "Connected to " + appWindow.activeHomeyName
            })

            setHandler("login_error", function(err) {
                appWindow.isConnected = false
                appWindow.connectionStatusText = "Connection error: " + err
            })

            setHandler("homey_selected", function(data) {
                appWindow.isConnected = true
                appWindow.activeHomeyName = data.name || "Homey Pro"
                appWindow.activeHomeyUrl = data.url || ""
                if (data.url) appWindow.savedDirectBaseUrl = data.url
                appWindow.connectionStatusText = "Connected to " + appWindow.activeHomeyName
            })

            setHandler("homeys_refreshed", function(homeys) {
                homeysModel.clear()
                for (var i = 0; i < homeys.length; i++) {
                    homeysModel.append(homeys[i])
                }
            })

            setHandler("devices_loaded", function(devices) {
                devicesModel.clear()
                var map = {}
                var onCount = 0
                for (var i = 0; i < devices.length; i++) {
                    var dev = devices[i]
                    map[dev.id] = dev

                    // Append flat primitive roles so Qt ListModel doesn't drop/mangle nested structures
                    devicesModel.append({
                        "id": dev.id || "",
                        "name": dev.name || "",
                        "class": dev.class || "other",
                        "zoneId": dev.zoneId || "",
                        "zoneName": dev.zoneName || "",
                        "iconUrl": dev.iconUrl || "",
                        "onoff": dev.onoff === true,
                        "dim": (dev.dim !== null && dev.dim !== undefined) ? Number(dev.dim) : 0.0,
                        "hasOnOff": dev.capabilities ? (dev.capabilities.indexOf("onoff") !== -1) : false,
                        "hasDim": dev.capabilities ? (dev.capabilities.indexOf("dim") !== -1) : false,
                        "isFavorite": dev.isFavorite === true
                    })
                    if (dev.class === "light" && dev.onoff === true) {
                        onCount++
                    }
                }
                appWindow.devicesMap = map
                appWindow.lightsOnCount = onCount
                appWindow.totalDevicesCount = devices.length
                appWindow.isConnected = true
                appWindow.connectionStatusText = "Connected (" + devices.length + " devices)"
                appWindow.devicesUpdated()
            })

            setHandler("zones_loaded", function(zones) {
                zonesModel.clear()
                for (var i = 0; i < zones.length; i++) {
                    zonesModel.append(zones[i])
                }
            })

            setHandler("flows_loaded", function(flows) {
                flowsModel.clear()
                for (var i = 0; i < flows.length; i++) {
                    flowsModel.append(flows[i])
                }
            })

            setHandler("device_capability_updated", function(data) {
                var devId = data.deviceId
                var capId = data.capabilityId
                var val = data.value

                if (appWindow.devicesMap && appWindow.devicesMap[devId]) {
                    var rawDev = appWindow.devicesMap[devId]
                    if (!rawDev.state) rawDev.state = {}
                    rawDev.state[capId] = val
                    if (rawDev.capabilitiesObj && rawDev.capabilitiesObj[capId]) {
                        rawDev.capabilitiesObj[capId].value = val
                    }
                    if (capId === "onoff") rawDev.onoff = val
                    if (capId === "dim") rawDev.dim = val
                }

                for (var i = 0; i < devicesModel.count; i++) {
                    var item = devicesModel.get(i)
                    if (item.id === devId) {
                        if (capId === "onoff") {
                            devicesModel.setProperty(i, "onoff", val)
                        } else if (capId === "dim") {
                            devicesModel.setProperty(i, "dim", val)
                        }
                        break
                    }
                }
                updateLightsCount()
                appWindow.deviceCapabilityChanged(devId, capId, val)
            })

            setHandler("favorite_toggled", function(data) {
                if (appWindow.devicesMap && appWindow.devicesMap[data.deviceId]) {
                    appWindow.devicesMap[data.deviceId].isFavorite = data.isFavorite
                }
                for (var i = 0; i < devicesModel.count; i++) {
                    if (devicesModel.get(i).id === data.deviceId) {
                        devicesModel.setProperty(i, "isFavorite", data.isFavorite)
                        break
                    }
                }
                appWindow.favoriteChanged(data.deviceId, data.isFavorite)
            })

            setHandler("flow_triggered", function(data) {
                // Flash notification
            })

            setHandler("logged_out", function() {
                appWindow.isConnected = false
                appWindow.activeHomeyName = "Homey Pro"
                appWindow.connectionStatusText = "Not connected"
                appWindow.devicesMap = {}
                devicesModel.clear()
                zonesModel.clear()
                flowsModel.clear()
                homeysModel.clear()
            })

            importModule("homeport.bridge", function() {
                py.call("homeport.bridge.init", [], function(state) {
                    if (state) {
                        appWindow.savedEmail = state.email || ""
                        appWindow.savedUsername = state.username || ""
                        appWindow.savedClientId = state.clientId || ""
                        appWindow.savedClientSecret = state.clientSecret || ""
                        appWindow.savedSessionToken = state.sessionToken || ""
                        appWindow.savedDirectBaseUrl = state.directBaseUrl || ""
                    }
                    if (state && state.isConfigured) {
                        appWindow.activeHomeyName = state.activeHomeyName || "Homey Pro"
                        appWindow.activeHomeyUrl = state.directBaseUrl || ""
                        appWindow.isConnected = true
                        appWindow.connectionStatusText = "Connecting..."
                        refreshDevices()
                        refreshFlows()
                    } else {
                        appWindow.isConnected = false
                        if (state && state.directBaseUrl) {
                            appWindow.activeHomeyUrl = state.directBaseUrl
                        }
                        appWindow.connectionStatusText = "Not configured. Go to Settings."
                    }
                })
            })
        }
    }

    function updateLightsCount() {
        var onCount = 0
        for (var i = 0; i < devicesModel.count; i++) {
            var dev = devicesModel.get(i)
            if (dev.class === "light" && dev.onoff === true) {
                onCount++
            }
        }
        appWindow.lightsOnCount = onCount
    }

    function refreshDevices() {
        py.call("homeport.bridge.fetch_devices", [], function() {})
    }

    function refreshFlows() {
        py.call("homeport.bridge.fetch_flows", [], function() {})
    }

    function toggleDevice(deviceId) {
        py.call("homeport.bridge.toggle_device", [deviceId], function() {})
    }

    function setDeviceCapability(deviceId, capabilityId, value) {
        py.call("homeport.bridge.set_device_capability", [deviceId, capabilityId, value], function() {})
    }

    function getDevice(deviceId) {
        if (appWindow.devicesMap && appWindow.devicesMap[deviceId]) {
            return appWindow.devicesMap[deviceId]
        }
        return null
    }

    function isDeviceFavorite(deviceId) {
        var dev = getDevice(deviceId)
        if (dev && dev.isFavorite !== undefined) {
            return dev.isFavorite === true
        }
        for (var i = 0; i < devicesModel.count; i++) {
            if (devicesModel.get(i).id === deviceId) {
                return devicesModel.get(i).isFavorite === true
            }
        }
        return false
    }

    function toggleFavorite(deviceId) {
        py.call("homeport.bridge.toggle_favorite", [deviceId], function() {})
    }

    function setFavorite(deviceId, isFav) {
        py.call("homeport.bridge.set_favorite", [deviceId, isFav], function() {})
    }

    function triggerFlow(flowId) {
        py.call("homeport.bridge.trigger_flow", [flowId], function() {})
    }

    function loginDirect(url, token, name, email, username) {
        appWindow.savedDirectBaseUrl = url || ""
        appWindow.activeHomeyUrl = url || ""
        appWindow.savedSessionToken = token || ""
        if (email !== undefined) appWindow.savedEmail = email
        if (username !== undefined) appWindow.savedUsername = username
        py.call("homeport.bridge.login_direct", [url, token, name || "Homey Pro Local", email || "", username || ""], function() {})
    }

    function loginOAuth(clientId, clientSecret, authCode, urlPref, email, username) {
        appWindow.savedClientId = clientId || ""
        appWindow.savedClientSecret = clientSecret || ""
        if (email !== undefined) appWindow.savedEmail = email
        if (username !== undefined) appWindow.savedUsername = username
        py.call("homeport.bridge.login_oauth", [clientId, clientSecret, authCode, urlPref || "auto", email || "", username || ""], function() {})
    }

    function saveSettings(settingsData, callback) {
        if (settingsData) {
            if (settingsData.email !== undefined) appWindow.savedEmail = settingsData.email
            if (settingsData.username !== undefined) appWindow.savedUsername = settingsData.username
            if (settingsData.client_id !== undefined) appWindow.savedClientId = settingsData.client_id
            if (settingsData.client_secret !== undefined) appWindow.savedClientSecret = settingsData.client_secret
            if (settingsData.session_token !== undefined) appWindow.savedSessionToken = settingsData.session_token
            if (settingsData.direct_base_url !== undefined) {
                appWindow.savedDirectBaseUrl = settingsData.direct_base_url
                appWindow.activeHomeyUrl = settingsData.direct_base_url
            }
        }
        py.call("homeport.bridge.save_settings", [settingsData || {}], function(result) {
            if (callback) callback(result)
        })
    }

    function selectHomey(homeyId, urlPref) {
        py.call("homeport.bridge.select_homey", [homeyId, urlPref || "auto"], function() {})
    }

    function logout() {
        appWindow.savedSessionToken = ""
        py.call("homeport.bridge.logout", [], function() {})
    }
}
