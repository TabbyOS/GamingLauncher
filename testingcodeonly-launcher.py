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

# Konfigurationsdatei im Benutzerverzeichnis speichern
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".launcher_config.json")

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
    for var in ["LD_PRELOAD", "GAME_MODE"]:
        if var in os.environ:
            print(f"Clearing {var} to avoid conflicts.")
            del os.environ[var]

# Hilfsfunktion, um die richtige Ausführung von Programmen auf verschiedenen Plattformen zu gewährleisten
def open_url_platform_compatible(url):
    if platform.system() == "Linux":
        subprocess.run(["xdg-open", url])
    elif platform.system() == "Windows":
        os.startfile(url)

# Funktion zum Starten eines Spiels über Steam
def start_game(app_id):
    command = ["steam", "-applaunch", str(app_id)]
    try:
        subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        print("Steam executable not found. Ensure Steam is installed and in PATH.")

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
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)
        
        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText("Search for a game...")
        self.search_bar.textChanged.connect(self.filter_games)
        self.layout.addWidget(self.search_bar)

        self.game_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.game_list)

        self.refresh_button = QtWidgets.QPushButton("Refresh Library")
        self.refresh_button.clicked.connect(self.refresh_library)
        self.layout.addWidget(self.refresh_button)

        self.update_game_list()
    
    def refresh_library(self):
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
        self.game_list.clear()
        for game in self.filtered_games:
            item = QtWidgets.QListWidgetItem(game.get("name", "Unknown Game"))
            item.setData(QtCore.Qt.UserRole, game.get("appid"))
            self.game_list.addItem(item)

def main():
    app = QtWidgets.QApplication(sys.argv)
    launcher = GamingLauncher()
    launcher.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
