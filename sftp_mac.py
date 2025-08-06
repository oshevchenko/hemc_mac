import paramiko
from datetime import datetime
import argparse
import os
import time

PATH_SFTP_HEMC_MAC_LIST = 'uploads/HEMC_MAC.txt'
PATH_LOCAL_HEMC_MAC_LIST = '/tmp/HEMC_MAC.txt'
PATH_SFTP_MUTEX_UNLOCKED = 'uploads/mutex.unlocked'
PATH_SFTP_MUTEX_LOCKED = 'uploads/mutex.locked'

PATH_LOCAL_MUTEX_UNLOCKED = '/tmp/mutex.unlocked'
ATTEMPTS_GET_SERIAL_NUMBER = 5
SAPLING_MAC_OUI = "60:36:96"  # Sapling OUI
SAPLING_HEMC_DEVICE_TYPE = "10"  # Sapling HEMC device type
SAPLING_HEMC_NUM_OF_MAC = 6  # Number of MAC addresses to generate

class LocalFileProcess:
    def __init__(self, local_file_path=PATH_LOCAL_HEMC_MAC_LIST):
        self._local_file_path = local_file_path


    def read(self):
        """
        Retrieve the total number, serial number, and MAC address from the local file.
        """
        total_number, serial_number = None, None
        with open(self._local_file_path, 'r') as file:
            # Read the last line of the file
            lines = file.readlines()
            if not lines:
                raise ValueError("The MAC address file is empty.")
        last_line_words_list = lines[-1].strip().split()
        total_number_dec = last_line_words_list[0].strip()
        serial_number_dec = last_line_words_list[1].strip()
        mac = last_line_words_list[2].strip()
        # Convert the serial from string to integer
        total_number = int(total_number_dec, 10)
        serial_number = int(serial_number_dec, 16)
        return total_number, serial_number, mac


    def update(self, total_number, serial_number, mac):
        """
        Save the total number, serial number, and MAC address to the local file.
        """
        # Open the file in append mode
        with open(self._local_file_path, 'a') as file:
            # Append the new total number, serial number and current time/date to the file
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # extent total number to 7 symbols with trailing spaces
            total_number = str(total_number).ljust(7)
            serial_number = f"{serial_number:04x}"
            # extend serial number to 7 symols with trailing spaces
            serial_number = serial_number.ljust(7)
            file.write(f"{total_number} {serial_number} {mac} {current_time}\n")


    def delete(self):
        """
        Cleanup method to remove the local file.
        """
        if os.path.exists(self._local_file_path):
            os.remove(self._local_file_path)


    def create(self, total_number=0, serial_number=0, mac="00:00:00:00:00:00", header=None):
        """
        Create a dummy serial file with a single entry.
        """
        self.delete()  # Ensure the file is clean before creating
        if header is None:
            header="Total   Serial  MAC               DateTime"
        with open(self._local_file_path, 'w') as file:
            file.write(f"{header}\n")
        self.update(total_number, serial_number, mac)


