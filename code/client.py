import socket
import common 
import sys
import threading

messages = [[]]
chatMessages = []
specialMessages = []
incomingData = []
serverPublicKey = None
def connectionCheck(socket):
    try:
        socket.send(common.CONNECTION_CHECK)
    except: 
        print("server unavailable")
        clientSocket.close()
        sys.exit()

def parse_message(message):     ## TODO crude. needs error handling
    msgType = message[1]
    data = []
    i = 2
    while message and message[i] != common.EOT:
        data.append(message[i])
        i += 1
    if msgType == common.MT_CHAT:
        chatMessages.append(data)
    if msgType == common.MT_KEY:
        chatMessages.append(specialMessages)
        serverPublicKey = data

def create_message_list():
    i = 0
    messageCounter = 0
    dataLength = len(incomingData[0])

    ## Saving all of my messages
    while(i <= dataLength):
        byteBuffer = incomingData[0][i:i+1]
        messages[messageCounter].append([byteBuffer])
        i += 1
        if(byteBuffer == common.EOT):
            messages.append([])
            messageCounter += 1
    incomingData.clear()
    i = 0
    while(i <= len(messages)):
        parse_message(messages[0])
        messages.clear()

        


def read_from_server(socket):
    while(1):
        try:
            incomingData.append(socket.recv(4095))
            create_message_list()
            messages
        except Exception as e:
            print(f"Error reading data: {e}")

    

print("Starting Client")
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    ## First we want to connect
    clientSocket.connect((common.SERVER_IP, common.PORT))
    socketInfo = clientSocket.getsockname
    reader = threading.Thread(target=read_from_server,args=(clientSocket,))
    reader.daemon = True
    reader.start()
    #heartBeat = threading.Thread(connectionCheck)
    #heartBeat.daemon = True
    #heartBeat.start = True
except Exception as e:
    print(f"Could not connect to server! Exeption:{e} | Shutting down!")
    clientSocket.close()
    sys.exit()

while(1):
    data = input("")
    data = data.encode('utf-8')
    if(data == common.EXIT):
        print("Quitting")
        clientSocket.send(data)
        clientSocket.close()
    clientSocket.send(data)

