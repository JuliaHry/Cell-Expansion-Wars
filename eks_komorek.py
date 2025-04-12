import sys
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem, QMenu, QAction, QPushButton, QGraphicsRectItem, QGraphicsPixmapItem, QLabel, QTextEdit, QDialog, QVBoxLayout, QRadioButton, QButtonGroup, QDialogButtonBox
from PyQt5.QtGui import QBrush, QPen, QLinearGradient, QRadialGradient, QColor, QPainter, QFont, QTransform, QPixmap
from PyQt5.QtCore import Qt, QRectF, QLineF, QPointF, QTimer
from random import uniform
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp
from network import NetworkClient, NetworkServer
import os
import subprocess
import xml.etree.ElementTree as ET
import json
import resources
import pickle
from PyQt5.QtWidgets import QMessageBox
import xml.etree.ElementTree as ET
import threading
from network import network_signal_handler

game_view_instance = None

class Logger:
    def __init__(self, log_widget=None, max_lines=100):
        self.log_widget = log_widget
        self.max_lines = max_lines
        self.log_buffer = []

    def log(self, message):
 
        print(message)

        if self.log_widget:
            self.log_buffer.append(message)
            if len(self.log_buffer) > self.max_lines:
                self.log_buffer.pop(0)
            self.log_widget.setPlainText("\n".join(self.log_buffer))
            self.log_widget.verticalScrollBar().setValue(self.log_widget.verticalScrollBar().maximum())

