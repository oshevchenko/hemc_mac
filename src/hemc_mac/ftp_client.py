from ftplib import FTP
from ftplib import error_perm

class FtpWrapper():
    """
    We need this to call FTP method 'quit' as 'close' to be consistent with SFTP client.
    FTP uses 'quit', but simultaneously it also has 'close' private method.
    """
    def __init__(self, client):
        self._client = client
    def get(self, sftp_path, local_path):
        self._client.get(sftp_path, local_path)
    def put(self, local_path, sftp_path):
        self._client.put(local_path, sftp_path)
    def remove(self, sftp_path):
        self._client.remove(sftp_path)
    def rename(self, old_path, new_path):
        self._client.rename(old_path, new_path)
    def close(self):
        self._client.close_()

class SaplingFTP(FTP):

    def get(self, ftp_path, local_path):
        with open(local_path, 'wb') as f:
            try:
                self.retrbinary(f'RETR {ftp_path}', f.write)
            except error_perm as e:
                if '550' in str(e):
                    # Raise FileNotFoundError if the file does not exist to be consistent with SFTP behavior
                    raise FileNotFoundError(f"File {ftp_path} not found on server.")
                else:
                    raise e


    def put(self, local_path, ftp_path):
        with open(local_path, 'rb') as f:
            self.storbinary(f'STOR {ftp_path}', f)


    def rename(self, fromname, toname):
        try:
            ret = super().rename(fromname, toname)
        except error_perm as e:
            if '550' in str(e):
                # Raise FileNotFoundError if the file does not exist to be consistent with SFTP behavior
                raise FileNotFoundError(f"File {fromname} not found on server.")
            else:
                raise e
        return ret


    def remove(self, ftp_path):
        try:
            ret = self.delete(ftp_path)
        except error_perm as e:
            if '550' in str(e):
                # Raise FileNotFoundError if the file does not exist to be consistent with SFTP behavior
                raise FileNotFoundError(f"File {ftp_path} not found on server.")
            else:
                raise e  # Re-raise if it's a different error
        return ret

    def close_(self):
        """
        FTP uses 'quit', but simultaneously it also has 'close' private method.
        Together with FtpWrapper we can call 'quit' as 'close' to be consistent with SFTP client.
        """
        return super().quit()


class FtpClient():
    _ftp_server = None
    _ftp_name = None
    _ftp_password = None
    _timeout = None
    _ftp_port = None


    @classmethod
    def init(cls,
                 server,
                 name,
                 password,
                 timeout=2,
                 port=21):
        cls._ftp_server = server
        cls._ftp_name = name
        cls._ftp_password = password
        cls._timeout = timeout
        cls._ftp_port = port


    @classmethod
    def connect(cls):
        # Connect to FTP server
        ftp = SaplingFTP()
        ftp.connect(host=cls._ftp_server, port=cls._ftp_port, timeout=cls._timeout)
        ftp.login(user=cls._ftp_name, passwd=cls._ftp_password)
        return FtpWrapper(ftp)


    @classmethod
    def disconnect(cls):
        pass
