import socket
import common 
import sys
import threading
import math

messages = [[]]
plaintextMessages = []
cipherTextMessages = []
specialMessages = []
incomingData = None
class client:
    def __init__(self):
        self.serverE = None
        self.serverN = None
        self.clientE = None
        self.clientN = None
        self.clientD = None
        self.clientEBytes = None
        self.clientNBytes = None
        self.socket = None
        self.socketInfo = None

me = client()

def handshake(me: client):
    msg = common.frame_message(common.MT_PT_CHAT, common.SYN)
    me.socket.send(msg)
    me.socket.settimeout(common.SOCKET_TIMEOUT)            
    connection = False  
    try:
        serverData = me.socket.recv(common.RECEIVE_LEN)  
        create_message_list(serverData)
        if(any(common.ACK in packets for packets in plaintextMessages)):
            ## We're connected send your public key
            if(specialMessages[-1] is not None):
                if me.serverE is not None and me.serverN is not None:
                    me.clientEBytes = me.clientE.to_bytes(2, 'big')
                    me.clientNBytes = me.clientN.to_bytes(2, 'big')
                    msg = common.frame_message(common.MT_KEY, me.clientEBytes + me.clientNBytes)
                    me.socket.send(msg)
                    connection = True
                    return connection
    except Exception as e:
        print(f"Handshake Failed: {e}. Disconnecting")
        me.socket.shutdown(socket.SHUT_RDWR)
        me.socket.close()
        sys.exit()
  

def connectionCheck(activeSocket):
    try:
        activeSocket.send(common.CONNECTION_CHECK)
    except: 
        print("server unavailable")
        activeSocket.shutdown(socket.SHUT_RDWR)
        activeSocket.close()
        sys.exit()

def parse_message(message, client=me):     ## TODO crude. needs error handling
    msgType = message[2]
    message = b''.join(message)
    data = bytearray()
    data = common.unframe_message(message)
    if msgType == common.MT_PT_CHAT:
        plaintextMessages.append(data)
        plaintextMessages.append([])
    elif msgType == common.MT_CT_CHAT:
        cipherTextMessages.append(data)
        cipherTextMessages.append([])
    elif msgType == common.MT_KEY:                                ## TODO dangerous if another user sends a key message | Server should block these
        specialMessages.append(data)
        client.serverN = data[common.N_MSB_LOC] + data[common.N_LSB_LOC]
        client.serverN = int.from_bytes(client.serverN)
        client.serverE = data[common.E_MSB_LOC] + data[common.E_MIDDLEB_LOC] + data[common.E_LSB_LOC]
        client.serverE = int.from_bytes(client.serverE)
        specialMessages.append([])
    else:
        print("Bad packet")
   

def create_message_list(incomingData):
    i = 0
    messageCounter = 0
    dataLength = len(incomingData)

    ## Saving all of my messages
    while(i < dataLength):
        byteBuffer = incomingData[i:i+1]
        messages[messageCounter].append(byteBuffer)
        i += 1
        if(byteBuffer == common.EOT):
            messages.append([])
            messageCounter += 1
    incomingData = None
    i = 0
    while(i < len(messages)-1):
        parse_message(messages[i])
        i += 1
    messages.clear()
    messages.append([])

def decrypt(me: client, data):
    d = me.clientD
    n = me.clientN
    cipherTextBlocks = []
    plainTextBlocks = []
    buffer = None
    data = b''.join(data)
    for i in range(0, len(data), 2):
        cipherTextBlocks.append(data[i:i+2])
        buffer = int.from_bytes(cipherTextBlocks[-1], 'big')
        buffer = pow(buffer, d, n)
        plainTextBlocks.append(buffer.to_bytes(2, 'big'))
    return plainTextBlocks
        
def print_messages(messages, me:client, cipherText):
    if(messages):
        messages.pop()      # pop off the empty row
    while(messages):
        string = messages.pop()
        if cipherText:
            string = decrypt(me, string)
        string = b"".join(string).decode(common.ENCODING)
        print(string)
    messages.clear()


def read_from_server(me:client, dataBuffer):
    while(1):
        try:
            dataBuffer = me.socket.recv(4095) 
            create_message_list(dataBuffer)
            print_messages(plaintextMessages, me, False)
            print_messages(cipherTextMessages, me, True)
        except Exception as e:
            print(f"Error reading data: {e} quitting")
            me.socket.shutdown(socket.SHUT_RDWR)
            me.socket.close()
            sys.exit()

## Can't go any larger than 2 byte blocks for now
def encrypt(data, client=me):
    i = 0
    plaintextBlocks = []
    ciphertextBlocks = []
    if not client.serverE or not client.serverN:
        print("Handshake Failed | Sending Plaintext")
        return data                                    ## TODO come here and setup proper framming
    else:
        buffer = None
        for i in range(0, len(data), 2):
            plaintextBlocks.append(data[i:i+2])
            buffer = int.from_bytes(plaintextBlocks[-1], 'big')
            buffer = pow(buffer, client.serverE, client.serverN)
            ciphertextBlocks.append(buffer.to_bytes(2, 'big'))
        ciphertextBlocks = b"".join(ciphertextBlocks)
        return ciphertextBlocks
    

print("Starting Client")
print("Demo limited to 16-bit key values")
primeP = int(input("Please enter a prime number between 181 and 251:"))
primeQ = int(input("Please enter a prime number between 181 and 251 not equal to the first entered prime:"))
print("Generating Public and Private Keys....")
me.clientN = primeP * primeQ
phi = (primeP-1)*(primeQ-1)
possibleE = 3
while math.gcd(possibleE,phi) != 1:
    possibleE += 2
me.clientE = possibleE
me.clientD = pow(me.clientE,-1,phi)

me.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    ## First we want to connect
    me.socket.connect((common.SERVER_IP, common.PORT))
    me.socketInfo = me.socket.getsockname
    if(handshake(me)):
        me.socket.settimeout(None)
        reader = threading.Thread(target=read_from_server,args=(me,incomingData))
        reader.daemon = True
        reader.start()
    else:
        print("Handshake failed. Quitting")
        sys.exit()
except Exception as e:
    print(f"Could not connect to server! Exeption:{e} | Shutting down!")
    me.socket.shutdown(socket.SHUT_RDWR)
    me.socket.close()
    sys.exit()

while(1):
    data = input("")
    data = data.encode(common.ENCODING)
    if(data == common.EXIT):
        me.socket.send(data)
        print("Quitting")
        me.socket.shutdown(socket.SHUT_RDWR)
        me.socket.close()  
        sys.exit()
    data = encrypt(data) 
    data = common.frame_message(common.MT_CT_CHAT, data)
    me.socket.send(data)

