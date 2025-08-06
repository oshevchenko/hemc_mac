# Tool for devices serialization
To flash the device with MAC address we take the unique serial number from the
file located on SFTP server. MAC address is generated from this serial.

## Run the tool
```
python3 ./sftp_mac.py --credentials ./credentials.txt
```
The configuration is taken from 'credentials.txt' file:
The format of the 'credentials.txt' file:
```
# Sapling SFTP configuration file
# Comments are allowed!
# Empty lines are ignored.
# Must have the following keys:
Server: 192.168.1.102
Name: sftp_hemc
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

```
Clean up the local and remote files
```
python3 ./sftp_mac.py --credentials ./credentials.txt --clean
```
Initialize the SFTP server by creating a mutex file and a MAC list file with a single line.
```
python3 ./sftp_mac.py --credentials ./credentials.txt --init
```

## Text file on SFTP server
Download the file from SFTP server, process it and upload it back.
File is processed atomically by using a separate file as a mutex.
We assume that the SFTP server supports atomic rename file operation.

The text file located on the SFTP server contains the lines with the following format:
```
Total   Serial  MAC               DateTime
0       0000    60:36:96:08:00:00 2025-08-05 16:25:40
```
We take the last line, increment the serial number, and generate a new MAC address.
The MAC address is generated based on the OUI and device type from the credentials file.
The new serial number and generated MAC address is put to the file and saved back to the SFTP server.
```
Total   Serial  MAC               DateTime
0       0000    60:36:96:08:00:00 2025-08-05 16:25:40
1       0001    60:36:96:08:00:01 2025-08-05 16:25:54
```

## Configure SFTP server

Create a dedicated group for SFTP users:
```
sudo groupadd sftpusers
```
Create a new user and add them to the sftpusers group, configuring their shell to prevent SSH login and restrict them to SFTP access:
```
sudo useradd -m -g sftpusers -s /usr/sbin/nologin sftp_hemc
sudo passwd sftp_hemc
```
Configure SSH for SFTP (sshd_config):
Edit the SSH configuration file.
```
sudo vim /etc/ssh/sshd_config
```
Ensure the SFTP Subsystem is enabled: Locate or add the line:
```
    Subsystem sftp internal-sftp
```
Create a Match block for SFTP users (especially for restricted access): Add the following at the end of the file, replacing sftpusers with your chosen group name:
```
    Match group sftpusers
        ChrootDirectory %h
        X11Forwarding no
        AllowTcpForwarding no
        ForceCommand internal-sftp
```
**ChrootDirectory %h** This jails the user to their home directory (%h), preventing them from accessing other parts of the filesystem.

**X11Forwarding no** and **AllowTcpForwarding no** These disable X11 and TCP forwarding for security.

**ForceCommand internal-sftp** This forces the user to use the internal SFTP server, preventing them from gaining a shell.


Set Permissions for Chroot Directory. The **ChrootDirectory** must be owned by root and have specific permissions to function correctly. For the user's home directory (e.g., /home/sftp_hemc):
```
sudo chown root:root /home/sftp_hemc
sudo chmod 755 /home/sftp_hemc
```
Create a subdirectory within the user's home directory for uploads, and set its ownership to the SFTP user:
```
sudo mkdir /home/sftp_hemc/uploads
sudo chown sftp_hemc:sftpusers /home/sftp_hemc/uploads
```
Restart SSH Service:

```
sudo systemctl restart ssh
```
