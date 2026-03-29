import socket 
import sys
import common
import threading

## Eventually I will make a client class...for now
clientSockets = []
clientListeners = []
clientAddresses = []



def server_init():
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
    print("Server running")
    return serverSocket

def receiver(socket, address):
    while(1):
        data = socket.recv(4095)
        if (data != common.CONNECTION_CHECK):
            data = data.decode('utf-8')
            print("USER" + str(address[1]) + ": " + data)

def connection_handler(sockets, addresses, listeners, serverSocket):
    while(1):
        newConnection, newAddress = serverSocket.accept()
        clientSockets.append(newConnection)
        clientAddresses.append(newAddress)
        print("Client" + str(clientAddresses[-1][1]) + " Joined!")
        # listeners.append(threading.Thread(receiver(clientSockets[-1], clientAddresses[-1])))
        # listeners[-1].daemon = True
        # #listeners[-1].start





serverSocket = server_init()
thread_connection_handler = threading.Thread(connection_handler(clientSockets, clientAddresses, clientListeners, serverSocket))
thread_connection_handler.daemon = True
thread_connection_handler.start()




# while(1):
#     data = newConnection.recv(4095)
#     if(data == common.EXIT):
#         print("Client Quit")
#         newConnection.close()
#         break
#     else:
#         print(data)
# serverSocket.close()
