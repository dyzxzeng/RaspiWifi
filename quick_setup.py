import os
import sys
import setup_lib


if os.getuid():
    sys.exit('You need root access to install!')

os.system('clear')
print()
print()
print("All settings will be set to default \n")
print()
# install_ans = input("Are you ready to commit changes to the system? [y/N]: ")
#
# if(install_ans.lower() == 'y'):
setup_lib.install_prereqs()
setup_lib.copy_configs("")
setup_lib.update_main_config_file("","","","","","","")
# else:
# 	print()
# 	print()
# 	print("===================================================")
# 	print("---------------------------------------------------")
# 	print()
# 	print("RaspiWiFi installation cancelled. Nothing changed...")
# 	print()
# 	print("---------------------------------------------------")
# 	print("===================================================")
# 	print()
# 	print()
# 	sys.exit()

os.system('clear')
print()
print()
print("#####################################")
print("##### RaspiWiFi Setup Complete  #####")
print("#####################################")
print()
print()
# print("Initial setup is complete. A reboot is required to start in WiFi configuration mode...")
# reboot_ans = input("Would you like to do that now? [y/N]: ")
#
# if reboot_ans.lower() == 'y':
print("Rebooting...")
os.system('reboot')
