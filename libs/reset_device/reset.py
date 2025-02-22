import RPi.GPIO as GPIO
import os
import time
import subprocess
import reset_lib
import re

def wifi_mac_4():
    serial_last_four = "0000"
    if os.path.exists("/etc/raspiwifi/host_mode"):
        serial = re.search(b'Serial\s*:\s*\w*',subprocess.check_output(['cat', '/proc/cpuinfo']))
        serial_last_four = serial.group()[-4:].decode('utf-8')
        serial_last_four = int(serial_last_four, 16) ^ 0x555555
        serial_last_four = hex(serial_last_four)[-4:]
    return serial_last_four

GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


if os.path.exists("/etc/raspiwifi/host_mode"):
    # serial = re.search(b'Serial\s*:\s*\w*',subprocess.check_output(['cat', '/proc/cpuinfo']))
    # serial_last_four = serial.group()[-4:].decode('utf-8')
    serial_last_four = wifi_mac_4()

    config_hash = reset_lib.config_file_hash()
    ssid_prefix = config_hash['ssid_prefix']

    reboot_required = reset_lib.wpa_check_activate(config_hash['wpa_enabled'], config_hash['wpa_key'])
    reboot_required |= reset_lib.update_ssid(ssid_prefix, serial_last_four)
    reboot_required |= reset_lib.update_hostname(config_hash['hostname_prefix'], serial_last_four)

    if reboot_required == True:
        os.system('reboot')

# This is the main logic loop waiting for a button to be pressed on GPIO 18 for 10 seconds.
# If that happens the device will reset to its AP Host mode allowing for reconfiguration on a new network.

counter = 0

while True:
    while GPIO.input(18) == 1:
        time.sleep(1)
        counter = counter + 1

        print(counter)

        if counter == 9:
            reset_lib.reset_to_host_mode()

        if GPIO.input(18) == 0:
            counter = 0
            break

    time.sleep(1)