class ClickableLine(QGraphicsLineItem):
    def __init__(self, line, start_cell, end_cell=None, parent=None):
        super().__init__(line, parent)
        color = "#D8177E" if start_cell.base_color == QColor("#D8177E") else "#66C676"
        self.setPen(QPen(QColor(color), 8))
        self.setZValue(-1) 
        self.start_cell = start_cell
        self.end_cell = end_cell
        self.mini_cells = []  
 
    def update_position(self):
        if self.start_cell and self.end_cell:
            start_pos = self.start_cell.scenePos() + self.start_cell.rect().center()
            end_pos = self.end_cell.scenePos() + self.end_cell.rect().center()
            game_view_instance.logger.log(f"Aktualizacja linii: start_pos={start_pos}, end_pos={end_pos}")
            self.setLine(QLineF(start_pos, end_pos))
        else:
            game_view_instance.logger.log("Brak start_cell lub end_cell w linii")

    def mousePressEvent(self, event):
        # Check if this line can be clicked based on game mode and turn
        scene = self.scene()
        if isinstance(scene, GameScene):
            # For network games, check if line color matches player role
            if scene.game_mode == "Gra sieciowa":
                is_server = hasattr(scene, 'server') and scene.server is not None
                is_client = hasattr(scene, 'client') and scene.client is not None
                
                # Server can only click green lines during green turn
                if is_server and (self.start_cell.base_color != QColor("#66C676") or scene.current_turn != "green"):
                    game_view_instance.logger.log("Nie możesz usuwać tej linii!")
                    return
                    
                # Client can only click pink lines during pink turn
                if is_client and (self.start_cell.base_color != QColor("#D8177E") or scene.current_turn != "pink"):
                    game_view_instance.logger.log("Nie możesz usuwać tej linii!")
                    return
            
            # For all game modes, check if line color matches turn
            if (self.start_cell.base_color == QColor("#66C676") and scene.current_turn != "green") or \
            (self.start_cell.base_color == QColor("#D8177E") and scene.current_turn != "pink"):
                game_view_instance.logger.log("Nie możesz usuwać linii przeciwnika!")
                return
        
        # Get positions before removing line
        start_cell_pos = (int(self.start_cell.rect().x()), int(self.start_cell.rect().y()))
        end_cell_pos = (int(self.end_cell.rect().x()), int(self.end_cell.rect().y()))
        start_color = "zielona" if self.start_cell.base_color == QColor("#66C676") else "różowa"
        end_color = "zielona" if self.end_cell.base_color == QColor("#66C676") else "różowa"
        if self.end_cell.base_color == Qt.gray:
            end_color = "szara"
        
        # Original line interaction logic
        clicked_pos = event.scenePos()
        start_pos = self.line().p1()
        end_pos = self.line().p2()
        distance_to_start = QLineF(start_pos, clicked_pos).length()
        distance_to_end = QLineF(end_pos, clicked_pos).length()
        value_to_add = int(distance_to_start // 50) 
        value_to_subtract = int(distance_to_end // 50)  

        if self.start_cell:
            self.start_cell.update_value(value_to_add)

        if self.end_cell:
            if self.start_cell.base_color == self.end_cell.base_color:
                self.end_cell.update_value(value_to_subtract)  
            else:
                self.end_cell.update_value(-value_to_subtract)  

            if self.end_cell.base_color == Qt.gray:
                gray_center = self.end_cell.scenePos() + self.end_cell.rect().center()
                distance_to_gray_center = QLineF(clicked_pos, gray_center).length()
                gray_value_to_modify = int(distance_to_gray_center // 50)
                if self.start_cell.base_color == QColor("#66C676"):
                    game_view_instance.logger.log(f"Distance to gray center: {distance_to_gray_center}, Value to add: {gray_value_to_modify}")
                    self.end_cell.update_top_text(gray_value_to_modify)
                elif self.start_cell.base_color == QColor("#D8177E"):
                    game_view_instance.logger.log(f"Distance to gray center: {distance_to_gray_center}, Value to subtract: {gray_value_to_modify}")
                    self.end_cell.update_top_text(-gray_value_to_modify)

        for circle in self.start_cell.inner_circles:
            if circle.brush().color() == Qt.black:
                circle.setBrush(QBrush(Qt.white))
                break

        # Send line removal notification over network
        if isinstance(scene, GameScene) and scene.game_mode == "Gra sieciowa":
            line_info = f"USUNIETO_LINIE:{start_cell_pos[0]},{start_cell_pos[1]}:{end_cell_pos[0]},{end_cell_pos[1]}:{start_color}:{end_color}"
            
            if hasattr(scene, 'server') and scene.server is not None:
                # Server is sending
                for client in scene.server.clients:
                    client.sendall(line_info.encode())
            elif hasattr(scene, 'client') and scene.client is not None:
                # Client is sending
                scene.client.send(line_info)

        self.scene().removeItem(self)
        super().mousePressEvent(event)


class ClickableCell(QGraphicsEllipseItem):
    selected_green = None  
    is_creating_line = False  
    moving_cell = None  

    def __init__(self, rect, color, value, parent=None):
        super().__init__(rect, parent)
        self.base_color = QColor(color) if isinstance(color, str) else QColor(color)
        self.value = value
        self.set_gradient()
        self.setPen(QPen(Qt.black, 2))
        self.setAcceptHoverEvents(True)  
        self.is_selected = False
        self.inner_circles = []  
        self.value_text = None  
        self.level = 1  
    
    def set_gradient(self):
        if self.base_color == Qt.gray:
            gradient = QRadialGradient(self.rect().center(), self.rect().width() / 2)
            if hasattr(self, 'fill_color') and self.fill_color:
                fill_ratio = min(self.value / 8, 1) 
                gradient.setColorAt(0, self.fill_color.lighter(150)) 
                gradient.setColorAt(fill_ratio, self.fill_color.darker(150)) 
                gradient.setColorAt(fill_ratio, self.base_color) 
            gradient.setColorAt(1, self.base_color)  
            self.setBrush(QBrush(gradient))
        else:
            if self.base_color == QColor("#66C676"):
                pixmap = QPixmap(":/images/green_cell.png")
            elif self.base_color == QColor("#D8177E"):
                pixmap = QPixmap(":/images/pink_cell.png")
            else:
                pixmap = QPixmap()
        
            if not pixmap.isNull():
                pixmap = pixmap.scaled(self.rect().size().toSize(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                brush = QBrush(pixmap)
        
                offset_x = 50
                offset_y = 50

                brush.setTransform(QTransform().translate(offset_x, offset_y))
                
                self.setBrush(brush)
            else:
                gradient = QRadialGradient(self.rect().center(), self.rect().width() / 2)
                gradient.setColorAt(0, self.base_color.lighter(150)) 
                gradient.setColorAt(1, self.base_color.darker(150)) 
                self.setBrush(QBrush(gradient))
    
    def set_value_text(self, text_item):
        self.value_text = text_item

    def set_level_text(self, text_item):
        self.level_text = text_item

    def get_attack_power_per_mini_cell(self):
        return self.level 


    def increase_level(self):
        if self.level < 3:
            self.level += 1
            self.update_level_display()

    def update_level_display(self):
        if hasattr(self, 'level_text'):
            self.level_text.setPlainText(f"LVL {self.level}")

    def get_attack_power(self):
        return self.level * self.value

    
    def update_value(self, delta, fill_color=None, caused_by_enemy=False):
        self.value += delta
        if self.value > 30:
            self.value = 30
        if self.value_text:
            self.value_text.setPlainText(str(self.value))

        if self.value <= 0:
            if caused_by_enemy:
                if self.base_color == QColor("#D8177E"):
                    self.convert_to_green()
                elif self.base_color == QColor("#66C676"):
                    self.convert_to_pink()
            else:
                self.remove_lines()

        if self.base_color == Qt.gray:
            if fill_color:
                self.fill_color = fill_color
            self.set_gradient() 
    
    def remove_lines(self):
        """Remove all outgoing lines connected to this cell, reset inner circles to white, and allow line creation."""
        for item in self.scene().items():
            if isinstance(item, ClickableLine) and item.start_cell == self:
                self.scene().removeItem(item)
        for circle in self.inner_circles:
            if circle.brush().color() == Qt.black:
                circle.setBrush(QBrush(Qt.white))
        self.is_selected = False

    def set_top_text(self, text_item):
        self.top_text = text_item

    def update_top_text(self, delta):
        if not hasattr(self, '_actual_top_value'):
            self._actual_top_value = 0 
        self._actual_top_value += delta 
        self.top_text.setPlainText(str(abs(self._actual_top_value)))
        game_view_instance.logger.log(f"Updated top value on gray cell: {self._actual_top_value}")

        if self._actual_top_value >= 8:
            self.convert_to_green(attacker=self.scene().get_attacker(self))
        elif self._actual_top_value <= -8:
            self.convert_to_pink(attacker=self.scene().get_attacker(self))


        if self._actual_top_value >= 8:
            self.convert_to_green()
            return
        elif self._actual_top_value <= -8:
            self.convert_to_pink()
            return

        if self.base_color == Qt.gray:
            gradient = QRadialGradient(self.rect().center(), self.rect().width() / 2)
            if self._actual_top_value > 0:
                fill_ratio = min(self._actual_top_value / 8, 1) 
                self.fill_color = QColor("#66C676") 
                gradient.setColorAt(0, self.fill_color.lighter(150)) 
                gradient.setColorAt(fill_ratio, self.fill_color.darker(150)) 
                gradient.setColorAt(fill_ratio, self.base_color)  
            elif self._actual_top_value < 0:
                fill_ratio = min(abs(self._actual_top_value) / 8, 1) 
                self.fill_color = QColor("#D8177E")  
                gradient.setColorAt(0, self.fill_color.lighter(150)) 
                gradient.setColorAt(fill_ratio, self.fill_color.darker(150)) 
                gradient.setColorAt(fill_ratio, self.base_color) 
            else:
                self.fill_color = None  
                self.set_gradient()  
                return
            gradient.setColorAt(1, self.base_color) 
            self.setBrush(QBrush(gradient))
    
    def convert_to_green(self, attacker=None):
        self.base_color = QColor("#66C676")
        self.set_gradient()
        
        if attacker:
            attacker.increase_level()

        self.value = 20
        if self.value_text:
            self.value_text.setPlainText("20")
        else:
            text_item = QGraphicsTextItem("20")
            text_item.setFont(QFont("Arial", 14, QFont.Bold))
            text_item.setDefaultTextColor(Qt.white)
            text_rect = text_item.boundingRect()
            text_item.setPos(
                self.rect().x() + 50 - text_rect.width() / 2,
                self.rect().y() + 50 - text_rect.height() / 2
            )
            self.scene().addItem(text_item)
            self.set_value_text(text_item)
        
        if self.level > 1:
            self.level = 1
        self.update_level_display()

        if not hasattr(self, 'level_text'):
            level_text = QGraphicsTextItem("LVL 1")
            level_text.setFont(QFont("Arial", 10))
            level_text.setDefaultTextColor(Qt.white)
            level_text_rect = level_text.boundingRect()
            level_text.setPos(
                self.rect().x() + 50 - level_text_rect.width() / 2,
                self.rect().y() + 90
            )
            self.scene().addItem(level_text)
            self.set_level_text(level_text)
        
        # Usuń liczby z szarej komórki
        if hasattr(self, 'top_text'):
            self.scene().removeItem(self.top_text)
            del self.top_text
        
        if hasattr(self, 'bottom_text'):
            self.scene().removeItem(self.bottom_text)
            del self.bottom_text
        
        if not self.inner_circles:
            for dx, dy in [(-20, -20), (20, 20)]:
                inner_circle = QGraphicsEllipseItem(self.rect().x() + 50 + dx - 10, self.rect().y() + 50 + dy - 10, 20, 20)
                inner_circle.setBrush(QBrush(Qt.white))
                inner_circle.setPen(QPen(Qt.black, 1))
                inner_circle.setZValue(1)  
                self.scene().addItem(inner_circle)
                self.inner_circles.append(inner_circle)
    
    def convert_to_pink(self, attacker=None):
        self.base_color = QColor("#D8177E")
        self.set_gradient()

        if attacker:
            attacker.increase_level()
        
        self.value = 20
        if self.value_text:
            self.value_text.setPlainText("20")
        else:
            text_item = QGraphicsTextItem("20")
            text_item.setFont(QFont("Arial", 14, QFont.Bold))
            text_item.setDefaultTextColor(Qt.white)
            text_rect = text_item.boundingRect()
            text_item.setPos(
                self.rect().x() + 50 - text_rect.width() / 2,
                self.rect().y() + 50 - text_rect.height() / 2
            )
            self.scene().addItem(text_item)
            self.set_value_text(text_item)
        
        if self.level > 1:
            self.level = 1
        self.update_level_display()

        if not hasattr(self, 'level_text'):
            level_text = QGraphicsTextItem("LVL 1")
            level_text.setFont(QFont("Arial", 10))
            level_text.setDefaultTextColor(Qt.white)
            level_text_rect = level_text.boundingRect()
            level_text.setPos(
                self.rect().x() + 50 - level_text_rect.width() / 2,
                self.rect().y() + 75 
            )
            self.scene().addItem(level_text)
            self.set_level_text(level_text)
        
        if hasattr(self, 'top_text'):
            self.scene().removeItem(self.top_text)
            del self.top_text
        
        if hasattr(self, 'bottom_text'):
            self.scene().removeItem(self.bottom_text)
            del self.bottom_text
            
        
        if not self.inner_circles:
            for dx, dy in [(-20, -20), (20, 20)]:
                inner_circle = QGraphicsEllipseItem(self.rect().x() + 50 + dx - 10, self.rect().y() + 50 + dy - 10, 20, 20)
                inner_circle.setBrush(QBrush(QBrush(Qt.white)))
                inner_circle.setPen(QPen(Qt.black, 1))
                inner_circle.setZValue(1) 
                self.scene().addItem(inner_circle)
                self.inner_circles.append(inner_circle)

    def highlight_valid_targets(self):
        for cell in self.scene().cells:
            if cell == self:
                continue 
            if cell.base_color == Qt.gray or (
                cell.base_color != self.base_color and 
                cell.level <= self.level and 
                cell.value < self.value
            ):
                cell.setPen(QPen(QColor("#FFFF00"), 4))  

    def clear_highlight(self):
        for cell in self.scene().cells:
            cell.setPen(QPen(Qt.black, 2))

    def mousePressEvent(self, event):
        # Check scene and game mode
        scene = self.scene()
        if not isinstance(scene, GameScene):
            super().mousePressEvent(event)
            return
            
        # Handle moving cells first
        if ClickableCell.moving_cell:
            ClickableCell.moving_cell.setPen(QPen(Qt.black, 2))
            self.setPen(QPen(QColor("#FFA500"), 8, Qt.SolidLine))
            ClickableCell.moving_cell = self
            return
        
        # For network games, check which player color we are
        if scene.game_mode == "Gra sieciowa":
            # Determine if we're server (green) or client (pink)
            is_server = hasattr(scene, 'server') and scene.server is not None
            is_client = hasattr(scene, 'client') and scene.client is not None
            
            # Block interaction based on color and turn
            if is_server and scene.current_turn == "pink":
                # Server can only interact with green cells and only during green turn
                game_view_instance.logger.log("Nie twoja tura - poczekaj na swoją kolej!")
                return
            elif is_client and scene.current_turn == "green":
                # Client can only interact with pink cells and only during pink turn
                game_view_instance.logger.log("Nie twoja tura - poczekaj na swoją kolej!")
                return

        # Continue with the original mousePressEvent logic
        if self.base_color == QColor("#66C676") or self.base_color == QColor("#D8177E"): 
            # Color and turn check for all game modes
            if self.base_color == QColor("#66C676") and scene.current_turn != "green":
                game_view_instance.logger.log("Teraz jest tura różowego!")
                return
            if self.base_color == QColor("#D8177E") and scene.current_turn != "pink":
                game_view_instance.logger.log("Teraz jest tura zielonego!")
                return
                
            if all(circle.brush().color() == Qt.black for circle in self.inner_circles):
                game_view_instance.logger.log("Oba wewnętrzne kółka są czarne, nie można wybrać komórki.")
                return
            
            if ClickableCell.is_creating_line:
                if ClickableCell.selected_green and ClickableCell.selected_green != self:
                    game_view_instance.logger.log(f"Tworzenie linii z1 {ClickableCell.selected_green.base_color.name()} do {self.base_color.name()}")
                    start_pos = ClickableCell.selected_green.scenePos() + ClickableCell.selected_green.rect().center()
                    end_pos = self.scenePos() + self.rect().center()
                    line_length = QLineF(start_pos, end_pos).length()
                    cost = int(line_length // 50)
                    game_view_instance.logger.log(f"Koszt stworzenia linii: {cost}, długość linii: {line_length}")

                    if cost > ClickableCell.selected_green.value:
                        game_view_instance.logger.log("Koszt stworzenia linii przekracza wartość komórki, linia nie może zostać utworzona.")
                        return

                    line = ClickableLine(QLineF(start_pos, end_pos), ClickableCell.selected_green, self)
                    self.scene().addItem(line)
                    
                    ClickableCell.selected_green.update_value(-cost)
                    
                    ClickableCell.selected_green.setPen(QPen(Qt.black, 2))
                    self.setPen(QPen(Qt.black, 2))
                    
                    for circle in ClickableCell.selected_green.inner_circles:
                        if circle.brush().color() != Qt.black:
                            circle.setBrush(QBrush(Qt.black))
                            break
                    
                    ClickableCell.selected_green.clear_highlight()
                    
                    # Send line creation notification over network if in network mode
                    if scene.game_mode == "Gra sieciowa":
                        start_cell_pos = (int(ClickableCell.selected_green.rect().x()), int(ClickableCell.selected_green.rect().y()))
                        end_cell_pos = (int(self.rect().x()), int(self.rect().y()))
                        start_color = "zielona" if ClickableCell.selected_green.base_color == QColor("#66C676") else "różowa"
                        end_color = "zielona" if self.base_color == QColor("#66C676") else "różowa"
                        if end_color == "zielona":
                            end_color_desc = "zielonej"
                        elif end_color == "różowa":
                            end_color_desc = "różowej"
                        else:
                            end_color_desc = "szarej"
                        
                        line_info = f"UTWORZONO_LINIE:{start_cell_pos[0]},{start_cell_pos[1]}:{end_cell_pos[0]},{end_cell_pos[1]}:{start_color}:{end_color_desc}"
                        
                        if hasattr(scene, 'server') and scene.server is not None:
                            # Server is sending
                            for client in scene.server.clients:
                                client.sendall(line_info.encode())
                        elif hasattr(scene, 'client') and scene.client is not None:
                            # Client is sending
                            scene.client.send(line_info)
                    
                    ClickableCell.selected_green = None
                    ClickableCell.is_creating_line = False
            else:
                game_view_instance.logger.log(f"Rozpoczęcie tworzenia linii z {self.base_color.name()}")
                self.setPen(QPen(QColor("#A4DEFA"), 8, Qt.SolidLine))
                ClickableCell.selected_green = self
                ClickableCell.is_creating_line = True
                self.highlight_valid_targets() 

        elif self.base_color == Qt.gray and ClickableCell.selected_green:
            # For gray cells, check if the starting cell's color matches the current turn
            if (ClickableCell.selected_green.base_color == QColor("#66C676") and scene.current_turn != "green") or \
            (ClickableCell.selected_green.base_color == QColor("#D8177E") and scene.current_turn != "pink"):
                game_view_instance.logger.log("Nie możesz tworzyć linii w turze przeciwnika!")
                return
                
            game_view_instance.logger.log(f"Tworzenie linii z2 {ClickableCell.selected_green.base_color.name()} do szarej komórki")
            if all(circle.brush().color() == Qt.black for circle in ClickableCell.selected_green.inner_circles):
                game_view_instance.logger.log("Oba wewnętrzne kółka w komórce startowej są czarne, nie można stworzyć linii.")
                return

            start_pos = ClickableCell.selected_green.scenePos() + ClickableCell.selected_green.rect().center()
            end_pos = self.scenePos() + self.rect().center()
            line_length = QLineF(start_pos, end_pos).length()
            cost = int(line_length // 50)
            game_view_instance.logger.log(f"Koszt stworzenia linii: {cost}, długość linii: {line_length}")

            if cost > ClickableCell.selected_green.value:
                game_view_instance.logger.log("Koszt stworzenia linii przekracza wartość komórki, linia nie może zostać utworzona.")
                return

            ClickableCell.selected_green.setPen(QPen(Qt.black, 2))
            line = ClickableLine(QLineF(start_pos, end_pos), ClickableCell.selected_green, self)
            self.scene().addItem(line)
            self.setPen(QPen(Qt.black, 2))
            ClickableCell.selected_green.update_value(-cost)

            for circle in ClickableCell.selected_green.inner_circles:
                if circle.brush().color() != Qt.black:
                    circle.setBrush(QBrush(Qt.black))
                    break

            # Send line creation notification over network if in network mode
            if scene.game_mode == "Gra sieciowa":
                start_cell_pos = (int(ClickableCell.selected_green.rect().x()), int(ClickableCell.selected_green.rect().y()))
                end_cell_pos = (int(self.rect().x()), int(self.rect().y()))
                start_color = "zielona" if ClickableCell.selected_green.base_color == QColor("#66C676") else "różowa"
                
                line_info = f"UTWORZONO_LINIE:{start_cell_pos[0]},{start_cell_pos[1]}:{end_cell_pos[0]},{end_cell_pos[1]}:{start_color}:szarej"
                
                if hasattr(scene, 'server') and scene.server is not None:
                    # Server is sending
                    for client in scene.server.clients:
                        client.sendall(line_info.encode())
                elif hasattr(scene, 'client') and scene.client is not None:
                    # Client is sending
                    scene.client.send(line_info)

            ClickableCell.selected_green.clear_highlight()  
            ClickableCell.selected_green = None
            ClickableCell.is_creating_line = False

        super().mousePressEvent(event)

    def hoverEnterEvent(self, event):
        if ClickableCell.moving_cell:
            return 
        if self.base_color == QColor("#66C676") and ClickableCell.is_creating_line:
            self.setPen(QPen(QColor("#A4DEFA"), 8, Qt.SolidLine))
        elif (self.base_color == Qt.gray or self.base_color == QColor("#D8177E")) and ClickableCell.selected_green:
            if all(circle.brush().color() == Qt.black for circle in ClickableCell.selected_green.inner_circles):
                return  
            self.setPen(QPen(QColor("#A4DEFA"), 8, Qt.SolidLine))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if ClickableCell.moving_cell:
            return  
        if self.base_color == QColor("#66C676") and ClickableCell.is_creating_line:
            self.setPen(QPen(Qt.black, 2))
        elif (self.base_color == Qt.gray or self.base_color == QColor("#D8177E")) and ClickableCell.selected_green:
            self.setPen(QPen(Qt.black, 2))
        if ClickableCell.is_creating_line and ClickableCell.selected_green == self:
            self.clear_highlight() 
        super().hoverLeaveEvent(event)

    def contextMenuEvent(self, event):
        if ClickableCell.moving_cell:
            return 
        menu = QMenu()
        move_cell_action = menu.addAction("Przesuń komórkę")
        resize_cell_action = menu.addAction("Zmień rozmiar komórek")
        
        action = menu.exec_(event.screenPos())
        if action == move_cell_action:
            view = self.scene().views()[0]
            view.display_message("TRYB PRZESUWANIA KOMÓRKI (OBSŁUGA STRZAŁKAMI NA KLAWIATURZE)")
            if ClickableCell.moving_cell:
                ClickableCell.moving_cell.setPen(QPen(Qt.black, 2))  
            self.setPen(QPen(QColor("#FFA500"), 8, Qt.SolidLine)) 
            ClickableCell.moving_cell = self 
        elif action == resize_cell_action:
            game_view_instance.logger.log("Zwiększ rozmiar komórki")

    def keyPressEvent(self, event):
        if ClickableCell.moving_cell:
            dx, dy = 0, 0
            if event.key() == Qt.Key_Left:
                dx = -5
            elif event.key() == Qt.Key_Right:
                dx = 5
            elif event.key() == Qt.Key_Up:
                dy = -5
            elif event.key() == Qt.Key_Down:
                dy = 5

            if dx != 0 or dy != 0:
                ClickableCell.moving_cell.moveBy(dx, dy)
                for circle in ClickableCell.moving_cell.inner_circles:
                    circle.moveBy(dx, dy)
                if ClickableCell.moving_cell.value_text:
                    ClickableCell.moving_cell.value_text.moveBy(dx, dy)
                if hasattr(ClickableCell.moving_cell, 'top_text'):
                    ClickableCell.moving_cell.top_text.moveBy(dx, dy)
                if hasattr(ClickableCell.moving_cell, 'bottom_text'):
                    ClickableCell.moving_cell.bottom_text.moveBy(dx, dy)
                if hasattr(ClickableCell.moving_cell, 'level_text'):
                    ClickableCell.moving_cell.level_text.moveBy(dx, dy)
                
                global_pos = ClickableCell.moving_cell.scenePos() + ClickableCell.moving_cell.rect().center()
                game_view_instance.logger.log(f"Przesunięto komórkę: global_pos={global_pos}")
    
                self.scene().update_lines() 

    def update_lines(self):
            game_view_instance.logger.log("Aktualizacja linii w scenie...")
            for item in self.items():
                if isinstance(item, ClickableLine):
                    game_view_instance.logger.log(f"Znaleziono linię: {item}")
                    item.update_position() 

class ExplosionEffect(QGraphicsEllipseItem):
    def __init__(self, x, y, color, parent=None):
        super().__init__(0, 0, 40, 40, parent)
        self.setPos(x-20, y-20)
        self.color = QColor(color)
        self.current_radius = 20
        self.max_radius = 60
        self.growth_rate = 5
        self.opacity = 1.0
        self.fade_rate = 0.05
        
        gradient = QRadialGradient(20, 20, 20)
        gradient.setColorAt(0, self.color.lighter(150))
        gradient.setColorAt(0.7, self.color)
        gradient.setColorAt(1, Qt.transparent)
        self.setBrush(QBrush(gradient))
        self.setPen(QPen(Qt.NoPen)) 
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_effect)
        self.timer.start(50)

    def update_effect(self):
        self.current_radius += self.growth_rate
        self.opacity -= self.fade_rate
        
        if self.current_radius >= self.max_radius or self.opacity <= 0:
            self.timer.stop()
            self.scene().removeItem(self)
            return
            
        self.setRect(0, 0, self.current_radius*2, self.current_radius*2)
        self.setPos(self.pos().x() - self.growth_rate, self.pos().y() - self.growth_rate)
        
        gradient = QRadialGradient(self.current_radius, self.current_radius, self.current_radius)
        gradient.setColorAt(0, self.color.lighter(150))
        gradient.setColorAt(0.7, self.color)
        gradient.setColorAt(1, Qt.transparent)
        self.setBrush(QBrush(gradient))
        self.setOpacity(self.opacity)


class GameScene(QGraphicsScene):
    def __init__(self, level=1, game_mode="1 gracz", parent=None):
        super().__init__(parent)
        self.level = level  
        self.game_mode = game_mode 
        self.setSceneRect(0, 0, 900, 900)
        self.init_background()
        self.create_cells()  
        ClickableCell.moving_cell = None
        self.line = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.move_mini_cells)
        self.timer.start(30) 
        self.value_timer = QTimer()
        self.value_timer.timeout.connect(self.increase_cell_values)
        self.value_timer.start(1000)
        self.create_menu_button() 
        self.create_restart_button() 
        self.create_history_buttons()
        self.current_turn = "green"  
        
        # Setup turn timer differently for network vs local play
        self.turn_timer = QTimer()
        self.turn_time_limit = 10  
        self.turn_remaining = self.turn_time_limit
        
        # Only enable turn timer for non-network games
        # For network games, the server will control the timer
        if self.game_mode != "Gra sieciowa":
            self.turn_timer.timeout.connect(self.update_turn_timer)
            self.turn_timer.start(1000)
        
        self.create_turn_timer_display()
        self.create_turn_display()  
        self.replay_steps = []
        self.replay_timer = QTimer()
        self.replay_timer.timeout.connect(self.record_step)
        self.replay_timer.start(1000)

        self.create_save_button()
        
        # Network components
        self.server = None
        self.client = None


    def setup_network_role(self):
        """Sets up the network role (server or client) based on configuration"""
        # Check if we need to create a server
        # This will be called when starting a new game from the menu
        if hasattr(self, '_is_server') and self._is_server:
            self.server = NetworkServer()
            self.server.set_scene(self)  # Set scene reference
            self.server.start()
            game_view_instance.logger.log("Utworzono serwer - grasz zielonymi")
        elif hasattr(self, '_is_client') and self._is_client:
            self.client = NetworkClient()
            self.client.set_scene(self)  # Set scene reference
            self.client.connect()
            game_view_instance.logger.log("Połączono z serwerem - grasz różowymi")

    def set_network_role(self, is_server, ip=None, port=None):
        """Sets the network role before initializing the server/client"""
        self._is_server = is_server
        self._server_ip = ip
        self._server_port = port

    def handle_network_turn_update(self, current_turn, remaining_time):
        """Handle turn updates received from the network"""
        if self.game_mode == "Gra sieciowa":
            old_turn = self.current_turn
            self.current_turn = current_turn
            self.turn_remaining = remaining_time
            
            # Update the UI
            self.turn_timer_display.setPlainText(f"Timer: {self.turn_remaining}s")
            self.turn_display.setPlainText(f"Turn: {self.current_turn.capitalize()}")
            
            # Log the turn change if it's different
            if old_turn != current_turn:
                if self.server is not None:  # Server is playing as green
                    if self.current_turn == "green":
                        game_view_instance.logger.log("Twoja tura! (zielony)")
                    else:
                        game_view_instance.logger.log("Tura przeciwnika (różowy)")
                elif self.client is not None:  # Client is playing as pink
                    if self.current_turn == "pink":
                        game_view_instance.logger.log("Twoja tura! (różowy)")
                    else:
                        game_view_instance.logger.log("Tura przeciwnika (zielony)")
                
                # Reset selected cell and line creation state when turn changes
                ClickableCell.selected_green = None
                ClickableCell.is_creating_line = False
                
                # Remove any suggestion labels
                for item in self.items():
                    if isinstance(item, QGraphicsTextItem) and item.data(0) == "suggestion_label":
                        self.removeItem(item)
                
                # Reset cell highlighting
                for cell in self.cells:
                    cell.setPen(QPen(Qt.black, 2))


    def handle_network_cell_update(self, cell_values):
        """Handle cell value updates received from the network"""
        if self.game_mode != "Gra sieciowa":
            return

        # Determine if we should apply these updates based on whose turn it is
        is_server = self.server is not None
        is_client = self.client is not None
        
        # Only apply updates if:
        # - Server (green) receiving updates during pink's turn
        # - Client (pink) receiving updates during green's turn
        should_apply = (is_server and self.current_turn == "pink") or (is_client and self.current_turn == "green")
        
        if not should_apply:
            # Skip applying updates - we're the active player
            return
            
        game_view_instance.logger.log(f"Aktualizacja wartości komórek z sieci: {len(cell_values)} komórek")
        
        # Apply the received cell values
        for pos_key, cell_data in cell_values.items():
            # Parse position
            x, y = map(int, pos_key.split(","))
            
            # Find the matching cell
            target_cell = None
            for cell in self.cells:
                if int(cell.rect().x()) == x and int(cell.rect().y()) == y:
                    target_cell = cell
                    break
                    
            if not target_cell:
                continue
                
            # Get current cell color and new desired color
            current_color = target_cell.base_color
            new_color = QColor(cell_data["color"])
            
            # Update cell value
            old_value = target_cell.value
            target_cell.value = cell_data["value"]
            
            # Update cell level
            old_level = target_cell.level
            target_cell.level = cell_data["level"]
            
            # Handle color change if needed
            if current_color != new_color:
                if new_color == QColor("#66C676"):
                    target_cell.convert_to_green()
                elif new_color == QColor("#D8177E"):
                    target_cell.convert_to_pink()
                elif new_color == Qt.gray:
                    # Gray cell conversion would be more complex
                    # For simplicity, we're not handling this case
                    pass
            else:
                # Update the value text if it exists
                if target_cell.value_text:
                    target_cell.value_text.setPlainText(str(target_cell.value))
                    
                # Update level display
                target_cell.update_level_display()
                
            # Update gray cell's top value if applicable
            if target_cell.base_color == Qt.gray and "top_value" in cell_data:
                if not hasattr(target_cell, "_actual_top_value"):
                    target_cell._actual_top_value = 0
                    
                target_cell._actual_top_value = cell_data["top_value"]
                if hasattr(target_cell, "top_text"):
                    target_cell.top_text.setPlainText(str(abs(target_cell._actual_top_value)))
                    
            # Update inner circles if present
            if "circles" in cell_data and target_cell.inner_circles:
                circle_states = cell_data["circles"]
                for i, state in enumerate(circle_states):
                    if i < len(target_cell.inner_circles):
                        target_cell.inner_circles[i].setBrush(QBrush(QColor(state)))
        
        # Optionally log some information about what was updated
        if len(cell_values) > 0:
            game_view_instance.logger.log(f"Zaktualizowano {len(cell_values)} komórek z sieci")


    def create_cells(self):
        """Create cells based on the selected level."""
        self.cells = []
        if self.level == 1:
            self.create_level_1_cells()
        elif self.level == 2:
            self.create_level_2_cells()
        elif self.level == 3:
            self.create_level_3_cells()
        elif self.level == 4:
            self.create_level_4_cells()
        elif self.level == 5:
            self.create_level_5_cells()

    def create_level_1_cells(self):
        cell_positions = [
            (250, 250, "#66C676", 10),  
            (550, 550, "#D8177E", 20), 
        ]
        self.add_cells(cell_positions)

    
    def create_level_2_cells(self):
        cell_positions = [
            (150, 650, "#66C676", 20),  
            (650, 150, "#D8177E", 20),  
            (250, 250, QColor(Qt.gray), 0),  
            (550, 550, QColor(Qt.gray), 0),  
        ]
        self.add_cells(cell_positions)

    def record_step(self):
        step = {"cells": [], "lines": []}
        
        for cell in self.cells:
            cell_data = {
                "x": int(cell.rect().x()),
                "y": int(cell.rect().y()),
                "value": cell.value,
                "color": cell.base_color.name(),
                "level": cell.level
            }

            if cell.inner_circles:
                colors = [circle.brush().color().name() for circle in cell.inner_circles]
                cell_data["circles"] = ",".join(colors)


            if cell.base_color == Qt.gray and hasattr(cell, "_actual_top_value"):
                cell_data["top_value"] = cell._actual_top_value
            step["cells"].append(cell_data)
            
        
        for item in self.items():
            if isinstance(item, ClickableLine):
                line_data = {
                    "start_x": int(item.start_cell.rect().x()),
                    "start_y": int(item.start_cell.rect().y()),
                    "end_x": int(item.end_cell.rect().x()),
                    "end_y": int(item.end_cell.rect().y()),
                    "color": item.pen().color().name()
                }
                step["lines"].append(line_data)

        step["turn"] = self.current_turn
        step["timer"] = self.turn_remaining
        
        self.replay_steps.append(step)



    def create_level_3_cells(self):
        cell_positions = [
            (100, 700, "#66C676", 15),
            (700, 700, "#66C676", 15),
            (700, 100, "#D8177E", 15),
            (100, 100, "#D8177E", 15),
            (300, 300, QColor(Qt.gray), 0),
            (500, 500, QColor(Qt.gray), 0),
            (400, 400, QColor(Qt.gray), 0),
        ]
        self.add_cells(cell_positions)

    def create_level_4_cells(self):
        cell_positions = [
            (100, 500, "#66C676", 5),
            (400, 500, "#66C676", 10),
            (700, 500, "#66C676", 5),
            (100, 300, "#D8177E", 5),
            (400, 300, "#D8177E", 10),
            (700, 300, "#D8177E", 5),
            (250, 650, QColor(Qt.gray), 0),
            (550, 650, QColor(Qt.gray), 0),
            (250, 150, QColor(Qt.gray), 0),
            (550, 150, QColor(Qt.gray), 0),
        ]
        self.add_cells(cell_positions)


    def create_save_button(self):
        save_button = HoverableRectItem(700, 70, 160, 30)
        save_button.setBrush(QBrush(QColor(10, 10, 50)))
        save_button.setPen(QPen(Qt.white, 2))
        self.addItem(save_button)

        save_text = QGraphicsTextItem("ZAKOŃCZ I ZAPISZ", save_button)
        save_text.setFont(QFont("Arial", 10))
        save_text.setDefaultTextColor(Qt.white)
        save_text_rect = save_text.boundingRect()
        save_text.setPos(
            save_button.rect().center().x() - save_text_rect.width() / 2,
            save_button.rect().center().y() - save_text_rect.height() / 2
        )
        save_button.mousePressEvent = self.save_and_exit_game

    def save_and_exit_game(self, event):
        save_current_game_to_xml(self)
        QApplication.instance().quit()

    def create_level_5_cells(self):
        cell_positions = [
            (350, 450, "#66C676", 10),
            (450, 350, "#D8177E", 10),
            (170, 630, QColor(Qt.gray), 0),
            (630, 630, QColor(Qt.gray), 0),
            (170, 170, QColor(Qt.gray), 0),
            (630, 170, QColor(Qt.gray), 0),

            (130, 400, QColor(Qt.gray), 0),
            (400, 130, QColor(Qt.gray), 0),
            (670, 400, QColor(Qt.gray), 0),
            (400, 670, QColor(Qt.gray), 0),
        ]
        self.add_cells(cell_positions)

    def create_history_buttons(self):
        def create_button(x, y, label, callback):
            button = HoverableRectItem(x, y, 120, 30)
            button.setBrush(QBrush(QColor(10, 10, 50)))
            button.setPen(QPen(Qt.white, 2))
            self.addItem(button)

            text = QGraphicsTextItem(label, button)
            text.setFont(QFont("Arial", 6))
            text.setDefaultTextColor(Qt.white)
            text_rect = text.boundingRect()
            text.setPos(
                button.rect().center().x() - text_rect.width() / 2,
                button.rect().center().y() - text_rect.height() / 2
            )
            button.mousePressEvent = callback

        create_button(20, 20, "SAVE HISTORY [XML]", self.save_history_to_xml)
        create_button(160, 20, "REPLAY [XML]", self.launch_replay)
        create_button(20, 60, "SAVE HISTORY [JSON]", self.save_history_to_json)
        create_button(160, 60, "REPLAY [JSON]", self.launch_json_replay)
        create_button(20, 100, "SAVE HISTORY [MONGO]", self.save_history_to_mongo)
        create_button(160, 100, "REPLAY [MONGO]", self.launch_mongo_replay)


    def apply_step(self, step_data):
        for cell_data in step_data["cells"]:
            for cell in self.cells:
                if int(cell.rect().x()) == cell_data["x"] and int(cell.rect().y()) == cell_data["y"]:
                    cell.value = cell_data["value"]
                    cell.level = cell_data["level"]
                    cell.update_level_display()

                    new_color = QColor(cell_data["color"])
                    if cell.base_color != new_color:
                        cell.base_color = new_color
                        cell.set_gradient()

                    if cell.base_color != Qt.gray:
                        if hasattr(cell, 'top_text'):
                            self.removeItem(cell.top_text)
                            del cell.top_text
                        if hasattr(cell, 'bottom_text'):
                            self.removeItem(cell.bottom_text)
                            del cell.bottom_text

                        if cell.value_text:
                            cell.value_text.setPlainText(str(cell.value))
                        else:
                            text_item = QGraphicsTextItem(str(cell.value))
                            text_item.setFont(QFont("Arial", 14, QFont.Bold))
                            text_item.setDefaultTextColor(Qt.white)
                            text_rect = text_item.boundingRect()
                            text_item.setPos(
                                cell.rect().x() + 50 - text_rect.width() / 2,
                                cell.rect().y() + 50 - text_rect.height() / 2
                            )
                            self.addItem(text_item)
                            cell.set_value_text(text_item)

                        if not hasattr(cell, 'level_text'):
                            level_text = QGraphicsTextItem(f"LVL {cell.level}")
                            level_text.setFont(QFont("Arial", 10))
                            level_text.setDefaultTextColor(Qt.white)
                            level_text_rect = level_text.boundingRect()
                            level_text.setPos(
                                cell.rect().x() + 50 - level_text_rect.width() / 2,
                                cell.rect().y() + 100
                            )
                            self.addItem(level_text)
                            cell.set_level_text(level_text)


                        circle_colors = ["#ffffff", "#ffffff"]
                        if "circles" in cell_data:
                            circle_colors = cell_data["circles"].split(",")

                        for i, (dx, dy) in enumerate([(-20, -20), (20, 20)]):
                            color = QColor(circle_colors[i]) if i < len(circle_colors) else Qt.white
                            if i < len(cell.inner_circles):
                                cell.inner_circles[i].setBrush(QBrush(color))
                            else:
                                inner_circle = QGraphicsEllipseItem(
                                    cell.rect().x() + 50 + dx - 10,
                                    cell.rect().y() + 50 + dy - 10,
                                    20, 20
                                )
                                inner_circle.setBrush(QBrush(color))
                                inner_circle.setPen(QPen(Qt.black, 1))
                                inner_circle.setZValue(1)
                                self.addItem(inner_circle)
                                cell.inner_circles.append(inner_circle)


                    else:
                        if "top_value" in cell_data:
                            cell._actual_top_value = cell_data["top_value"]
                            if hasattr(cell, "top_text"):
                                cell.top_text.setPlainText(str(abs(cell._actual_top_value)))

        for item in self.items():
            if isinstance(item, ClickableLine):
                self.removeItem(item)

        for line_data in step_data.get("lines", []):
            start = next((c for c in self.cells if int(c.rect().x()) == line_data["start_x"] and int(c.rect().y()) == line_data["start_y"]), None)
            end = next((c for c in self.cells if int(c.rect().x()) == line_data["end_x"] and int(c.rect().y()) == line_data["end_y"]), None)
            if start and end:
                line = ClickableLine(QLineF(
                    start.scenePos() + start.rect().center(),
                    end.scenePos() + end.rect().center()
                ), start, end)
                line.setPen(QPen(QColor(line_data["color"]), 8))
                self.addItem(line)

        self.current_turn = step_data.get("turn", "green")
        self.turn_remaining = step_data.get("timer", 10)
        self.turn_display.setPlainText(f"Turn: {self.current_turn.capitalize()}")
        self.turn_timer_display.setPlainText(f"Timer: {self.turn_remaining}s")




    def save_history_to_xml(self, event=None):
        root = ET.Element("game")
        root.set("level", str(self.level))
        root.set("mode", self.game_mode) 

        for step_num, step in enumerate(self.replay_steps):
            step_el = ET.SubElement(root, "step", {
                "time": str(step_num),
                "turn": step["turn"],
                "timer": str(step["timer"])
            })


            for cell_data in step["cells"]:
                cell_el = ET.SubElement(step_el, "cell", {
                    "x": str(cell_data["x"]),
                    "y": str(cell_data["y"]),
                    "value": str(cell_data["value"]),
                    "color": cell_data["color"],
                    "level": str(cell_data["level"])
                })

                if "top_value" in cell_data:
                    cell_el.set("top_value", str(cell_data["top_value"]))

                if "circles" in cell_data:
                    cell_el.set("circles", cell_data["circles"])

                for line_data in step["lines"]:
                    ET.SubElement(step_el, "line", {
                        "start_x": str(line_data["start_x"]),
                        "start_y": str(line_data["start_y"]),
                        "end_x": str(line_data["end_x"]),
                        "end_y": str(line_data["end_y"]),
                        "color": line_data["color"]  
                    })



        tree = ET.ElementTree(root)
        tree.write("history.xml")
        game_view_instance.logger.log("Zapisano pełną historię do history.xml")

    def save_history_to_json(self, event=None):
        json_data = {
            "level": self.level,
            "mode": self.game_mode, 
            "steps": self.replay_steps
        }

        with open("history.json", "w") as f:
            json.dump(json_data, f, indent=4)

        game_view_instance.logger.log("Zapisano historię do history.json")

    def save_history_to_mongo(self, event=None):
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017/")
        db = client["game_db"]
        collection = db["full_game_history"]

        document = {
            "level": self.level,
            "mode": self.game_mode, 
            "steps": self.replay_steps
        }

        collection.insert_one(document)
        game_view_instance.logger.log("✅ Zapisano historię do MongoDB (pełna gra).")

    def launch_mongo_replay(self, event=None):
        import subprocess
        subprocess.Popen([sys.executable, "replay_view_mongo.py"])



    def launch_replay(self, event=None):
        if not os.path.exists("history.xml"):
            game_view_instance.logger.log("Brak pliku history.xml – najpierw zapisz poziom.")
            return
        subprocess.Popen([sys.executable, "replay_view.py"])

    def launch_json_replay(self, event=None):
        if not os.path.exists("history.json"):
            game_view_instance.logger.log("Brak pliku history.json – najpierw zapisz historię.")
            return
        subprocess.Popen([sys.executable, "replay_view_json.py"])



    def add_cells(self, cell_positions):
        for x, y, color, value in cell_positions:
            cell_rect = QRectF(x, y, 100, 100)
            cell = ClickableCell(cell_rect, color, value)
            self.cells.append(cell)
            if color == QColor(Qt.gray):
                self.addItem(cell)
            else:
                text_item = QGraphicsTextItem(str(value))
                text_item.setFont(QFont("Arial", 14, QFont.Bold))
                text_item.setDefaultTextColor(Qt.white)
                text_rect = text_item.boundingRect()
                text_item.setPos(
                    x + 50 - text_rect.width() / 2,
                    y + 50 - text_rect.height() / 2
                )
                self.addItem(cell)
                self.addItem(text_item)
                cell.set_value_text(text_item)
                for dx, dy in [(-20, -20), (20, 20)]:
                    inner_circle = QGraphicsEllipseItem(x + 50 + dx - 10, y + 50 + dy - 10, 20, 20)
                    inner_circle.setBrush(QBrush(Qt.white))
                    inner_circle.setPen(QPen(Qt.black, 1))
                    inner_circle.setZValue(1)
                    self.addItem(inner_circle)
                    cell.inner_circles.append(inner_circle)
                level_text = QGraphicsTextItem("LVL 1")
                level_text.setFont(QFont("Arial", 10))
                level_text.setDefaultTextColor(Qt.white)
                level_text_rect = level_text.boundingRect()
                level_text.setPos(
                    x + 50 - level_text_rect.width() / 2,
                    y + 100
                )
                self.addItem(level_text)
                cell.set_level_text(level_text)
            if color == QColor(Qt.gray):
                top_text = QGraphicsTextItem("0")
                top_text.setFont(QFont("Arial", 14, QFont.Bold))
                top_text.setDefaultTextColor(Qt.white)
                top_text_rect = top_text.boundingRect()
                top_text.setPos(
                    x + 50 - top_text_rect.width() / 2,
                    y + 10
                )
                self.addItem(top_text)
                cell.set_top_text(top_text)
                bottom_text = QGraphicsTextItem("8")
                bottom_text.setFont(QFont("Arial", 14, QFont.Bold))
                bottom_text.setDefaultTextColor(Qt.white)
                bottom_text_rect = bottom_text.boundingRect()
                bottom_text.setPos(
                    x + 50 - bottom_text_rect.width() / 2,
                    y + 55
                )
                self.addItem(bottom_text)
                cell.bottom_text = bottom_text

    def create_turn_timer_display(self):
        self.turn_timer_display = QGraphicsTextItem(f"Timer: {self.turn_remaining}s")
        self.turn_timer_display.setFont(QFont("Arial", 14, QFont.Bold))
        self.turn_timer_display.setDefaultTextColor(Qt.white)
        self.turn_timer_display.setPos(600, 50)  
        self.addItem(self.turn_timer_display)

    def create_turn_display(self):
        self.turn_display = QGraphicsTextItem(f"Turn: {self.current_turn.capitalize()}")
        self.turn_display.setFont(QFont("Arial", 16, QFont.Bold))
        self.turn_display.setDefaultTextColor(Qt.white)
        self.turn_display.setPos(600, 20)  
        self.addItem(self.turn_display)

    def update_turn_timer(self):
        self.turn_remaining -= 1
        if self.turn_remaining <= 0:
            self.switch_turn()
        self.turn_timer_display.setPlainText(f"Timer: {self.turn_remaining}s")

    def switch_turn(self):
        self.current_turn = "pink" if self.current_turn == "green" else "green"
        self.turn_remaining = self.turn_time_limit
        self.turn_timer_display.setPlainText(f"Pozostały czas: {self.turn_remaining}s")
        self.turn_display.setPlainText(f"Turn: {self.current_turn.capitalize()}") 
        ClickableCell.selected_green = None
        ClickableCell.is_creating_line = False

        # Display turn status for network games
        if self.game_mode == "Gra sieciowa":
            if self.server is not None:  # Server is playing as green
                if self.current_turn == "green":
                    game_view_instance.logger.log("Twoja tura! (zielony)")
                else:
                    game_view_instance.logger.log("Tura przeciwnika (różowy)")
            elif self.client is not None:  # Client is playing as pink
                if self.current_turn == "pink":
                    game_view_instance.logger.log("Twoja tura! (różowy)")
                else:
                    game_view_instance.logger.log("Tura przeciwnika (zielony)")

        for item in self.items():
            if isinstance(item, QGraphicsTextItem) and item.data(0) == "suggestion_label":
                self.removeItem(item)

        for cell in self.cells:
            cell.setPen(QPen(Qt.black, 2))

    def init_background(self, color1=QColor(10, 10, 50), color2=QColor(20, 20, 100)):
        gradient = QLinearGradient(0, 0, 900, 900)
        gradient.setColorAt(0, color1)
        gradient.setColorAt(1, color2)
        self.setBackgroundBrush(QBrush(gradient))

    def update_lines(self):
            game_view_instance.logger.log("Aktualizacja linii w scenie...")
            for item in self.items():
                if isinstance(item, ClickableLine):
                    game_view_instance.logger.log(f"Znaleziono linię: {item}")
                    item.update_position() 

    def get_attacker(self, target_cell):
        for item in self.items():
            if isinstance(item, ClickableLine) and item.end_cell == target_cell:
                return item.start_cell
        return None
    
    def mouseMoveEvent(self, event):
        if ClickableCell.moving_cell:
            return 
        if ClickableCell.selected_green and ClickableCell.is_creating_line:
            if all(circle.brush().color() == Qt.black for circle in ClickableCell.selected_green.inner_circles):
                return 
            
            if not self.line:
                self.line = QGraphicsLineItem()
                color = "#D8177E" if ClickableCell.selected_green.base_color == QColor("#D8177E") else "#66C676"
                self.line.setPen(QPen(QColor(color), 8))
                self.addItem(self.line)
                self.line.setZValue(-1) 
            
            start_point = ClickableCell.selected_green.scenePos() + ClickableCell.selected_green.rect().center()
            end_point = event.scenePos()
            self.line.setLine(QLineF(start_point, end_point)) 
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if ClickableCell.moving_cell:
            return 
        if self.line:
            self.removeItem(self.line)
            self.line = None
        super().mouseReleaseEvent(event)

    def mousePressEvent(self, event):
        # Skip interaction if not your turn in network mode
        if self.game_mode == "Gra sieciowa":
            is_server = self.server is not None
            is_client = self.client is not None
            
            if (is_server and self.current_turn != "green") or (is_client and self.current_turn != "pink"):
                game_view_instance.logger.log("Teraz nie twoja tura!")
                return
        
        # For moving cells
        if ClickableCell.moving_cell:
            item = self.itemAt(event.scenePos(), QTransform())
            if isinstance(item, ClickableCell):
                ClickableCell.moving_cell.setPen(QPen(Qt.black, 2))  
                item.setPen(QPen(QColor("#FFA500"), 8, Qt.SolidLine))  
                ClickableCell.moving_cell = item 
            return
        
        # For handling clicked items
        item = self.itemAt(event.scenePos(), QTransform())
        if isinstance(item, ClickableLine):
            # Line handling is now checked within the ClickableLine class
            item.mousePressEvent(event)
        elif not isinstance(item, ClickableCell) and ClickableCell.selected_green:
            ClickableCell.selected_green.clear_highlight() 
            ClickableCell.selected_green.setPen(QPen(Qt.black, 2)) 
            ClickableCell.selected_green = None
            ClickableCell.is_creating_line = False
            if self.line:
                self.removeItem(self.line)
                self.line = None
        super().mousePressEvent(event)

    def move_mini_cells(self):
        for item in self.items():
            if isinstance(item, ClickableLine):
                if not item.mini_cells:
                    color = "#7D1B4F" if item.start_cell.base_color == QColor("#D8177E") else "#186527"
                    mini_cell = QGraphicsEllipseItem(-5, -5, 10, 10, item)
                    mini_cell.setBrush(QBrush(QColor(color)))
                    mini_cell.setPen(QPen(QColor(color), 1))
                    mini_cell.setPos(item.line().p1())
                    mini_cell.setZValue(1)
                    item.mini_cells.append(mini_cell)

                for mini_cell in item.mini_cells:
                    current_pos = mini_cell.pos()
                    end_pos = item.line().p2()
                    direction = end_pos - current_pos
                    step = direction / 10  
                    mini_cell.setPos(current_pos + step)

                    if (current_pos - end_pos).manhattanLength() < 5:
                        self.removeItem(mini_cell)
                        item.mini_cells.remove(mini_cell)

                        attacker = item.start_cell
                        explosion = ExplosionEffect(end_pos.x(), end_pos.y(), attacker.base_color)
                        self.addItem(explosion)

                        for cell in self.cells:
                            if cell.rect().contains(end_pos):
                                if cell.base_color == Qt.gray:
                                    if attacker.base_color == QColor("#66C676"):
                                        cell.update_top_text(1)
                                    elif attacker.base_color == QColor("#D8177E"):
                                        cell.update_top_text(-1)
                                elif cell.base_color != attacker.base_color:
                                    damage = attacker.get_attack_power_per_mini_cell()
                                    game_view_instance.logger.log(f"Mini-komórka z poziomem {attacker.level} atakuje! Obrażenia: {damage}")
                                    cell.update_value(-damage, caused_by_enemy=True)
                                elif cell.base_color == attacker.base_color:
                                    cell.update_value(1)

                                break  

                        item.start_cell.update_value(-1, caused_by_enemy=False)

        self.check_winner()

    def increase_cell_values(self):
        """Increment cell values based on color and game mode"""
        # In network mode, only increase values during your turn
        if self.game_mode == "Gra sieciowa":
            is_server = self.server is not None
            is_client = self.client is not None
            
            # Only increase values if it's your turn
            if (is_server and self.current_turn != "green") or (is_client and self.current_turn != "pink"):
                return  # Not your turn, don't increase values
        
        # Regular value increase logic
        for cell in self.cells:
            if cell.base_color == QColor("#66C676"): 
                cell.update_value(1)
            elif cell.base_color == QColor("#D8177E"):  
                cell.update_value(1)

        self.check_winner()

    def check_winner(self):
        green_cells = all(cell.base_color == QColor("#66C676") for cell in self.cells)
        pink_cells = all(cell.base_color == QColor("#D8177E") for cell in self.cells)

        if green_cells:
            self.declare_winner("ZWYCIĘSTWO ZIELONYCH")
        elif pink_cells:
            self.declare_winner("ZWYCIĘSTWO RÓŻOWYCH")

    def declare_winner(self, message):
        if not hasattr(self, 'winner_label'):
            self.winner_label = QGraphicsTextItem(message)
            self.winner_label.setFont(QFont("Arial", 30, QFont.Bold))
            self.winner_label.setDefaultTextColor(Qt.white)
            self.winner_label.setPos(450 - self.winner_label.boundingRect().width() / 2, 400)
            self.addItem(self.winner_label)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.scenePos(), QTransform())
        if isinstance(item, ClickableCell):
            item.contextMenuEvent(event)
        else:
            menu = QMenu()
            change_background_menu = menu.addMenu("Zmień tło")

            current_action = QAction("Obecne", self)
            current_action.setCheckable(True)
            current_action.setChecked(True)
            change_background_menu.addAction(current_action)

            orange_action = QAction("Pomarańczowe", self)
            orange_action.setCheckable(True)
            change_background_menu.addAction(orange_action)

            red_action = QAction("Czerwone", self)
            red_action.setCheckable(True)
            change_background_menu.addAction(red_action)

            beige_action = QAction("Beżowe", self)
            beige_action.setCheckable(True)
            change_background_menu.addAction(beige_action)

            action = menu.exec_(event.screenPos())
            if action == current_action:
                self.init_background(QColor(10, 10, 50), QColor(20, 20, 100))
            elif action == orange_action:
                self.init_background(QColor(255, 165, 0), QColor(255, 140, 0))
            elif action == red_action:
                self.init_background(QColor(255, 0, 0), QColor(139, 0, 0))
            elif action == beige_action:
                self.init_background(QColor(245, 245, 220), QColor(222, 184, 135))

    def create_menu_button(self):
        menu_button = HoverableRectItem(350, 20, 200, 40)
        menu_button.setBrush(QBrush(QColor(10, 10, 50)))
        menu_button.setPen(QPen(Qt.white, 2))
        self.addItem(menu_button)

        menu_text = QGraphicsTextItem("MENU", menu_button)
        menu_text.setFont(QFont("Arial", 20))
        menu_text.setDefaultTextColor(Qt.white)
        menu_text_rect = menu_text.boundingRect()
        menu_text.setPos(
            menu_button.rect().center().x() - menu_text_rect.width() / 2,
            menu_button.rect().center().y() - menu_text_rect.height() / 2
        )

        menu_button.mousePressEvent = self.back_to_main_menu

    def create_restart_button(self):
        restart_button = HoverableRectItem(400, 70, 100, 30)
        restart_button.setBrush(QBrush(QColor(10, 10, 50)))
        restart_button.setPen(QPen(Qt.white, 2))
        self.addItem(restart_button)

        restart_text = QGraphicsTextItem("RESTART", restart_button)
        restart_text.setFont(QFont("Arial", 10))
        restart_text.setDefaultTextColor(Qt.white)
        restart_text_rect = restart_text.boundingRect()
        restart_text.setPos(
            restart_button.rect().center().x() - restart_text_rect.width() / 2,
            restart_button.rect().center().y() - restart_text_rect.height() / 2
        )

        restart_button.mousePressEvent = self.restart_game

    def restart_game(self, event):
        view = self.views()[0]
        view.suggestion_label.hide()  
        self.clear()  
        self.init_background()  
        self.create_cells() 
        self.create_menu_button() 
        self.create_restart_button()
        self.create_turn_timer_display() 
        self.create_turn_display()  
        self.timer.start(30)  
        self.value_timer.start(1000)  
        self.turn_remaining = self.turn_time_limit 
        self.current_turn = "green"  
        self.turn_timer.start(1000)  

        ClickableCell.moving_cell = None

        if hasattr(self, 'winner_label'):
            self.removeItem(self.winner_label)
            del self.winner_label

    def back_to_main_menu(self, event):
        view = self.views()[0]
        view.suggestion_label.hide()  
        view.setScene(MainMenuScene())

        ClickableCell.moving_cell = None

        if hasattr(self, 'winner_label'):
            self.removeItem(self.winner_label)
            del self.winner_label

    def suggest_best_move(self):
        best_move = None
        max_value_difference = -float('inf')

        for item in self.items():
            if isinstance(item, QGraphicsTextItem) and item.data(0) == "suggestion_label":
                self.removeItem(item)

        for cell in self.cells:
            if cell.base_color == QColor("#66C676") and self.current_turn == "green":
                for target in self.cells:
                    if target != cell and target.base_color != QColor("#66C676"):
                        value_difference = cell.value - target.value
                        if value_difference > max_value_difference:
                            max_value_difference = value_difference
                            best_move = (cell, target)
            elif cell.base_color == QColor("#D8177E") and self.current_turn == "pink":
                for target in self.cells:
                    if target != cell and target.base_color != QColor("#D8177E"):
                        value_difference = cell.value - target.value
                        if value_difference > max_value_difference:
                            max_value_difference = value_difference
                            best_move = (cell, target)

        if best_move:
            source, target = best_move
            suggestion = f"Attack from cell at ({source.rect().x()}, {source.rect().y()}) to cell at ({target.rect().x()}, {target.rect().y()})."

            attacker_label = QGraphicsTextItem("Attacker")
            attacker_label.setFont(QFont("Arial", 12, QFont.Bold))
            attacker_label.setDefaultTextColor(Qt.green if self.current_turn == "green" else Qt.red)
            attacker_label.setPos(source.rect().x() + 50 - attacker_label.boundingRect().width() / 2, source.rect().y() - 20)
            attacker_label.setData(0, "suggestion_label") 
            self.addItem(attacker_label)

            target_label = QGraphicsTextItem("Target")
            target_label.setFont(QFont("Arial", 12, QFont.Bold))
            target_label.setDefaultTextColor(Qt.green if self.current_turn == "green" else Qt.red)
            target_label.setPos(target.rect().x() + 50 - target_label.boundingRect().width() / 2, target.rect().y() - 20)
            target_label.setData(0, "suggestion_label")  
            self.addItem(target_label)
        else:
            suggestion = "No valid moves available."

        game_view_instance.logger.log(suggestion)
        view = self.views()[0]
        view.display_suggestion(suggestion)

class LevelSelectionScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 900, 900)
        self.init_background()
        self.create_level_selection_menu()

    def init_background(self, color1=QColor(10, 10, 50), color2=QColor(20, 20, 100)):
        gradient = QLinearGradient(0, 0, 900, 900)
        gradient.setColorAt(0, color1)
        gradient.setColorAt(1, color2)
        self.setBackgroundBrush(QBrush(gradient))

    def create_level_selection_menu(self):
        title = QGraphicsTextItem("WYBÓR POZIOMU")
        title.setFont(QFont("Arial", 30, QFont.Bold))
        title.setDefaultTextColor(Qt.white)
        title_rect = title.boundingRect()
        title.setPos(450 - title_rect.width() / 2, 100)
        self.addItem(title)

        levels = ["POZIOM 1", "POZIOM 2", "POZIOM 3", "POZIOM 4", "POZIOM 5"]
        for i, level in enumerate(levels):
            level_button = HoverableRectItem(250, 200 + i * 100, 400, 50)
            level_button.setBrush(QBrush(QColor(10, 10, 50)))
            level_button.setPen(QPen(Qt.white, 2))
            self.addItem(level_button)

            level_text = QGraphicsTextItem(level, level_button)
            level_text.setFont(QFont("Arial", 20, QFont.Bold))
            level_text.setDefaultTextColor(Qt.white)
            level_text_rect = level_text.boundingRect()
            level_text.setPos(
                level_button.rect().center().x() - level_text_rect.width() / 2,
                level_button.rect().center().y() - level_text_rect.height() / 2
            )

            level_button.mousePressEvent = lambda event, lvl=level: self.start_game(event, lvl)

        back_button = HoverableRectItem(100, 700, 700, 50)
        back_button.setBrush(QBrush(QColor(10, 10, 50)))
        back_button.setPen(QPen(Qt.white, 2))
        self.addItem(back_button)

        back_text = QGraphicsTextItem("POWRÓT DO MENU GŁÓWNEGO", back_button)
        back_text.setFont(QFont("Arial", 20, QFont.Bold))
        back_text.setDefaultTextColor(Qt.white)
        back_text_rect = back_text.boundingRect()
        back_text.setPos(
            back_button.rect().center().x() - back_text_rect.width() / 2,
            back_button.rect().center().y() - back_text_rect.height() / 2
        )

        back_button.mousePressEvent = self.back_to_main_menu

    def start_game(self, event, level):
        dialog = ConfigDialog()
        if dialog.exec_() == QDialog.Accepted:
            selected_mode = dialog.get_selected_mode()
            ip, port = dialog.get_ip_port()
            print(f"Wybrany tryb gry: {selected_mode}")

            view = self.views()[0]
            scene = GameScene(level=int(level.split()[-1]), game_mode=selected_mode)

            if selected_mode == "Gra sieciowa":
                if ip == "server":
                    # Create waiting dialog for server
                    wait_dialog = QDialog()
                    wait_dialog.setWindowTitle("Oczekiwanie na połączenie")
                    layout = QVBoxLayout()
                    label = QLabel("Serwer nasłuchuje... Oczekiwanie na połączenie klienta.")
                    layout.addWidget(label)
                    wait_dialog.setLayout(layout)
                    wait_dialog.setFixedSize(300, 100)
                    
                    # Start server
                    server = NetworkServer(port=port)
                    server.set_scene(scene)  # Set scene reference
                    server.start()
                    scene.server = server  # Store server reference
                    
                    # Check connection in background
                    def check_connection():
                        while not server.connected:
                            QApplication.processEvents()
                        wait_dialog.accept()
                    
                    threading.Thread(target=check_connection, daemon=True).start()
                    wait_dialog.exec_()
                    
                    game_view_instance.logger.log("Klient połączony! Grasz zielonymi.")
                else:
                    # Connect as client
                    client = NetworkClient(ip=ip, port=port)
                    client.set_scene(scene)  # Set scene reference
                    client.connect()
                    client.send("Gracz dołączył!")
                    scene.client = client  # Store client reference
                    
                    game_view_instance.logger.log("Połączono z serwerem! Grasz różowymi.")

            view.setScene(scene)


    def back_to_main_menu(self, event):
        view = self.views()[0]
        view.setScene(MainMenuScene())

class MainMenuScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 900, 900)
        self.init_background()
        self.create_menu()

    def init_background(self, color1=QColor(10, 10, 50), color2=QColor(20, 20, 100)):
        gradient = QLinearGradient(0, 0, 900, 900)
        gradient.setColorAt(0, color1)
        gradient.setColorAt(1, color2)
        self.setBackgroundBrush(QBrush(gradient))

    def create_menu(self):
        title = QGraphicsTextItem("MENU")
        title.setFont(QFont("Arial", 30, QFont.Bold))
        title.setDefaultTextColor(Qt.white)
        title_rect = title.boundingRect()
        title.setPos(450 - title_rect.width() / 2, 200)
        self.addItem(title)

        play_button = HoverableRectItem(250, 300, 400, 100)
        play_button.setBrush(QBrush(QColor(10, 10, 50)))
        play_button.setPen(QPen(Qt.white, 2))
        self.addItem(play_button)

        play_text = QGraphicsTextItem("GRAJ", play_button)
        play_text.setFont(QFont("Arial", 20, QFont.Bold))
        play_text.setDefaultTextColor(Qt.white)
        play_text_rect = play_text.boundingRect()
        play_text.setPos(
            play_button.rect().center().x() - play_text_rect.width() / 2,
            play_button.rect().center().y() - play_text_rect.height() / 2
        )

        level_button = HoverableRectItem(250, 450, 400, 100)
        level_button.setBrush(QBrush(QColor(10, 10, 50)))
        level_button.setPen(QPen(Qt.white, 2))
        self.addItem(level_button)

        level_text = QGraphicsTextItem("WYBIERZ POZIOM", level_button)
        level_text.setFont(QFont("Arial", 20, QFont.Bold))
        level_text.setDefaultTextColor(Qt.white)
        level_text_rect = level_text.boundingRect()
        level_text.setPos(
            level_button.rect().center().x() - level_text_rect.width() / 2,
            level_button.rect().center().y() - level_text_rect.height() / 2
        )

        exit_button = HoverableRectItem(250, 600, 400, 100) 
        exit_button.setBrush(QBrush(QColor(10, 10, 50)))
        exit_button.setPen(QPen(Qt.white, 2))
        self.addItem(exit_button)

        exit_text = QGraphicsTextItem("ZAKOŃCZ", exit_button)
        exit_text.setFont(QFont("Arial", 20, QFont.Bold))
        exit_text.setDefaultTextColor(Qt.white)
        exit_text_rect = exit_text.boundingRect()
        exit_text.setPos(
            exit_button.rect().center().x() - exit_text_rect.width() / 2,
            exit_button.rect().center().y() - exit_text_rect.height() / 2
        )

        play_button.mousePressEvent = self.start_game
        level_button.mousePressEvent = self.show_level_selection
        exit_button.mousePressEvent = self.exit_game

# Update the start_game method in MainMenuScene

    def start_game(self, event):
        dialog = ConfigDialog()
        if dialog.exec_() == QDialog.Accepted:
            selected_mode = dialog.get_selected_mode()
            ip, port = dialog.get_ip_port()
            print(f"Wybrany tryb gry: {selected_mode}")

            view = self.views()[0]
            scene = GameScene(game_mode=selected_mode)

            if selected_mode == "Gra sieciowa":
                if ip == "server":
                    # Create waiting dialog for server
                    wait_dialog = QDialog()
                    wait_dialog.setWindowTitle("Oczekiwanie na połączenie")
                    layout = QVBoxLayout()
                    label = QLabel("Serwer nasłuchuje... Oczekiwanie na połączenie klienta.")
                    layout.addWidget(label)
                    wait_dialog.setLayout(layout)
                    wait_dialog.setFixedSize(300, 100)
                    
                    # Start server
                    server = NetworkServer(port=port)
                    server.set_scene(scene)  # Set scene reference
                    server.start()
                    scene.server = server  # Store server reference
                    
                    # Check connection in background
                    def check_connection():
                        while not server.connected:
                            QApplication.processEvents()
                        wait_dialog.accept()
                    
                    threading.Thread(target=check_connection, daemon=True).start()
                    wait_dialog.exec_()
                    
                    game_view_instance.logger.log("Klient połączony! Grasz zielonymi.")
                else:
                    # Connect as client
                    client = NetworkClient(ip=ip, port=port)
                    client.set_scene(scene)  # Set scene reference
                    client.connect()
                    client.send("Gracz dołączył!")
                    scene.client = client  # Store client reference
                    
                    game_view_instance.logger.log("Połączono z serwerem! Grasz różowymi.")

            view.setScene(scene)


    def show_level_selection(self, event):
        view = self.views()[0]
        view.setScene(LevelSelectionScene())

    def exit_game(self, event):
        QApplication.instance().quit() 

class HoverableRectItem(QGraphicsRectItem):
    def __init__(self, x, y, width, height, parent=None):
        super().__init__(x, y, width, height, parent)
        self.default_brush = QBrush(QColor(10, 10, 50))
        self.setBrush(self.default_brush)
        self.setAcceptHoverEvents(True) 

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(QColor("#001E5A")))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(self.default_brush)
        super().hoverLeaveEvent(event)

class GameView(QGraphicsView):
    def __init__(self):
        super().__init__()
        global game_view_instance
        game_view_instance = self 
        self.suggestion_button = QPushButton("PODPOWIEDŹ", self)  
        self.suggestion_button.setGeometry(400, 780, 100, 40) 
        self.suggestion_button.setFont(QFont("Arial", 9, QFont.Bold))
        self.suggestion_button.setStyleSheet("background-color: rgb(10, 10, 50); color: white;")
        self.suggestion_button.clicked.connect(self.request_suggestion)
        self.suggestion_button.hide()  

        self.logger_widget = QTextEdit(self)
        self.logger_widget.setGeometry(40, 830, 820, 60)
        self.logger_widget.setReadOnly(True)
        self.logger_widget.setStyleSheet("background-color: rgb(10, 10, 50); color: white;")
        self.logger_widget.hide()

        self.logger = Logger(self.logger_widget)

        # Connect all network signals
        network_signal_handler.log_message.connect(self.handle_network_log)
        network_signal_handler.create_line.connect(self.handle_create_line)
        network_signal_handler.remove_line.connect(self.handle_remove_line)
        network_signal_handler.update_turn.connect(self.handle_network_turn_update)
        network_signal_handler.update_cells.connect(self.handle_network_cell_update)  # Add this line

        self.setScene(MainMenuScene()) 
        self.setRenderHint(QPainter.Antialiasing)
        self.setFixedSize(900, 900)
        self.message_label = QGraphicsTextItem("")
        self.message_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.message_label.setDefaultTextColor(Qt.white)
        self.message_label.setPos(150, 20) 
        self.scene().addItem(self.message_label)
        
        self.moving_mode_label = QLabel("Tryb przesuwania komórek. Obsługa strzałkami na klawiaturze. Kliknij \"ZAKOŃCZ\", aby wyjść z trybu.", self)
        self.moving_mode_label.setStyleSheet("color: white; background-color: rgba(10, 10, 50, 200); padding: 5px;")
        self.moving_mode_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.moving_mode_label.setGeometry(40, 760, 820, 30)  
        self.moving_mode_label.setAlignment(Qt.AlignCenter)
        self.moving_mode_label.hide()  

        self.end_button = QPushButton("ZAKOŃCZ", self)
        self.end_button.setGeometry(400, 800, 100, 40)  
        font = self.end_button.font()
        font.setBold(True)  
        font.setPointSize(9) 
        self.end_button.setFont(font)
        self.end_button.setStyleSheet("background-color: rgb(10, 10, 50); color: white;") 
        self.end_button.clicked.connect(self.hide_message)
        self.end_button.hide()  

        self.suggestion_label = QLabel("", self)
        self.suggestion_label.setStyleSheet("color: white; background-color: rgba(10, 10, 50, 200); padding: 5px;")
        self.suggestion_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.suggestion_label.setGeometry(40, 790, 820, 30) 
        self.suggestion_label.setAlignment(Qt.AlignCenter)
        self.suggestion_label.hide()

        self.show()

    # Add the handler method for turn updates
    def handle_network_turn_update(self, current_turn, remaining_time):
        """Handle turn updates received from the network"""
        scene = self.scene()
        if isinstance(scene, GameScene) and scene.game_mode == "Gra sieciowa":
            scene.handle_network_turn_update(current_turn, remaining_time)

    def handle_network_cell_update(self, cell_values):
        """Handle cell value updates received from the network"""
        scene = self.scene()
        if isinstance(scene, GameScene) and scene.game_mode == "Gra sieciowa":
            scene.handle_network_cell_update(cell_values)

    def setScene(self, scene):
        super().setScene(scene)
        self.message_label = QGraphicsTextItem("")
        self.message_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.message_label.setDefaultTextColor(Qt.white)
        self.message_label.setPos(150, 20) 
        self.scene().addItem(self.message_label)

        if isinstance(scene, GameScene):
            self.suggestion_button.show()
            self.logger_widget.show()
        else:
            self.suggestion_button.hide()
            self.logger_widget.hide()

    def handle_remove_line(self, start_x, start_y, end_x, end_y):
        """Obsługa usuwania linii z powiadomień sieciowych"""
        scene = self.scene()
        if isinstance(scene, GameScene):
            # Znajdź linię do usunięcia
            for item in scene.items():
                if isinstance(item, ClickableLine):
                    start_cell = item.start_cell
                    end_cell = item.end_cell
                    
                    if start_cell and end_cell:
                        s_x = int(start_cell.rect().x())
                        s_y = int(start_cell.rect().y())
                        e_x = int(end_cell.rect().x())
                        e_y = int(end_cell.rect().y())
                        
                        # Sprawdź, czy to jest linia, którą mamy usunąć
                        if s_x == start_x and s_y == start_y and e_x == end_x and e_y == end_y:
                            # Usuń linię ze sceny
                            scene.removeItem(item)
                            
                            # Zaktualizuj biały krąg w komórce startowej (odbija czarny z powrotem na biały)
                            for circle in start_cell.inner_circles:
                                if circle.brush().color() == Qt.black:
                                    circle.setBrush(QBrush(Qt.white))
                                    break
                            
                            self.logger.log(f"Usunięto odbieraną linię: {start_x},{start_y} -> {end_x},{end_y}")
                            return  # Znaleźliśmy i usunęliśmy linię, więc kończymy


    def update_turn_timer(self):
        self.turn_remaining -= 1
        if self.turn_remaining <= 0:
            self.switch_turn()
        self.turn_timer_display.setPlainText(f"Timer: {self.turn_remaining}s")

    def handle_network_log(self, message):
        """Handle log messages from network threads"""
        if hasattr(self, 'logger'):
            self.logger.log(message)

    def display_message(self, message):
        self.message_label.setPlainText(message)
        self.end_button.show()
        self.moving_mode_label.show() 

    def hide_message(self):
        if hasattr(self, "message_label") and self.message_label.scene():
            self.message_label.setPlainText("") 
        self.end_button.hide()  
        self.moving_mode_label.hide()  
        if ClickableCell.moving_cell:
            ClickableCell.moving_cell.setPen(QPen(Qt.black, 2)) 
            ClickableCell.moving_cell = None 

    def display_suggestion(self, suggestion):
        self.suggestion_label.setText(suggestion)
        self.suggestion_label.show()

    def request_suggestion(self):
        if isinstance(self.scene(), GameScene):
            self.scene().suggest_best_move()


    def handle_create_line(self, start_x, start_y, end_x, end_y, color):
        """Obsługa tworzenia linii z powiadomień sieciowych"""
        # Sprawdź, czy scena jest instancją GameScene
        scene = self.scene()
        if isinstance(scene, GameScene):
            # Znajdź komórki początkową i końcową
            start_cell = None
            end_cell = None
            
            for cell in scene.cells:
                cell_x = int(cell.rect().x())
                cell_y = int(cell.rect().y())
                
                if cell_x == start_x and cell_y == start_y:
                    start_cell = cell
                
                if cell_x == end_x and cell_y == end_y:
                    end_cell = cell
                
                if start_cell and end_cell:
                    break
            
            if start_cell and end_cell:
                # Utwórz linię między komórkami
                start_pos = start_cell.scenePos() + start_cell.rect().center()
                end_pos = end_cell.scenePos() + end_cell.rect().center()
                
                # Utwórz linię
                line = ClickableLine(QLineF(start_pos, end_pos), start_cell, end_cell)
                line.setPen(QPen(QColor(color), 8))
                
                # Dodaj linię do sceny
                scene.addItem(line)
                
                self.logger.log(f"Utworzono odbieraną linię: {start_x},{start_y} -> {end_x},{end_y}")

    def keyPressEvent(self, event):
        if ClickableCell.moving_cell:
            ClickableCell.moving_cell.keyPressEvent(event)
        else:
            super().keyPressEvent(event)


from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QRadioButton, QButtonGroup,
    QDialogButtonBox, QLineEdit, QMessageBox
)

