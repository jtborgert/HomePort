import QtQuick 2.0
import Sailfish.Silica 1.0

Page {
    id: page
    allowedOrientations: defaultAllowedOrientations

    SilicaListView {
        id: listView
        anchors.fill: parent
        model: zonesModel

        header: PageHeader {
            title: qsTr("Rooms & Zones")
        }

        PullDownMenu {
            MenuItem {
                text: qsTr("Refresh")
                onClicked: {
                    appWindow.refreshDevices()
                }
            }
        }

        delegate: ListItem {
            id: zoneItem
            width: listView.width
            contentHeight: Theme.itemSizeMedium

            Row {
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.centerIn: parent
                spacing: Theme.paddingMedium

                Image {
                    source: "image://theme/icon-m-home"
                    anchors.verticalCenter: parent.verticalCenter
                }

                Column {
                    width: parent.width - Theme.iconSizeMedium - 60
                    anchors.verticalCenter: parent.verticalCenter

                    Label {
                        text: name
                        font.pixelSize: Theme.fontSizeMedium
                        color: Theme.primaryColor
                        truncationMode: TruncationMode.Fade
                        width: parent.width
                    }

                    Label {
                        text: qsTr("%1 devices").arg(countDevicesInZone(id))
                        font.pixelSize: Theme.fontSizeExtraSmall
                        color: Theme.secondaryColor
                    }
                }

                IconButton {
                    icon.source: "image://theme/icon-m-right"
                    anchors.verticalCenter: parent.verticalCenter
                    onClicked: zoneItem.clicked()
                }
            }

            onClicked: pageStack.push(Qt.resolvedUrl("DevicesPage.qml"), {
                "searchFilter": name.toLowerCase()
            })
        }

        ViewPlaceholder {
            enabled: listView.count === 0
            text: qsTr("No zones found")
            hintText: qsTr("Pull down to refresh from Homey Pro")
        }
    }

    function countDevicesInZone(zoneId) {
        var count = 0
        for (var i = 0; i < devicesModel.count; i++) {
            if (devicesModel.get(i).zoneId === zoneId) {
                count++
            }
        }
        return count
    }
}
