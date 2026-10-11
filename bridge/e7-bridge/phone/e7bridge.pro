TEMPLATE = app
TARGET = E7Bridge
QT += core gui network
CONFIG += release warn_on
CONFIG -= debug app_bundle
SOURCES += main.cpp
HEADERS += sha256_compat.h

symbian {
    # Private/unprotected development UID. This is NOT PocketJS's probe UID.
    TARGET.UID3 = 0xE94B7001
    TARGET.CAPABILITY = NetworkServices ReadUserData WriteUserData
    # WriteUserData permits E: user storage staging; not AllFiles/TCB.
    # HAL::Get and RProperty::Get remain read-only.
    LIBS += -lhal -lsisregistryclient -lcone -lws32
    TARGET.EPOCSTACKSIZE = 0x14000
    TARGET.EPOCHEAPSIZE = 0x20000 0x800000

    # The PocketJS GCCE bridge is only available inside its pinned container.
    exists(/toolchain/current/bin/symbian-gcce-link) {
        QMAKE_LINK = /toolchain/current/bin/symbian-gcce-link
        QMAKE_ELF2E32_FLAGS -= --compressionmethod bytepair
        QMAKE_ELF2E32_FLAGS += --compressionmethod inflate
    }
}
