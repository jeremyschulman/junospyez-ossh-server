import re
from io import BytesIO
import socket

DMI_MSG_FIELDS_LIST = [
    ('msg_id',      r'MSG-ID: (.*)\r\n'),
    ('dev_id',      r'DEVICE-ID: (.*)\r\n'),
    ('msg_ver',     r'MSG-VER: (.*)\r\n'),
    ('host_key',    r'HOST-KEY: (.*)\x00\r\n'),
    ('hmac',        r'HMAC: (.*)\r\n')
]

tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in DMI_MSG_FIELDS_LIST)
get_token = re.compile(tok_regex).match


def extract_dmi_fields(recv_io):

    recv_str = recv_io.getvalue().decode()

    match = get_token(recv_str)
    dmi_dict = {}

    while match is not None:
        group = match.lastgroup
        value = match.group(match.lastindex + 1)
        dmi_dict[group] = value
        match = get_token(recv_str, match.end())

    return dmi_dict


def recv_dmi_io(d_sock):

    recv_io = BytesIO()
    d_sock.settimeout(1)

    while True:
        try:
            recv_bytes = d_sock.recv(128)

        except socket.timeout:
            break

        recv_io.write(recv_bytes)

    recv_io.seek(0)
    return recv_io
