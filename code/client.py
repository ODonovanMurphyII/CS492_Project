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

me = client()

def connectionCheck(socket):
    try:
        socket.send(common.CONNECTION_CHECK)
    except: 
        print("server unavailable")
        clientSocket.close()
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
    messages.pop()      # pop off the empty row
    while(messages):
        string = messages.pop()
        string = b"".join(string).decode(common.ENCODING)
        print(string)
    messages.clear()

def read_from_server(socket):
    while(1):
        try:
            incomingData.append(socket.recv(4095))
            create_message_list()
            print_messages(chatMessages)
        except Exception as e:
            print(f"Error reading data: {e}")

## Can't go any larger than 2 byte blocks for now
def encrypt(data, client=me):
    i = 0
    plaintextBlocks = []
    ciphertextBlocks = []
    buffer = None
    for i in range(0, len(data), 2):
        plaintextBlocks.append(data[i:i+2])
        buffer = int.from_bytes(plaintextBlocks[-1], 'big')
        buffer = pow(buffer, client.e, client.n)
        ciphertextBlocks.append(buffer.to_bytes(2, 'big'))
    return ciphertextBlocks
    

print("Starting Client")
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    ## First we want to connect
    clientSocket.connect((common.SERVER_IP, common.PORT))
    socketInfo = clientSocket.getsockname
    reader = threading.Thread(target=read_from_server,args=(clientSocket,))
    reader.daemon = True
    reader.start()
except Exception as e:
    print(f"Could not connect to server! Exeption:{e} | Shutting down!")
    clientSocket.close()
    sys.exit()

while(1):
    data = input("")
    data = data.encode(common.ENCODING)
    if(data == common.EXIT):
        print("Quitting")
        clientSocket.send(data)
        clientSocket.close()  
    data = encrypt(data)  
    data = b"".join(data)
    clientSocket.send(data)

