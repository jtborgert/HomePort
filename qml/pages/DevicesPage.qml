import QtQuick 2.0
import Sailfish.Silica 1.0

Page {
    id: page
    allowedOrientations: defaultAllowedOrientations

    property string searchFilter: ""
    property string classFilter: "all"

    SilicaListView {
        id: listView
        anchors.fill: parent
        model: devicesModel

        header: Column {
            width: page.width
            spacing: Theme.paddingMedium

            PageHeader {
                title: qsTr("Devices")
            }

            SearchField {
                id: searchField
                width: parent.width
                placeholderText: qsTr("Search devices...")
                onTextChanged: page.searchFilter = text.toLowerCase()
            }

            ComboBox {
                label: qsTr("Filter category")
                currentIndex: 0
                menu: ContextMenu {
                    MenuItem { text: qsTr("All Categories"); onClicked: page.classFilter = "all" }
                    MenuItem { text: qsTr("Lights"); onClicked: page.classFilter = "light" }
                    MenuItem { text: qsTr("Sockets & Switches"); onClicked: page.classFilter = "socket" }
                    MenuItem { text: qsTr("Sensors"); onClicked: page.classFilter = "sensor" }
                    MenuItem { text: qsTr("Thermostats"); onClicked: page.classFilter = "thermostat" }
                    MenuItem { text: qsTr("Other"); onClicked: page.classFilter = "other" }
                }
            }
        }

        PullDownMenu {
            MenuItem {
                text: qsTr("Turn all lights OFF")
                onClicked: {
                    for (var i = 0; i < devicesModel.count; i++) {
                        var dev = devicesModel.get(i)
                        if (dev.class === "light" && dev.onoff === true) {
                            appWindow.setDeviceCapability(dev.id, "onoff", false)
                        }
                    }
                }
            }
            MenuItem {
                text: qsTr("Turn all lights ON")
                onClicked: {
                    for (var i = 0; i < devicesModel.count; i++) {
                        var dev = devicesModel.get(i)
                        if (dev.class === "light" && dev.onoff === false) {
                            appWindow.setDeviceCapability(dev.id, "onoff", true)
                        }
                    }
                }
            }
            MenuItem {
                text: qsTr("Refresh devices")
                onClicked: appWindow.refreshDevices()
            }
        }

        delegate: ListItem {
            id: listItem
            width: listView.width
            contentHeight: isVisible ? Theme.itemSizeMedium : 0
            visible: isVisible

            property bool hasOnOff: model.hasOnOff !== undefined ? model.hasOnOff : (typeof capabilities !== "undefined" && capabilities && capabilities.indexOf ? capabilities.indexOf("onoff") !== -1 : false)
            property bool hasDim: model.hasDim !== undefined ? model.hasDim : (typeof capabilities !== "undefined" && capabilities && capabilities.indexOf ? capabilities.indexOf("dim") !== -1 : false)
            property bool matchesSearch: searchFilter === "" ||
                                         name.toLowerCase().indexOf(searchFilter) !== -1 ||
                                         (zoneName && zoneName.toLowerCase().indexOf(searchFilter) !== -1)
            property bool matchesClass: classFilter === "all" || model.class === classFilter
            property bool isVisible: matchesSearch && matchesClass

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

            menu: ContextMenu {
                MenuItem {
                    text: isFavorite ? qsTr("Remove from favorites") : qsTr("Add to favorites")
                    onClicked: appWindow.toggleFavorite(id)
                }
                MenuItem {
                    text: qsTr("View device details")
                    onClicked: listItem.clicked()
                }
            }

            Row {
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.centerIn: parent
                spacing: Theme.paddingSmall

                IconButton {
                    id: favoriteBtn
                    icon.source: isFavorite ? "image://theme/icon-m-favorite-selected" : "image://theme/icon-m-favorite"
                    anchors.verticalCenter: parent.verticalCenter
                    onClicked: appWindow.toggleFavorite(id)
                }

                Column {
                    width: parent.width - favoriteBtn.width - (hasOnOff ? (switchControl.width + Theme.paddingSmall) : 0) - Theme.paddingSmall
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
                    id: switchControl
                    visible: hasOnOff
                    checked: onoff === true
                    anchors.verticalCenter: parent.verticalCenter
                    onClicked: appWindow.toggleDevice(id)
                }
            }
        }

        ViewPlaceholder {
            enabled: listView.count === 0
            text: qsTr("No devices found")
            hintText: qsTr("Pull down to refresh or check connection in Settings")
        }
    }
}
