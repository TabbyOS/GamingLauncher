import os
import json
import requests
import subprocess
import sys
from PyQt5 import QtWidgets, QtGui, QtCore
import platform

# Function to install missing required packages
def install_missing_packages():
    required_packages = ["requests", "PyQt5"]
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"Package {package} not found. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Ensure all required packages are installed at the start
install_missing_packages()

CONFIG_FILE = "launcher_config.json"

# Save configuration to the JSON file
def save_config(config):
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file)

# Load configuration from the JSON file if it exists, otherwise return an empty dict
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    return {}

# Function to clean up problematic environment variables
def clean_environment():
    if "LD_PRELOAD" in os.environ:
        print("Clearing LD_PRELOAD to avoid conflicts.")
        del os.environ["LD_PRELOAD"]
    if "GAME_MODE" in os.environ:
        print("Clearing GameMode environment variable.")
        del os.environ["GAME_MODE"]

class GamingLauncher(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gaming Launcher Advanced")
        self.setGeometry(100, 100, 900, 700)

        # Load the user configuration settings
        self.config = load_config()
        self.steam_api_key = self.config.get("steam_api_key", "")
        self.steam_profile_id = self.config.get("steam_profile_id", "")
        self.user_profile = self.config.get("user_profile", {"name": "Guest", "avatar": None})

        self.steam_games = []
        self.filtered_games = []
        self.favorites = self.config.get("favorites", [])

        # Initialize the UI
        self.initUI()

    def initUI(self):
        # Set up the main UI components and layout
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)

        # Menu bar setup
        menubar = self.menuBar()
        settings_menu = menubar.addMenu("Settings")

        # Actions for Steam API Key and Profile ID setup
        set_api_key_action = QtWidgets.QAction("Set Steam API Key", self)
        set_api_key_action.triggered.connect(self.set_steam_api_key)
        settings_menu.addAction(set_api_key_action)

        set_profile_id_action = QtWidgets.QAction("Set Steam Profile ID", self)
        set_profile_id_action.triggered.connect(self.set_steam_profile_id)
        settings_menu.addAction(set_profile_id_action)

        create_profile_action = QtWidgets.QAction("Create Profile", self)
        create_profile_action.triggered.connect(self.create_user_profile)
        settings_menu.addAction(create_profile_action)

        # Search bar for filtering games
        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText("Search for a game...")
        self.search_bar.textChanged.connect(self.filter_games)
        self.layout.addWidget(self.search_bar)

        # Filter dropdown for game categories (All, Recently Played, Installed)
        self.filter_dropdown = QtWidgets.QComboBox()
        self.filter_dropdown.addItem("All")
        self.filter_dropdown.addItem("Recently Played")
        self.filter_dropdown.addItem("Installed")
        self.filter_dropdown.currentIndexChanged.connect(self.filter_games)
        self.layout.addWidget(self.filter_dropdown)

        # List widget to display games
        self.game_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.game_list)

        # Profile section with avatar and username
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

        # Refresh button to reload the game library
        self.refresh_button = QtWidgets.QPushButton("Refresh Library")
        self.refresh_button.clicked.connect(self.refresh_library)
        self.layout.addWidget(self.refresh_button)

        # Button to open the Steam profile in the browser
        self.steam_profile_button = QtWidgets.QPushButton("Go to Steam Profile")
        self.steam_profile_button.clicked.connect(self.open_steam_profile)
        self.layout.addWidget(self.steam_profile_button)

        # Button to guide the user on obtaining a Steam API key
        self.api_key_help_button = QtWidgets.QPushButton("Get Steam API Key")
        self.api_key_help_button.clicked.connect(self.open_api_key_help)
        self.layout.addWidget(self.api_key_help_button)

        self.update_profile_ui()

        # Set up the context menu for the game list
        self.game_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.game_list.customContextMenuRequested.connect(self.show_context_menu)

    def set_steam_api_key(self):
        # Prompt to set the Steam API Key
        key, ok = QtWidgets.QInputDialog.getText(self, "Steam API Key", "Enter your Steam API Key:")
        if ok and key:
            self.steam_api_key = key
            self.config["steam_api_key"] = key
            save_config(self.config)
            QtWidgets.QMessageBox.information(self, "Success", "Steam API Key has been set.")

    def set_steam_profile_id(self):
        # Prompt to set the Steam Profile ID
        profile_id, ok = QtWidgets.QInputDialog.getText(self, "Steam Profile ID", "Enter your Steam Profile ID:")
        if ok and profile_id:
            self.steam_profile_id = profile_id
            self.config["steam_profile_id"] = profile_id
            save_config(self.config)
            QtWidgets.QMessageBox.information(self, "Success", "Steam Profile ID has been set.")

    def create_user_profile(self):
        # Allow the user to create a profile with a name and avatar
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
        # Update the profile UI with the new name and avatar
        self.profile_name_label.setText(self.user_profile.get("name", "Guest"))
        avatar_path = self.user_profile.get("avatar")
        if avatar_path and os.path.exists(avatar_path):
            pixmap = QtGui.QPixmap(avatar_path).scaled(50, 50, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.avatar_label.setPixmap(pixmap)
        else:
            self.avatar_label.clear()

    def refresh_library(self):
        # Refresh the Steam game library using the API
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
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to fetch Steam library: {e}")

    def update_game_list(self):
        # Update the list of games shown in the UI
        self.game_list.clear()
        for game in self.filtered_games:
            name = game.get('name', f"Steam Game {game.get('appid', '')}")
            app_id = game.get('appid', '')

            item = QtWidgets.QListWidgetItem(name)
            icon_url = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg"
            icon_path = f"cache/{app_id}.jpg"

            if not os.path.exists("cache"):
                os.mkdir("cache")

            if not os.path.exists(icon_path):
                try:
                    img_data = requests.get(icon_url).content
                    with open(icon_path, "wb") as img_file:
                        img_file.write(img_data)
                except Exception as e:
                    print(f"Error downloading icon: {e}")
                    continue

            if os.path.exists(icon_path):
                icon = QtGui.QIcon(icon_path)
                item.setIcon(icon)

            item.setData(QtCore.Qt.UserRole, app_id)

            self.game_list.addItem(item)

    def filter_games(self):
        # Filter the list of games based on search and filter criteria
        search_term = self.search_bar.text().lower()
        filter_index = self.filter_dropdown.currentIndex()

        self.filtered_games = [
            game for game in self.steam_games
            if search_term in game['name'].lower()
        ]

        if filter_index == 1:  # Recently Played filter
            self.filtered_games = [
                game for game in self.filtered_games if game.get('playtime_2weeks', 0) > 0
            ]
        elif filter_index == 2:  # Installed filter
            self.filtered_games = [
                game for game in self.filtered_games if game.get('has_community_visible_stats', False)
            ]

        self.update_game_list()

    def show_context_menu(self, pos):
        # Display the context menu for each game in the list
        menu = QtWidgets.QMenu(self)

        play_action = menu.addAction("Play")
        play_action.triggered.connect(self.start_game)

        favorite_action = menu.addAction("Add to Favorites")
        favorite_action.triggered.connect(self.add_to_favorites)

        menu.exec_(self.game_list.mapToGlobal(pos))

    def start_game(self):
        # Start the selected game
        item = self.game_list.currentItem()
        if item is None:
            return

        app_id = item.data(QtCore.Qt.UserRole)
        if app_id is None:
            return

        print(f"Starting game with App ID: {app_id}")

        # Clean up environment variables before launching the game
        clean_environment()

        # Launch Steam in silent mode with the game
        try:
            subprocess.Popen(["steam", "-silent", f"steam://run/{app_id}"])
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to start the game: {e}")

    def add_to_favorites(self):
        # Add the selected game to the favorites list
        item = self.game_list.currentItem()
        if item is None:
            return

        app_id = item.data(QtCore.Qt.UserRole)
        if app_id in self.favorites:
            return

        self.favorites.append(app_id)
        self.config["favorites"] = self.favorites
        save_config(self.config)

        QtWidgets.QMessageBox.information(self, "Success", "Game added to favorites.")

    def open_steam_profile(self):
        # Open the user's Steam profile in the default browser
        profile_url = f"https://steamcommunity.com/profiles/{self.steam_profile_id}"
        subprocess.run(["xdg-open", profile_url])

    def open_api_key_help(self):
        # Open the URL for obtaining the Steam API key
        url = "https://steamcommunity.com/dev/apikey"
        subprocess.run(["xdg-open", url])

def main():
    app = QtWidgets.QApplication(sys.argv)
    launcher = GamingLauncher()
    launcher.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
