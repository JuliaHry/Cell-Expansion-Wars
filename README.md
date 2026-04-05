  # Cell Expansion Wars

  Turn-based strategy game built with PyQt5 in which two factions (green and pink) fight to capture all cells on the board. The game uses QGraphicsScene/QGraphicsItem, has a unit level system, turn timer, move suggestions and a network mode with synchronized game state.

  ---

  ## Key Features

  - Two-player, turn-based strategy (green vs pink).
  - 5 board layouts with different cell placements, including neutral gray cells.
  - Unit levels (LVL 1–3) that affect the attack strength of each cell.
  - Bridges (lines) between cells with a limit of 2 bridges per cell.
  - Highlighting of valid attack targets and the cost of creating a bridge.
  - Combat system with mini-cells moving along bridges and explosion effects when capturing a cell.
  - Turn timer (10 s) and alternating turns with current player and time displayed.
  - “HINT” button with simple AI suggesting a potentially good move (attacking + target cell).
  - Logger printing messages to the console and a QTextEdit widget (rotating log with a 100-line limit).
  - Saving the current game state and resuming later.
  - Full game history recording and replay in separate windows from three sources:
    - XML file (`history.xml`),
    - JSON file (`history.json`),
    - MongoDB collection (`game_db.full_game_history`).
  - Network mode (server/client) with synchronized turns, cell values, levels and bridges.

  ---

  ## Game Modes

  - **Single player** – standard game with move suggestions available.
  - **Local 2-player** – two people play on the same machine, taking turns.
  - **Network game** – one instance runs as a server (green), the other as a client (pink):
    - the server owns the authoritative game state and sends updates to clients,
    - synchronized are: cell values, levels, bridges, current turn and remaining time,
    - each player can act only during their own turn (validated on both server and client).

  ---

  ## Requirements

  - Python 3.x (recommended 3.8+).
  - Libraries:
    - `PyQt5` – GUI,
    - `pymongo` – **optional**, for saving/replaying history in MongoDB.
  - For network mode: TCP connectivity (default port 5000).
  - For MongoDB replays: running MongoDB server (e.g. `mongodb://localhost:27017/`).

  Example installation:

  ```bash
  pip install PyQt5 pymongo
  ```

  If you do not use MongoDB, `pymongo` is not required to play the core game.

  ---

  ## Running the Game

  ### Main game

  From the project directory:

  ```bash
  python eks_komorek.py
  ```

  On startup you choose the level and game mode (single player / local / network). In network mode one instance acts as the server, the other as the client – you provide IP and port in the dialogs.

  ### Replaying recorded games

  During a game you have buttons in the top area of the window:

  - **SAVE HISTORY [XML]** – save history to `history.xml`.
  - **SAVE HISTORY [JSON]** – save history to `history.json`.
  - **SAVE HISTORY [MONGO]** – save history to MongoDB collection `game_db.full_game_history`.
  - **REPLAY [XML] / [JSON] / [MONGO]** – open the corresponding replay window.

  You can also run them manually from the terminal:

  ```bash
  python replay_view.py         # replay from history.xml
  python replay_view_json.py    # replay from history.json
  python replay_view_mongo.py   # replay from MongoDB
  ```

  Replay windows offer **Start** and **REPLAY** buttons and a speed slider.

  ### Saving and exiting

  The **“ZAKOŃCZ I ZAPISZ”** button (“FINISH AND SAVE”, at the bottom of the main window) saves the current match to a file and closes the app. On the next launch you can resume from the saved state.

  ---

  ## Rules and Controls

  ### Objective

  Capture all cells on the board. The game is turn-based: green and pink take turns, and each turn lasts 10 seconds.

  ### Creating bridges (attacks)

  1. Left-click your own cell (the attacker).
  2. Move the mouse – a line will follow from the center of the cell.
  3. Left-click the cell you want to attack or reinforce.

  This creates a bridge along which mini-cells travel from the attacking cell to the target. The cost of creating a bridge depends on its length and is subtracted from the attacking cell’s value. Attack strength depends on the cell level (LVL 1–3).

  ### Combat rules

  - **Bridge between cells of the same color**  
    The value of the source cell decreases, while the value of the target cell increases.

  - **Bridge to an enemy cell**  
    Both cells lose value. When the enemy cell’s value reaches 0, it is captured and changes to the attacker’s color with a starting value.

  - **Bridge to a gray (neutral) cell**  
    A gray cell has a top number (fill progress) and a bottom target value (e.g. 8).  
    The top number:
    - increases when the cell is being filled with a given color,
    - decreases when the opposite color starts filling it.  
    When the top number reaches the bottom value, the gray cell converts to the team that completed the fill.

  - **Bridge limit**  
    Each cell can have at most **2 bridges**. The two small circles on a cell indicate available bridge slots – when both are black, no more bridges can be created from that cell.

  ### Removing bridges

  - Left-click a bridge:
    - clicking closer to the attacking cell sends more mini-cells back to it,
    - clicking closer to the target cell lets more mini-cells reach it before the bridge is removed.

  ### Moving cells (edit mode)

  - Right-click a cell and choose **“Przesuń komórkę”** (“Move cell”).
  - The cell gets an orange outline and enters move mode.
  - Use the **arrow keys** to move the selected cell.
  - To move a different cell while in move mode, left-click it.
  - To leave move mode, use the corresponding UI option/button.

  ---

  ## Repository Structure

  - `eks_komorek.py` – main game logic, scene (`GameScene`), cells (`ClickableCell`), lines (`ClickableLine`), turn timer, history recording.
  - `network.py` – TCP client and server implementation (networked game synchronization).
  - `replay_view.py` – replay from XML history.
  - `replay_view_json.py` – replay from JSON history.
  - `replay_view_mongo.py` – replay from MongoDB history.
  - `resources.py`, `resources.qrc`, `images/` – graphical assets (e.g. cell textures for each team).

