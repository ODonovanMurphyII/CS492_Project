import socket
import common 
import sys
import threading

messages = [[]]
chatMessages = []
specialMessages = []
incomingData = []
class client:
    def __init__(self):
        self.e = None
        self.n = None
        self.activeSocket = None
        self.socketInfo = None

me = client()

def connectionCheck(activeSocket):
    try:
        activeSocket.send(common.CONNECTION_CHECK)
    except: 
        print("server unavailable")
        activeSocket.shutdown(socket.SHUT_RDWR)
        activeSocket.close()
        sys.exit()

def parse_message(message, client=me):     ## TODO crude. needs error handling
    msgType = message[1]
    data = []
    i = 2
    while message and message[i] != common.EOT: 
        data.append(message[i])
        i += 1
    if msgType == common.MT_PT_CHAT:
        chatMessages.append(data)
        chatMessages.append([])
    if msgType == common.MT_KEY:
        specialMessages.append(data)
        specialMessages.append([])
        client.n = data[common.N_MSB_LOC] + data[common.N_LSB_LOC]
        client.n = int.from_bytes(client.n)
        client.e = data[common.E_MSB_LOC] + data[common.E_MIDDLEB_LOC] + data[common.E_LSB_LOC]
        client.e = int.from_bytes(client.e)
   

def create_message_list():
    i = 0
    messageCounter = 0
    dataLength = len(incomingData[0])

    ## Saving all of my messages
    while(i < dataLength):
        byteBuffer = incomingData[0][i:i+1]
        messages[messageCounter].append(byteBuffer)
        i += 1
        if(byteBuffer == common.EOT):
            messages.append([])
            messageCounter += 1
    incomingData.clear()
    incomingData.append([])
    i = 0
    while(i < len(messages)-1):
        parse_message(messages[i])
        i += 1
    messages.clear()

        
def print_messages(messages):
    if(messages):
        messages.pop()      # pop off the empty row
    while(messages):
        string = messages.pop()
        string = b"".join(string).decode(common.ENCODING)
        print(string)
    messages.clear()

def read_from_server(activeSocket):
    while(1):
        try:
            incomingData.append(activeSocket.recv(4095))
            create_message_list()
            print_messages(chatMessages)
        except Exception as e:
            print(f"Error reading data: {e} quitting")
            activeSocket.shutdown(socket.SHUT_RDWR)
            activeSocket.close()
            sys.exit()

## Can't go any larger than 2 byte blocks for now
def encrypt(data, client=me):
    i = 0
    plaintextBlocks = []
    ciphertextBlocks = []
    if not client.e or not client.n:
        print("Handshake Failed | Sending Plaintext")
        return data                                    ## TODO come here and setup proper framming
    else:
        buffer = None
        for i in range(0, len(data), 2):
            plaintextBlocks.append(data[i:i+2])
            buffer = int.from_bytes(plaintextBlocks[-1], 'big')
            buffer = pow(buffer, client.e, client.n)
            ciphertextBlocks.append(buffer.to_bytes(2, 'big'))
        ciphertextBlocks = b"".join(ciphertextBlocks)
        return ciphertextBlocks
    

print("Starting Client")
me.activeSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    ## First we want to connect
    me.activeSocket.connect((common.SERVER_IP, common.PORT))
    me.socketInfo = me.activeSocket.getsockname
    reader = threading.Thread(target=read_from_server,args=(me.activeSocket,))
    reader.daemon = True
    reader.start()
except Exception as e:
    print(f"Could not connect to server! Exeption:{e} | Shutting down!")
    me.activeSocket.shutdown(socket.SHUT_RDWR)
    me.activeSocket.close()
    sys.exit()

while(1):
    data = input("")
    data = data.encode(common.ENCODING)
    if(data == common.EXIT):
        me.activeSocket.send(data)
        print("Quitting")
        me.activeSocket.shutdown(socket.SHUT_RDWR)
        me.activeSocket.close()  
        sys.exit()
    data = encrypt(data)  
    me.activeSocket.send(data)