class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Konfiguracja Gry")
        self.setFixedSize(300, 300)

        layout = QVBoxLayout(self)

        # Label
        label = QLabel("Wybierz tryb gry:")
        layout.addWidget(label)

        self.button_group = QButtonGroup(self)
        self.radio_single = QRadioButton("1 gracz")
        self.radio_local = QRadioButton("2 graczy lokalnie")
        self.radio_network = QRadioButton("Gra sieciowa")
        self.button_group.addButton(self.radio_single)
        self.button_group.addButton(self.radio_local)
        self.button_group.addButton(self.radio_network)
        layout.addWidget(self.radio_single)
        layout.addWidget(self.radio_local)
        layout.addWidget(self.radio_network)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Adres IP (np. 192.168.1.100 lub 'server')")
        layout.addWidget(self.ip_input)

        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("Port (np. 5000)")
        layout.addWidget(self.port_input)

        self.ip_input.hide()
        self.port_input.hide()

        self.radio_network.toggled.connect(self.toggle_network_fields)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        self.radio_single.setChecked(True)

    def toggle_network_fields(self, checked):
        self.ip_input.setVisible(checked)
        self.port_input.setVisible(checked)

    def get_selected_mode(self):
        if self.radio_single.isChecked():
            return "1 gracz"
        elif self.radio_local.isChecked():
            return "2 graczy lokalnie"
        elif self.radio_network.isChecked():
            return "Gra sieciowa"
        return None

    def get_ip_port(self):
        return self.ip_input.text().strip(), self.port_input.text().strip()

    def accept(self):
        if self.radio_network.isChecked():
            ip = self.ip_input.text().strip()
            port = self.port_input.text().strip()

            if ip.lower() != "server":
                import re
                ip_pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
                if not re.match(ip_pattern, ip):
                    QMessageBox.warning(self, "Błąd", "Wprowadź poprawny adres IP lub wpisz 'server'")
                    return

            if not port.isdigit() or not (0 < int(port) < 65536):
                QMessageBox.warning(self, "Błąd", "Wprowadź poprawny port (1–65535)")
                return

        super().accept()


