import socket
import common 
import sys
import threading

messages = [[]]
chatMessages = []
specialMessages = []
incomingData = None
class client:
    def __init__(self):
        self.serverE = None
        self.serverN = None
        self.clientE = None
        self.clientN = None
        self.socket = None
        self.socketInfo = None

me = client()

def handshake(me: client):
    msg = common.frame_message(common.MT_PT_CHAT, common.SYN)
    me.socket.send(msg)
    me.socket.settimeout(10)            # wait ten seconds for the server to respond
    connection = False  
    try:
        serverData = me.socket.recv()  
        create_message_list(serverData)
        if(any(common.ACK in packets for packets in chatMessages)):
            ## We're connected send your public key
            if(specialMessages[-1]):
                parse_message(specialMessages[-1],me)
                if me.serverE is not None and me.n is not None:
                    msg = common.frame_message(common.MT_KEY, me.clientE+me.clientN)
                    me.socket.send()
                    connection = True
                    return connection
    except me.socket.timeout:
        print("Handshake Failed. Disconnecting")
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
    msgType = message[1]
    data = []
    i = 2
    while message and message[i] != common.EOT: 
        data.append(message[i])
        i += 1
    if msgType == common.MT_PT_CHAT or msgType == common.MT_CT_CHAT:  ## TODO treating these the same for now
        chatMessages.append(data)
        chatMessages.append([])
    if msgType == common.MT_KEY:                                ## TODO dangerous if another user sends a key message | Server should block these
        specialMessages.append(data)
        specialMessages.append([])
        client.serverN = data[common.N_MSB_LOC] + data[common.N_LSB_LOC]
        client.serverN = int.from_bytes(client.serverN)
        client.serverE = data[common.E_MSB_LOC] + data[common.E_MIDDLEB_LOC] + data[common.E_LSB_LOC]
        client.serverE = int.from_bytes(client.serverE)
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

        
def print_messages(messages):
    if(messages):
        messages.pop()      # pop off the empty row
    while(messages):
        string = messages.pop()
        string = b"".join(string).decode(common.ENCODING)
        print(string)
    messages.clear()

def read_from_server(activeSocket, dataBuffer):
    while(1):
        try:
            dataBuffer = activeSocket.recv(4095) 
            create_message_list(dataBuffer)
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
if(len(sys.argv) < 3):
    print("Missing public key information. Quiting")
    sys.exit(1)
me.clientE = int(sys.argv[1]).to_bytes
me.clientN = int(sys.argv[2]).to_bytes
me.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    ## First we want to connect
    me.socket.connect((common.SERVER_IP, common.PORT))
    me.socketInfo = me.socket.getsockname
    if(handshake(me)):
        reader = threading.Thread(target=read_from_server,args=(me.socket,incomingData))
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

