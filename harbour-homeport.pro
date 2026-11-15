TARGET = harbour-homeport

CONFIG += sailfishapp

SOURCES += src/harbour-homeport.cpp

DISTFILES += \
    qml/harbour-homeport.qml \
    qml/cover/CoverPage.qml \
    qml/pages/MainPage.qml \
    qml/pages/DevicesPage.qml \
    qml/pages/DeviceDetailPage.qml \
    qml/pages/ZonesPage.qml \
    qml/pages/FlowsPage.qml \
    qml/pages/SettingsPage.qml \
    rpm/harbour-homeport.spec \
    harbour-homeport.desktop

# Copy python sources to application directory
pythonsources.files = src/homeport
pythonsources.path = /usr/share/$${TARGET}/src

INSTALLS += pythonsources

SAILFISHAPP_ICONS = 86x86 108x108 128x128 172x172
