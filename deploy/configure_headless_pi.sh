#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Run with sudo: sudo $0" >&2
    exit 1
fi

systemctl set-default multi-user.target
systemctl disable --now \
    lightdm.service wayvnc-control.service \
    bluetooth.service hciuart.service \
    cups.path cups.service cups.socket cups-browsed.service \
    ModemManager.service triggerhappy.service triggerhappy.socket \
    udisks2.service accounts-daemon.service colord.service \
    packagekit.service rtkit-daemon.service rpi-display-backlight.service \
    NetworkManager-wait-online.service glamor-test.service rp1-test.service

for unit in NetworkManager.service wpa_supplicant.service ssh.service avahi-daemon.service; do
    if ! systemctl is-active --quiet "$unit"; then
        echo "Required connectivity service is not active: $unit" >&2
        exit 1
    fi
done

echo "Headless boot configured; Wi-Fi, SSH, and mDNS are active."
