import socket
import common 
import sys

print("Starting Client")
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    ## First we want to get the server up and running
    clientSocket.connect((common.SERVER_IP, common.PORT))
    socketInfo = clientSocket.getsockname
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

