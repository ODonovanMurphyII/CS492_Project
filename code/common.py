SERVER_IP = '127.0.0.1' 
RECEIVE_LEN = 4095
PORT = 12345
END_OF_STRING = '\n'
EXIT = b'\x18'
CONNECTION_CHECK = b'\x00'
CLEAR_TERMINAL = b'\x01\x1b\x5b\x32\x4b'
SYN = b'\x16'
ACK = b'\x06'
SOH = b'\x01'
EOT = b'\x04' 
MT_PT_CHAT = b'\x00'
MT_CT_CHAT = b'\x02'
MT_KEY = b'\x05'
KEY_LOCATION = 0
N_MSB_LOC = 0
N_LSB_LOC = 1
E_MSB_LOC = 2
E_MIDDLEB_LOC = 3
E_LSB_LOC = 4
ENCODING = 'latin-1'
SOCKET_TIMEOUT = 600

def frame_message(messageType: bytes, data):
    if isinstance(data, str):
        data = data.encode('utf-8')
        message = SOH + messageType + data + EOT
    else:
        bytes = [data[i:i+1] for i in range(len(data))]
        message = []
        message.append(SOH)
        message.append(messageType)
        i = 0
        while(i < len(bytes)):
            message.append(bytes[i])
            i += 1
        message.append(EOT)
        message = b"".join(message)
    return message 




