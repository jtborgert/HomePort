import QtQuick 2.0
import Sailfish.Silica 1.0

Page {
    id: page
    allowedOrientations: defaultAllowedOrientations

    Component.onCompleted: {
        loadSettingsFromStorage()
        if (appWindow.py) {
            appWindow.py.call("homeport.bridge.get_settings", [], function(settings) {
                if (settings) {
                    if (settings.email && (!emailField.text || emailField.text.length === 0)) {
                        emailField.text = settings.email
                        appWindow.savedEmail = settings.email
                    }
                    if (settings.username && (!usernameField.text || usernameField.text.length === 0)) {
                        usernameField.text = settings.username
                        appWindow.savedUsername = settings.username
                    }
                    if (settings.direct_base_url && (!localUrlField.text || localUrlField.text.length === 0)) {
                        localUrlField.text = settings.direct_base_url
                        appWindow.savedDirectBaseUrl = settings.direct_base_url
                        if (!appWindow.activeHomeyUrl) appWindow.activeHomeyUrl = settings.direct_base_url
                    }
                    if (settings.session_token && (!sessionTokenField.text || sessionTokenField.text.length === 0)) {
                        sessionTokenField.text = settings.session_token
                        appWindow.savedSessionToken = settings.session_token
                    }
                    if (settings.client_id && (!clientIdField.text || clientIdField.text.length === 0)) {
                        clientIdField.text = settings.client_id
                        appWindow.savedClientId = settings.client_id
                    }
                    if (settings.client_secret && (!clientSecretField.text || clientSecretField.text.length === 0)) {
                        clientSecretField.text = settings.client_secret
                        appWindow.savedClientSecret = settings.client_secret
                    }
                }
            })
        }
    }

    function loadSettingsFromStorage() {
        if (appWindow.savedEmail && !emailField.text) emailField.text = appWindow.savedEmail
        if (appWindow.savedUsername && !usernameField.text) usernameField.text = appWindow.savedUsername
        var directUrl = appWindow.savedDirectBaseUrl || appWindow.activeHomeyUrl
        if (directUrl && !localUrlField.text) localUrlField.text = directUrl
        if (appWindow.savedSessionToken && !sessionTokenField.text) sessionTokenField.text = appWindow.savedSessionToken
        if (appWindow.savedClientId && !clientIdField.text) clientIdField.text = appWindow.savedClientId
        if (appWindow.savedClientSecret && !clientSecretField.text) clientSecretField.text = appWindow.savedClientSecret
    }

    SilicaFlickable {
        anchors.fill: parent
        contentHeight: contentCol.height + Theme.paddingLarge

        Column {
            id: contentCol
            width: page.width
            spacing: Theme.paddingMedium

            PageHeader {
                title: qsTr("Settings & Connection")
            }

            SectionHeader {
                text: qsTr("User / Account Info")
            }

            Label {
                text: qsTr("Saved user details and credentials are automatically remembered and stored securely.")
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                wrapMode: Text.Wrap
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.horizontalCenter: parent.horizontalCenter
            }

            TextField {
                id: emailField
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.horizontalCenter: parent.horizontalCenter
                label: qsTr("User / Account Email")
                placeholderText: qsTr("user@example.com")
                text: appWindow.savedEmail
                inputMethodHints: Qt.ImhEmailCharactersOnly
                onTextChanged: {
                    if (text !== appWindow.savedEmail) {
                        appWindow.savedEmail = text
                    }
                }
            }

            TextField {
                id: usernameField
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.horizontalCenter: parent.horizontalCenter
                label: qsTr("Username / Profile Name")
                placeholderText: qsTr("Username")
                text: appWindow.savedUsername
                onTextChanged: {
                    if (text !== appWindow.savedUsername) {
                        appWindow.savedUsername = text
                    }
                }
            }

            SectionHeader {
                text: qsTr("Direct Local Connection")
            }

            Label {
                text: qsTr("Connect directly to your Homey Pro on your local Wi-Fi network using its IP address or local hostname and session token / API key.")
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                wrapMode: Text.Wrap
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.horizontalCenter: parent.horizontalCenter
            }

            TextField {
                id: localUrlField
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.horizontalCenter: parent.horizontalCenter
                label: qsTr("Homey URL / IP")
                placeholderText: "http://192.168.1.100"
                text: appWindow.savedDirectBaseUrl || appWindow.activeHomeyUrl
                inputMethodHints: Qt.ImhUrlCharactersOnly
                onTextChanged: {
                    if (text !== appWindow.savedDirectBaseUrl) {
                        appWindow.savedDirectBaseUrl = text
                        appWindow.activeHomeyUrl = text
                    }
                }
            }

            TextField {
                id: sessionTokenField
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.horizontalCenter: parent.horizontalCenter
                label: qsTr("Session Token / API Key")
                placeholderText: qsTr("Paste token here")
                text: appWindow.savedSessionToken
                echoMode: TextInput.PasswordEchoOnEdit
                onTextChanged: {
                    if (text !== appWindow.savedSessionToken) {
                        appWindow.savedSessionToken = text
                    }
                }
            }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Theme.paddingMedium

                Button {
                    text: qsTr("Connect Direct")
                    onClicked: {
                        if (localUrlField.text.length > 0 && sessionTokenField.text.length > 0) {
                            appWindow.loginDirect(
                                localUrlField.text,
                                sessionTokenField.text,
                                "Homey Pro Local",
                                emailField.text,
                                usernameField.text
                            )
                        }
                    }
                }

                Button {
                    text: qsTr("Save Settings")
                    onClicked: {
                        appWindow.saveSettings({
                            "email": emailField.text,
                            "username": usernameField.text,
                            "direct_base_url": localUrlField.text,
                            "session_token": sessionTokenField.text,
                            "client_id": clientIdField.text,
                            "client_secret": clientSecretField.text
                        })
                    }
                }
            }

            SectionHeader {
                text: qsTr("Athom Cloud OAuth2")
            }

            Label {
                text: qsTr("Use your Athom Developer Client ID & Secret to authenticate and discover all Homey Pro devices in your account.")
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                wrapMode: Text.Wrap
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.horizontalCenter: parent.horizontalCenter
            }

            TextField {
                id: clientIdField
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.horizontalCenter: parent.horizontalCenter
                label: qsTr("Client ID")
                placeholderText: qsTr("Athom Developer Client ID")
                text: appWindow.savedClientId
                onTextChanged: {
                    if (text !== appWindow.savedClientId) {
                        appWindow.savedClientId = text
                    }
                }
            }

            TextField {
                id: clientSecretField
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.horizontalCenter: parent.horizontalCenter
                label: qsTr("Client Secret")
                placeholderText: qsTr("Athom Developer Client Secret")
                text: appWindow.savedClientSecret
                echoMode: TextInput.PasswordEchoOnEdit
                onTextChanged: {
                    if (text !== appWindow.savedClientSecret) {
                        appWindow.savedClientSecret = text
                    }
                }
            }

            TextField {
                id: authCodeField
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.horizontalCenter: parent.horizontalCenter
                label: qsTr("Authorization Code")
                placeholderText: qsTr("Paste code from browser redirect")
            }

            Button {
                text: qsTr("Exchange Code & Connect")
                anchors.horizontalCenter: parent.horizontalCenter
                onClicked: {
                    if (clientIdField.text.length > 0 && clientSecretField.text.length > 0 && authCodeField.text.length > 0) {
                        appWindow.loginOAuth(
                            clientIdField.text,
                            clientSecretField.text,
                            authCodeField.text,
                            "auto",
                            emailField.text,
                            usernameField.text
                        )
                    }
                }
            }

            SectionHeader {
                text: qsTr("Discovered Homey Pros")
                visible: homeysModel.count > 0
            }

            Repeater {
                model: homeysModel
                delegate: ListItem {
                    width: contentCol.width
                    contentHeight: Theme.itemSizeMedium

                    Row {
                        width: parent.width - (2 * Theme.horizontalPageMargin)
                        anchors.centerIn: parent

                        Column {
                            width: parent.width - 120
                            anchors.verticalCenter: parent.verticalCenter

                            Label {
                                text: name
                                font.pixelSize: Theme.fontSizeMedium
                                color: Theme.primaryColor
                            }

                            Label {
                                text: localUrlSecure || localUrl || remoteUrl || ""
                                font.pixelSize: Theme.fontSizeExtraSmall
                                color: Theme.secondaryColor
                                truncationMode: TruncationMode.Fade
                                width: parent.width
                            }
                        }

                        Button {
                            text: qsTr("Select")
                            width: 100
                            anchors.verticalCenter: parent.verticalCenter
                            onClicked: {
                                appWindow.selectHomey(id, "auto")
                            }
                        }
                    }
                }
            }

            SectionHeader {
                text: qsTr("Security & Storage")
            }

            Label {
                text: qsTr("In accordance with Sailfish OS security guidelines, sensitive tokens and credentials are stored in user-isolated configuration storage (~/.config/harbour-homeport/) with strict POSIX permissions (0600 mode, accessible only by the application owner).")
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                wrapMode: Text.Wrap
                width: parent.width - (2 * Theme.horizontalPageMargin)
                anchors.horizontalCenter: parent.horizontalCenter
            }

            SectionHeader {
                text: qsTr("Account & Session")
                visible: appWindow.isConnected
            }

            Button {
                text: qsTr("Disconnect / Logout")
                anchors.horizontalCenter: parent.horizontalCenter
                visible: appWindow.isConnected
                onClicked: {
                    appWindow.logout()
                }
            }
        }
    }
}
