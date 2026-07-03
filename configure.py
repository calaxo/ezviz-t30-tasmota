#!/usr/bin/env python3
"""
Helper to flash Tasmota onto an EZVIZ T30 (TYWE2S / ESP8285) and configure it
(Wi-Fi, MQTT, GPIO template) over the serial console.

Edit the CONFIG block below, wire up the module (see README), then:

    # 1) module in bootloader (IO0 -> GND + power-cycle), then:
    python configure.py flash          # erase + write tasmota.bin (DOUT)

    # 2) remove IO0 from GND, power-cycle so Tasmota boots, then:
    python configure.py configure      # send Wi-Fi + MQTT + GPIO template over serial

Requires: pip install --user esptool     (and a local tasmota.bin next to this script)
"""

import subprocess
import sys
import time

# ============================= CONFIG (edit me) =============================
PORT        = "COM3"                 # e.g. COM3 (Windows) or /dev/ttyUSB0 (Linux)
FIRMWARE    = "tasmota.bin"          # https://ota.tasmota.com/tasmota/release/tasmota.bin

WIFI_SSID     = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

MQTT_BROKER = "YOUR_MQTT_BROKER_IP"  # e.g. 192.168.1.10
MQTT_PORT   = 1883
TOPIC       = "ezviz-t30"            # must be unique per plug
DEVICE_NAME = "EZVIZ T30"

# GPIO template found on a CS-T30 10A EU (WG08 v1.4). Verify on your unit (see README).
#   GPIO12 = Relay1(224), GPIO13 = Button1(32), GPIO4 = LedLink(544), GPIO5 = Led_i1(320)
GPIO_TEMPLATE = "Module 18; GPIO12 224; GPIO13 32; GPIO4 544; GPIO5 320"
# ===========================================================================


def flash():
    """Erase and write Tasmota. Module must be in bootloader (IO0->GND + power-cycle)."""
    base = [sys.executable, "-m", "esptool", "--port", PORT, "--baud", "115200",
            "--before", "no-reset", "--after", "no-reset"]
    print(">> erasing flash ...")
    subprocess.run(base + ["erase-flash"], check=True)
    print(">> writing Tasmota (DOUT) ...")
    subprocess.run(base + ["write-flash", "--flash-mode", "dout",
                           "--flash-size", "1MB", "0x0", FIRMWARE], check=True)
    print(">> done. Remove IO0 from GND and power-cycle, then run: python configure.py configure")


def configure():
    """Send Wi-Fi + MQTT + GPIO template to a freshly-flashed Tasmota over serial."""
    import serial  # pyserial ships with esptool
    s = serial.Serial(PORT, 115200, timeout=0.2)
    s.dtr = False
    s.rts = False

    def send(cmd):
        s.write((cmd + "\n").encode())
        time.sleep(1.0)

    print(">> configuring over serial ...")
    # Network + identity + safe defaults. SetOption65 1 = don't wipe config on power-cycles.
    send(f"Backlog SSID1 {WIFI_SSID}; Password1 {WIFI_PASSWORD}; "
         f"MqttHost {MQTT_BROKER}; MqttPort {MQTT_PORT}; "
         f"Topic {TOPIC}; DeviceName {DEVICE_NAME}; FriendlyName1 {DEVICE_NAME}; "
         f"PowerOnState 0; SetOption65 1")
    # GPIO template (triggers one restart)
    send(f"Backlog {GPIO_TEMPLATE}")

    time.sleep(6)
    print(">> sent. The plug should reconnect to Wi-Fi/MQTT within a few seconds.")
    print(f">> control it via MQTT: cmnd/{TOPIC}/POWER  (payload ON/OFF)")
    s.close()


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "flash":
        flash()
    elif action == "configure":
        configure()
    else:
        print(__doc__)
        sys.exit(1)
