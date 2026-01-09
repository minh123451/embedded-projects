SUMMARY = "This is a simple QTapp_smarthome"
DESCRIPTION = "This is a simple QTapp_smarthome"
LICENSE = "CLOSED"

DEPENDS += " qtbase wayland "

SRC_URI = "file://main.cpp \
	file://mainwindow.cpp \
	file://mainwindow.h \
	file://mainwindow.ui \
	file://smarthome.pro \
	"



S = "${WORKDIR}"

do_install:append () {
	install -d ${D}${bindir}
	install -m 0775 smarthome ${D}${bindir}/
}

FILES_${PN} += "${bindir}/smarthome"

inherit qmake5
