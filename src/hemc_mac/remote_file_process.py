import paramiko
from .local_file_process import LocalFileProcess, PATH_LOCAL_HEMC_MAC_LIST
from .serial_to_mac import SerialToMacAddress, SAPLING_MAC_OUI, SAPLING_HEMC_DEVICE_TYPE, SAPLING_HEMC_NUM_OF_MAC
import argparse
import os
import time
import logging

PATH_REMOTE_HEMC_MAC_LIST = 'uploads/HEMC_MAC.txt'
PATH_REMOTE_MUTEX_UNLOCKED = 'uploads/mutex.unlocked'
PATH_REMOTE_MUTEX_LOCKED = 'uploads/mutex.locked'
PATH_LOCAL_MUTEX_UNLOCKED = '/tmp/mutex.unlocked'
ATTEMPTS_GET_SERIAL_NUMBER = 5

logger = logging.getLogger(__name__.split('.')[0])

class RemoteFileProcess():
    def __init__(self,
                 local_storage_cls,
                 remote_storage_cls,
                 mac_process=None,
                 local_file_path=PATH_LOCAL_HEMC_MAC_LIST,
                 remote_file_path=PATH_REMOTE_HEMC_MAC_LIST,
                 path_remote_mutex_unlocked=PATH_REMOTE_MUTEX_UNLOCKED,
                 path_remote_mutex_locked=PATH_REMOTE_MUTEX_LOCKED,
                 path_local_mutex_unlocked=PATH_LOCAL_MUTEX_UNLOCKED):

        self._local_file_path = local_file_path
        self._remote_storage_cls = remote_storage_cls
        self._local_storage = local_storage_cls(local_file_path=self._local_file_path)
        self._mac_process = mac_process
        self._remote_file_path = remote_file_path
        self._path_remote_mutex_unlocked = path_remote_mutex_unlocked
        self._path_remote_mutex_locked = path_remote_mutex_locked
        self._path_local_mutex_unlocked = path_local_mutex_unlocked
        self.file_data = []


    def process_file_atomicaly(self):
        """
        Download the file from SFTP server, process it, and upload it back.
        This method ensures that the file is processed atomically by using a separate file as a mutex.
        We assume that the SFTP server supports atomic rename file operation.
        """
        h_remote = self._remote_storage_cls.connect()
        exception = None
        # LOCK MUTEX!
        for attempt in range(ATTEMPTS_GET_SERIAL_NUMBER):
            try:
                h_remote.rename(self._path_remote_mutex_unlocked, self._path_remote_mutex_locked)
                break
            except FileNotFoundError as e:
                logger.error(f"Attempt {attempt + 1}: {e}")
                if attempt == ATTEMPTS_GET_SERIAL_NUMBER - 1:
                    logger.error(f"Failed to lock mutex after {ATTEMPTS_GET_SERIAL_NUMBER} attempts.")
                    raise e
            logger.error(f"Retrying in 1 second... (Attempt {attempt + 1})")
            time.sleep(1)
        # Successfully locked the mutex, now we can proceed
        try:
            h_remote.get(self._remote_file_path, self._local_file_path)
            # At this point we have the local file with the serial number
            entry = self._local_storage.read()
            self.file_data = self._mac_process.generate_mac_address_list(*entry)
            for entry in self.file_data:
                self._local_storage.update(*entry)
            h_remote.put(self._local_file_path, self._remote_file_path)
        except Exception as e:
            exception = e
        finally:
            # Always UNLOCK MUTEX!
            h_remote.rename(self._path_remote_mutex_locked, self._path_remote_mutex_unlocked)
            h_remote.close()
            self._remote_storage_cls.disconnect()
            if exception:
                logger.error(f"Error while processing {self._local_file_path}: {exception}")
                raise exception
        return self.file_data


    def cleanup(self):
        """
        Cleanup method to remove all files on SFTP server.
        Also removes the local mutex file if it exists.
        """
        self._local_storage.delete()

        if os.path.exists(self._path_local_mutex_unlocked):
            os.remove(self._path_local_mutex_unlocked)

        h_remote = self._remote_storage_cls.connect()
        try:
            h_remote.remove(self._path_remote_mutex_unlocked)
        except FileNotFoundError:
            pass
        try:
            h_remote.remove(self._path_remote_mutex_locked)
        except FileNotFoundError:
            pass
        try:
            h_remote.remove(self._remote_file_path)
        except FileNotFoundError:
            pass
        h_remote.close()
        self._remote_storage_cls.disconnect()


    def init(self):
        """
        Create mutex on SFTP server.
        Copy the local file to SFTP server (must be created beforehand).
        """
        if os.path.exists(self._path_local_mutex_unlocked):
            os.remove(self._path_local_mutex_unlocked)
        with open(self._path_local_mutex_unlocked, 'w') as f:
            f.write("h_remote mutex!\n")
        h_remote = self._remote_storage_cls.connect()
        h_remote.put(self._path_local_mutex_unlocked, self._path_remote_mutex_unlocked)
        mac = self._mac_process.serial_to_mac(0)
        self._local_storage.create(mac=mac)  # Create the initial MAC list file on local storage
        h_remote.put(self._local_file_path, self._remote_file_path)
        h_remote.close()
        self._remote_storage_cls.disconnect()
        os.remove(self._path_local_mutex_unlocked)