import xml.etree.ElementTree as ET

def save_current_game_to_xml(scene):
    root = ET.Element("game")
    root.set("level", str(scene.level))
    root.set("mode", scene.game_mode)

    last_step = scene.replay_steps[-1] if scene.replay_steps else None
    if last_step:
        step_el = ET.SubElement(root, "step", {
            "turn": last_step["turn"],
            "timer": str(last_step["timer"])
        })

        for cell_data in last_step["cells"]:
            cell_el = ET.SubElement(step_el, "cell", {
                "x": str(cell_data["x"]),
                "y": str(cell_data["y"]),
                "value": str(cell_data["value"]),
                "color": cell_data["color"],
                "level": str(cell_data["level"])
            })

            if "top_value" in cell_data:
                cell_el.set("top_value", str(cell_data["top_value"]))
            if "circles" in cell_data:
                cell_el.set("circles", cell_data["circles"])

        for line_data in last_step.get("lines", []):
            ET.SubElement(step_el, "line", {
                "start_x": str(line_data["start_x"]),
                "start_y": str(line_data["start_y"]),
                "end_x": str(line_data["end_x"]),
                "end_y": str(line_data["end_y"]),
                "color": line_data["color"]
            })

    tree = ET.ElementTree(root)
    tree.write("last_save.xml")
    game_view_instance.logger.log("Zapisano stan gry do last_save.xml")


