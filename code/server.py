import socket 
import sys
import common
import threading
import key

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

def receiver(socket, address, users):
    while(1):
        data = socket.recv(4095)
        data = data.decode('utf-8')
        username = "USER" + str(address[1]) 
        print(username + ":" + data)
        data = username + ":" + data
        data = data.encode('utf-8') 
        for user in users:
            if (user != socket):
                user.send(data)

def connection_handler(sockets, addresses, listeners, serverSocket):
    while(1):
        newConnection, newAddress = serverSocket.accept()
        clientSockets.append(newConnection)
        clientAddresses.append(newAddress)
        username = "Client" + str(clientAddresses[-1][1])
        print(username + " Joined!")
        welcomeMsg = "Welcome to the Chatroom " + username + '!'
        newConnection.send(common.frame_message(common.MT_CHAT,welcomeMsg))
        keyMesssage = key.publicKey + common.CLEAR_TERMINAL
        newConnection.send(common.frame_message(common.MT_KEY, keyMesssage))
        threading.Thread(target=receiver, args=(clientSockets[-1], clientAddresses[-1], clientSockets), daemon=True).start()
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
