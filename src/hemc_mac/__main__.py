import argparse
from .serial_to_mac import SerialToMacAddress, SAPLING_MAC_OUI, SAPLING_HEMC_DEVICE_TYPE, SAPLING_HEMC_NUM_OF_MAC
from .local_file_process import LocalFileProcess, PATH_LOCAL_HEMC_MAC_LIST 
from .remote_file_process import RemoteFileProcess, PATH_REMOTE_HEMC_MAC_LIST, PATH_REMOTE_MUTEX_UNLOCKED, PATH_REMOTE_MUTEX_LOCKED, PATH_LOCAL_MUTEX_UNLOCKED
# from saplinguboot import UBootEnv, SAPLING_ETH_MAC_ADDR_VARS, SAPLING_ETH_MAC_ADDR_DEFAULT
SAPLING_ETH_MAC_ADDR_VARS = ['ethaddr', 'eth1addr', 'eth2addr', 'eth3addr', 'eth4addr', 'eth5addr']

from .sftp_client import SftpClient
from .ftp_client import FtpClient

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="SFTP MAC serial number updater")
    parser.add_argument('--credentials', type=str, default='credentials.txt', help='Path to credentials file')
    parser.add_argument('--clean', action='store_true', help='Clean up local and remote files')
    parser.add_argument('--init', action='store_true', help='Create initial serial file and mutex on SFTP server')
    args = parser.parse_args()

    credentials_file = args.credentials
    init_mode = args.init
    clean_mode = args.clean
    config_from_file = {}
    # All the keys should be present in the credentials file
    must_have_list_of_keys = ['server', 'name', 'password', 'protocol', 'port']
    try:
        """
        Example of credentials file:
            # Sapling SFTP configuration file
            # Comments are allowed!
            # Empty lines are ignored.

# Sapling SFTP configuration file
Server: 192.168.1.102
#Server: 192.168.3.102
Name: sftp_hemc
Password: SaplingHemc
Protocol: SFTP
Port: 22
OUI: 60:36:96
DEVICE_TYPE: 10
NUM_OF_MAC: 6
PATH_LOCAL_HEMC_MAC_LIST: /tmp/HEMC_MAC.txt
PATH_REMOTE_HEMC_MAC_LIST: uploads/HEMC_MAC.txt
PATH_REMOTE_MUTEX_UNLOCKED: uploads/mutex.unlocked
PATH_REMOTE_MUTEX_LOCKED: uploads/mutex.locked
PATH_LOCAL_MUTEX_UNLOCKED: /tmp/mutex.unlocked

# Sapling FTP configuration file
Server: patch.sapling-inc.com
#Server: 192.168.3.102
Name: ****************
Password: ****************
Protocol: FTP
Port: 21
OUI: 60:36:96
DEVICE_TYPE: 10
NUM_OF_MAC: 6
PATH_LOCAL_HEMC_MAC_LIST: /tmp/HEMC_MAC.txt
PATH_REMOTE_HEMC_MAC_LIST: tmp/HEMC_MAC.txt
PATH_REMOTE_MUTEX_UNLOCKED: tmp/mutex.unlocked
PATH_REMOTE_MUTEX_LOCKED: tmp/mutex.locked
PATH_LOCAL_MUTEX_UNLOCKED: /tmp/mutex.unlocked

        """
        with open(credentials_file, 'r') as f:
            lines = f.readlines()
        for line in lines:
            if line.startswith('#') or not line.strip():
                continue
            words = line.strip().split(': ')
            if len(words) != 2:
                raise ValueError("Each line in the credentials file must be in the format 'Key: Value'.")
            key = words[0].strip().lower()
            value = words[1].strip()
            if len(value) == 0:
                raise ValueError(f"Value for '{key}' cannot be empty.")
            config_from_file[key] = value
        missing_keys = [key for key in must_have_list_of_keys if key not in config_from_file]
        if missing_keys:
            raise ValueError(f"Credentials file must contain the following keys: {', '.join(missing_keys)}.")
    except Exception as e:
        print(f"Error reading credentials: {e}")
        exit(1)

    remote_storage_cls = config_from_file['protocol'].lower()
    if remote_storage_cls == 'sftp':
        remote_storage_cls = SftpClient
    elif remote_storage_cls == 'ftp':
        remote_storage_cls = FtpClient
    else:
        print(f"Unsupported FTP client: {remote_storage_cls}. Supported clients are 'sftp' and 'ftp'.")
        exit(1)

    remote_storage_cls.init(
            server=config_from_file['server'],
            name=config_from_file['name'],
            password=config_from_file['password'],
            port=int(config_from_file['port']),
            timeout=int(config_from_file.get('timeout', 10)))

    serial_to_mac_address = SerialToMacAddress(
                            oui = config_from_file.get('oui', SAPLING_MAC_OUI),
                            device_type = config_from_file.get('device_type', SAPLING_HEMC_DEVICE_TYPE),
                            num_of_macs= len(SAPLING_ETH_MAC_ADDR_VARS))

    remote_file_process = RemoteFileProcess(
                            local_file_path=config_from_file.get('path_local_hemc_mac_list', PATH_LOCAL_HEMC_MAC_LIST),
                            remote_file_path=config_from_file.get('path_remote_hemc_mac_list', PATH_REMOTE_HEMC_MAC_LIST),
                            path_remote_mutex_unlocked=config_from_file.get('path_remote_mutex_unlocked', PATH_REMOTE_MUTEX_UNLOCKED),
                            path_remote_mutex_locked=config_from_file.get('path_remote_mutex_locked', PATH_REMOTE_MUTEX_LOCKED),
                            path_local_mutex_unlocked=config_from_file.get('path_local_mutex_unlocked', PATH_LOCAL_MUTEX_UNLOCKED),
                            local_storage_cls = LocalFileProcess,
                            remote_storage_cls=remote_storage_cls,
                            mac_process=serial_to_mac_address)


    """
    The text file located on the SFTP server contains the lines with the following format:
        Total   Serial  MAC               DateTime
        0       0000    60:36:96:08:00:00 2025-08-05 16:25:40
    We take the last line, increment the serial number, and generate a new MAC address.
    The MAC address is generated based on the OUI and device type from the credentials file.
    The new serial number and generated MAC address is put to the file and saved back to the SFTP server.
        Total   Serial  MAC               DateTime
        0       0000    60:36:96:08:00:00 2025-08-05 16:25:40
        1       0001    60:36:96:08:00:01 2025-08-05 16:25:54
    """

    if clean_mode:
        # Clean up the local and remote files
        remote_file_process.cleanup()
        print("Cleanup completed successfully.")
    if init_mode:
        # Initialize the SFTP server by creating a mutex file and a MAC list file
        remote_file_process.init()
        print("Initialization completed successfully.")
    normal_mode = not (init_mode or clean_mode)
    if normal_mode:
        remote_file_process.process_file_atomicaly()
        for i, eth_addr_var in enumerate(SAPLING_ETH_MAC_ADDR_VARS):
            _, _, mac = remote_file_process.file_data[i]
            print(f"Setting U-Boot variable '{eth_addr_var}' to MAC: {mac}")

    exit(0)
