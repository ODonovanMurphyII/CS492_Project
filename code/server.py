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

clients = []
print("Server running")
print("Waiting for client")
clients.append(serverSocket.accept())
print("Client Joined!")
serverSocket.close()
