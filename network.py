import socket
import threading
import time
import json
from PyQt5.QtCore import QObject, pyqtSignal, Qt


class NetworkSignalHandler(QObject):
    log_message = pyqtSignal(str)
    create_line = pyqtSignal(int, int, int, int, str)                                         
    remove_line = pyqtSignal(int, int, int, int)                                  
    update_turn = pyqtSignal(str, int)                                
    update_cells = pyqtSignal(object)                          

network_signal_handler = NetworkSignalHandler()

class NetworkServer:
    def __init__(self, ip='0.0.0.0', port=5000):
        self.ip = ip
        self.port = int(port)
        self.clients = []
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = False
        self.connected = False
        self.current_turn = "green"                                 
        self.turn_remaining = 10                       
        self.turn_timer_active = False
        self.scene = None                               

    def set_scene(self, scene):
        """Set reference to the game scene for accessing cell values"""
        self.scene = scene

    def start(self):
        self.server_socket.bind((self.ip, self.port))
        self.server_socket.listen()
        self.running = True
        print(f"Serwer nasłuchuje na {self.ip}:{self.port}")
        threading.Thread(target=self.accept_clients, daemon=True).start()

    def start_turn_timer(self):
        if not self.turn_timer_active:
            self.turn_timer_active = True
            threading.Thread(target=self.turn_timer_thread, daemon=True).start()

    def turn_timer_thread(self):
        while self.running and self.turn_timer_active:
            time.sleep(1)
            self.turn_remaining -= 1

            turn_msg = f"TURN_INFO:{self.current_turn}:{self.turn_remaining}"
            self.broadcast(turn_msg)

            network_signal_handler.update_turn.emit(self.current_turn, self.turn_remaining)

            if self.current_turn == "green" and self.scene:
                self.send_cell_values()

            if self.turn_remaining <= 0:
                self.switch_turn()

    def send_cell_values(self):
        """Collect and send all cell values to clients during server's turn"""
        if not self.scene:
            return

        cell_values = {}

        for cell in self.scene.cells:
            cell_key = f"{int(cell.rect().x())},{int(cell.rect().y())}"
            cell_data = {
                "value": cell.value,
                "color": cell.base_color.name(),
                "level": cell.level
            }

            if cell.base_color == Qt.gray and hasattr(cell, "_actual_top_value"):
                cell_data["top_value"] = cell._actual_top_value

            if cell.inner_circles:
                circle_states = []
                for circle in cell.inner_circles:
                    circle_states.append(circle.brush().color().name())
                cell_data["circles"] = circle_states

            cell_values[cell_key] = cell_data

        cell_values_json = json.dumps(cell_values)
        cell_update_msg = f"CELL_VALUES:{cell_values_json}"
        self.broadcast(cell_update_msg)

    def switch_turn(self):
        self.current_turn = "pink" if self.current_turn == "green" else "green"
        self.turn_remaining = 10               

        turn_msg = f"TURN_INFO:{self.current_turn}:{self.turn_remaining}"
        self.broadcast(turn_msg)

        network_signal_handler.update_turn.emit(self.current_turn, self.turn_remaining)

    def accept_clients(self):
        while self.running:
            client_socket, addr = self.server_socket.accept()
            print(f"Połączono z: {addr}")
            self.clients.append(client_socket)
            self.connected = True                       

            if not self.turn_timer_active:
                self.start_turn_timer()

            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()

    def handle_client(self, client_socket):
        initial_turn_info = f"TURN_INFO:{self.current_turn}:{self.turn_remaining}"
        client_socket.sendall(initial_turn_info.encode())

        threading.Thread(target=self.send_periodic_message, args=(client_socket,), daemon=True).start()

        while self.running:
            try:
                data = client_socket.recv(1024).decode()
                if data:
                    print("Odebrano:", data)
                    network_signal_handler.log_message.emit(f"Odebrano: {data}")

                    if data.startswith("CELL_VALUES:"):
                        try:
                            json_str = data[len("CELL_VALUES:"):]
                            cell_values = json.loads(json_str)
                            network_signal_handler.update_cells.emit(cell_values)
                        except json.JSONDecodeError as e:
                            print(f"Error decoding JSON: {e}")

                    elif data.startswith("UTWORZONO_LINIE:"):
                        parts = data.split(":")
                        if len(parts) >= 5:
                            start_pos = parts[1].split(",")
                            end_pos = parts[2].split(",")
                            start_color = parts[3]
                            end_type = parts[4]

                            start_x = int(start_pos[0])
                            start_y = int(start_pos[1])
                            end_x = int(end_pos[0])
                            end_y = int(end_pos[1])

                            line_color = "#D8177E" if start_color == "różowa" else "#66C676"

                            network_signal_handler.create_line.emit(start_x, start_y, end_x, end_y, line_color)

                            line_msg = f"Odebrano: utworzono linię z {start_color} komórki ({start_pos[0]},{start_pos[1]}) do {end_type} komórki ({end_pos[0]},{end_pos[1]})"
                            network_signal_handler.log_message.emit(line_msg)

                    elif data.startswith("USUNIETO_LINIE:"):
                        parts = data.split(":")
                        if len(parts) >= 5:
                            start_pos = parts[1].split(",")
                            end_pos = parts[2].split(",")
                            start_color = parts[3]
                            end_color = parts[4]

                            start_x = int(start_pos[0])
                            start_y = int(start_pos[1])
                            end_x = int(end_pos[0])
                            end_y = int(end_pos[1])

                            network_signal_handler.remove_line.emit(start_x, start_y, end_x, end_y)

                            line_msg = f"Odebrano: usunięto linię z {start_color} komórki ({start_pos[0]},{start_pos[1]}) do {end_color} komórki ({end_pos[0]},{end_pos[1]})"
                            network_signal_handler.log_message.emit(line_msg)

                    self.broadcast(data, client_socket)
            except Exception as e:
                print(f"Błąd w obsłudze klienta: {e}")
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
                break

    def send_periodic_message(self, client_socket):
        while self.running:
            try:
                client_socket.sendall("HEARTBEAT:SERVER".encode())
                time.sleep(5)                                  
            except:
                break

    def broadcast(self, msg, source_socket=None):
        for client in self.clients:
            if source_socket is None or client != source_socket:
                try:
                    client.sendall(msg.encode())
                except:
                    pass

    def stop(self):
        self.running = False
        self.turn_timer_active = False
        self.server_socket.close()

