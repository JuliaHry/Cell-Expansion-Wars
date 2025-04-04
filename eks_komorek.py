import sys
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem, QMenu, QAction, QPushButton, QGraphicsRectItem, QGraphicsPixmapItem, QLabel
from PyQt5.QtGui import QBrush, QPen, QLinearGradient, QRadialGradient, QColor, QPainter, QFont, QTransform, QPixmap
from PyQt5.QtCore import Qt, QRectF, QLineF, QPointF, QTimer
from random import uniform

# Import zasobów z pliku resources.py
import resources

class ClickableLine(QGraphicsLineItem):
    def __init__(self, line, start_cell, end_cell=None, parent=None):
        super().__init__(line, parent)
        color = "#D8177E" if start_cell.base_color == QColor("#D8177E") else "#66C676"
        self.setPen(QPen(QColor(color), 8))
        self.setZValue(-1)  # Linia jest pod komórkami
        self.start_cell = start_cell
        self.end_cell = end_cell
        self.mini_cells = []  # Przechowuje referencje do mini kółek
 
    def update_position(self):
        if self.start_cell and self.end_cell:
            start_pos = self.start_cell.scenePos() + self.start_cell.rect().center()
            end_pos = self.end_cell.scenePos() + self.end_cell.rect().center()
            print(f"Aktualizacja linii: start_pos={start_pos}, end_pos={end_pos}")  # Debugowanie
            self.setLine(QLineF(start_pos, end_pos))
        else:
            print("Brak start_cell lub end_cell w linii")  # Debugowanie

    def mousePressEvent(self, event):
        # Calculate the distance from the click point to the start and end of the line
        clicked_pos = event.scenePos()
        start_pos = self.line().p1()
        end_pos = self.line().p2()
        distance_to_start = QLineF(start_pos, clicked_pos).length()
        distance_to_end = QLineF(end_pos, clicked_pos).length()
        value_to_add = int(distance_to_start // 50)  # Round down to integer
        value_to_subtract = int(distance_to_end // 50)  # Round down to integer

        # Add the calculated value to the starting cell
        if self.start_cell:
            self.start_cell.update_value(value_to_add)

        # Update the ending cell
        if self.end_cell:
            if self.start_cell.base_color == self.end_cell.base_color:
                self.end_cell.update_value(value_to_subtract)  # Increase value in the ending cell
            else:
                self.end_cell.update_value(-value_to_subtract)  # Decrease value in the ending cell

            # If the ending cell is gray, calculate the distance to its center
            if self.end_cell.base_color == Qt.gray:
                gray_center = self.end_cell.scenePos() + self.end_cell.rect().center()
                distance_to_gray_center = QLineF(clicked_pos, gray_center).length()
                gray_value_to_modify = int(distance_to_gray_center // 50)
                if self.start_cell.base_color == QColor("#66C676"):
                    print(f"Distance to gray center: {distance_to_gray_center}, Value to add: {gray_value_to_modify}")  # Debugging
                    self.end_cell.update_top_text(gray_value_to_modify)
                elif self.start_cell.base_color == QColor("#D8177E"):
                    print(f"Distance to gray center: {distance_to_gray_center}, Value to subtract: {gray_value_to_modify}")  # Debugging
                    self.end_cell.update_top_text(-gray_value_to_modify)

        # Change one of the inner circles back to white
        for circle in self.start_cell.inner_circles:
            if circle.brush().color() == Qt.black:
                circle.setBrush(QBrush(Qt.white))
                break

        # Remove the line from the scene
        self.scene().removeItem(self)
        super().mousePressEvent(event)


class ClickableCell(QGraphicsEllipseItem):
    selected_green = None  # Przechowuje referencję do wybranej zielonej komórki
    is_creating_line = False  # Flaga informująca, czy trwa tworzenie linii
    moving_cell = None  # Przechowuje referencję do komórki w trybie przesuwania

    def __init__(self, rect, color, value, parent=None):
        super().__init__(rect, parent)
        self.base_color = QColor(color) if isinstance(color, str) else QColor(color)
        self.value = value
        self.set_gradient()
        self.setPen(QPen(Qt.black, 2))
        self.setAcceptHoverEvents(True)  # Włącz zdarzenia hover dla komórki
        self.is_selected = False
        self.inner_circles = []  # Przechowuje referencje do wewnętrznych kółek
        self.value_text = None  # Referencja do tekstu wyświetlającego wartość
        self.level = 1  # Poziom komórki (domyślnie 1)
    
    def set_gradient(self):
        if self.base_color == Qt.gray:
            gradient = QRadialGradient(self.rect().center(), self.rect().width() / 2)
            if hasattr(self, 'fill_color') and self.fill_color:
                fill_ratio = min(self.value / 8, 1)  # Calculate the ratio of fill color
                gradient.setColorAt(0, self.fill_color.lighter(150))  # Lighter fill center
                gradient.setColorAt(fill_ratio, self.fill_color.darker(150))  # Darker fill edge
                gradient.setColorAt(fill_ratio, self.base_color)  # Transition to gray
            gradient.setColorAt(1, self.base_color)  # Gray edge
            self.setBrush(QBrush(gradient))
        else:
            # Załaduj obrazek z zasobów
            if self.base_color == QColor("#66C676"):
                pixmap = QPixmap(":/images/green_cell.png")
            elif self.base_color == QColor("#D8177E"):
                pixmap = QPixmap(":/images/pink_cell.png")
            else:
                pixmap = QPixmap()
            
            # Przeskaluj obrazek do rozmiaru komórki
            if not pixmap.isNull():
                pixmap = pixmap.scaled(self.rect().size().toSize(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                # Utwórz QBrush z obrazkiem i przesunięciem
                brush = QBrush(pixmap)
                
                # Oblicz przesunięcie, aby środek obrazka był na środku kółka
                offset_x = 50
                offset_y = 50
                
                # Ustaw przesunięcie
                brush.setTransform(QTransform().translate(offset_x, offset_y))
                
                self.setBrush(brush)
            else:
                gradient = QRadialGradient(self.rect().center(), self.rect().width() / 2)
                gradient.setColorAt(0, self.base_color.lighter(150))  # Lighter center
                gradient.setColorAt(1, self.base_color.darker(150))  # Darker edge
                self.setBrush(QBrush(gradient))
    
    def set_value_text(self, text_item):
        self.value_text = text_item

    def set_level_text(self, text_item):
        self.level_text = text_item

    def get_attack_power_per_mini_cell(self):
        return self.level  # albo: return max(1, round(self.level * 1.5))


    def increase_level(self):
        if self.level < 3:
            self.level += 1
            self.update_level_display()

    def update_level_display(self):
        if hasattr(self, 'level_text'):
            self.level_text.setPlainText(f"LVL {self.level}")

    def get_attack_power(self):
        return self.level * self.value

    
    def update_value(self, delta, fill_color=None):
        self.value += delta
        if self.value > 30:
            self.value = 30
        if self.value_text:
            self.value_text.setPlainText(str(self.value))
        if self.base_color == QColor("#D8177E") and self.value <= 0:
            self.convert_to_green()
        elif self.base_color == QColor("#66C676") and self.value <= 0:
            self.convert_to_pink()  # Convert green cell to pink when value reaches 0
        if self.base_color == Qt.gray:
            if fill_color:
                self.fill_color = fill_color
            self.set_gradient()  # Update gradient for gray cells
    
    def set_top_text(self, text_item):
        self.top_text = text_item

    def update_top_text(self, delta):
        if not hasattr(self, '_actual_top_value'):
            self._actual_top_value = 0  # Initialize the actual value if not present
        self._actual_top_value += delta  # Update the actual value
        self.top_text.setPlainText(str(abs(self._actual_top_value)))  # Display absolute value
        print(f"Updated top value on gray cell: {self._actual_top_value}")  # Debugging

        if self._actual_top_value >= 8:
            self.convert_to_green(attacker=self.scene().get_attacker(self))
        elif self._actual_top_value <= -8:
            self.convert_to_pink(attacker=self.scene().get_attacker(self))


        # Check for conversion conditions
        if self._actual_top_value >= 8:
            self.convert_to_green()
            return
        elif self._actual_top_value <= -8:
            self.convert_to_pink()
            return

        # Update the fill color for the gray cell
        if self.base_color == Qt.gray:
            gradient = QRadialGradient(self.rect().center(), self.rect().width() / 2)
            if self._actual_top_value > 0:
                fill_ratio = min(self._actual_top_value / 8, 1)  # Cap the ratio at 1
                self.fill_color = QColor("#66C676")  # Green color
                gradient.setColorAt(0, self.fill_color.lighter(150))  # Lighter center
                gradient.setColorAt(fill_ratio, self.fill_color.darker(150))  # Darker edge
                gradient.setColorAt(fill_ratio, self.base_color)  # Transition to gray
            elif self._actual_top_value < 0:
                fill_ratio = min(abs(self._actual_top_value) / 8, 1)  # Cap the ratio at 1
                self.fill_color = QColor("#D8177E")  # Pink color
                gradient.setColorAt(0, self.fill_color.lighter(150))  # Lighter center
                gradient.setColorAt(fill_ratio, self.fill_color.darker(150))  # Darker edge
                gradient.setColorAt(fill_ratio, self.base_color)  # Transition to gray
            else:
                self.fill_color = None  # Reset fill color if value is zero
                self.set_gradient()  # Reset to default gradient
                return
            gradient.setColorAt(1, self.base_color)  # Gray edge
            self.setBrush(QBrush(gradient))
    
    def convert_to_green(self, attacker=None):
        # Zmień kolor na zielony
        self.base_color = QColor("#66C676")
        self.set_gradient()
        
        if attacker:
            attacker.increase_level()

        # Ustaw wartość na 20
        self.value = 20
        if self.value_text:
            self.value_text.setPlainText("20")
        else:
            # Dodaj tekst wyświetlający wartość, jeśli go nie ma
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
        
        # Resetuj poziom do 1, jeśli był wyższy
        if self.level > 1:
            self.level = 1
        self.update_level_display()

        # Dodaj tekst poziomu, jeśli go nie ma
        if not hasattr(self, 'level_text'):
            level_text = QGraphicsTextItem("LVL 1")
            level_text.setFont(QFont("Arial", 10))
            level_text.setDefaultTextColor(Qt.white)
            level_text_rect = level_text.boundingRect()
            level_text.setPos(
                self.rect().x() + 50 - level_text_rect.width() / 2,
                self.rect().y() + 90  # poniżej komórki
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
        
        # Dodaj dwa wewnętrzne kółka (jeśli ich nie ma)
        if not self.inner_circles:
            for dx, dy in [(-20, -20), (20, 20)]:
                inner_circle = QGraphicsEllipseItem(self.rect().x() + 50 + dx - 10, self.rect().y() + 50 + dy - 10, 20, 20)
                inner_circle.setBrush(QBrush(Qt.white))
                inner_circle.setPen(QPen(Qt.black, 1))
                inner_circle.setZValue(1)  # Kółka są na wierzchu komórek
                self.scene().addItem(inner_circle)
                self.inner_circles.append(inner_circle)
    
    def convert_to_pink(self, attacker=None):
        # Zmień kolor na różowy
        self.base_color = QColor("#D8177E")
        self.set_gradient()

        if attacker:
            attacker.increase_level()
        
        # Ustaw wartość na 20
        self.value = 20
        if self.value_text:
            self.value_text.setPlainText("20")
        else:
            # Dodaj tekst wyświetlający wartość, jeśli go nie ma
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
        
        # Resetuj poziom do 1, jeśli był wyższy
        if self.level > 1:
            self.level = 1
        self.update_level_display()

        # Dodaj tekst poziomu, jeśli go nie ma
        if not hasattr(self, 'level_text'):
            level_text = QGraphicsTextItem("LVL 1")
            level_text.setFont(QFont("Arial", 10))
            level_text.setDefaultTextColor(Qt.white)
            level_text_rect = level_text.boundingRect()
            level_text.setPos(
                self.rect().x() + 50 - level_text_rect.width() / 2,
                self.rect().y() + 75  # poniżej komórki
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
        
        # Dodaj dwa wewnętrzne kółka (jeśli ich nie ma)
        if not self.inner_circles:
            for dx, dy in [(-20, -20), (20, 20)]:
                inner_circle = QGraphicsEllipseItem(self.rect().x() + 50 + dx - 10, self.rect().y() + 50 + dy - 10, 20, 20)
                inner_circle.setBrush(QBrush(QBrush(Qt.white)))
                inner_circle.setPen(QPen(Qt.black, 1))
                inner_circle.setZValue(1)  # Kółka są na wierzchu komórek
                self.scene().addItem(inner_circle)
                self.inner_circles.append(inner_circle)

    def highlight_valid_targets(self):
        """Highlight valid target cells based on the current cell's level and value."""
        for cell in self.scene().cells:
            if cell == self:
                continue  # Skip the current cell
            if cell.base_color == Qt.gray or (
                cell.base_color != self.base_color and 
                cell.level <= self.level and 
                cell.value < self.value
            ):
                cell.setPen(QPen(QColor("#FFFF00"), 4))  # Highlight with yellow border

    def clear_highlight(self):
        """Clear the highlight from all cells."""
        for cell in self.scene().cells:
            cell.setPen(QPen(Qt.black, 2))  # Reset to default border

    def mousePressEvent(self, event):
            
        if ClickableCell.moving_cell:
            # Usuń pomarańczową obwódkę z poprzedniej komórki
            ClickableCell.moving_cell.setPen(QPen(Qt.black, 2))
            self.setPen(QPen(QColor("#FFA500"), 8, Qt.SolidLine))
            ClickableCell.moving_cell = self
            return

        if self.base_color == QColor("#66C676") or self.base_color == QColor("#D8177E"):  # Zielona lub różowa komórka
            if all(circle.brush().color() == Qt.black for circle in self.inner_circles):
                print("Oba wewnętrzne kółka są czarne, nie można wybrać komórki.")  # Debugowanie
                return
            
            if ClickableCell.is_creating_line:
                if ClickableCell.selected_green and ClickableCell.selected_green != self:
                    print(f"Tworzenie linii z1 {ClickableCell.selected_green.base_color.name()} do {self.base_color.name()}")  # Debugowanie
                    start_pos = ClickableCell.selected_green.scenePos() + ClickableCell.selected_green.rect().center()
                    end_pos = self.scenePos() + self.rect().center()
                    line_length = QLineF(start_pos, end_pos).length()
                    cost = int(line_length // 50)
                    print(f"Koszt stworzenia linii: {cost}, długość linii: {line_length}")  # Debugowanie

                    if cost > ClickableCell.selected_green.value:
                        print("Koszt stworzenia linii przekracza wartość komórki, linia nie może zostać utworzona.")  # Debugowanie
                        return

                    line = ClickableLine(QLineF(start_pos, end_pos), ClickableCell.selected_green, self)
                    self.scene().addItem(line)
                    
                    # Oblicz koszt stworzenia mostu dla wszystkich komórek
                    ClickableCell.selected_green.update_value(-cost)
                    
                    ClickableCell.selected_green.setPen(QPen(Qt.black, 2))
                    self.setPen(QPen(Qt.black, 2))
                    
                    for circle in ClickableCell.selected_green.inner_circles:
                        if circle.brush().color() != Qt.black:
                            circle.setBrush(QBrush(Qt.black))
                            break
                    
                    ClickableCell.selected_green.clear_highlight()  # Clear highlights after creating a line
                    ClickableCell.selected_green = None
                    ClickableCell.is_creating_line = False
            else:
                scene = self.scene()
                if isinstance(scene, GameScene):
                    if self.base_color == QColor("#66C676") and scene.current_turn != "green":
                        return
                    if self.base_color == QColor("#D8177E") and scene.current_turn != "pink":
                        return

                print(f"Rozpoczęcie tworzenia linii z {self.base_color.name()}")  # Debugowanie
                self.setPen(QPen(QColor("#A4DEFA"), 8, Qt.SolidLine))
                ClickableCell.selected_green = self
                ClickableCell.is_creating_line = True
                self.highlight_valid_targets()  # Highlight valid targets

        elif self.base_color == Qt.gray and ClickableCell.selected_green:  # Szara komórka
            print(f"Tworzenie linii z2 {ClickableCell.selected_green.base_color.name()} do szarej komórki")  # Debugowanie
            if all(circle.brush().color() == Qt.black for circle in ClickableCell.selected_green.inner_circles):
                print("Oba wewnętrzne kółka w komórce startowej są czarne, nie można stworzyć linii.")  # Debugowanie
                return

            start_pos = ClickableCell.selected_green.scenePos() + ClickableCell.selected_green.rect().center()
            end_pos = self.scenePos() + self.rect().center()
            line_length = QLineF(start_pos, end_pos).length()
            cost = int(line_length // 50)
            print(f"Koszt stworzenia linii: {cost}, długość linii: {line_length}")  # Debugowanie

            if cost > ClickableCell.selected_green.value:
                print("Koszt stworzenia linii przekracza wartość komórki, linia nie może zostać utworzona.")  # Debugowanie
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

            ClickableCell.selected_green.clear_highlight()  # Clear highlights after creating a line
            ClickableCell.selected_green = None
            ClickableCell.is_creating_line = False

        super().mousePressEvent(event)

    def hoverEnterEvent(self, event):
        if ClickableCell.moving_cell:
            return  # Wyłącz pozostałą funkcjonalność, gdy tryb przesuwania jest włączony
        if self.base_color == QColor("#66C676") and ClickableCell.is_creating_line:
            self.setPen(QPen(QColor("#A4DEFA"), 8, Qt.SolidLine))
        elif (self.base_color == Qt.gray or self.base_color == QColor("#D8177E")) and ClickableCell.selected_green:
            if all(circle.brush().color() == Qt.black for circle in ClickableCell.selected_green.inner_circles):
                return  # Nie zmieniaj obwódki, jeśli oba kółka są czarne
            self.setPen(QPen(QColor("#A4DEFA"), 8, Qt.SolidLine))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if ClickableCell.moving_cell:
            return  # Wyłącz pozostałą funkcjonalność, gdy tryb przesuwania jest włączony
        if self.base_color == QColor("#66C676") and ClickableCell.is_creating_line:
            self.setPen(QPen(Qt.black, 2))
        elif (self.base_color == Qt.gray or self.base_color == QColor("#D8177E")) and ClickableCell.selected_green:
            self.setPen(QPen(Qt.black, 2))
        if ClickableCell.is_creating_line and ClickableCell.selected_green == self:
            self.clear_highlight()  # Clear highlights if the user cancels the action
        super().hoverLeaveEvent(event)

    def contextMenuEvent(self, event):
        if ClickableCell.moving_cell:
            return  # Wyłącz pozostałą funkcjonalność, gdy tryb przesuwania jest włączony
        menu = QMenu()
        move_cell_action = menu.addAction("Przesuń komórkę")
        resize_cell_action = menu.addAction("Zmień rozmiar komórek")
        
        action = menu.exec_(event.screenPos())
        if action == move_cell_action:
            view = self.scene().views()[0]
            view.display_message("TRYB PRZESUWANIA KOMÓRKI (OBSŁUGA STRZAŁKAMI NA KLAWIATURZE)")
            if ClickableCell.moving_cell:
                ClickableCell.moving_cell.setPen(QPen(Qt.black, 2))  # Usuń pomarańczową obwódkę z poprzedniej komórki
            self.setPen(QPen(QColor("#FFA500"), 8, Qt.SolidLine))  # Pomarańczowa obwódka
            ClickableCell.moving_cell = self  # Ustaw referencję do komórki w trybie przesuwania
        elif action == resize_cell_action:
            print("Zwiększ rozmiar komórki")

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
                
                # Wyświetl globalne współrzędne komórki
                global_pos = ClickableCell.moving_cell.scenePos() + ClickableCell.moving_cell.rect().center()
                print(f"Przesunięto komórkę: global_pos={global_pos}")  # Debugowanie
                self.scene().update_lines()  # Dodaj tę linię, aby zaktualizować linie

    def update_lines(self):
            print("Aktualizacja linii w scenie...")  # Debugowanie
            for item in self.items():
                if isinstance(item, ClickableLine):
                    print(f"Znaleziono linię: {item}")  # Debugowanie
                    item.update_position()  # Wywołaj update_position dla każdej linii

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
        self.setPen(QPen(Qt.NoPen))  # Fix: Use QPen(Qt.NoPen) instead of Qt.NoPen
        
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 900, 900)
        self.init_background()
        self.create_cells()
        self.line = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.move_mini_cells)
        self.timer.start(30)  # Timer co 100 ms
        self.value_timer = QTimer()
        self.value_timer.timeout.connect(self.increase_cell_values)
        self.value_timer.start(1000)  # Timer co 1000 ms (1 sekunda)
        self.create_menu_button()  # Add this line to create the menu button
        self.create_restart_button()  # Add this line to create the restart button
        self.current_turn = "green"  # "green" lub "pink"
        self.turn_timer = QTimer()
        self.turn_time_limit = 10  # sekund
        self.turn_remaining = self.turn_time_limit

        self.turn_timer.timeout.connect(self.update_turn_timer)
        self.turn_timer.start(1000)  # Odliczanie co sekundę
        self.create_turn_timer_display()
        self.create_turn_display()  # Add this line to create the turn display

    def create_turn_timer_display(self):
        """Create a display for the remaining time in the current round."""
        self.turn_timer_display = QGraphicsTextItem(f"Timer: {self.turn_remaining}s")
        self.turn_timer_display.setFont(QFont("Arial", 14, QFont.Bold))
        self.turn_timer_display.setDefaultTextColor(Qt.white)
        self.turn_timer_display.setPos(600, 50)  # Position the timer display
        self.addItem(self.turn_timer_display)

    def create_turn_display(self):
        """Create a display for the current player's turn."""
        self.turn_display = QGraphicsTextItem(f"Turn: {self.current_turn.capitalize()}")
        self.turn_display.setFont(QFont("Arial", 16, QFont.Bold))
        self.turn_display.setDefaultTextColor(Qt.white)
        self.turn_display.setPos(600, 20)  # Position the turn display above the timer
        self.addItem(self.turn_display)

    def update_turn_timer(self):
        """Update the timer display and handle turn switching."""
        self.turn_remaining -= 1
        if self.turn_remaining <= 0:
            self.switch_turn()
        self.turn_timer_display.setPlainText(f"Timer: {self.turn_remaining}s")

    def switch_turn(self):
        """Switch the turn and reset the timer."""
        self.current_turn = "pink" if self.current_turn == "green" else "green"
        self.turn_remaining = self.turn_time_limit
        self.turn_timer_display.setPlainText(f"Pozostały czas: {self.turn_remaining}s")
        self.turn_display.setPlainText(f"Turn: {self.current_turn.capitalize()}")  # Update the turn display
        ClickableCell.selected_green = None
        ClickableCell.is_creating_line = False

        # Clear suggestion label
        view = self.views()[0]
        view.suggestion_label.hide()

        # Remove "Attacker" and "Target" labels
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
            print("Aktualizacja linii w scenie...")  # Debugowanie
            for item in self.items():
                if isinstance(item, ClickableLine):
                    print(f"Znaleziono linię: {item}")  # Debugowanie
                    item.update_position()  # Wywołaj update_position dla każdej linii

    def get_attacker(self, target_cell):
        for item in self.items():
            if isinstance(item, ClickableLine) and item.end_cell == target_cell:
                return item.start_cell
        return None
    
    def create_cells(self):
        self.cells = []
        cell_positions = [
            (150, 650, "#66C676", 20),  # Zielona komórka
            (350, 650, "#66C676", 20),  # Zielona komórka
            (650, 150, "#D8177E", 20),  # Różowa komórka
            (450, 150, "#D8177E", 20),  # Różowa komórka
            (250, 250, QColor(Qt.gray), 0),  # Szara komórka (wartość 0, ale nie używana)
            (550, 550, QColor(Qt.gray), 0),  # Szara komórka (wartość 0, ale nie używana)
        ]
        
        for x, y, color, value in cell_positions:
            cell_rect = QRectF(x, y, 100, 100)
            cell = ClickableCell(cell_rect, color, value)
            self.cells.append(cell)
            
            # Dodanie szarej komórki przed napisami
            if (color == QColor(Qt.gray)):
                self.addItem(cell)
            
            # Dodanie tekstu do komórki (jeśli nie jest szara)
            if color != QColor(Qt.gray):
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
            
            # Dodanie dwóch małych kółek na komórce, jeśli nie jest szara
            if color != QColor(Qt.gray):
                for dx, dy in [(-20, -20), (20, 20)]:
                    inner_circle = QGraphicsEllipseItem(x + 50 + dx - 10, y + 50 + dy - 10, 20, 20)
                    inner_circle.setBrush(QBrush(Qt.white))
                    inner_circle.setPen(QPen(Qt.black, 1))
                    inner_circle.setZValue(1)  # Kółka są na wierzchu komórek
                    self.addItem(inner_circle)
                    cell.inner_circles.append(inner_circle)

            if color != QColor(Qt.gray):
                level_text = QGraphicsTextItem("LVL 1")
                level_text.setFont(QFont("Arial", 10))
                level_text.setDefaultTextColor(Qt.white)
                level_text_rect = level_text.boundingRect()
                level_text.setPos(
                    x + 50 - level_text_rect.width() / 2,
                    y + 100  # poniżej komórki (adjusted to be lower)
                )
                self.addItem(level_text)
                cell.set_level_text(level_text)  # Set reference to level text  
            
            # Dodanie dwóch liczb na szarej komórce (0 u góry i 8 na dole)
            if color == QColor(Qt.gray):
                # Liczba u góry (0)
                top_text = QGraphicsTextItem("0")
                top_text.setFont(QFont("Arial", 14, QFont.Bold))
                top_text.setDefaultTextColor(Qt.white)
                top_text_rect = top_text.boundingRect()
                top_text.setPos(
                    x + 50 - top_text_rect.width() / 2,  # Wyśrodkowanie poziome
                    y + 10  # U góry komórki
                )
                self.addItem(top_text)
                cell.set_top_text(top_text)  # Set reference to top text
                
                # Liczba na dole (8)
                bottom_text = QGraphicsTextItem("8")
                bottom_text.setFont(QFont("Arial", 14, QFont.Bold))
                bottom_text.setDefaultTextColor(Qt.white)
                bottom_text_rect = bottom_text.boundingRect()
                bottom_text.setPos(
                    x + 50 - bottom_text_rect.width() / 2,  # Wyśrodkowanie poziome
                    y + 55  # Na dole komórki
                )
                self.addItem(bottom_text)
                cell.bottom_text = bottom_text  # Set reference to bottom text
        
    
    def mouseMoveEvent(self, event):
        if ClickableCell.moving_cell:
            return  # Wyłącz pozostałą funkcjonalność, gdy tryb przesuwania jest włączony
        if ClickableCell.selected_green and ClickableCell.is_creating_line:
            if all(circle.brush().color() == Qt.black for circle in ClickableCell.selected_green.inner_circles):
                return  # Nie twórz linii, jeśli oba kółka są czarne
            
            if not self.line:
                self.line = QGraphicsLineItem()
                color = "#D8177E" if ClickableCell.selected_green.base_color == QColor("#D8177E") else "#66C676"
                self.line.setPen(QPen(QColor(color), 8))
                self.addItem(self.line)
                self.line.setZValue(-1)  # Linia jest pod komórkami
            
            # Użyj globalnych współrzędnych
            start_point = ClickableCell.selected_green.scenePos() + ClickableCell.selected_green.rect().center()
            end_point = event.scenePos()
            self.line.setLine(QLineF(start_point, end_point)) 
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if ClickableCell.moving_cell:
            return  # Wyłącz pozostałą funkcjonalność, gdy tryb przesuwania jest włączony
        if self.line:
            self.removeItem(self.line)
            self.line = None
        super().mouseReleaseEvent(event)

    def mousePressEvent(self, event):
        if ClickableCell.moving_cell:
            item = self.itemAt(event.scenePos(), QTransform())
            if isinstance(item, ClickableCell):
                ClickableCell.moving_cell.setPen(QPen(Qt.black, 2))  # Usuń pomarańczową obwódkę z poprzedniej komórki
                item.setPen(QPen(QColor("#FFA500"), 8, Qt.SolidLine))  # Pomarańczowa obwódka
                ClickableCell.moving_cell = item  # Ustaw nową referencję do komórki w trybie przesuwania
            return  # Wyłącz pozostałą funkcjonalność, gdy tryb przesuwania jest włączony
        item = self.itemAt(event.scenePos(), QTransform())
        if isinstance(item, ClickableLine):
            item.mousePressEvent(event)
        elif not isinstance(item, ClickableCell) and ClickableCell.selected_green:
            ClickableCell.selected_green.clear_highlight()  # Clear highlights when canceling line creation
            ClickableCell.selected_green.setPen(QPen(Qt.black, 2))  # Usunięcie obwódki z zielonego
            ClickableCell.selected_green = None  # Reset wyboru zielonego
            ClickableCell.is_creating_line = False  # Zakończ tworzenie linii
            if self.line:
                self.removeItem(self.line)
                self.line = None
        super().mousePressEvent(event)

    def move_mini_cells(self):
        for item in self.items():
            if isinstance(item, ClickableLine):
                if not item.mini_cells:
                    # Utwórz nowe mini kółko
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
                    step = direction / 10  # krok ruchu
                    mini_cell.setPos(current_pos + step)

                    if (current_pos - end_pos).manhattanLength() < 5:
                        self.removeItem(mini_cell)
                        item.mini_cells.remove(mini_cell)

                        # Po trafieniu w komórkę
                        attacker = item.start_cell  # Define the attacker here
                        explosion = ExplosionEffect(end_pos.x(), end_pos.y(), attacker.base_color)
                        self.addItem(explosion)

                        for cell in self.cells:
                            if cell.rect().contains(end_pos):
                                attacker = item.start_cell
                                if cell.base_color == Qt.gray:
                                    if attacker.base_color == QColor("#66C676"):
                                        cell.update_top_text(1)
                                    elif attacker.base_color == QColor("#D8177E"):
                                        cell.update_top_text(-1)

                                elif cell.base_color != attacker.base_color:
    # WROGA KOMÓRKA – zastosuj siłę ataku
                                    damage = attacker.get_attack_power_per_mini_cell()
                                    print(f"Mini-komórka z poziomem {attacker.level} atakuje! Obrażenia: {damage}")  # DEBUG
                                    cell.update_value(-damage)
                                elif cell.base_color == attacker.base_color:
                                    # PRZYJACIELSKA KOMÓRKA – dodaj 1 wartość
                                    cell.update_value(1)

                                break  # znaleziono cel, nie szukamy dalej

                        # Zmniejsz wartość atakującej komórki (zawsze o 1)
                        item.start_cell.update_value(-1)


    def increase_cell_values(self):
        for cell in self.cells:
            if cell.base_color == QColor("#66C676"):  # Zielona komórka
                cell.update_value(1)
            elif cell.base_color == QColor("#D8177E"):  # Różowa komórka
                cell.update_value(1)

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
        view.suggestion_label.hide()  # Hide the suggestion label
        self.clear()  # Clear the scene
        self.init_background()  # Reinitialize the background
        self.create_cells()  # Recreate the cells
        self.create_menu_button()  # Recreate the menu button
        self.create_restart_button()  # Recreate the restart button
        self.create_turn_timer_display()  # Recreate the turn timer display
        self.create_turn_display()  # Recreate the turn display
        self.timer.start(30)  # Restart the mini cell movement timer
        self.value_timer.start(1000)  # Restart the cell value increase timer
        self.turn_remaining = self.turn_time_limit  # Reset the turn timer
        self.current_turn = "green"  # Reset the turn to green
        self.turn_timer.start(1000)  # Restart the turn timer

    def back_to_main_menu(self, event):
        view = self.views()[0]
        view.suggestion_label.hide()  # Hide the suggestion label
        view.setScene(MainMenuScene())

    def suggest_best_move(self):
        """Provide a basic AI suggestion for the best move."""
        best_move = None
        max_value_difference = -float('inf')

        # Clear previous suggestion labels
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

            # Add "Attacker" label above the source cell
            attacker_label = QGraphicsTextItem("Attacker")
            attacker_label.setFont(QFont("Arial", 12, QFont.Bold))
            attacker_label.setDefaultTextColor(Qt.green if self.current_turn == "green" else Qt.red)
            attacker_label.setPos(source.rect().x() + 50 - attacker_label.boundingRect().width() / 2, source.rect().y() - 20)
            attacker_label.setData(0, "suggestion_label")  # Mark as suggestion label
            self.addItem(attacker_label)

            # Add "Target" label above the target cell
            target_label = QGraphicsTextItem("Target")
            target_label.setFont(QFont("Arial", 12, QFont.Bold))
            target_label.setDefaultTextColor(Qt.green if self.current_turn == "green" else Qt.red)
            target_label.setPos(target.rect().x() + 50 - target_label.boundingRect().width() / 2, target.rect().y() - 20)
            target_label.setData(0, "suggestion_label")  # Mark as suggestion label
            self.addItem(target_label)
        else:
            suggestion = "No valid moves available."

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
        view = self.views()[0]
        view.setScene(GameScene())

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

        play_button.mousePressEvent = self.start_game
        level_button.mousePressEvent = self.show_level_selection

    def start_game(self, event):
        view = self.views()[0]
        view.setScene(GameScene())

    def show_level_selection(self, event):
        view = self.views()[0]
        view.setScene(LevelSelectionScene())

class HoverableRectItem(QGraphicsRectItem):
    def __init__(self, x, y, width, height, parent=None):
        super().__init__(x, y, width, height, parent)
        self.default_brush = QBrush(QColor(10, 10, 50))
        self.setBrush(self.default_brush)
        self.setAcceptHoverEvents(True)  # Enable hover events

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(QColor("#001E5A")))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(self.default_brush)
        super().hoverLeaveEvent(event)

class GameView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.suggestion_button = QPushButton("PODPOWIEDŹ", self)  # Initialize suggestion button first
        self.suggestion_button.setGeometry(400, 830, 100, 40)  # Position and size of the button
        self.suggestion_button.setFont(QFont("Arial", 9, QFont.Bold))
        self.suggestion_button.setStyleSheet("background-color: rgb(10, 10, 50); color: white;")
        self.suggestion_button.clicked.connect(self.request_suggestion)
        self.suggestion_button.hide()  # Initially hide the button

        self.setScene(MainMenuScene())  # Call setScene after initializing suggestion_button
        self.setRenderHint(QPainter.Antialiasing)
        self.setFixedSize(900, 900)
        self.message_label = QGraphicsTextItem("")
        self.message_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.message_label.setDefaultTextColor(Qt.white)
        self.message_label.setPos(150, 20)  # Position at the top center
        self.scene().addItem(self.message_label)
        
        # Create a QLabel for the moving mode message
        self.moving_mode_label = QLabel("Tryb przesuwania komórek. Obsługa strzałkami na klawiaturze. Kliknij \"ZAKOŃCZ\", aby wyjść z trybu.", self)
        self.moving_mode_label.setStyleSheet("color: white; background-color: rgba(10, 10, 50, 200); padding: 5px;")
        self.moving_mode_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.moving_mode_label.setGeometry(40, 760, 820, 30)  # Position above the "ZAKOŃCZ" button
        self.moving_mode_label.setAlignment(Qt.AlignCenter)
        self.moving_mode_label.hide()  # Initially hide the label

        self.end_button = QPushButton("ZAKOŃCZ", self)
        self.end_button.setGeometry(400, 800, 100, 40)  # Position and size of the button
        font = self.end_button.font()
        font.setBold(True)  # Pogrubienie czcionki
        font.setPointSize(9)  # Zwiększenie rozmiaru czcionki
        self.end_button.setFont(font)
        self.end_button.setStyleSheet("background-color: rgb(10, 10, 50); color: white;")  # Kolor tła i tekstu przycisku
        self.end_button.clicked.connect(self.hide_message)
        self.end_button.hide()  # Initially hide the button

        self.suggestion_label = QLabel("", self)
        self.suggestion_label.setStyleSheet("color: white; background-color: rgba(10, 10, 50, 200); padding: 5px;")
        self.suggestion_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.suggestion_label.setGeometry(40, 790, 820, 30)  # Lowered by 100 pixels
        self.suggestion_label.setAlignment(Qt.AlignCenter)
        self.suggestion_label.hide()

        self.show()

    def setScene(self, scene):
        super().setScene(scene)
        # Show or hide the suggestion button based on the scene type
        if isinstance(scene, GameScene):
            self.suggestion_button.show()
        else:
            self.suggestion_button.hide()

    def display_message(self, message):
        self.message_label.setPlainText(message)
        self.end_button.show()  # Show the button when displaying the message
        self.moving_mode_label.show()  # Show the moving mode label

    def hide_message(self):
        self.message_label.setPlainText("")
        self.end_button.hide()  # Hide the button when the message is hidden
        self.moving_mode_label.hide()  # Hide the moving mode label
        if ClickableCell.moving_cell:
            ClickableCell.moving_cell.setPen(QPen(Qt.black, 2))  # Usuń pomarańczową obwódkę
            ClickableCell.moving_cell = None  # Reset komórki w trybie przesuwania

    def display_suggestion(self, suggestion):
        """Display the AI suggestion."""
        self.suggestion_label.setText(suggestion)
        self.suggestion_label.show()

    def request_suggestion(self):
        """Request a suggestion from the game scene."""
        if isinstance(self.scene(), GameScene):
            self.scene().suggest_best_move()

    def keyPressEvent(self, event):
        if ClickableCell.moving_cell:
            ClickableCell.moving_cell.keyPressEvent(event)
        else:
            super().keyPressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    view = GameView()
    sys.exit(app.exec_())