class SftpFileProcess():
    def __init__(self,
                 server,
                 name,
                 password,
                 local_storage_cls,
                 mac_process=None,
                 local_file_path=PATH_LOCAL_HEMC_MAC_LIST,
                 sftp_file_path=PATH_SFTP_HEMC_MAC_LIST,
                 path_sftp_mutex_unlocked=PATH_SFTP_MUTEX_UNLOCKED,
                 path_sftp_mutex_locked=PATH_SFTP_MUTEX_LOCKED,
                 path_local_mutex_unlocked=PATH_LOCAL_MUTEX_UNLOCKED):

        self._transport = None
        self._sftp_server = server
        self._sftp_name = name
        self._sftp_password = password
        self._local_file_path = local_file_path
        self._local_storage = local_storage_cls(local_file_path=self._local_file_path)
        self._mac_process = mac_process
        self._sftp_file_path = sftp_file_path
        self._path_sftp_mutex_unlocked = path_sftp_mutex_unlocked
        self._path_sftp_mutex_locked = path_sftp_mutex_locked
        self._path_local_mutex_unlocked = path_local_mutex_unlocked


    def connect(self):
        if not self._transport:
            self._transport = paramiko.Transport((self._sftp_server, 22))
            self._transport.connect(username=self._sftp_name, password=self._sftp_password)
        return paramiko.SFTPClient.from_transport(self._transport)


    def disconnect(self):
        if self._transport:
            self._transport.close()
            self._transport = None


    def process_sftp_file_atomicaly(self):
        """
        Download the file from SFTP server, process it, and upload it back.
        This method ensures that the file is processed atomically by using a separate file as a mutex.
        We assume that the SFTP server supports atomic rename file operation.
        """
        sftp = self.connect()
        exception = None
        # LOCK MUTEX!
        for attempt in range(ATTEMPTS_GET_SERIAL_NUMBER):
            try:
                sftp.rename(self._path_sftp_mutex_unlocked, self._path_sftp_mutex_locked)
                break
            except FileNotFoundError as e:
                print(f"Attempt {attempt + 1}: {e}")
                if attempt == ATTEMPTS_GET_SERIAL_NUMBER - 1:
                    print(f"Failed to lock mutex after {ATTEMPTS_GET_SERIAL_NUMBER} attempts.")
                    raise e
            print(f"Retrying in 1 second... (Attempt {attempt + 1})")
            time.sleep(1)
        # Successfully locked the mutex, now we can proceed
        try:
            sftp.get(self._sftp_file_path, self._local_file_path)
            # At this point we have the local file with the serial number
            entry = self._local_storage.read()
            file_data = self._mac_process.generate_mac_address_list(*entry)
            for entry in file_data:
                self._local_storage.update(*entry)
            sftp.put(self._local_file_path, self._sftp_file_path)
        except Exception as e:
            exception = e
        finally:
            # Always UNLOCK MUTEX!
            sftp.rename(self._path_sftp_mutex_locked, self._path_sftp_mutex_unlocked)
            sftp.close()
            self.disconnect()
            if exception:
                print(f"Error while processing {self._local_file_path}: {exception}")
                raise exception


    def cleanup(self):
        """
        Cleanup method to remove all files on SFTP server.
        Also removes the local mutex file if it exists.
        """
        self._local_storage.delete()

        if os.path.exists(self._path_local_mutex_unlocked):
            os.remove(self._path_local_mutex_unlocked)

        sftp = self.connect()
        try:
            sftp.remove(self._path_sftp_mutex_unlocked)
        except FileNotFoundError:
            pass
        try:
            sftp.remove(self._path_sftp_mutex_locked)
        except FileNotFoundError:
            pass
        try:
            sftp.remove(self._sftp_file_path)
        except FileNotFoundError:
            pass
        sftp.close()
        self.disconnect()


    def init(self):
        """
        Create mutex on SFTP server.
        Copy the local file to SFTP server (must be created beforehand).
        """
        if os.path.exists(self._path_local_mutex_unlocked):
            os.remove(self._path_local_mutex_unlocked)
        with open(self._path_local_mutex_unlocked, 'w') as f:
            f.write("sftp mutex!\n")
        sftp = self.connect()
        sftp.put(self._path_local_mutex_unlocked, self._path_sftp_mutex_unlocked)
        mac = self._mac_process.serial_to_mac(0)
        self._local_storage.create(mac=mac)  # Create the initial MAC list file on local storage
        sftp.put(self._local_file_path, self._sftp_file_path)
        sftp.close()
        self.disconnect()
        os.remove(self._path_local_mutex_unlocked)


