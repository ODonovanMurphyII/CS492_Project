SERVER_IP = '127.0.0.1' 
PORT = 12345
END_OF_STRING = '\n'
EXIT = b'\x18'
CONNECTION_CHECK = b'\x00'
CLEAR_TERMINAL = b'\x01\x1b\x5b\x32\x4b'
SOH = b'\x01'
EOT = b'\x04' 
MT_CHAT = b'\x00'
MT_KEY = b'\x05'
KEY_LOCATION = 2

def frame_message(messageType: bytes, data):
    bytes = []
    if isinstance(data, str):
        data = data.encode('utf-8')
        message = SOH + messageType + data + EOT
    else:
        message = [SOH, messageType, data, EOT]
        message = b"".join(message)
    return message 


