# Poor Louis Farms LED matrix workflow

## Connect to the Pi

The controller is a Raspberry Pi Zero 2 W Rev 1.0 running Debian 12 Bookworm.
Its hostname is `mncs-pi` and it connects to Wi-Fi
`thecloud`. The workstation can reach it over the same LAN via wired Ethernet.
Use mDNS first. The last observed address was `192.168.1.227` and may change.

```sh
getent ahostsv4 mncs-pi.local
ip neigh show to 192.168.1.227
ssh-add -l
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes epi13@mncs-pi.local hostname
```

An empty neighbour table does not rule out connectivity. If mDNS fails, check the
router's DHCP lease list or verify the address on the Pi's console. To use the
previous address if it still belongs to the Pi, pass
`deploy/matrixctl --host epi13@192.168.1.227 …`. On first contact from a new
workstation, verify the SSH host-key fingerprint against the Pi's console or a
trusted record before accepting it. A changed fingerprint requires investigation.

The login is `epi13` using the workstation's existing Ed25519 key through its
SSH agent. If the key is locked, the operator can run
`ssh-add -t 1h ~/.ssh/id_ed25519` in their own terminal and enter the passphrase
directly at its prompt. The management commands use the existing noninteractive
`sudo` access. Check it with `ssh epi13@mncs-pi.local 'sudo -n true'`.

For a fresh hardware and software inventory, use these read-only commands.

```sh
ssh epi13@mncs-pi.local '
  tr -d "\000" </proc/device-tree/model
  printf "\n"
  cat /etc/os-release
  systemctl cat poor-louis-farms.service
  systemctl is-enabled poor-louis-farms.service
  cat /opt/rgbmatrix_painter/config.py
  journalctl -u poor-louis-farms.service -n 25 --no-pager
  vcgencmd get_throttled
'
```

## Hardware and playback

