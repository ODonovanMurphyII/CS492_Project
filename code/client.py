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

##clientSocket.send("test" + common.END_OF_STRING)
clientSocket.close()
