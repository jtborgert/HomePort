import QtQuick 2.0
import Sailfish.Silica 1.0

Page {
    id: page
    allowedOrientations: defaultAllowedOrientations

    SilicaFlickable {
        anchors.fill: parent
        contentHeight: column.height + Theme.paddingLarge

        PullDownMenu {
            MenuItem {
                text: qsTr("Settings & Accounts")
                onClicked: pageStack.push(Qt.resolvedUrl("SettingsPage.qml"))
            }
            MenuItem {
                text: qsTr("Flows & Automations")
                onClicked: pageStack.push(Qt.resolvedUrl("FlowsPage.qml"))
            }
            MenuItem {
                text: qsTr("Rooms & Zones")
                onClicked: pageStack.push(Qt.resolvedUrl("ZonesPage.qml"))
            }
            MenuItem {
                text: qsTr("All Devices")
                onClicked: pageStack.push(Qt.resolvedUrl("DevicesPage.qml"))
            }
            MenuItem {
                text: qsTr("Refresh")
                onClicked: {
                    appWindow.refreshDevices()
                    appWindow.refreshFlows()
                }
            }
        }

        Column {
            id: column
            width: page.width
            spacing: Theme.paddingMedium

            PageHeader {
                title: "HomePort"
            }

            // Connection Status Banner
            BackgroundItem {
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.horizontalCenter: parent.horizontalCenter
                height: Theme.itemSizeSmall
                onClicked: pageStack.push(Qt.resolvedUrl("SettingsPage.qml"))

                Row {
                    anchors.centerIn: parent
                    spacing: Theme.paddingSmall

                    Rectangle {
                        width: Theme.iconSizeExtraSmall / 2
                        height: width
                        radius: width / 2
                        color: appWindow.isConnected ? Theme.highlightColor : Theme.secondaryHighlightColor
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Label {
                        text: appWindow.connectionStatusText
                        font.pixelSize: Theme.fontSizeSmall
                        color: Theme.highlightColor
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }

            // Summary Stats Card
            Row {
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Theme.paddingLarge

                DetailItem {
                    width: parent.width / 2 - Theme.paddingMedium
                    label: qsTr("Lights On")
                    value: appWindow.lightsOnCount.toString()
                }

                DetailItem {
                    width: parent.width / 2 - Theme.paddingMedium
                    label: qsTr("Total Devices")
                    value: appWindow.totalDevicesCount.toString()
                }
            }

            SectionHeader {
                text: qsTr("Quick Navigation")
            }

            Row {
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Theme.paddingMedium

                Button {
                    width: (parent.width - Theme.paddingMedium) / 2
                    text: qsTr("Devices")
                    onClicked: pageStack.push(Qt.resolvedUrl("DevicesPage.qml"))
                }

                Button {
                    width: (parent.width - Theme.paddingMedium) / 2
                    text: qsTr("Zones")
                    onClicked: pageStack.push(Qt.resolvedUrl("ZonesPage.qml"))
                }
            }

            Row {
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Theme.paddingMedium

                Button {
                    width: (parent.width - Theme.paddingMedium) / 2
                    text: qsTr("Flows")
                    onClicked: pageStack.push(Qt.resolvedUrl("FlowsPage.qml"))
                }

                Button {
                    width: (parent.width - Theme.paddingMedium) / 2
                    text: qsTr("Settings")
                    onClicked: pageStack.push(Qt.resolvedUrl("SettingsPage.qml"))
                }
            }

            SectionHeader {
                text: qsTr("Favorite Devices")
            }

            // Favorites Repeater
            Repeater {
                model: devicesModel
                delegate: Item {
                    width: column.width
                    height: isFavorite ? Theme.itemSizeMedium : 0
                    visible: isFavorite

                    property bool hasOnOff: model.hasOnOff !== undefined ? model.hasOnOff : (typeof capabilities !== "undefined" && capabilities && capabilities.indexOf ? capabilities.indexOf("onoff") !== -1 : false)
                    property bool hasDim: model.hasDim !== undefined ? model.hasDim : (typeof capabilities !== "undefined" && capabilities && capabilities.indexOf ? capabilities.indexOf("dim") !== -1 : false)

                    BackgroundItem {
                        anchors.fill: parent
                        onClicked: {
                            var devObj = (typeof appWindow !== "undefined" && appWindow.getDevice) ? appWindow.getDevice(id) : null
                            pageStack.push(Qt.resolvedUrl("DeviceDetailPage.qml"), {
                                "deviceId": id,
                                "deviceName": devObj ? devObj.name : name,
                                "deviceClass": devObj ? devObj.class : model.class,
                                "zoneName": devObj ? (devObj.zoneName || "") : (zoneName || ""),
                                "capabilities": devObj ? (devObj.capabilities || []) : [],
                                "capabilitiesObj": devObj ? (devObj.capabilitiesObj || {}) : {},
                                "state": devObj ? (devObj.state || {}) : {}
                            })
                        }

                        Row {
                            width: parent.width - (2 * Theme.horizontalPageMargin)
                            anchors.centerIn: parent
                            spacing: Theme.paddingSmall

                            IconButton {
                                id: favIcon
                                icon.source: "image://theme/icon-m-favorite-selected"
                                anchors.verticalCenter: parent.verticalCenter
                                onClicked: appWindow.toggleFavorite(id)
                            }

                            Column {
                                width: parent.width - favIcon.width - (hasOnOff ? (favSwitch.width + Theme.paddingSmall) : 0) - Theme.paddingSmall
                                anchors.verticalCenter: parent.verticalCenter

                                Label {
                                    text: name
                                    font.pixelSize: Theme.fontSizeMedium
                                    color: (hasOnOff && onoff) ? Theme.highlightColor : Theme.primaryColor
                                    truncationMode: TruncationMode.Fade
                                    width: parent.width
                                }

                                Label {
                                    text: (zoneName ? zoneName + " • " : "") + model.class + (hasDim ? " • " + Math.round((dim || 0) * 100) + "%" : "")
                                    font.pixelSize: Theme.fontSizeExtraSmall
                                    color: Theme.secondaryColor
                                    truncationMode: TruncationMode.Fade
                                    width: parent.width
                                }
                            }

                            Switch {
                                id: favSwitch
                                visible: hasOnOff
                                checked: onoff === true
                                anchors.verticalCenter: parent.verticalCenter
                                onClicked: appWindow.toggleDevice(id)
                            }
                        }
                    }
                }
            }

            Label {
                text: qsTr("No favorite devices yet. Star a device to see it here.")
                color: Theme.secondaryColor
                font.pixelSize: Theme.fontSizeSmall
                anchors.horizontalCenter: parent.horizontalCenter
                visible: countFavorites() === 0
            }
        }
    }

    function countFavorites() {
        var count = 0
        for (var i = 0; i < devicesModel.count; i++) {
            if (devicesModel.get(i).isFavorite) count++
        }
        return count
    }
}
