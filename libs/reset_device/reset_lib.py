import os
import fileinput
import subprocess
import syslog
import time

def config_file_hash():
	config_file = open('/etc/raspiwifi/raspiwifi.conf')
	config_hash = {}

	for line in config_file:
		line_key = line.split("=")[0]
		line_value = line.split("=")[1].rstrip()
		config_hash[line_key] = line_value

	return config_hash

def wpa_check_activate(wpa_enabled, wpa_key):
	wpa_active = False
	reboot_required = False

	with open('/etc/hostapd/hostapd.conf') as hostapd_conf:
		for line in hostapd_conf:
			if 'wpa_passphrase' in line:
				wpa_active = True

	if wpa_enabled == '1' and wpa_active == False:
		reboot_required = True
		os.system('cp /usr/lib/raspiwifi/reset_device/static_files/hostapd.conf.wpa /etc/hostapd/hostapd.conf')

	if wpa_enabled == '1':
		with fileinput.FileInput('/etc/hostapd/hostapd.conf', inplace=True) as hostapd_conf:
			for line in hostapd_conf:
				if 'wpa_passphrase' in line:
					if 'wpa_passphrase=' + wpa_key not in line:
						print('wpa_passphrase=' + wpa_key)
						reboot_required = True
						break
					else:
						print(line, end = '')
				else:
					print(line, end = '')

	if wpa_enabled == '0' and wpa_active == True:
		reboot_required = True
		os.system('cp /usr/lib/raspiwifi/reset_device/static_files/hostapd.conf.nowpa /etc/hostapd/hostapd.conf')

	return reboot_required

def update_ssid(ssid_prefix, serial_last_four):
	reboot_required = False
	ssid_correct = False
	ssid = ssid_prefix + ' ' + serial_last_four

	with open('/etc/hostapd/hostapd.conf') as hostapd_conf:
		for line in hostapd_conf:
			if ssid in line:
				ssid_correct = True

	if ssid_correct == False:
		with fileinput.FileInput("/etc/hostapd/hostapd.conf", inplace=True) as file:
			for line in file:
				if 'ssid=' in line:
					line_array = line.split('=')
					line_array[1] = ssid
					print(line_array[0] + '=' + line_array[1])
				else:
					print(line, end = '')

		reboot_required = True
			
	return reboot_required

def update_hostname(hostname_prefix, serial_last_four):
	current_hostname = subprocess.check_output(['hostname']).decode('utf-8').rstrip()
	hostname = hostname_prefix + '-' + serial_last_four

	if current_hostname == hostname:
		return False

	with open('/etc/hostname', 'w') as hostname_file:
		hostname_file.write(hostname)

	with open('/etc/hosts', 'r') as hosts_file:
		hosts_file_data = hosts_file.read()

	hosts_file_data = hosts_file_data.replace(current_hostname, hostname)

	with open('/etc/hosts', 'w') as hosts_file:
		hosts_file.write(hosts_file_data)

	return True

def is_wifi_active():
	iwconfig_out = subprocess.check_output(['iwconfig']).decode('utf-8')
	wifi_active = True

	if "Access Point: Not-Associated" in iwconfig_out:
		wifi_active = False

	return wifi_active

def reset_to_host_mode():
	if not os.path.isfile('/etc/raspiwifi/host_mode'):
		#os.system('aplay /usr/lib/raspiwifi/reset_device/button_chime.wav')
		os.system('rm -f /etc/wpa_supplicant/wpa_supplicant.conf')
		os.system('rm -f /etc/cron.raspiwifi/apclient_bootstrapper')
		os.system('cp /usr/lib/raspiwifi/reset_device/static_files/aphost_bootstrapper /etc/cron.raspiwifi/')
		os.system('chmod +x /etc/cron.raspiwifi/aphost_bootstrapper')
		os.system('rm -f /etc/dhcpcd.conf 2>/dev/null')
		os.system('cp /usr/lib/raspiwifi/reset_device/static_files/dhcpcd.conf /etc/')
		os.system('rm -f /etc/dnsmasq.conf 2>/dev/null')
		os.system('cp /usr/lib/raspiwifi/reset_device/static_files/dnsmasq.conf /etc/')
		# /etc/hostapd/hostapd.conf no need to reset
		os.system('touch /etc/raspiwifi/host_mode')
		os.system('systemctl enable dnsmasq.service')
		os.system('systemctl enable hostapd.service')
		syslog.syslog('raspiwifi - reset_to_host_mode')
		time.sleep(2)
		
	os.system('reboot')

