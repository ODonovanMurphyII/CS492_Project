import socket 
import sys
import common
import threading
import key

## Eventually I will make a client class...for now
clientSockets = []
clientListeners = []
clientAddresses = []

class server_information:
    def __init__(self):
        self.public_key = None
        self.clientCount = None


def server_init(serverInfo: server_information, keyManager: key.key_manager):
    print("Starting Server")
    serverInfo.public_key = keyManager.generate_public_key()
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

def receiver(socket, address, users):
    while(1):
        data = socket.recv(4095)
        data = data.decode(common.ENCODING)
        username = "USER" + str(address[1]) 
        print(username + ":" + data)
        data = username + ":" + data
        data = data.encode(common.ENCODING) 
        for user in users:
            if (user != socket):
                user.send(data)

def connection_handler(sockets, addresses, listeners, serverSocket, serverInfo: server_information):
    while(1):
        newConnection, newAddress = serverSocket.accept()
        clientSockets.append(newConnection)
        clientAddresses.append(newAddress)
        username = "Client" + str(clientAddresses[-1][1])
        print(username + " Joined!")
        welcomeMsg = "Welcome to the Chatroom " + username + '!'
        newConnection.send(common.frame_message(common.MT_PT_CHAT,welcomeMsg))
        publicKeyMsg = common.frame_message(common.MT_KEY,serverInfo.public_key)
        newConnection.send(publicKeyMsg)
        threading.Thread(target=receiver, args=(clientSockets[-1], clientAddresses[-1], clientSockets), daemon=True).start()


serverInfo = server_information()
keyManager = key.key_manager()
serverSocket = server_init(serverInfo, keyManager)
thread_connection_handler = threading.Thread(connection_handler(clientSockets, clientAddresses, clientListeners, serverSocket, serverInfo))
thread_connection_handler.daemon = True
thread_connection_handler.start()





