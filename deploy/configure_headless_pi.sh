#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Run with sudo: sudo $0" >&2
    exit 1
fi

# The matrix driver's real-time refresh thread is pinned to CPU 3. Keep normal
# device interrupts, especially Wi-Fi, on the other three CPUs.
BOOT_CMDLINE=/boot/firmware/cmdline.txt
if [ ! -f "$BOOT_CMDLINE" ]; then
    BOOT_CMDLINE=/boot/cmdline.txt
fi
if [ ! -f "$BOOT_CMDLINE" ]; then
    echo "Could not find the Raspberry Pi kernel command line." >&2
    exit 1
fi

CURRENT_CMDLINE=$(cat "$BOOT_CMDLINE")
UPDATED_CMDLINE=$CURRENT_CMDLINE
BOOT_ARGS_CHANGED=0
for arg in isolcpus=3 irqaffinity=0-2; do
    case " $UPDATED_CMDLINE " in
        *" $arg "*) ;;
        *) UPDATED_CMDLINE="$UPDATED_CMDLINE $arg"; BOOT_ARGS_CHANGED=1 ;;
    esac
done
if [ "$BOOT_ARGS_CHANGED" -eq 1 ]; then
    cp "$BOOT_CMDLINE" "$BOOT_CMDLINE.backup.$(date +%Y%m%d%H%M%S)"
    TEMP_CMDLINE="$BOOT_CMDLINE.tmp.$$"
    printf '%s\n' "$UPDATED_CMDLINE" > "$TEMP_CMDLINE"
    mv "$TEMP_CMDLINE" "$BOOT_CMDLINE"
    echo "Saved a boot-command backup. Reboot is required to apply CPU 3 isolation and route device interrupts to CPUs 0-2."
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
