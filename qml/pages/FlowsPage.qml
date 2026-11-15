import QtQuick 2.0
import Sailfish.Silica 1.0

Page {
    id: page
    allowedOrientations: defaultAllowedOrientations

    SilicaListView {
        id: listView
        anchors.fill: parent
        model: flowsModel

        header: PageHeader {
            title: qsTr("Flows & Automations")
        }

        PullDownMenu {
            MenuItem {
                text: qsTr("Refresh Flows")
                onClicked: appWindow.refreshFlows()
            }
        }

        delegate: ListItem {
            id: flowItem
            width: listView.width
            contentHeight: Theme.itemSizeMedium

            Row {
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.centerIn: parent
                spacing: Theme.paddingMedium

                Image {
                    source: "image://theme/icon-m-media-songs"
                    anchors.verticalCenter: parent.verticalCenter
                }

                Column {
                    width: parent.width - Theme.iconSizeMedium - 120
                    anchors.verticalCenter: parent.verticalCenter

                    Label {
                        text: name
                        font.pixelSize: Theme.fontSizeMedium
                        color: enabled ? Theme.primaryColor : Theme.secondaryColor
                        truncationMode: TruncationMode.Fade
                        width: parent.width
                    }

                    Label {
                        text: enabled ? (triggerable ? qsTr("Ready to run") : qsTr("Active")) : qsTr("Disabled")
                        font.pixelSize: Theme.fontSizeExtraSmall
                        color: Theme.secondaryColor
                    }
                }

                Button {
                    text: qsTr("Run")
                    width: 100
                    anchors.verticalCenter: parent.verticalCenter
                    enabled: triggerable && enabled
                    onClicked: {
                        appWindow.triggerFlow(id)
                    }
                }
            }
        }

        ViewPlaceholder {
            enabled: listView.count === 0
            text: qsTr("No flows found")
            hintText: qsTr("Pull down to refresh from Homey Pro")
        }
    }
}