class SerialToMacAddress():
    """
    This class is used to manage the conversion of serial numbers to MAC addresses.
    """
    def __init__(self, oui=SAPLING_MAC_OUI, device_type=SAPLING_HEMC_DEVICE_TYPE, num_of_macs=SAPLING_HEMC_NUM_OF_MAC):
        """
        Initialize the SerialToMacAddress class with OUI, device type, and local file path.
        """
        if len(oui.split(':')) != 3:
            raise ValueError("OUI must be in the format 'XX:XX:XX'.")
        self._oui = oui
        self._device_type = device_type
        self._num_of_macs = num_of_macs


    def serial_to_mac(self, serial_number):
        """
        Create a new MAC address based on the OUI and device type.
        If a local file path is provided, it will be used to save the MAC address.
        """
        # get the upper 8 bits of the serial number
        serial_number_high = serial_number >> 8
        serial_number_high &= 0xFF
        # get the lower 8 bits of the serial number
        serial_number_low = serial_number & 0xFF
        mac = f"{self._oui}:{self._device_type}:{serial_number_high:02x}:{serial_number_low:02x}"
        return mac


    def generate_mac_address_list(self, total_number, serial_number, mac="00:00:00:00:00:00"):
        """
        Generate a MAC address based on the serial number.
        """
        file_data = []
        # print(f"self._num_of_macs: {self._num_of_macs}")
        for _ in range(self._num_of_macs):
            total_number += 1
            serial_number += 1
            mac = self.serial_to_mac(serial_number)
            file_data.append((total_number, serial_number, mac))
        """
        ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        TODO: Add functionality to set Ethernet MAC address on the devices.
        ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        """
        return file_data



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
    must_have_list_of_keys = ['server', 'name', 'password']
    try:
        """
        Example of credentials file:
            # Sapling SFTP configuration file
            # Comments are allowed!
            # Empty lines are ignored.
            # Must have the following keys:
            Server: 192.168.1.102
            Name: *****
            Password: *********
            # Optional keys
            OUI: 60:36:96
            DEVICE_TYPE: 10
            NUM_OF_MAC: 6
            PATH_LOCAL_HEMC_MAC_LIST: /tmp/HEMC_MAC.txt
            PATH_SFTP_HEMC_MAC_LIST: uploads/HEMC_MAC.txt
            PATH_SFTP_MUTEX_UNLOCKED: uploads/mutex.unlocked
            PATH_SFTP_MUTEX_LOCKED: uploads/mutex.locked
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

    serial_to_mac_address = SerialToMacAddress(
                            oui = config_from_file.get('oui', SAPLING_MAC_OUI),
                            device_type = config_from_file.get('device_type', SAPLING_HEMC_DEVICE_TYPE),
                            num_of_macs= int(config_from_file.get('num_of_mac', SAPLING_HEMC_NUM_OF_MAC)))

    sftp_file_process = SftpFileProcess(
                            server=config_from_file['server'],
                            name=config_from_file['name'],
                            password=config_from_file['password'],
                            local_file_path=config_from_file.get('path_local_hemc_mac_list', PATH_LOCAL_HEMC_MAC_LIST),
                            sftp_file_path=config_from_file.get('path_sftp_hemc_mac_list', PATH_SFTP_HEMC_MAC_LIST),
                            path_sftp_mutex_unlocked=config_from_file.get('path_sftp_mutex_unlocked', PATH_SFTP_MUTEX_UNLOCKED),
                            path_sftp_mutex_locked=config_from_file.get('path_sftp_mutex_locked', PATH_SFTP_MUTEX_LOCKED),
                            path_local_mutex_unlocked=config_from_file.get('path_local_mutex_unlocked', PATH_LOCAL_MUTEX_UNLOCKED),
                            local_storage_cls = LocalFileProcess,
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
        sftp_file_process.cleanup()
        print("Cleanup completed successfully.")
    if init_mode:
        # Initialize the SFTP server by creating a mutex file and a MAC list file
        sftp_file_process.init()
        print("Initialization completed successfully.")
    normal_mode = not (init_mode or clean_mode)
    if normal_mode:
        sftp_file_process.process_sftp_file_atomicaly()

    exit(0)
