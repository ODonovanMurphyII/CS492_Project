import socket
import common 
import sys
import threading

def connectionCheck(socket):
    try:
        socket.send(common.CONNECTION_CHECK)
    except: 
        print("server unavailable")
        clientSocket.close()
        sys.exit()

def read_from_server(socket):
    while(1):
        try:
            data = socket.recv(4095)
            data = data.decode('utf-8')
            print(data)
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
    data = input(":")
    data = data.encode('utf-8')
    if(data == common.EXIT):
        print("Quitting")
        clientSocket.send(data)
        clientSocket.close()
    clientSocket.send(data)

