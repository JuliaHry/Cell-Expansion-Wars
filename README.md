# Cell Expansion Wars

### Opis projektu

Projekt to turowa gra strategiczna zaimplementowana w PyQt5, w której dwie strony (zielona i różowa) rywalizują o przejęcie nwszystkich komórek na planszy. Gra posiada system walki, poziomy jednostek, efekty wizualne oraz mechanizm tur i AI podpowiadające najlepszy ruch. Interfejs oparty jest na QGraphicsScene i QGraphicsItem.

### Wymagania zaliczone w projekcie

- QGraphicsScene – implementacja sceny gry (1 pkt)

  - Klasa GameScene dziedziczy po QGraphicsScene i obsługuje całą logikę gry, w tym rysowanie, aktualizacje i zdarzenia myszy.

- Dziedziczenie po QGraphicsItem – jednostki jako osobne obiekty (1 pkt)

  - ClickableCell oraz ClickableLine dziedziczą odpowiednio po QGraphicsEllipseItem i QGraphicsLineItem, tworząc niezależne interaktywne jednostki.

- Interaktywność jednostek – klikalność, przeciąganie, menu kontekstowe (3 pkt)

  - Klikalne komórki i linie.

  - Menu kontekstowe dla komórek (przesuwanie, zmiana rozmiaru). Wyświetlane po kliknięciu prawym przyciskiem myszy na komórkę. Po kliknięciu prawym przyciskiem myszy na tło wyświetla się menu dla tła (możliwość jego zmiany)

  - Możliwość przesuwania komórek za pomocą klawiatury (tryb przesuwania) - aby go odpalić należy wybrać opcję "Przesuń komórkę" z menu kontekstowego komórek. Wprowadza to komórki w tryb przesuwania. Obługa przesuwania odywa się za pomocą klawiatury.
  - Aby przesuwać inną komórkę, należy - wciąż będąc w trybie przesuwania - kliknąć lewym przyciskiem myszy na inną komórkę (komórka aktualnie przesuwana zaznaczona jest pomarańczową obwódką). Aby opuścić tryb przesuwania należy kliknąć przycisk "ZAKOŃCZ"

- Sterowanie jednostkami – wybór z menu i ruch na siatce planszy (2 pkt)

  - Wybór jednostki oraz atak na przeciwnika.

  - Obsługa logicznych ruchów poprzez kliknięcia i przyciski.
 
  - Tryb przesuwania komórek.
 
    
- Zaciąganie grafik jednostek z pliku .rc (1 pkt)

  - Obrazy zielonych oraz różowych komórek wczytywane są z pliku resources.py w formacie .rc.

- Podświetlanie możliwych ruchów i ataków w zależności od mnożnika (2 pkt)

  - Komórki podświetlane na żółto, jeśli mogą zostać zaatakowane w momencie kliknięcia na komórkę, którą chcemy zaatakować (atakującą)

  - Zależność możliwości ataku od poziomu i wartości komórek.

- System walki uwzględniający poziomy, mnożenie jednostek i specjalne efekty bitewne (3 pkt)

  - Wartość ataku zależy od poziomu jednostki.

  - Po każdej walce (doprowadzeniu wrogiej mini komórki do komórki przeciwnika) następuje eksplozja graficzna.

  - System poziomów (LVL 1–3), który zwiększa siłę ataku.

 - Mechanizm tur i licznik czasu na wykonanie ruchu (zegar rundowy) (2 pkt)

  - Naprzemienne tury graczy (zielony/różowy).

  - Odliczanie czasu każdej tury (10 sekund).

- System podpowiedzi strategicznych oparty na AI (np. najlepszy ruch w turze) (1 pkt)

  - Przycisk „PODPOWIEDŹ” sugeruje optymalny ruch w bieżącej turze.

  - Informacje o sugerowanych jednostkach (atakujący, cel).

- Logger wyświetlający komunikaty na konsoli i w interfejsie QTextEdit z rotującym logowaniem (1 pkt)

  - Klasa Logger zapisuje logi do konsoli i do widgetu QTextEdit z limitem 100 linii.

- Sterowanie jednostkami za pomocą gestów z kamery (kliknięcie ruchem dłoni) (1 pkt) oraz Przełączanie widoku między 2D i 3D (w tym renderowanie jednostek w 3D) (2 pkt)

  - Niezaimplementowane.

**Podsumowując - projekt został wykonany na 17pkt**

### Jak uruchomić projekt

- Wymagania

  - Python 3.x

  - PyQt5

- Uruchomienie gry

  - python main.py
    

### Główne okno zawiera:

  - Menu główne z opcjami gry i wyboru poziomu.

  - Tryb gry z systemem tur, wartości, ataków i poziomów.

  - Podpowiedzi, logger, licznik czasu i system podświetlania.

