import socket
import threading
import time
import json
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox

# Create a global signal handler for thread-safe logging and synchronization
class NetworkSignalHandler(QObject):
    log_message = pyqtSignal(str)
    create_line = pyqtSignal(int, int, int, int, str)  # start_x, start_y, end_x, end_y, color
    remove_line = pyqtSignal(int, int, int, int)  # start_x, start_y, end_x, end_y
    update_turn = pyqtSignal(str, int)  # current_turn, remaining_time
    update_cells = pyqtSignal(object)  # cell_values dictionary

# Create a global instance
network_signal_handler = NetworkSignalHandler()

class NetworkServer:
    def __init__(self, ip='0.0.0.0', port=5000):
        self.ip = ip
        self.port = int(port)
        self.clients = []
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = False
        self.connected = False
        self.current_turn = "green"  # Server starts with green turn
        self.turn_remaining = 10  # 10 seconds per turn
        self.turn_timer_active = False
        self.scene = None  # Reference to the game scene
        
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
            
            # Broadcast turn info to all clients
            turn_msg = f"TURN_INFO:{self.current_turn}:{self.turn_remaining}"
            self.broadcast(turn_msg)
            
            # Update the local UI
            network_signal_handler.update_turn.emit(self.current_turn, self.turn_remaining)
            
            # If it's green's turn (server's turn), send cell values to clients
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
            
            # Add gray cell specific values
            if cell.base_color == Qt.gray and hasattr(cell, "_actual_top_value"):
                cell_data["top_value"] = cell._actual_top_value
                
            # Add inner circle states if present
            if cell.inner_circles:
                circle_states = []
                for circle in cell.inner_circles:
                    circle_states.append(circle.brush().color().name())
                cell_data["circles"] = circle_states
                
            cell_values[cell_key] = cell_data
            
        # Convert to JSON and send
        cell_values_json = json.dumps(cell_values)
        cell_update_msg = f"CELL_VALUES:{cell_values_json}"
        self.broadcast(cell_update_msg)
                
    def switch_turn(self):
        self.current_turn = "pink" if self.current_turn == "green" else "green"
        self.turn_remaining = 10  # Reset timer
        
        # Broadcast turn switch to all clients
        turn_msg = f"TURN_INFO:{self.current_turn}:{self.turn_remaining}"
        self.broadcast(turn_msg)
        
        # Update the local UI
        network_signal_handler.update_turn.emit(self.current_turn, self.turn_remaining)

    def accept_clients(self):
        while self.running:
            client_socket, addr = self.server_socket.accept()
            print(f"Połączono z: {addr}")
            self.clients.append(client_socket)
            self.connected = True  # Set connection flag
            
            # Start turn timer once client connects
            if not self.turn_timer_active:
                self.start_turn_timer()
                
            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()

    def handle_client(self, client_socket):
        # Send initial turn information to the client
        initial_turn_info = f"TURN_INFO:{self.current_turn}:{self.turn_remaining}"
        client_socket.sendall(initial_turn_info.encode())
        
        # Start heartbeat thread
        threading.Thread(target=self.send_periodic_message, args=(client_socket,), daemon=True).start()
        
        while self.running:
            try:
                data = client_socket.recv(1024).decode()
                if data:
                    print("Odebrano:", data)
                    network_signal_handler.log_message.emit(f"Odebrano: {data}")
                    
                    # Handle level check from client
                    if data.startswith("LEVEL_CHECK:"):
                        client_level = int(data.split(":")[1])
                        if client_level != self.scene.level:
                            mismatch_msg = f"LEVEL_MISMATCH:{self.scene.level}"
                            client_socket.sendall(mismatch_msg.encode())
                            client_socket.close()
                            self.clients.remove(client_socket)
                            return
                        else:
                            client_socket.sendall("LEVEL_OK".encode())
                    
                    # Handle cell values update from client
                    elif data.startswith("CELL_VALUES:"):
                        try:
                            json_str = data[len("CELL_VALUES:"):]
                            cell_values = json.loads(json_str)
                            network_signal_handler.update_cells.emit(cell_values)
                        except json.JSONDecodeError as e:
                            print(f"Error decoding JSON: {e}")
                    
                    # Handle line creation notification
                    elif data.startswith("UTWORZONO_LINIE:"):
                        parts = data.split(":")
                        if len(parts) >= 5:
                            start_pos = parts[1].split(",")
                            end_pos = parts[2].split(",")
                            start_color = parts[3]
                            end_type = parts[4]
                            
                            # Extract numerical positions
                            start_x = int(start_pos[0])
                            start_y = int(start_pos[1])
                            end_x = int(end_pos[0])
                            end_y = int(end_pos[1])
                            
                            # Determine line color
                            line_color = "#D8177E" if start_color == "różowa" else "#66C676"
                            
                            # Emit signal to create line in the scene
                            network_signal_handler.create_line.emit(start_x, start_y, end_x, end_y, line_color)
                            
                            line_msg = f"Odebrano: utworzono linię z {start_color} komórki ({start_pos[0]},{start_pos[1]}) do {end_type} komórki ({end_pos[0]},{end_pos[1]})"
                            network_signal_handler.log_message.emit(line_msg)
                    
                    # Handle line removal notification
                    elif data.startswith("USUNIETO_LINIE:"):
                        parts = data.split(":")
                        if len(parts) >= 5:
                            start_pos = parts[1].split(",")
                            end_pos = parts[2].split(",")
                            start_color = parts[3]
                            end_color = parts[4]
                            
                            # Extract numerical positions
                            start_x = int(start_pos[0])
                            start_y = int(start_pos[1])
                            end_x = int(end_pos[0])
                            end_y = int(end_pos[1])
                            
                            # Emit signal to remove line in the scene
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
                time.sleep(5)  # Send heartbeat every 5 seconds
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
        self.scene = None  # Reference to the game scene
        self.current_turn = "green"  # Default initial value
        
    def set_scene(self, scene):
        """Set reference to the game scene for accessing cell values"""
        self.scene = scene

    def connect(self):
        while not self.connected:
            try:
                self.client_socket.connect((self.ip, self.port))
                self.connected = True
                print(f"Połączono z serwerem {self.ip}:{self.port}")
                
                # Verify level compatibility
                self.verify_level_compatibility()
                
                threading.Thread(target=self.receive_messages, daemon=True).start()
                threading.Thread(target=self.send_periodic_message, daemon=True).start()
                threading.Thread(target=self.send_cell_updates, daemon=True).start()
            except Exception as e:
                print("Błąd połączenia:", e)
                self.show_connection_error_dialog()

    def verify_level_compatibility(self):
        """Send the client's level to the server and verify compatibility."""
        if not self.scene:
            return
        
        client_level = self.scene.level
        self.send(f"LEVEL_CHECK:{client_level}")
        
        # Wait for server response
        response = self.client_socket.recv(1024).decode()
        if response.startswith("LEVEL_MISMATCH"):
            server_level = response.split(":")[1]
            self.show_level_mismatch_dialog(server_level)
            self.connected = False
            self.client_socket.close()

    def show_level_mismatch_dialog(self, server_level):
        """Display a dialog box to inform the user about level mismatch."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Błąd poziomu")
        msg.setText("Poziom gry na serwerze nie zgadza się z poziomem klienta.")
        msg.setInformativeText(f"Serwer działa na poziomie {server_level}. Zmień poziom i spróbuj ponownie.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def show_connection_error_dialog(self):
        """Display a dialog box to inform the user about connection failure and allow retry."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Błąd połączenia")
        msg.setText("Nie udało się połączyć z serwerem pod podanym adresem IP i portem.")
        msg.setInformativeText("Sprawdź poprawność adresu IP i portu, a następnie spróbuj ponownie.")
        msg.setStandardButtons(QMessageBox.Retry | QMessageBox.Cancel)
        result = msg.exec_()

        if result == QMessageBox.Retry:
            self.ip, self.port = self.prompt_for_new_connection_details()
        else:
            self.connected = False

    def prompt_for_new_connection_details(self):
        """Prompt the user to enter a new IP and port."""
        dialog = QDialog()
        dialog.setWindowTitle("Podaj nowe dane połączenia")
        layout = QVBoxLayout(dialog)

        ip_label = QLabel("Adres IP:")
        ip_input = QLineEdit()
        ip_input.setText(self.ip)
        layout.addWidget(ip_label)
        layout.addWidget(ip_input)

        port_label = QLabel("Port:")
        port_input = QLineEdit()
        port_input.setText(str(self.port))
        layout.addWidget(port_label)
        layout.addWidget(port_input)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec_() == QDialog.Accepted:
            new_ip = ip_input.text().strip()
            new_port = port_input.text().strip()
            return new_ip, int(new_port) if new_port.isdigit() else self.port
        return self.ip, self.port

    def send_cell_updates(self):
        """Periodically send cell values during pink's turn"""
        while self.connected:
            time.sleep(1)  # Send updates every second
            
            # Only send updates during pink's turn
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
            
            # Add gray cell specific values
            if cell.base_color == Qt.gray and hasattr(cell, "_actual_top_value"):
                cell_data["top_value"] = cell._actual_top_value
                
            # Add inner circle states if present
            if cell.inner_circles:
                circle_states = []
                for circle in cell.inner_circles:
                    circle_states.append(circle.brush().color().name())
                cell_data["circles"] = circle_states
                
            cell_values[cell_key] = cell_data
            
        # Convert to JSON and send
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
                time.sleep(5)  # Send heartbeat every 5 seconds
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
                    
                    # Handle turn information updates
                    if data.startswith("TURN_INFO:"):
                        parts = data.split(":")
                        if len(parts) >= 3:
                            self.current_turn = parts[1]  # Update local turn tracking
                            turn_remaining = int(parts[2])
                            network_signal_handler.update_turn.emit(self.current_turn, turn_remaining)
                    
                    # Handle cell values update from server
                    elif data.startswith("CELL_VALUES:"):
                        try:
                            json_str = data[len("CELL_VALUES:"):]
                            cell_values = json.loads(json_str)
                            network_signal_handler.update_cells.emit(cell_values)
                        except json.JSONDecodeError as e:
                            print(f"Error decoding JSON: {e}")
                    
                    # Handle line creation notification
                    elif data.startswith("UTWORZONO_LINIE:"):
                        parts = data.split(":")
                        if len(parts) >= 5:
                            start_pos = parts[1].split(",")
                            end_pos = parts[2].split(",")
                            start_color = parts[3]
                            end_type = parts[4]
                            
                            # Extract numerical positions
                            start_x = int(start_pos[0])
                            start_y = int(start_pos[1])
                            end_x = int(end_pos[0])
                            end_y = int(end_pos[1])
                            
                            # Determine line color
                            line_color = "#D8177E" if start_color == "różowa" else "#66C676"
                            
                            # Emit signal to create line in the scene
                            network_signal_handler.create_line.emit(start_x, start_y, end_x, end_y, line_color)
                            
                            line_msg = f"Odebrano: utworzono linię z {start_color} komórki ({start_pos[0]},{start_pos[1]}) do {end_type} komórki ({end_pos[0]},{end_pos[1]})"
                            network_signal_handler.log_message.emit(line_msg)
                    
                    # Handle line removal notification
                    elif data.startswith("USUNIETO_LINIE:"):
                        parts = data.split(":")
                        if len(parts) >= 5:
                            start_pos = parts[1].split(",")
                            end_pos = parts[2].split(",")
                            start_color = parts[3]
                            end_color = parts[4]
                            
                            # Extract numerical positions
                            start_x = int(start_pos[0])
                            start_y = int(start_pos[1])
                            end_x = int(end_pos[0])
                            end_y = int(end_pos[1])
                            
                            # Emit signal to remove line in the scene
                            network_signal_handler.remove_line.emit(start_x, start_y, end_x, end_y)
                            
                            line_msg = f"Odebrano: usunięto linię z {start_color} komórki ({start_pos[0]},{start_pos[1]}) do {end_color} komórki ({end_pos[0]},{end_pos[1]})"
                            network_signal_handler.log_message.emit(line_msg)
            except Exception as e:
                print(f"Błąd odbioru: {e}")
                self.connected = False
                break