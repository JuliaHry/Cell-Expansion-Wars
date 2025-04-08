import socket
import threading

class NetworkServer:
    def __init__(self, ip='0.0.0.0', port=5000):
        self.ip = ip
        self.port = int(port)
        self.clients = []
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = False

    def start(self):
        self.server_socket.bind((self.ip, self.port))
        self.server_socket.listen()
        self.running = True
        print(f"Serwer nasłuchuje na {self.ip}:{self.port}")
        threading.Thread(target=self.accept_clients, daemon=True).start()

    def accept_clients(self):
        while self.running:
            client_socket, addr = self.server_socket.accept()
            print(f"Połączono z: {addr}")
            self.clients.append(client_socket)
            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()

    def handle_client(self, client_socket):
        while self.running:
            try:
                data = client_socket.recv(1024).decode()
                if data:
                    print("Odebrano:", data)
                    self.broadcast(data, client_socket)
            except:
                break

    def broadcast(self, msg, source_socket):
        for client in self.clients:
            if client != source_socket:
                try:
                    client.sendall(msg.encode())
                except:
                    pass

    def stop(self):
        self.running = False
        self.server_socket.close()

class NetworkClient:
    def __init__(self, ip='127.0.0.1', port=5000):
        self.ip = ip
        self.port = int(port)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False

    def connect(self):
        try:
            self.client_socket.connect((self.ip, self.port))
            self.connected = True
            print(f"Połączono z serwerem {self.ip}:{self.port}")
            threading.Thread(target=self.receive_messages, daemon=True).start()
        except Exception as e:
            print("Błąd połączenia:", e)

    def send(self, msg):
        if self.connected:
            try:
                self.client_socket.sendall(msg.encode())
            except Exception as e:
                print("Błąd wysyłania:", e)

    def receive_messages(self):
        while self.connected:
            try:
                data = self.client_socket.recv(1024).decode()
                if data:
                    print("Odebrano:", data)
            except:
                break
