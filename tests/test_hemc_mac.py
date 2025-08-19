import threading
import os
import sys
import unittest
from unittest.mock import Mock
import logging
from dataclasses import dataclass, field

# Force insert the path to the beginning of sys.path
# to use the local package instead of the installed package.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from hemc_mac import SerialToMacAddress

"""
To run this test, run the following commands:
make venv
source ./venv/bin/activate
python3 tests/test_hemc_mac.py

To run all unittests from the root directory, run the following command:
make test

To install the package locally, run the following command:
make install
"""

# @dataclass
# class BigHemcMessage(HemcMessage):
#     payload: dict = field(default_factory=dict)

class TestHemcMac(unittest.TestCase):
    def test_send_wait_reply(self):
            serial_to_mac_address = SerialToMacAddress(
                                    oui = "60:36:96",
                                    device_type = "10",
                                    num_of_macs= 5)

            file_data = serial_to_mac_address.generate_mac_address_list(0, 0)
            # Assert file_data 
            expected_data = [
                (1, 1, '60:36:96:10:00:01'),
                (2, 2, '60:36:96:10:00:02'),
                (3, 3, '60:36:96:10:00:03'),
                (4, 4, '60:36:96:10:00:04'),
                (5, 5, '60:36:96:10:00:05')
            ]
            self.assertEqual(file_data, expected_data)
            # print(file_data)

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger('test_hemc_mac')

    unittest.main()
