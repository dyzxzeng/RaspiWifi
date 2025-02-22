import re

import yaml
from flask import Flask, render_template, request, jsonify
import subprocess
import os
import time
from threading import Thread
import fileinput
import syslog

app = Flask(__name__, static_folder='./build/', template_folder='./build/', static_url_path='/')
app.debug = True

@app.route('/', methods = ['GET', 'POST'])
def index():
    # config = configparser.ConfigParser();
    # config.read_file("/etc/raspiwifi/raspiwifi.conf")
    # isAuto = config["auto_config"]
    if request.method == "POST":
        if request.form.get("toggle_auto_ap"):
            # os.system('sed -i \'s/auto_config=0/auto_config=1/\' /etc/raspiwifi/raspiwifi.conf')
            updateAutoReconfig(1)
        else:
            updateAutoReconfig(0)
            # os.system('sed -i \'s/auto_config=1/auto_config=0/\' /etc/raspiwifi/raspiwifi.conf')

    wifi_ap_array = scan_wifi_networks()
    config_hash = config_file_hash()

    return render_template('index.html')

@app.route('/get_mac', methods = ['GET'])
def get_mac_address():
    return jsonify({"mac": get_mac()}), 200

@app.route('/get_auto_reconfigure', methods = ['GET'])
def get_auto_reconfigure():
    config = config_file_hash()
    return jsonify(config['auto_config']), 200

@app.route('/get_wifi_networks', methods = ['GET'])
def get_wifi_networks():
    wifi_ap_array = scan_wifi_networks()
    return jsonify(wifi_ap_array), 200

@app.route('/get_wifi_info', methods = ['GET'])
def get_wifi_info():
    ssid, ping = get_wifi_ssid_and_ping()
    return jsonify({"ssid": ssid, "ping": ping}), 200

@app.route('/get_hostname', methods = ['GET'])
def get_host():
    return jsonify(hostname()), 200

@app.route('/update_credentials', methods = ['POST'])
def update_credentials():
    data = request.get_json()
    ssid = data['ssid']
    connection_type = data['security']

    if ssid is None:
        return "SSID was not provided"

    if connection_type == "WPA":
        key = data['pass']
        
        if key is None:
            return "Key was not provided"
        else:
            create_wpa_supplicant(ssid, key)
    elif connection_type == "WPA2":
        password = data['pass']

        if password is None:
            return "password was not provided"
        else:
            create_wpa_supplicant(ssid, password)
    elif connection_type == "EAP":
        username = data['user']
        password = data['pass']

        if username is None or password is None:
            return "Username or password was not provided"
        else:
            create_wpa_supplicant_with_username(ssid, username, password)
    else:
        return "Invalid connection type: " + connection_type

    def sleep_and_start_ap():
        time.sleep(2)
        set_ap_client_mode()
    t = Thread(target=sleep_and_start_ap)
    t.start()

    return "Success"

@app.route('/update_auto_reconfigure', methods = ['POST'])
def update_auto_reconfigure():
    data = request.get_json()
    reconfig_enabled = data['autoReconfigure']

    if reconfig_enabled is None:
        return "autoReconfigure was not provided"

    updateAutoReconfig(reconfig_enabled)

    return "Success"

@app.route('/wifi')
def save_credentials_from_wifi():
    """
    This function that is used to quickly set the Wi-Fi credentials by accessing
    a link from the device's browser without having to manually enter the
    credentials.
    """
    connection_type = request.args.get('method')
    ssid = request.args.get('ssid')
    wifi_pass = request.args.get('pass')
    wifi_user = request.args.get('user')
    wifi_key = request.args.get('key')

    # if connection_type is None or ssid is None:
    #     raise KeyError("connection_type or ssid is None")

    # if wifi_user == "":
    #     create_wpa_supplicant(ssid, wifi_pass)
    # else:
    #     create_wpa_supplicant_with_username(ssid, wifi_user, wifi_pass)

    if connection_type == "eap":
        create_wpa_supplicant_with_username(ssid, wifi_user, wifi_pass)
    elif connection_type == "wpa":
        create_wpa_supplicant(ssid, wifi_key)
    elif connection_type == "wpa2":
        create_wpa_supplicant(ssid, wifi_pass)

    broker = request.args.get('broker')
    if broker is not None:
        set_mqtt_server(broker)

    # Call set_ap_client_mode() in a thread otherwise the reboot will prevent
    # the response from getting to the browser
    def sleep_and_start_ap():
        time.sleep(2)
        set_ap_client_mode()
    t = Thread(target=sleep_and_start_ap)
    t.start()

    # return render_template('save_credentials.html', connection_type = connection_type, ssid = ssid, user = wifi_user, passs = wifi_pass, key = wifi_key)
    # return render_template('save_credentials.html', connection_type = "connection_type", ssid = "ssid", user = "wifi_user", passs = "wifi_pass", key = "wifi_key")

    if broker is not None or connection_type is not None:
        return "Configured MQTT server and Wi-Fi credentials!"
    elif connection_type is not None:
        return "Configured Wi-Fi credentials!"
    elif broker is not None:
        return "Configured MQTT server!"
    else:
        return "Invalid set of parameters given, no configuration was done."

