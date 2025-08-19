import paramiko

class SftpClient():
    _transport = None
    _sftp_server = None
    _sftp_name = None
    _sftp_password = None
    _timeout = None
    _port = None

    @classmethod
    def init(cls,
                 server,
                 name,
                 password,
                 port=22,
                 timeout=2):
        cls._sftp_server = server
        cls._sftp_name = name
        cls._sftp_password = password
        cls._timeout = timeout
        cls._port = port

    @classmethod
    def connect(cls):
        cls._transport = paramiko.SSHClient()
        cls._transport.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        cls._transport.connect(cls._sftp_server,
                    username=cls._sftp_name,
                    password=cls._sftp_password,
                    port=cls._port,
                    timeout=cls._timeout)
        sftp = cls._transport.open_sftp()
        return sftp

    @classmethod
    def disconnect(cls):
        if cls._transport:
            cls._transport.close()
            cls._transport = None


