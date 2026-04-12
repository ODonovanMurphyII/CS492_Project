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
        self.privateKey = None
        self.clientCount = None

def decrypt(data, serverInfo: server_information):
    d, n = serverInfo.privateKey
    cipherTextBlocks = []
    plainTextBlocks = []
    buffer = None
    for i in range(0, len(data), 2):
        cipherTextBlocks.append(data[i:i+2])
        buffer = int.from_bytes(cipherTextBlocks[-1], 'big')
        buffer = pow(buffer, d, n)
        plainTextBlocks.append(buffer.to_bytes(2, 'big'))
    return plainTextBlocks

def server_init(serverInfo: server_information, keyManager: key.key_manager):
    print("Starting Server")
    serverInfo.public_key = keyManager.generate_public_key()
    serverInfo.privateKey = keyManager.generate_private_key()
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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

def receiver(socket, address, users, serverInfo: server_information):
    while(1):
        try:
            ## Server output (Raw)
            rawData = socket.recv(4095)
            if rawData:
                rawData = rawData.decode(common.ENCODING)
                username = "USER" + str(address[1]) 
                print(username + "(RAW):" + rawData)           

                ## Sending raw data to everyone
                broadcast = username + ":" + rawData
                broadcast = rawData.encode(common.ENCODING) 
                for user in users:
                    if (user != socket):
                        user.send(broadcast)

                ## Decrypting 
                rawData = rawData.encode(common.ENCODING)
                plaintext = decrypt(rawData,serverInfo)
                plaintext = b"".join(plaintext)
                plaintext = plaintext.decode(common.ENCODING)
                print(username + "(Plaintext):" + plaintext)
        except Exception as e:
            print(f"Server Error: {e}")
            socket.close()
            sys.exit()

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
        threading.Thread(target=receiver, args=(clientSockets[-1], clientAddresses[-1], clientSockets, serverInfo), daemon=True).start()


serverInfo = server_information()
keyManager = key.key_manager()
serverSocket = server_init(serverInfo, keyManager)
thread_connection_handler = threading.Thread(connection_handler(clientSockets, clientAddresses, clientListeners, serverSocket, serverInfo))
thread_connection_handler.daemon = True
thread_connection_handler.start()