######## FUNCTIONS ##########

def scan_wifi_networks():
    """
    This function scans for available Wi-Fi networks and returns an array of
    the SSIDs of the networks found.

    Parameters:
    None

    Returns:
    ap_array (array): An array of the SSIDs of the Wi-Fi networks found.
    """
    iwlist_raw = subprocess.Popen(['iwlist', 'scan'], stdout=subprocess.PIPE)
    ap_list, err = iwlist_raw.communicate()
    ap_array = []

    for line in ap_list.decode('utf-8').rsplit('\n'):
        if 'ESSID' in line:
            ap_ssid = line[27:-1]
            if ap_ssid != '':
                ap_array.append(ap_ssid)

    return ap_array

def create_wpa_supplicant(ssid, wifi_key):
    """
    This function generates a wpa_supplicant.conf file which is used to store
    Wi-Fi network user credentials. This file is essential for automatic
    connection to the Wi-Fi network after a reboot.

    Parameters:
    ssid (str): The SSID of the Wi-Fi network.
    wifi_key (str): The Wi-Fi network password.

    Returns:
    None
    """
    temp_conf_file = open('wpa_supplicant.conf.tmp', 'w')
    temp_conf_file.write('ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n')
    temp_conf_file.write('update_config=1\n')
    temp_conf_file.write('\n')
    temp_conf_file.write('network={\n')
    temp_conf_file.write('	ssid="' + ssid + '"\n')
    if wifi_key == '':
        temp_conf_file.write('	key_mgmt=NONE\n')
    else:
        temp_conf_file.write('	psk="' + wifi_key + '"\n')
    temp_conf_file.write('	}')
    temp_conf_file.close()
    os.system('mv wpa_supplicant.conf.tmp /etc/wpa_supplicant/wpa_supplicant.conf')

def create_wpa_supplicant_with_username(ssid, username, password):
    """
    Creates a wpa_supplicant.conf file with the given ssid, username, and password.
    :param ssid: The ssid of the network
    :param username: The username for the network
    :param password: The password for the network
    """
    toWrite = f"""
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid="{ssid}"
    eap=PEAP
    key_mgmt=WPA-EAP
    phase2="auth=MSCHAPV2"
    identity="{username}"
    password="{password}"
}}

 """
    temp_conf_file = open('wpa_supplicant.conf.tmp', 'w')
    temp_conf_file.write(toWrite)
    temp_conf_file.close()
    os.system('mv wpa_supplicant.conf.tmp /etc/wpa_supplicant/wpa_supplicant.conf')

def set_mqtt_server(mqtt_server):
    """
    Sets the MQTT server in the raspiwifi.conf file.
    :param mqtt_server: The MQTT server
    """
    with open('../../../DigitizerDriver/config.yaml') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
        data['broker'] = mqtt_server
    yaml.dump(data, open('../../../DigitizerDriver/config.yaml', 'w'), default_flow_style=False)

