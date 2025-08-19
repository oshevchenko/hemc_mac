import os
from datetime import datetime
"""
LocalFileProcess class for managing a local file that stores
the total number, serial number, and MAC address.

CRUD operations are supported:
- create: Create a new file with a single entry.
- read: Retrieve the total number, serial number, and MAC address.
- update: Save the total number, serial number, and MAC address to the file.
- delete: Remove the local file.
"""

PATH_LOCAL_HEMC_MAC_LIST = '/tmp/HEMC_MAC.txt'

class LocalFileProcess:
    def __init__(self, local_file_path=PATH_LOCAL_HEMC_MAC_LIST):
        self._local_file_path = local_file_path


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