class NetworkClient:
    def __init__(self, ip='127.0.0.1', port=5000):
        self.ip = ip
        self.port = int(port)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.scene = None                               
        self.current_turn = "green"                         

    def set_scene(self, scene):
        """Set reference to the game scene for accessing cell values"""
        self.scene = scene

    def disconnect(self):
        """Properly disconnect the client socket"""
        self.connected = False
        try:
            if self.client_socket:
                self.client_socket.close()
        except Exception as e:
            print(f"Error closing client socket: {e}")

    def connect(self):
        try:
            self.client_socket.connect((self.ip, self.port))
            self.connected = True
            print(f"Połączono z serwerem {self.ip}:{self.port}")
            threading.Thread(target=self.receive_messages, daemon=True).start()
            threading.Thread(target=self.send_periodic_message, daemon=True).start()
            threading.Thread(target=self.send_cell_updates, daemon=True).start()
        except Exception as e:
            print("Błąd połączenia:", e)

    def send_cell_updates(self):
        """Periodically send cell values during pink's turn"""
        while self.connected:
            time.sleep(1)                             

            if self.current_turn == "pink" and self.scene:
                self.send_cell_values()

    def send_cell_values(self):
        """Collect and send all cell values to server during client's turn"""
        if not self.scene:
            return

        cell_values = {}

        for cell in self.scene.cells:
            cell_key = f"{int(cell.rect().x())},{int(cell.rect().y())}"
            cell_data = {
                "value": cell.value,
                "color": cell.base_color.name(),
                "level": cell.level
            }

            if cell.base_color == Qt.gray and hasattr(cell, "_actual_top_value"):
                cell_data["top_value"] = cell._actual_top_value

            if cell.inner_circles:
                circle_states = []
                for circle in cell.inner_circles:
                    circle_states.append(circle.brush().color().name())
                cell_data["circles"] = circle_states

            cell_values[cell_key] = cell_data

        cell_values_json = json.dumps(cell_values)
        cell_update_msg = f"CELL_VALUES:{cell_values_json}"
        self.send(cell_update_msg)

    def send(self, msg):
        if self.connected:
            try:
                self.client_socket.sendall(msg.encode())
            except Exception as e:
                print("Błąd wysyłania:", e)
                self.connected = False

    def send_periodic_message(self):
        while self.connected:
            try:
                self.client_socket.sendall("HEARTBEAT:CLIENT".encode())
                time.sleep(5)                                  
            except:
                self.connected = False
                break

    def receive_messages(self):
        while self.connected:
            try:
                data = self.client_socket.recv(1024).decode()
                if data:
                    print("Odebrano:", data)
                    network_signal_handler.log_message.emit(f"Odebrano: {data}")

                    if data.startswith("TURN_INFO:"):
                        parts = data.split(":")
                        if len(parts) >= 3:
                            self.current_turn = parts[1]                              
                            turn_remaining = int(parts[2])
                            network_signal_handler.update_turn.emit(self.current_turn, turn_remaining)

                    elif data.startswith("CELL_VALUES:"):
                        try:
                            json_str = data[len("CELL_VALUES:"):]
                            cell_values = json.loads(json_str)
                            network_signal_handler.update_cells.emit(cell_values)
                        except json.JSONDecodeError as e:
                            print(f"Error decoding JSON: {e}")

                    elif data.startswith("UTWORZONO_LINIE:"):
                        parts = data.split(":")
                        if len(parts) >= 5:
                            start_pos = parts[1].split(",")
                            end_pos = parts[2].split(",")
                            start_color = parts[3]
                            end_type = parts[4]

                            start_x = int(start_pos[0])
                            start_y = int(start_pos[1])
                            end_x = int(end_pos[0])
                            end_y = int(end_pos[1])

                            line_color = "#D8177E" if start_color == "różowa" else "#66C676"

                            network_signal_handler.create_line.emit(start_x, start_y, end_x, end_y, line_color)

                            line_msg = f"Odebrano: utworzono linię z {start_color} komórki ({start_pos[0]},{start_pos[1]}) do {end_type} komórki ({end_pos[0]},{end_pos[1]})"
                            network_signal_handler.log_message.emit(line_msg)

                    elif data.startswith("USUNIETO_LINIE:"):
                        parts = data.split(":")
                        if len(parts) >= 5:
                            start_pos = parts[1].split(",")
                            end_pos = parts[2].split(",")
                            start_color = parts[3]
                            end_color = parts[4]

                            start_x = int(start_pos[0])
                            start_y = int(start_pos[1])
                            end_x = int(end_pos[0])
                            end_y = int(end_pos[1])

                            network_signal_handler.remove_line.emit(start_x, start_y, end_x, end_y)

                            line_msg = f"Odebrano: usunięto linię z {start_color} komórki ({start_pos[0]},{start_pos[1]}) do {end_color} komórki ({end_pos[0]},{end_pos[1]})"
                            network_signal_handler.log_message.emit(line_msg)
            except Exception as e:
                print(f"Błąd odbioru: {e}")
                self.connected = False
                break