def set_ap_client_mode():
    """
    Sets the device to AP Client mode by removing the host_mode file and
    copying the apclient_bootstrapper to the cron directory.
    """
    if os.path.exists("/etc/raspiwifi/host_mode"):
        os.system('rm -f /etc/raspiwifi/host_mode')
        os.system('rm -f /etc/cron.raspiwifi/aphost_bootstrapper')
        os.system('cp /usr/lib/raspiwifi/reset_device/static_files/apclient_bootstrapper /etc/cron.raspiwifi/')
        os.system('chmod +x /etc/cron.raspiwifi/apclient_bootstrapper')
        os.system('rm -f /etc/dnsmasq.conf 2>/dev/null')
        os.system('cp /etc/dnsmasq.conf.original /etc/dnsmasq.conf')
        os.system('rm -f /etc/dhcpcd.conf 2>/dev/null')
        os.system('cp /etc/dhcpcd.conf.original /etc/dhcpcd.conf')
        os.system('systemctl disable dnsmasq.service')
        os.system('systemctl disable hostapd.service')
        syslog.syslog('raspiwifi - set_ap_client_mode')

    os.system('reboot')

def update_wpa(wpa_enabled, wpa_key):
    """
    Updates the raspiwifi.conf file with the new wpa_enabled and wpa_key values.
    :param wpa_enabled: 1 or 0
    :param wpa_key: The WPA key
    """
    with fileinput.FileInput('/etc/raspiwifi/raspiwifi.conf', inplace=True) as raspiwifi_conf:
        for line in raspiwifi_conf:
            if 'wpa_enabled=' in line:
                line_array = line.split('=')
                line_array[1] = wpa_enabled
                print(line_array[0] + '=' + str(line_array[1]))

            if 'wpa_key=' in line:
                line_array = line.split('=')
                line_array[1] = wpa_key
                print(line_array[0] + '=' + line_array[1])

            if 'wpa_enabled=' not in line and 'wpa_key=' not in line:
                print(line, end='')

def updateAutoReconfig(reconfig_enabled):
    """
    Updates the raspiwifi.conf file with the new auto_config value.
    :param reconfig_enabled: 1 or 0
    """
    with fileinput.FileInput('/etc/raspiwifi/raspiwifi.conf', inplace=True) as raspiwifi_conf:
        for line in raspiwifi_conf:
            if 'auto_config=' in line:
                line_array = line.split('=')
                line_array[1] = reconfig_enabled
                print(line_array[0] + '=' + str(line_array[1]))

            if 'auto_config=' not in line:
                print(line, end='')

def config_file_hash():
    """
    Reads the raspiwifi.conf file and returns a dictionary of the key/value pairs
    """
    config_file = open('/etc/raspiwifi/raspiwifi.conf')
    config_hash = {}

    for line in config_file:
        line_key = line.split("=")[0]
        line_value = line.split("=")[1].rstrip()
        config_hash[line_key] = line_value

    return config_hash

def get_wifi_ssid_and_ping():
    """
    Gets the current wifi ssid and pings google.com
    :return: The ssid and ping result
    """
    try:
        ssid = subprocess.check_output(['iwgetid', '-r']).decode('utf-8').rstrip()
        if ssid == "":
            return None, None

        # ping = subprocess.check_output(['ping', '-c', '1', 'google.com']).decode('utf-8').rstrip()
        #
        # match = re.search('time=(\d+.\d+) ms', ping)
        # if match:
        #     ping_time = match.group(1)
        # else:
        #     ping_time = '---'

        # ping_time = get_average_ping()
        ping_time = 0

        if ping_time is None:
            ping_time = '---'

        return ssid, ping_time
    except Exception as e:
        return None, None

def get_average_ping():
    ping_times = []
    for _ in range(5):
        ping = subprocess.check_output(['ping', '-c', '1', 'google.com']).decode('utf-8').rstrip()
        match = re.search('time=(\d+.\d+) ms', ping)
        if match:
            ping_time = float(match.group(1))
            ping_times.append(ping_time)

    average_ping = sum(ping_times) / len(ping_times) if ping_times else None
    return round(average_ping, 2)

def hostname():
    """
    Gets the hostname of the device
    :return: The hostname
    """
    return subprocess.check_output(['hostname']).decode('utf-8').rstrip()

def get_mac():
    """
    Gets the mac address of the device
    :return: The mac address
    """
    command = "ifconfig wlan0 | awk '/ether/{print $2}'"
    mac = subprocess.check_output(command, shell=True)
    return mac.decode('utf-8').rstrip()



if __name__ == '__main__':
    config_hash = config_file_hash()

    if config_hash['ssl_enabled'] == "1":
        app.run(host = '0.0.0.0', port = int(config_hash['server_port']), ssl_context='adhoc', threaded=True)
    else:
        app.run(host = '0.0.0.0', port = int(config_hash['server_port']), threaded=True)

