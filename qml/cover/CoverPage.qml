import QtQuick 2.0
import Sailfish.Silica 1.0

CoverBackground {
    id: cover

    Column {
        width: parent.width - (2 * Theme.paddingMedium)
        anchors.centerIn: parent
        spacing: Theme.paddingMedium

        Image {
            source: "image://theme/icon-m-home"
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Label {
            text: "HomePort"
            font.pixelSize: Theme.fontSizeMedium
            font.bold: true
            color: Theme.primaryColor
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Label {
            text: appWindow.activeHomeyName
            font.pixelSize: Theme.fontSizeSmall
            color: Theme.highlightColor
            truncationMode: TruncationMode.Fade
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
        }

        Separator {
            width: parent.width
            color: Theme.primaryColor
            horizontalAlignment: Qt.AlignHCenter
        }

        Label {
            text: qsTr("💡 Lights on: %1").arg(appWindow.lightsOnCount)
            font.pixelSize: Theme.fontSizeExtraSmall
            color: Theme.secondaryColor
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Label {
            text: qsTr("📱 Devices: %1").arg(appWindow.totalDevicesCount)
            font.pixelSize: Theme.fontSizeExtraSmall
            color: Theme.secondaryColor
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }

    CoverActionList {
        id: coverAction

        CoverAction {
            iconSource: "image://theme/icon-m-refresh"
            onTriggered: {
                appWindow.refreshDevices()
                appWindow.refreshFlows()
            }
        }
    }
}
