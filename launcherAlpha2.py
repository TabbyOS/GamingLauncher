import os
import json
import requests
import subprocess
import sys
from PyQt5 import QtWidgets, QtGui, QtCore
import platform

# Funktion zum Installieren fehlender Pakete
def install_missing_packages():
    required_packages = ["requests", "PyQt5"]
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"Package {package} not found. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Stelle sicher, dass alle benötigten Pakete zu Beginn installiert werden
install_missing_packages()

CONFIG_FILE = "launcher_config.json"

# Konfiguration in der JSON-Datei speichern
def save_config(config):
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file)

# Konfiguration aus der JSON-Datei laden, falls sie existiert, andernfalls ein leeres Dict zurückgeben
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    return {}

# Funktion zum Bereinigen von problematischen Umgebungsvariablen
def clean_environment():
    if "LD_PRELOAD" in os.environ:
        print("Clearing LD_PRELOAD to avoid conflicts.")
        del os.environ["LD_PRELOAD"]
    if "GAME_MODE" in os.environ:
        print("Clearing GameMode environment variable.")
        del os.environ["GAME_MODE"]

# Hilfsfunktion, um die richtige Ausführung von Programmen auf verschiedenen Plattformen zu gewährleisten
def open_url_platform_compatible(url):
    if platform.system() == "Linux":
        subprocess.run(["xdg-open", url])  # Linux verwendet xdg-open
    elif platform.system() == "Windows":
        subprocess.run(["start", url], shell=True)  # Windows verwendet start