def load_last_game_from_xml():
    try:
        tree = ET.parse("last_save.xml")
        root = tree.getroot()

        level = int(root.get("level"))
        mode = root.get("mode")
        step_el = root.find("step")
        if step_el is None:
            return None

        step = {
            "turn": step_el.get("turn"),
            "timer": int(step_el.get("timer")),
            "cells": [],
            "lines": []
        }

        for cell_el in step_el.findall("cell"):
            cell_data = {
                "x": int(cell_el.get("x")),
                "y": int(cell_el.get("y")),
                "value": int(cell_el.get("value")),
                "color": cell_el.get("color"),
                "level": int(cell_el.get("level"))
            }
            if cell_el.get("top_value"):
                cell_data["top_value"] = int(cell_el.get("top_value"))
            if cell_el.get("circles"):
                cell_data["circles"] = cell_el.get("circles")
            step["cells"].append(cell_data)

        for line_el in step_el.findall("line"):
            line_data = {
                "start_x": int(line_el.get("start_x")),
                "start_y": int(line_el.get("start_y")),
                "end_x": int(line_el.get("end_x")),
                "end_y": int(line_el.get("end_y")),
                "color": line_el.get("color")
            }
            step["lines"].append(line_data)

        return {
            "level": level,
            "mode": mode,
            "last_step": step
        }
    except Exception as e:
        print("Błąd przy wczytywaniu last_save.xml:", e)
        return None


