import socket
import common 
import sys
import threading

messages = []
incomingData = []
def connectionCheck(socket):
    try:
        socket.send(common.CONNECTION_CHECK)
    except: 
        print("server unavailable")
        clientSocket.close()
        sys.exit()

def parse_from_server():
    messageCounter = 0
    i = 0
    dataLength = len(incomingData[0])
    while(i < dataLength):
        byteBuffer = incomingData[0][0:1]


def read_from_server(socket):
    while(1):
        try:
            incomingData.append(socket.recv(4095))
            # if(byteData[0] == common.SOH):                  # grabing the public key
            #     serverPublicKey = byteData[1]
            # else:
            #     #byteData[-1] = b'\x00'
            #     printData = byteData[2:]
            #     printData = printData.decode('utf-8')
            #     print(printData)
            parse_from_server()
        except Exception as e:
            print(f"Error reading data: {e}")

    

print("Starting Client")
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverPublicKey = None

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

