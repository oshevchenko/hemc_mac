import dbus
import dbus.service
import json
from .serial_to_mac import SerialToMacAddress, SAPLING_MAC_OUI, SAPLING_HEMC_DEVICE_TYPE
from .local_file_process import LocalFileProcess, PATH_LOCAL_HEMC_MAC_LIST 
from .remote_file_process import RemoteFileProcess, PATH_REMOTE_HEMC_MAC_LIST, PATH_REMOTE_MUTEX_UNLOCKED, PATH_REMOTE_MUTEX_LOCKED, PATH_LOCAL_MUTEX_UNLOCKED
from saplinguboot import UBootEnv, SAPLING_ETH_MAC_ADDR_VARS, SAPLING_ETH_MAC_ADDR_DEFAULT
from .sftp_client import SftpClient
from .ftp_client import FtpClient

import logging

logger = logging.getLogger(__name__.split('.')[0])


class SetMacDbusHandler(dbus.service.Object):
    def __init__(self, bus_name, object_path):
        super().__init__(bus_name, object_path)


    @dbus.service.method("com.sapling.hemc.setmac", in_signature='', out_signature='s')
    def get_mac_addresses(self):
        """
        Get U-Boot variables for MAC addresses.
        Compare the first MAC address with the default value.
        If it matches, return "default" as True, otherwise False.

        To test use command:
        dbus-send --system --print-reply  --dest=com.sapling.hemc /com/sapling/hemc/setmac \
            com.sapling.hemc.setmac.get_mac_addresses

        The output will be a JSON string like:
          string "{"result": "OK", "default": false, "mac_addresses": ["60:36:96:10:00:61", "60:36:96:10:00:62", "60:36:96:10:00:63", "60:36:96:10:00:64", "60:36:96:10:00:65", "60:36:96:10:00:66"]}"

        """
        ret = "FAIL"
        default = True
        mac = []
        try:
            for eth_addr_var in SAPLING_ETH_MAC_ADDR_VARS:
                mac.append(UBootEnv.get_variable(eth_addr_var))
            if mac[0] == SAPLING_ETH_MAC_ADDR_DEFAULT:
                default = True
            else:
                default = False
            ret = "OK"
        except Exception as e:
            logger.error(f"Error getting MAC addresses: {e}")
            ret = "FAIL"
            default = True
            mac = []
        ret = {"result": ret, "default": default, "mac_addresses": mac}
        return json.dumps(ret)


    @dbus.service.method("com.sapling.hemc.setmac", in_signature='s', out_signature='s')
    def set_mac_addresses_manually(self, config):
        """
        Set U-Boot variables for MAC addresses.
        To test use command:
dbus-send --system --print-reply  --dest=com.sapling.hemc /com/sapling/hemc/setmac \
com.sapling.hemc.setmac.set_mac_addresses_manually \
string:"$(cat << 'EOF'
{
    "mac_addresses":[
    "60:36:96:10:00:67",
    "60:36:96:10:00:68",
    "60:36:96:10:00:69",
    "60:36:96:10:00:6a",
    "60:36:96:10:00:6b",
    "60:36:96:10:00:6c"
    ]
}
EOF
)"
        """
        mac_all = []
        try:
            config = json.loads(config)
            mac_all = config.get('mac_addresses', [])
            for i, eth_addr_var in enumerate(SAPLING_ETH_MAC_ADDR_VARS):
                    mac = mac_all[i]
                    logger.info(f"Setting U-Boot variable '{eth_addr_var}' to MAC: {mac}")
                    UBootEnv.set_variable(eth_addr_var, mac)
            ret = "OK"
        except Exception as e:
            logger.error(f"Error: {e}")
            ret = "FAIL"
        ret = {"result": ret, "mac_addresses": mac_all}
        return json.dumps(ret)


    @dbus.service.method("com.sapling.hemc.setmac", in_signature='s', out_signature='s')
    def set_mac_addresses_ftp(self, config):
        """
        To test use command:

        dbus-send --system --print-reply --dest=com.sapling.hemc \
            /com/sapling/hemc/setmac \
            com.sapling.hemc.setmac.set_mac_addresses_ftp string:"{}"

        The output will be a JSON string like:
        string "{"result": "OK", "mac_addresses": ["60:36:96:10:00:67", "60:36:96:10:00:68", "60:36:96:10:00:69", "60:36:96:10:00:6a", "60:36:96:10:00:6b", "60:36:96:10:00:6c"]}"

        The full command (all parameters are optional):

dbus-send --system --print-reply --dest=com.sapling.hemc \
/com/sapling/hemc/setmac \
com.sapling.hemc.setmac.set_mac_addresses_ftp \
string:"$(cat << 'EOF'
{
"server": "192.168.1.102",
"name": "sftp_hemc",
"password": "SaplingHemc",
"path_local_hemc_mac_list": "/tmp/HEMC_MAC.txt",
"path_remote_hemc_mac_list": "uploads/HEMC_MAC.txt",
"path_remote_mutex_unlocked": "uploads/mutex.unlocked",
"path_remote_mutex_locked": "uploads/mutex.locked",
"path_local_mutex_unlocked": "/tmp/mutex.unlocked",
"protocol": "sftp",
"port": 22,
"timeout": 10,
"oui": "60:36:96",
"device_type": "10"
}
EOF
)"

dbus-send --system --print-reply --dest=com.sapling.hemc \
/com/sapling/hemc/setmac \
com.sapling.hemc.setmac.set_mac_addresses_ftp \
string:"$(cat << 'EOF'
{
"server": "patch.sapling-inc.com",
"name": "****************",
"password": "****************",
"protocol": "ftp",
"port": 21,
"timeout": 10,
"path_local_hemc_mac_list": "/tmp/HEMC_MAC.txt",
"path_remote_hemc_mac_list": "tmp/HEMC_MAC.txt",
"path_remote_mutex_unlocked": "tmp/mutex.unlocked",
"path_remote_mutex_locked": "tmp/mutex.locked",
"path_local_mutex_unlocked": "/tmp/mutex.unlocked",
"oui": "60:36:96",
"device_type": "10"
}
EOF
)"
        """
        ret = "FAIL"
        mac_all = []
        try:
            config = json.loads(config)

            remote_storage_cls = config.get('protocol', 'sftp').lower()
            if remote_storage_cls == 'sftp':
                remote_storage_cls = SftpClient
            elif remote_storage_cls == 'ftp':
                remote_storage_cls = FtpClient
            else:
                logger.error(f"Unsupported FTP client: {remote_storage_cls}. Supported clients are 'sftp' and 'ftp'.")
                raise ValueError(f"Unsupported FTP client: {remote_storage_cls}. Supported clients are 'sftp' and 'ftp'.")

            remote_storage_cls.init(
                    server=config.get('server', '192.168.1.102'),
                    name=config.get('name', 'sftp_hemc'),
                    password=config.get('password', 'SaplingHemc'),
                    port=int(config.get('port', 22)),
                    timeout=int(config.get('timeout', 10)))

            serial_to_mac_address = SerialToMacAddress(
                                    oui = config.get('oui', SAPLING_MAC_OUI),
                                    device_type = config.get('device_type', SAPLING_HEMC_DEVICE_TYPE),
                                    num_of_macs= len(SAPLING_ETH_MAC_ADDR_VARS))

            remote_file_process = RemoteFileProcess(
                                    local_file_path=config.get('path_local_hemc_mac_list', PATH_LOCAL_HEMC_MAC_LIST),
                                    remote_file_path=config.get('path_remote_hemc_mac_list', PATH_REMOTE_HEMC_MAC_LIST),
                                    path_remote_mutex_unlocked=config.get('path_remote_mutex_unlocked', PATH_REMOTE_MUTEX_UNLOCKED),
                                    path_remote_mutex_locked=config.get('path_remote_mutex_locked', PATH_REMOTE_MUTEX_LOCKED),
                                    path_local_mutex_unlocked=config.get('path_local_mutex_unlocked', PATH_LOCAL_MUTEX_UNLOCKED),
                                    local_storage_cls = LocalFileProcess,
                                    remote_storage_cls=remote_storage_cls,
                                    mac_process=serial_to_mac_address)

            file_data = remote_file_process.process_file_atomicaly()
            for i, eth_addr_var in enumerate(SAPLING_ETH_MAC_ADDR_VARS):
                _, _, mac = file_data[i]
                logger.info(f"Setting U-Boot variable '{eth_addr_var}' to MAC: {mac}")
                UBootEnv.set_variable(eth_addr_var, mac)
            mac_all = []
            for eth_addr_var in SAPLING_ETH_MAC_ADDR_VARS:
                mac_all.append(UBootEnv.get_variable(eth_addr_var))

            ret = "OK"
        except Exception as e:
            logger.error(f"Error: {e}")
            ret = "FAIL"
            mac_all = []
        ret = {"result": ret, "mac_addresses": mac_all}
        return json.dumps(ret)

