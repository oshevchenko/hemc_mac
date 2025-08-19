SAPLING_MAC_OUI = "60:36:96"  # Sapling OUI
SAPLING_HEMC_DEVICE_TYPE = "10"  # Sapling HEMC device type
SAPLING_HEMC_NUM_OF_MAC = 6  # Number of MAC addresses to generate


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

