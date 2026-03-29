import socket 
import sys
import common

print("Starting Server")
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


try:
    ## First we want to get the server up and running
    serverSocket.bind((common.SERVER_IP, common.PORT))
    serverSocket.listen()
except Exception as e:
    print(f"Could not start server! Exeption:{e} | Shutting down!")
    serverSocket.close()
    sys.exit()

clientSockets = []
clientAddresses = []
print("Server running")
print("Waiting for client")
newConnection, newAddress = serverSocket.accept()
clientSockets.append(newConnection)
clientAddresses.append(newAddress)
print("Client Joined!")
data = newConnection.recv(4095)
print(data)
serverSocket.close()