# Funktion zum Starten eines Spiels über Steam
def start_game(app_id):
    if platform.system() == "Linux":
        # Steam im Hintergrund starten (ohne UI sichtbar)
        subprocess.Popen(["steam", "-applaunch", str(app_id)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    elif platform.system() == "Windows":
        # Steam im Hintergrund starten (ohne UI sichtbar)
        subprocess.Popen(["steam", "-applaunch", str(app_id)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

class GamingLauncher(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gaming Launcher Advanced")
        self.setGeometry(100, 100, 900, 700)

        # Benutzerkonfiguration laden
        self.config = load_config()
        self.steam_api_key = self.config.get("steam_api_key", "")
        self.steam_profile_id = self.config.get("steam_profile_id", "")
        self.user_profile = self.config.get("user_profile", {"name": "Guest", "avatar": None})

        self.steam_games = []
        self.filtered_games = []
        self.favorites = self.config.get("favorites", [])

        # Initialisiere die UI
        self.initUI()

    def initUI(self):
        # Haupt-UI-Komponenten und Layout einrichten
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)

        # Menüleiste einrichten
        menubar = self.menuBar()
        settings_menu = menubar.addMenu("Settings")

        # Aktionen für Steam API Key und Profile ID
        set_api_key_action = QtWidgets.QAction("Set Steam API Key", self)
        set_api_key_action.triggered.connect(self.set_steam_api_key)
        settings_menu.addAction(set_api_key_action)

        set_profile_id_action = QtWidgets.QAction("Set Steam Profile ID", self)
        set_profile_id_action.triggered.connect(self.set_steam_profile_id)
        settings_menu.addAction(set_profile_id_action)

        create_profile_action = QtWidgets.QAction("Create Profile", self)
        create_profile_action.triggered.connect(self.create_user_profile)
        settings_menu.addAction(create_profile_action)

        # Suchleiste für die Filterung der Spiele
        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText("Search for a game...")
        self.search_bar.textChanged.connect(self.filter_games)
        self.layout.addWidget(self.search_bar)

        # Dropdown für Spielkategorien (Alle, Kürzlich Gespielt, Installiert)
        self.filter_dropdown = QtWidgets.QComboBox()
        self.filter_dropdown.addItem("All")
        self.filter_dropdown.addItem("Recently Played")
        self.filter_dropdown.addItem("Installed")
        self.filter_dropdown.currentIndexChanged.connect(self.filter_games)
        self.layout.addWidget(self.filter_dropdown)

        # List-Widget für die Anzeige der Spiele
        self.game_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.game_list)

        # Profilbereich mit Avatar und Benutzernamen
        self.profile_widget = QtWidgets.QWidget()
        profile_layout = QtWidgets.QHBoxLayout(self.profile_widget)
        self.avatar_label = QtWidgets.QLabel()
        self.avatar_label.setFixedSize(50, 50)
        self.avatar_label.setScaledContents(True)
        self.avatar_label.setStyleSheet("border-radius: 25px;")

        self.profile_name_label = QtWidgets.QLabel(self.user_profile.get("name", "Guest"))
        profile_layout.addWidget(self.avatar_label)
        profile_layout.addWidget(self.profile_name_label)
        profile_layout.addStretch()
        self.layout.addWidget(self.profile_widget)

        # Refresh-Button, um die Spielbibliothek neu zu laden
        self.refresh_button = QtWidgets.QPushButton("Refresh Library")
        self.refresh_button.clicked.connect(self.refresh_library)
        self.layout.addWidget(self.refresh_button)

        # Button zum Öffnen des Steam-Profils im Browser
        self.steam_profile_button = QtWidgets.QPushButton("Go to Steam Profile")
        self.steam_profile_button.clicked.connect(self.open_steam_profile)
        self.layout.addWidget(self.steam_profile_button)

        # Button, um den Benutzer bei der Beschaffung eines Steam API-Schlüssels zu unterstützen
        self.api_key_help_button = QtWidgets.QPushButton("Get Steam API Key")
        self.api_key_help_button.clicked.connect(self.open_api_key_help)
        self.layout.addWidget(self.api_key_help_button)

        self.update_profile_ui()

        # Kontextmenü für die Spielliste einrichten
        self.game_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.game_list.customContextMenuRequested.connect(self.show_context_menu)

        # Doppelklick-Handler für das Starten eines Spiels
        self.game_list.itemDoubleClicked.connect(self.launch_game)

    def launch_game(self, item):
        # Startet das Spiel, wenn darauf geklickt wird
        app_id = item.data(QtCore.Qt.UserRole)
        start_game(app_id)

    def set_steam_api_key(self):
        # Eingabeaufforderung zur Festlegung des Steam API-Schlüssels
        key, ok = QtWidgets.QInputDialog.getText(self, "Steam API Key", "Enter your Steam API Key:")
        if ok and key:
            self.steam_api_key = key
            self.config["steam_api_key"] = key
            save_config(self.config)
            QtWidgets.QMessageBox.information(self, "Success", "Steam API Key has been set.")

    def set_steam_profile_id(self):
        # Eingabeaufforderung zur Festlegung der Steam-Profil-ID
        profile_id, ok = QtWidgets.QInputDialog.getText(self, "Steam Profile ID", "Enter your Steam Profile ID:")
        if ok and profile_id:
            self.steam_profile_id = profile_id
            self.config["steam_profile_id"] = profile_id
            save_config(self.config)
            QtWidgets.QMessageBox.information(self, "Success", "Steam Profile ID has been set.")

    def create_user_profile(self):
        # Ermögliche dem Benutzer, ein Profil mit Namen und Avatar zu erstellen
        name, ok = QtWidgets.QInputDialog.getText(self, "Create Profile", "Enter your profile name:")
        if not ok or not name:
            return

        avatar_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Avatar", "", "Images (*.png *.jpg *.jpeg)")
        if not avatar_path:
            return

        self.user_profile = {"name": name, "avatar": avatar_path}
        self.config["user_profile"] = self.user_profile
        save_config(self.config)
        self.update_profile_ui()

    def update_profile_ui(self):
        # Update das Profil-UI mit dem neuen Namen und Avatar
        self.profile_name_label.setText(self.user_profile.get("name", "Guest"))
        avatar_path = self.user_profile.get("avatar")
        if avatar_path and os.path.exists(avatar_path):
            pixmap = QtGui.QPixmap(avatar_path).scaled(50, 50, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.avatar_label.setPixmap(pixmap)
        else:
            self.avatar_label.clear()

    def refresh_library(self):
        # Steam-Spielbibliothek mit der API neu laden
        if not self.steam_api_key or not self.steam_profile_id:
            QtWidgets.QMessageBox.warning(self, "Error", "Please set your Steam API Key and Profile ID first.")
            return

        try:
            url = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?key={self.steam_api_key}&steamid={self.steam_profile_id}&include_appinfo=true"
            response = requests.get(url)
            response.raise_for_status()

            data = response.json()
            games = data.get('response', {}).get('games', [])

            if not games:
                QtWidgets.QMessageBox.warning(self, "No Games Found", "No games were found in your Steam library. Please check your Steam ID or API key.")
                return

            self.steam_games = games
            self.filtered_games = games
            self.update_game_list()

        except requests.RequestException as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to retrieve game data: {str(e)}")

    def update_game_list(self):
        # Aktualisiert die Anzeige der Spiele im Launcher mit Bildern
        self.game_list.clear()
        for game in self.filtered_games:
            item = QtWidgets.QListWidgetItem(game.get("name", "Unknown Game"))
            item.setData(QtCore.Qt.UserRole, game.get("appid"))

            # Spielbild hinzufügen
            img_url = game.get("img_icon_url")
            if img_url:
                img_url = f"http://media.steampowered.com/steamcommunity/public/images/apps/{game['appid']}/{img_url}.jpg"
                pixmap = QtGui.QPixmap()
                pixmap.loadFromData(requests.get(img_url).content)  # Laden des Bildes
                icon = QtGui.QIcon(pixmap)
                item.setIcon(icon)

            self.game_list.addItem(item)

    def filter_games(self):
        # Filtert die Spiele nach Namen oder Kategorie
        query = self.search_bar.text().lower()
        category = self.filter_dropdown.currentText()

        self.filtered_games = [
            game for game in self.steam_games
            if query in game.get('name', '').lower()
        ]
        self.update_game_list()

    def show_context_menu(self, pos):
        # Kontextmenü zum Hinzufügen von Spielen zu den Favoriten
        context_menu = QtWidgets.QMenu(self)
        add_favorite_action = context_menu.addAction("Add to Favorites")
        action = context_menu.exec_(self.game_list.mapToGlobal(pos))

        if action == add_favorite_action:
            current_item = self.game_list.currentItem()
            if current_item:
                app_id = current_item.data(QtCore.Qt.UserRole)
                if app_id not in self.favorites:
                    self.favorites.append(app_id)
                    self.config["favorites"] = self.favorites
                    save_config(self.config)
                    QtWidgets.QMessageBox.information(self, "Added", "Game added to favorites.")

    def open_steam_profile(self):
        # Öffnet das Steam-Profil im Standard-Browser
        profile_url = f"https://steamcommunity.com/profiles/{self.steam_profile_id}"
        open_url_platform_compatible(profile_url)

    def open_api_key_help(self):
        # Öffnet die Seite zum Abrufen des Steam API-Schlüssels
        url = "https://steamcommunity.com/dev/apikey"
        open_url_platform_compatible(url)

def main():
    app = QtWidgets.QApplication(sys.argv)
    launcher = GamingLauncher()
    launcher.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