def save_current_game(scene):
    game_state = {
        "level": scene.level,
        "mode": scene.game_mode,
        "last_step": scene.replay_steps[-1] if scene.replay_steps else None
    }
    with open("last_save.pkl", "wb") as f:
        pickle.dump(game_state, f)
    game_view_instance.logger.log("Zapisano stan gry do last_save.pkl")

def load_last_game():
    try:
        with open("last_save.pkl", "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print("Brak zapisu lub błąd odczytu:", e)
        return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    view = GameView()
    view.setWindowTitle("Strategia – Gra Komórkowa")
    view.setFixedSize(900, 900)
    view.setRenderHint(QPainter.Antialiasing)

    game_view_instance = view  

    if os.path.exists("last_save.xml"):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("Wznawianie gry")
        msg.setText("Chcesz kontynuować ostatnią zapisaną grę?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        result = msg.exec_()
        if result == QMessageBox.Yes:
            saved = load_last_game_from_xml()

            if saved and saved["last_step"]:
                scene = GameScene(level=saved["level"], game_mode=saved["mode"])
                view.setScene(scene)
                scene.apply_step(saved["last_step"])  
            else:
                view.setScene(MainMenuScene())
        else:
            view.setScene(MainMenuScene())
    else:
        view.setScene(MainMenuScene())

    view.show()
    sys.exit(app.exec_())