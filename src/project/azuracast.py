import os

import paramiko


def get_current_user():
    for name in ("LOGNAME", "USER", "LNAME", "USERNAME"):
        user = os.environ.get(name)
        if user:
            return user


def connect_azura_sftp(host: str, port: int, username: str, password: str | None):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, password=password)
    sftp = ssh.open_sftp()
    return sftp
