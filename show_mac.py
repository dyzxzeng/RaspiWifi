import os
import re
import subprocess
import netifaces

def wifi_mac_4():
    serial_last_four = "0000"
    # if os.path.exists("/etc/raspiwifi/host_mode"):
    serial = re.search(b'Serial\s*:\s*\w*',subprocess.check_output(['cat', '/proc/cpuinfo']))
    serial_last_four = serial.group()[-4:].decode('utf-8')
    serial_last_four = int(serial_last_four, 16) ^ 0x555555
    serial_last_four = hex(serial_last_four)[-4:]
    return serial_last_four

def wifi_mac_ifconfig():
    mac = "if.config"
    data = netifaces.interfaces()
    for i in data:
        if i == 'wlan0': #'en0': # 'eth0':
            interface = netifaces.ifaddresses(i)
            info = interface[netifaces.AF_LINK]
            if info:
                mac = interface[netifaces.AF_LINK][0]["addr"]
    return mac

def wifi_mac_cpuinfo():
    mac = "cpu.info"
    serial = re.search(b'Serial\s*:\s*\w*',subprocess.check_output(['cat', '/proc/cpuinfo']))
    serial_last_four = serial.group()[-6:].decode('utf-8')
    # print(hex(serial_last_four))
    serial_last_four = int(serial_last_four, 16) ^ 0x555555
    mac = hex(serial_last_four)
    mac = "b8:27:eb:" + mac[-6:-4] + ":" + mac[-4:-2] + ":" + mac[-2:]
    return mac


if __name__== '__main__':
    print(wifi_mac_4())
    print(wifi_mac_ifconfig())
    print(wifi_mac_cpuinfo())