The previously working display has four 64×64 HUB75 panels and a Seengreat RGB
matrix adapter board rev 3.8. The panels are fed in parallel by an external 5 V,
15 A supply. The single data chain folds into a 2×2 square via `U-mapper`.
In the driver's intended front view, data runs from top right to top left to
bottom left to bottom right. The mapper reverses both coordinates on the bottom
row to account for the rotated panels. Feed the player a normal 128×128 image
with the origin at top left. [Upstream U-mapper implementation](https://github.com/hzeller/rpi-rgb-led-matrix/blob/master/lib/pixel-mapper.cc).

The deployed Python binding at `/opt/rgbmatrix_painter/rgbmatrix` drives GPIO
and exposes the refresh wait option. The Pi's driver checkout is at
`~/rpi-rgb-led-matrix` (observed revision `2f72a32`). The installed binding
defaults to `regular` GPIO mapping and `RGB` color order. Preserve the installed
build and configuration. The verified working
settings are chain length 4, parallel 1, GPIO slowdown 3, brightness 60%,
4-bit PWM, zero temporal dithering, and a 120 Hz refresh cap with busy waiting.
The Pi kernel command line isolates CPU 3 for refresh and routes interrupts
to CPUs 0–2.

`/etc/systemd/system/poor-louis-farms.service` runs
`/usr/bin/python3 /opt/rgbmatrix_painter/poor_louis_farms.py` as root for GPIO.
The existing unit is expected to be enabled at boot. Check `UnitFileState`
with `matrixctl status`. Native frames are loaded before steady playback, with the
first visible during cache creation. Halloween uses the procedural scene at
30 fps. GIFs use their own variable delays, rounded at cumulative frame
boundaries to the nearest panel refresh. At 120 Hz the intended cycle differs by
at most half a refresh from the source timing, assuming the panel meets the cap.
The driver handles frame swaps at VSync.
[Upstream refresh implementation](https://github.com/hzeller/rpi-rgb-led-matrix/blob/master/lib/led-matrix.cc).

## Build and review artwork

Create artwork directly on a 128×128 canvas. Export numbered PNGs with
zero-padded filenames, in playback order, to build a uniform-delay GIF.
Use the source GIF directly when it is already available. The Christmas scene's
reproducible builder and finished native GIF are under `artwork/christmas`.
Its 18.8-second loop holds the farm for 7.75 seconds, follows Santa into the
woods over 3.75 seconds, then holds the forest for about 6 seconds before the
fade back. The camera crops the scenery layers at different speeds while
keeping each exported frame at 128×128.

```sh
python3 matrix_animation.py build /path/to/128px-frames seasonal.gif --duration-ms 100
python3 artwork/christmas/build_poor_louis_christmas.py artwork/christmas/outputs/poor_louis_christmas_native_128.gif
python3 matrix_animation.py validate artwork/christmas/outputs/poor_louis_christmas_native_128.gif
```

Use an infinite loop, positive GIF delays in 10 ms units, and at most 384 GIF
frames to bound native cache memory on the Pi. The PNG builder uses Pillow and
can combine identical neighbouring frames. GIF transparency remaining after
GIF compositing displays as black. The validator decodes every frame, checks
size and loop metadata, and reports timing at the configured refresh rate.
Inspect the source at native size through at least two loops to check the visual
seam and lettering. GIF color quantization and the panel's 4-bit PWM can hide
dim accents. Use simple shapes, readable letter counters, and enough contrast
for edge highlights. Preserve supplied artwork and avoid resampling or
requantizing a valid GIF during deployment.

## Deploy and operate

Run these commands from the repository on the workstation.

```sh
deploy/matrixctl status
deploy/matrixctl setup
deploy/matrixctl deploy artwork/christmas/outputs/poor_louis_christmas_native_128.gif
deploy/matrixctl status
deploy/matrixctl brightness 60
deploy/matrixctl stop
deploy/matrixctl start
deploy/matrixctl restart
deploy/matrixctl restore
deploy/matrixctl halloween
```

`setup` upgrades the renderer and restarts the existing service by itself.
`deploy` includes that upgrade, so a first asset deployment can use one command.
Both reuse the installed driver, configuration, and unit. They preserve the
original player at `/opt/rgbmatrix_painter/poor_louis_farms.py.bak-before-seasonal`.
The asset is copied byte for byte and validated again on the Pi against its
configuration. It is stored as `animations/<SHA-256>.gif` inside the app directory.
Compare the local and Pi hashes printed by the command. The selection and any
brightness override are saved in `display.json` and used on boot.

`restore` swaps the current and prior animation selections. `halloween` explicitly
selects the built-in Halloween scene, leaving the last asset available to restore.
The brightness override accepts 1–100 and takes effect on restart. `stop`
stops playback until the next start or boot. Successful activation checks that
the new systemd invocation reached native playback. Failed activation restores
the prior files and running state. Software checks cannot confirm how the LEDs
look. For physical confirmation, look for the correct colors and orientation
across all four panels and watch a complete loop.

## Recover or troubleshoot

- If the service is running but the artwork looks wrong, use
  `deploy/matrixctl restore` or `deploy/matrixctl halloween`, then check the
  native asset. Preserve orientation and color settings during seasonal work.
- If startup fails, read `sudo journalctl -u poor-louis-farms.service -b -n 80`
  on the Pi. Check the selected hash, whether the asset exists, the last
  `RGB matrix canvas` line, and `vcgencmd get_throttled`. The logs separate cache
  preparation from playback. On the Halloween build, preloading 195 frames
  historically took about 16–20 seconds.
- For exact recovery of the pre-seasonal player, copy its preserved backup back
  into place with the command below. This uses the original hardware and unit
  configuration. The old renderer ignores `display.json`. A later deployment
  can reinstall the new renderer.

```sh
ssh epi13@mncs-pi.local '
  set -e
  sudo -n install -m 0644 \
    /opt/rgbmatrix_painter/poor_louis_farms.py.bak-before-seasonal \
    /opt/rgbmatrix_painter/poor_louis_farms.py
  sudo -n systemctl reset-failed poor-louis-farms.service
  sudo -n systemctl restart poor-louis-farms.service
'
```

Use the existing binding and headless setup scripts only when provisioning or
repairing a known driver or OS problem. A normal seasonal update requires no
reinstall, reboot, or change to panel settings.
