import socket 
import sys
import common
import threading
import key

## TODO delete these
clientSockets = []
clientListeners = []
clientAddresses = []

class server_information:
    def __init__(self):
        self.publicKey = None
        self.privateKey = None
        self.clientCount = None

class client:
    def __init__(self):
        self.socket = None
        self.address = None
        self.publicKeyBytes = None
        self.active = False
        self.listener = None # Might link the listener here as well

def parse_message(message):
    i = 2
    data = bytearray()
    rawBytes = bytes(message)
    while(rawBytes[i] != common.EOT and i < len(rawBytes)-2):
        data.append(rawBytes[i])
        i += 1
    return data

def handshake(activeClient: client, serverInfo: server_information):
    activeClient.socket.settimeout(common.SOCKET_TIMEOUT)
    connection = False
    try:
        clientData = activeClient.socket.recv(common.RECEIVE_LEN)  
        if common.SYN in clientData: # Client is trying to connect
            msg = common.frame_message(common.MT_PT_CHAT, common.ACK)  
            activeClient.socket.send(msg)
            msg = common.frame_message(common.MT_KEY, serverInfo.publicKey)
            activeClient.socket.send(msg)
            clientData = activeClient.socket.recv(common.RECEIVE_LEN)   ## Waiting for clients public key
            activeClient.publicKeyBytes = parse_message(clientData)
            connection = True
            return connection
    except socket.timeout:
        return connection
    except Exception as e:
        print(f"Connection Failure: {e}")

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
    serverInfo.publicKey = keyManager.generate_public_key()
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

def broadcast(clients, serverInfo, message, originAddress):
    ## First, lets get rid of clients that might have left.
    #message = message.encode(common.ENCODING)
    clients = [soc for soc in clients if soc.socket.fileno() != -1]            ## TODO crude but good enough for the demo
    for client in clients:
        if client.address[1] != originAddress:
            client.socket.send(message)

def receiver(activeClient: client, allClients, serverInfo: server_information):
    while(1):
        try:
            ## Server output
            username = "USER" + str(activeClient.address[1])
            rawData = activeClient.socket.recv(4095)
            if not rawData or rawData == common.EXIT or rawData == b'':
                print(username + " left the chat")
                activeClient.socket.close()
                break
            elif rawData:
                ## TODO strip the framming
                rawData = rawData.decode(common.ENCODING) 
                print(username + "(Ciphertext):" + rawData)           

                rawData = rawData.encode(common.ENCODING)
                plaintext = decrypt(rawData,serverInfo)
                plaintext = b"".join(plaintext)
                plaintext = plaintext.decode(common.ENCODING)
                print(username + "(Plaintext):" + plaintext)

                #debug code
                plaintext = common.frame_message(common.MT_CT_CHAT, plaintext)
                broadcast(allClients, serverInfo, plaintext, activeClient.address[1])
        except Exception as e:
            print(f"Server Error: {e}")
            activeClient.socket.shutdown(socket.SHUT_RDWR)
            activeClient.socket.close()
            activeClient.active = False
            break
    return


            

def connection_handler(activeClients: client,  serverSocket, serverInfo: server_information):
    while(1):
        newclient = client()
        newclient.socket, address = serverSocket.accept()
        activeClients.append(newclient)
        if(handshake(activeClients[-1], serverInfo)):
            activeClients[-1].socket.settimeout(None)
            activeClients[-1].address = address
            activeClients[-1].active = True
            username = "Client" + str(activeClients[-1].address[1])
            print(username + " Joined!")
            welcomeMsg = "Welcome to the Chatroom " + username + '!'
            activeClients[-1].socket.send(common.frame_message(common.MT_PT_CHAT,welcomeMsg))
            publicKeyMsg = common.frame_message(common.MT_KEY,serverInfo.publicKey)
            activeClients[-1].socket.send(publicKeyMsg)
            threading.Thread(target=receiver, args=(activeClients[-1], activeClients, serverInfo), daemon=True).start()
        else:
            activeClients.pop()     ## No connection. Get rid of the dead client

serverInfo = server_information()
keyManager = key.key_manager()
activeClients = []
serverSocket = server_init(serverInfo, keyManager)
thread_connection_handler = threading.Thread(connection_handler(activeClients, serverSocket, serverInfo))
thread_connection_handler.daemon = True
thread_connection_handler.start()





