import sys, requests
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QScrollArea, QGridLayout,
                           QFrame, QLineEdit, QStackedWidget, QSizePolicy, QLayout,
                           QDialog, QDialogButtonBox, QFileDialog, QMessageBox, QProgressDialog,
                           QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QSize, QRect, QPoint, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QPalette, QColor, QPainter, QPainterPath, QFontMetrics
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtSvgWidgets import QSvgWidget
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from PIL import Image, ImageDraw
import io
import json
import tempfile
import atexit
import shutil
import zipfile
import webbrowser
import psutil

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def create_svg_widget(svg_path, width, height):
    """Create a QSvgWidget with the specified SVG file"""
    svg_widget = QSvgWidget(resource_path(svg_path))
    svg_widget.setFixedSize(width, height)
    return svg_widget

# Create a temporary directory for storing icon files
TEMP_DIR = os.path.join(tempfile.gettempdir(), "repohub_temp")
os.makedirs(TEMP_DIR, exist_ok=True)

def cleanup_temp_files():
    """Clean up all temporary files on application exit"""
    try:
        shutil.rmtree(TEMP_DIR)
    except:
        pass

# Register cleanup function to run on exit
atexit.register(cleanup_temp_files)

def get_temp_file_path(filename):
    """Get a path for a temporary file in the temp directory"""
    return os.path.join(TEMP_DIR, filename)

def launch_game(steam_app_id):
    # Tries to launch using webbrowser (works on all platforms if Steam is installed properly)
    steam_url = f"steam://run/{steam_app_id}"
    try:
        print(f"Launching Steam game with App ID: {steam_app_id}")
        webbrowser.open(steam_url)
    except Exception as e:
        print(f"Failed to launch the game: {e}")

def is_game_running(process_name="repo.exe"):
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
            return True
    return False

class ConfigManager:
    def __init__(self):
        self.config_path = os.path.join(os.path.expanduser("~"), ".repohub", "config.json")
        self.config = self.load_config()
    
    def load_config(self):
        # Create config directory if it doesn't exist
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Load config if it exists
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_config(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def set(self, key, value):
        self.config[key] = value
        self.save_config()
    
    def get_installed_mods(self):
        return self.config.get('installed_mods', {})
    
    def add_installed_mod(self, mod_name, mod_data):
        installed_mods = self.get_installed_mods()
        if not isinstance(installed_mods, dict):
            installed_mods = {}
        installed_mods[mod_name] = mod_data
        self.config['installed_mods'] = installed_mods
        self.save_config()
    
    def remove_installed_mod(self, mod_name):
        installed_mods = self.get_installed_mods()
        if mod_name in installed_mods:
            del installed_mods[mod_name]
            self.config['installed_mods'] = installed_mods
            self.save_config()
    
    def get_installed_dependencies(self):
        return self.config.get('installed_dependencies', [])
    
    def add_installed_dependency(self, dependency):
        installed_deps = self.get_installed_dependencies()
        if dependency not in installed_deps:
            installed_deps.append(dependency)
            self.config['installed_dependencies'] = installed_deps
            self.save_config()
    
    def is_dependency_installed(self, dependency):
        return dependency in self.get_installed_dependencies()

class HoverFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border-radius: 10px;
            }
        """)
        
        # Create hover overlay
        self.overlay = QFrame(self)
        self.overlay.setFixedSize(200, 200)
        self.overlay.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 10px;
            }
        """)
        self.overlay.hide()
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    
    def enterEvent(self, event):
        self.overlay.show()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.overlay.hide()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if hasattr(self, 'on_click'):
                self.on_click()
        super().mousePressEvent(event)

class CardSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create container for scroll area and buttons
        container = QWidget()
        container_layout = QHBoxLayout()
        container_layout.setSpacing(0)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Cards widget
        self.cards_widget = QWidget()
        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(15)
        self.cards_layout.setContentsMargins(20, 0, 20, 0)
        
        # Add placeholder cards
        for i in range(5):
            card = QWidget()
            card.setFixedSize(200, 200)
            card.setStyleSheet("background-color: #333; border-radius: 10px;")
            self.cards_layout.addWidget(card, 0, i)
        
        self.cards_widget.setLayout(self.cards_layout)
        
        # Calculate minimum width needed for all cards
        self.update_minimum_width()
        
        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.cards_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFixedHeight(220)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # Left scroll button
        self.left_button = QFrame()
        self.left_button.setFixedSize(40, 40)
        self.left_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.left_button.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.7);
                border: none;
                border-radius: 20px;
            }
            QFrame:hover {
                background-color: rgba(0, 0, 0, 0.8);
            }
        """)
        self.left_button.mousePressEvent = lambda event: self.scroll_left()
        
        # Add SVG icon to left button
        left_icon = create_svg_widget("static/img/arrow-left.svg", 20, 20)
        left_icon.setStyleSheet("background-color: transparent;")
        left_layout = QHBoxLayout(self.left_button)
        left_layout.addWidget(left_icon, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Right scroll button
        self.right_button = QFrame()
        self.right_button.setFixedSize(40, 40)
        self.right_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.right_button.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.7);
                border: none;
                border-radius: 20px;
            }
            QFrame:hover {
                background-color: rgba(0, 0, 0, 0.8);
            }
        """)
        self.right_button.mousePressEvent = lambda event: self.scroll_right()
        
        # Add SVG icon to right button
        right_icon = create_svg_widget("static/img/arrow-right.svg", 20, 20)
        right_icon.setStyleSheet("background-color: transparent;")
        right_layout = QHBoxLayout(self.right_button)
        right_layout.addWidget(right_icon, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Add buttons directly to the scroll area's viewport
        self.left_button.setParent(self.scroll_area.viewport())
        self.right_button.setParent(self.scroll_area.viewport())
        
        # Position buttons
        def update_button_positions():
            viewport = self.scroll_area.viewport()
            self.left_button.move(10, (viewport.height() - 40) // 2)
            self.right_button.move(viewport.width() - 50, (viewport.height() - 40) // 2)
        
        # Update button positions when scroll area resizes
        def resize_event(event):
            QScrollArea.resizeEvent(self.scroll_area, event)
            update_button_positions()
            self.update_minimum_width()
        
        self.scroll_area.resizeEvent = resize_event
        
        # Initial button positioning
        update_button_positions()
        
        # Add scroll area to container
        container_layout.addWidget(self.scroll_area)
        container.setLayout(container_layout)
        
        # Add container to main layout
        layout.addWidget(container)
        self.setLayout(layout)
    
    def update_minimum_width(self):
        """Update the minimum width of the cards widget based on the number of cards"""
        num_cards = self.cards_layout.count()
        if num_cards > 0:
            min_width = (num_cards * 200) + ((num_cards - 1) * 15) + 40  # cards * 200px + spaces * 15px + 40px margins
            self.cards_widget.setMinimumWidth(min_width)
    
    def scroll_left(self):
        self.scroll_area.horizontalScrollBar().setValue(
            self.scroll_area.horizontalScrollBar().value() - 220)
    
    def scroll_right(self):
        self.scroll_area.horizontalScrollBar().setValue(
            self.scroll_area.horizontalScrollBar().value() + 220)

class ModalOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setup_ui()
        
    def setup_ui(self):
        # Create main container
        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border-radius: 10px;
                border: 1px solid #333;
            }
        """)
        
        # Main layout
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Close button
        close_button = QPushButton("×")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 24px;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                color: #aaa;
            }
        """)
        close_button.setFixedSize(30, 30)
        close_button.clicked.connect(self.close)
        
        # Add close button to top right
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_layout.addWidget(close_button)
        layout.addLayout(close_layout)
        
        self.content_layout = QVBoxLayout()
        layout.addLayout(self.content_layout)
        
        # Set container as central widget
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
    def set_content(self, widget):
        # Clear existing content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new content
        self.content_layout.addWidget(widget)
        
    def showEvent(self, event):
        # Center the overlay
        parent_rect = self.parent().rect()
        self.move(parent_rect.center() - self.rect().center())
        super().showEvent(event)

class DependencyDialog(QDialog):
    def __init__(self, dependencies, repo_path=None, parent=None):
        super().__init__(parent)
        self.dependencies = dependencies
        self.repo_path = repo_path
        self.config = ConfigManager()
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Install Dependencies")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Message
        message = QLabel("The following dependencies are required:")
        layout.addWidget(message)
        
        # Dependencies list
        self.deps_list = QListWidget()
        for dep in self.dependencies:
            # Each dependency is a string in the format "author-modname-version"
            parts = dep.split("-")
            if len(parts) >= 2:
                name = f"{parts[0]}/{parts[1]}"
                if len(parts) >= 3:
                    name += f" (v{parts[2]})"
                
                # Check if dependency is already installed
                is_installed = self.config.is_dependency_installed(dep)
                if is_installed:
                    name += " (Already installed)"
                
                item = QListWidgetItem(name)
                item.setCheckState(Qt.CheckState.Checked)
                if is_installed:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                    item.setCheckState(Qt.CheckState.Unchecked)
                self.deps_list.addItem(item)
        layout.addWidget(self.deps_list)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.setCursor(Qt.CursorShape.PointingHandCursor)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_selected_dependencies(self):
        selected = []
        for i in range(self.deps_list.count()):
            item = self.deps_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(self.dependencies[i])
        return selected

class ModDetailsContent(QWidget):
    def __init__(self, mod_data, repo_path=None, parent=None, is_library=False):
        super().__init__(parent)
        self.mod_data = mod_data
        self.repo_path = repo_path
        self.is_library = is_library
        self.temp_file = get_temp_file_path(f"icon_{hash(mod_data['icon'])}.png")
        self.config = ConfigManager()
        self.setup_ui(mod_data)
    
    def setup_ui(self, mod_data):
        # Main layout with two columns
        main_layout = QHBoxLayout()
        main_layout.setSpacing(30)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left column for text content
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #181414;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #333;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #444;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        left_content = QWidget()
        left_column = QVBoxLayout(left_content)
        left_column.setSpacing(15)
        left_column.setContentsMargins(0, 0, 20, 0)  # Add right margin for scrollbar
        
        # Mod name
        name_label = QLabel(mod_data["name"])
        name_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 32px;
                font-weight: bold;
            }
        """)
        left_column.addWidget(name_label)
        
        # Creator name
        creator_label = QLabel(f"by {mod_data['creator']}")
        creator_label.setStyleSheet("""
            QLabel {
                color: #aaa;
                font-size: 18px;
            }
        """)
        left_column.addWidget(creator_label)
        
        # Version and downloads
        info_label = QLabel(f"Version: {mod_data['version']}\nDownloads: {mod_data['downloads']}\nFile Size: {self.format_file_size(mod_data['file_size'])}")
        info_label.setStyleSheet("""
            QLabel {
                color: #aaa;
                font-size: 16px;
            }
        """)
        info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        left_column.addWidget(info_label)
        
        # Dependencies
        if mod_data['dependencies']:
            deps_label = QLabel("Dependencies:")
            deps_label.setStyleSheet("""
                QLabel {
                    color: #aaa;
                    font-size: 16px;
                    font-weight: bold;
                }
            """)
            left_column.addWidget(deps_label)
            
            for dep in mod_data['dependencies']:
                dep_label = QLabel(f"• {dep}")
                dep_label.setStyleSheet("""
                    QLabel {
                        color: #aaa;
                        font-size: 14px;
                        margin-left: 10px;
                    }
                """)
                left_column.addWidget(dep_label)
        
        # Description
        desc_label = QLabel(mod_data["description"])
        desc_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                line-height: 1.5;
            }
        """)
        desc_label.setWordWrap(True)
        left_column.addWidget(desc_label)
        
        # Add stretch to push content to top
        left_column.addStretch()
        
        # Button container
        button_container = QHBoxLayout()
        button_container.setSpacing(10)
        
        if self.is_library:
            # Disable button
            self.disable_button = QPushButton("Disable")
            self.disable_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.disable_button.setStyleSheet("""
                QPushButton {
                    background-color: #666;
                    color: #1a1a1a;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    min-width: 150px;
                }
                QPushButton:hover {
                    background-color: #777;
                }
            """)
            self.disable_button.clicked.connect(self.toggle_mod)
            button_container.addWidget(self.disable_button)
            
            # Uninstall button
            self.uninstall_button = QPushButton("Uninstall")
            self.uninstall_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.uninstall_button.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: #1a1a1a;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    min-width: 150px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            self.uninstall_button.clicked.connect(self.uninstall_mod)
            button_container.addWidget(self.uninstall_button)
        else:
            # Add to mods button
            self.add_button = QPushButton("Add to mods")
            self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.add_button.setStyleSheet("""
                QPushButton {
                    background-color: #F7B10C;
                    color: #1a1a1a;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    min-width: 150px;
                }
                QPushButton:hover {
                    background-color: #FF8C00;
                }
                QPushButton:disabled {
                    background-color: #666;
                    color: #999;
                }
            """)
            self.add_button.clicked.connect(self.add_to_mods)
            
            # Check if BepInEx exists and disable button if not
            if self.repo_path:
                bepinex_path = os.path.join(self.repo_path, "BepInEx")
                if not os.path.exists(bepinex_path):
                    self.add_button.setEnabled(False)
            else:
                self.add_button.setEnabled(False)
            
            button_container.addWidget(self.add_button)
        
        left_column.addLayout(button_container)
        
        # Set the left content widget as the scroll area's widget
        left_scroll.setWidget(left_content)
        
        # Right column for icon
        right_column = QVBoxLayout()
        right_column.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Mod icon
        icon_label = QLabel()
        response = requests.get(mod_data["icon"])
        if response.status_code == 200:
            image = Image.open(io.BytesIO(response.content))
            image = image.resize((300, 300), Image.Resampling.LANCZOS)
            image.save(self.temp_file)
            icon_label.setPixmap(QPixmap(self.temp_file))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_column.addWidget(icon_label)
        
        # Add columns to main layout
        main_layout.addWidget(left_scroll, 1)  # Left column takes more space
        main_layout.addLayout(right_column, 1)  # Right column takes less space
        
        self.setLayout(main_layout)
    
    def add_to_mods(self):
        if not self.repo_path:
            QMessageBox.critical(
                self,
                "Error",
                "Please set a valid R.E.P.O. path first!",
                QMessageBox.StandardButton.Ok
            )
            return

        # Check for BepInEx and mark any BepInEx-related dependencies as installed
        bepinex_path = os.path.join(self.repo_path, "BepInEx")
        if os.path.exists(bepinex_path):
            # Get all installed dependencies
            installed_deps = self.config.get_installed_dependencies()
            
            # Check if any BepInEx-related dependency is already marked as installed
            has_bepinex_dep = any("bepinex" in dep.lower() for dep in installed_deps)
            
            if not has_bepinex_dep:
                # Find the first BepInEx-related dependency in the mod's dependencies
                bepinex_dep = next((dep for dep in self.mod_data.get('dependencies', []) 
                                  if "bepinex" in dep.lower()), None)
                if bepinex_dep:
                    self.config.add_installed_dependency(bepinex_dep)

        # Filter out BepInEx-related dependencies if BepInEx is installed
        filtered_dependencies = []
        if self.mod_data.get('dependencies'):
            for dep in self.mod_data['dependencies']:
                # Skip BepInEx-related dependencies if BepInEx is installed
                if os.path.exists(bepinex_path) and "bepinex" in dep.lower():
                    continue
                filtered_dependencies.append(dep)

        # Check for remaining dependencies
        if filtered_dependencies:
            dialog = DependencyDialog(filtered_dependencies, self.repo_path)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_deps = dialog.get_selected_dependencies()
                if selected_deps:
                    self.install_dependencies(selected_deps)
            else:
                return

        # Install the main mod
        self.install_mod(self.mod_data)
    
    def install_dependencies(self, dependencies):
        progress = QProgressDialog("Installing dependencies...", "Cancel", 0, len(dependencies), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle("Installing Dependencies")
        
        try:
            # First, fetch all available mods
            url = "https://thunderstore.io/c/repo/api/v1/package/"
            response = requests.get(url)
            if response.status_code != 200:
                raise Exception("Failed to fetch mod list from Thunderstore")
            
            all_mods = response.json()
            
            for i, dep in enumerate(dependencies):
                # Skip if already installed
                if self.config.is_dependency_installed(dep):
                    continue
                
                # Get the dependency mod data from the API
                dep_parts = dep.split("-")
                if len(dep_parts) >= 2:
                    # The first part is always the author
                    dep_author = dep_parts[0]
                    # The last part is the version if there are 3 parts
                    dep_version = dep_parts[-1] if len(dep_parts) >= 3 else None
                    # The mod name is everything in between
                    dep_name = "-".join(dep_parts[1:-1]) if len(dep_parts) >= 3 else dep_parts[1]
                    
                    # Search for the mod in the list
                    matching_mod = None
                    for mod in all_mods:
                        if mod["owner"] == dep_author and mod["name"] == dep_name:
                            matching_mod = mod
                            break
                    
                    if matching_mod:
                        # Find the correct version
                        if dep_version:
                            dep_version_data = next((v for v in matching_mod["versions"] if v["version_number"] == dep_version), None)
                        else:
                            dep_version_data = max(matching_mod["versions"], key=lambda v: v["version_number"])
                        
                        if dep_version_data:
                            progress.setLabelText(f"Installing {dep_name}...")
                            self.install_mod({
                                "name": dep_name,
                                "version": dep_version_data["version_number"],
                                "download_url": dep_version_data["download_url"],
                                "icon": dep_version_data["icon"]
                            })
                            # Mark dependency as installed
                            self.config.add_installed_dependency(dep)
                            progress.setValue(i + 1)
                            QApplication.processEvents()
                        else:
                            raise Exception(f"Could not find version {dep_version} for {dep_name}")
                    else:
                        raise Exception(f"Could not find mod {dep_name} by author {dep_author}")
                else:
                    raise Exception(f"Invalid dependency format: {dep}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to install dependencies: {str(e)}",
                QMessageBox.StandardButton.Ok
            )
        finally:
            progress.close()
    
    def install_mod(self, mod_data):
        progress = QProgressDialog(f"Installing {mod_data['name']}...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle("Installing Mod")
        
        try:
            # Get the download URL from the mod data
            download_url = mod_data.get('download_url')
            if not download_url:
                # If no download URL in mod_data, try to get it from the API
                mod_name = mod_data['name']
                url = f"https://thunderstore.io/c/repo/api/v1/package/{mod_name}/"
                response = requests.get(url)
                if response.status_code == 200:
                    api_data = response.json()
                    # Get the latest version
                    latest_version = max(api_data["versions"], key=lambda v: v["version_number"])
                    download_url = latest_version.get("download_url")
                    # Update mod_data with the latest version info
                    mod_data.update({
                        'version': latest_version['version_number'],
                        'download_url': download_url,
                        'icon': latest_version.get('icon', mod_data.get('icon')),
                        'description': latest_version.get('description', mod_data.get('description')),
                        'dependencies': latest_version.get('dependencies', mod_data.get('dependencies', []))
                    })
            
            if not download_url:
                raise Exception("Could not find download URL for the mod")

            # Determine if this is a dependency or main mod
            is_dependency = any(dep in mod_data['name'].lower() for dep in ['bepinex', 'repolib'])
            
            # Set the target directory based on whether it's a dependency or main mod
            if is_dependency:
                # For dependencies, extract directly to plugins folder
                target_dir = os.path.join(self.repo_path, "BepInEx", "plugins")
            else:
                # For main mods, create a subfolder
                target_dir = os.path.join(self.repo_path, "BepInEx", "plugins", mod_data['name'])
            
            os.makedirs(target_dir, exist_ok=True)

            # Download the mod
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            # Get the total file size
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            downloaded = 0
            
            # Create a temporary file
            temp_file = get_temp_file_path(f"{mod_data['name']}.zip")
            with open(temp_file, 'wb') as f:
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    progress.setValue(int((downloaded / total_size) * 100))
                    QApplication.processEvents()
            
            # Extract the mod to the appropriate directory
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            
            # Clean up
            os.remove(temp_file)
            
            # Save to installed mods (only for main mods, not dependencies)
            if not is_dependency:
                config = ConfigManager()
                config.add_installed_mod(mod_data['name'], mod_data)
                
                # Update the library tab
                main_window = self.window()
                if main_window:
                    for i in range(main_window.stacked_widget.count()):
                        widget = main_window.stacked_widget.widget(i)
                        if isinstance(widget, LibraryTab):
                            widget.load_installed_mods()  # Reload all mods
                            break
            
            QMessageBox.information(
                self,
                "Success",
                f"{mod_data['name']} has been successfully installed!",
                QMessageBox.StandardButton.Ok
            )
            
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(
                self,
                "Download Error",
                f"Failed to download {mod_data['name']}: {str(e)}",
                QMessageBox.StandardButton.Ok
            )
        except zipfile.BadZipFile:
            QMessageBox.critical(
                self,
                "Extraction Error",
                f"The downloaded file for {mod_data['name']} is corrupted. Please try again.",
                QMessageBox.StandardButton.Ok
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to install {mod_data['name']}: {str(e)}",
                QMessageBox.StandardButton.Ok
            )
        finally:
            progress.close()

    def closeEvent(self, event):
        # Clean up the temporary file when the widget is closed
        try:
            if os.path.exists(self.temp_file):
                os.remove(self.temp_file)
        except:
            pass
        super().closeEvent(event)

    def format_file_size(self, size_bytes):
        """Format file size in bytes to human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def toggle_mod(self):
        mod_dir = os.path.join(self.repo_path, "BepInEx", "plugins", self.mod_data['name'])
        disabled_mods_dir = os.path.join(self.repo_path, "BepInEx", "plugins", "disabled_mods")
        zip_path = os.path.join(disabled_mods_dir, f"{self.mod_data['name']}.zip")
        
        # Create disabled_mods directory if it doesn't exist
        os.makedirs(disabled_mods_dir, exist_ok=True)
        
        if os.path.exists(mod_dir):
            # Disable the mod by zipping it
            try:
                # Create a zip file of the mod directory
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(mod_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, mod_dir)
                            zipf.write(file_path, arcname)
                
                # Remove the original directory
                shutil.rmtree(mod_dir)
                
                # Update button text
                self.disable_button.setText("Enable")
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"{self.mod_data['name']} has been disabled.",
                    QMessageBox.StandardButton.Ok
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to disable {self.mod_data['name']}: {str(e)}",
                    QMessageBox.StandardButton.Ok
                )
        elif os.path.exists(zip_path):
            # Enable the mod by unzipping it
            try:
                # Create the mod directory
                os.makedirs(mod_dir, exist_ok=True)
                
                # Extract the zip file
                with zipfile.ZipFile(zip_path, 'r') as zipf:
                    zipf.extractall(mod_dir)
                
                # Remove the zip file
                os.remove(zip_path)
                
                # Update button text
                self.disable_button.setText("Disable")
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"{self.mod_data['name']} has been enabled.",
                    QMessageBox.StandardButton.Ok
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to enable {self.mod_data['name']}: {str(e)}",
                    QMessageBox.StandardButton.Ok
                )
    
    def uninstall_mod(self):
        reply = QMessageBox.question(
            self,
            "Uninstall Mod",
            f"Are you sure you want to uninstall {self.mod_data['name']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                mod_dir = os.path.join(self.repo_path, "BepInEx", "plugins", self.mod_data['name'])
                disabled_mods_dir = os.path.join(self.repo_path, "BepInEx", "plugins", "disabled_mods")
                zip_path = os.path.join(disabled_mods_dir, f"{self.mod_data['name']}.zip")
                
                # Check if mod is disabled (exists as zip)
                if os.path.exists(zip_path):
                    # Remove the zip file
                    os.remove(zip_path)
                # Check if mod is enabled (exists as directory)
                elif os.path.exists(mod_dir):
                    # Remove the mod directory
                    shutil.rmtree(mod_dir)
                
                # Remove from installed mods
                config = ConfigManager()
                config.remove_installed_mod(self.mod_data['name'])
                
                # Update the library tab
                main_window = self.window()
                if main_window:
                    # Find the library tab
                    library_tab = None
                    for i in range(main_window.stacked_widget.count()):
                        widget = main_window.stacked_widget.widget(i)
                        if isinstance(widget, LibraryTab):
                            library_tab = widget
                            break
                    
                    if library_tab:
                        library_tab.load_installed_mods()  # Reload the mod list
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"{self.mod_data['name']} has been successfully uninstalled!",
                    QMessageBox.StandardButton.Ok
                )
                
                # Find and close the modal overlay
                main_window = self.window()
                if main_window:
                    for child in main_window.findChildren(ModalOverlay):
                        child.close()
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to uninstall {self.mod_data['name']}: {str(e)}",
                    QMessageBox.StandardButton.Ok
                )

class ImageProcessor(QThread):
    imageProcessed = pyqtSignal(str, QPixmap, str)
    
    def __init__(self, icon_url, label_key):
        super().__init__()
        self.icon_url = icon_url
        self.label_key = label_key
        # Create a unique temp file name based on the URL and label key
        self.temp_file = get_temp_file_path(f"icon_{hash(icon_url + label_key)}.png")
        
    def run(self):
        try:
            response = requests.get(self.icon_url)
            if response.status_code == 200:
                image = Image.open(io.BytesIO(response.content))
                image = image.resize((200, 200), Image.Resampling.LANCZOS)
                image.save(self.temp_file)
                
                pixmap = QPixmap(self.temp_file)
                rounded = QPixmap(pixmap.size())
                rounded.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                
                path = QPainterPath()
                path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), 10, 10)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, pixmap)
                painter.end()
                
                self.imageProcessed.emit(self.icon_url, rounded, self.label_key)
                
                # Clean up the temporary file
                try:
                    if os.path.exists(self.temp_file):
                        os.remove(self.temp_file)
                except:
                    pass
            else:
                print(f"Failed to fetch image from {self.icon_url}: Status code {response.status_code}")
        except Exception as e:
            print(f"Error processing image from {self.icon_url}: {e}")

class ExploreTab(QWidget):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.repo_path = self.config.get('repo_path')
        self.setup_ui()
        self.original_content = None
        self.search_results = None
        self.all_mods = []  # Cache for all mods
        self.image_cache = {}  # Cache for processed images
        self.active_labels = {}  # Track active labels
        self.active_processors = []  # Track active processors
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        self.load_all_mods()  # Load mods on initialization
        
    def load_all_mods(self):
        """Load all mods from the API and cache them"""
        url = "https://thunderstore.io/c/repo/api/v1/package/"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            self.all_mods = []
            
            for mod in data:
                mod_name = mod["name"]
                
                # Skip mods with "modpack" or "bepinex" in their name
                if "modpack" in mod_name.lower() or "bepinex" in mod_name.lower():
                    continue
                
                # Get the latest version
                newest_version = max(mod["versions"], key=lambda version: version["version_number"])
                
                # Store mod data
                self.all_mods.append({
                    "name": mod_name,
                    "creator": mod["owner"],  # Add creator's name
                    "description": newest_version["description"],
                    "version": newest_version["version_number"],
                    "downloads": newest_version["downloads"],
                    "icon": newest_version["icon"],
                    "file_size": newest_version.get("file_size", 0),  # Add file size
                    "dependencies": newest_version.get("dependencies", []),  # Add dependencies
                    "download_url": newest_version["download_url"]  # Add download URL
                })
            
            # Sort all mods by downloads
            sorted_mods = sorted(self.all_mods, key=lambda x: x["downloads"], reverse=True)
            
            # Get top 10 for popular section
            popular_mods = sorted_mods[:10]
            
            # Get next 10 for game changer section
            game_changer_mods = sorted_mods[10:20]
            
            # Filter mods with "cosmetic" in name for funny section
            funny_mods = [mod for mod in self.all_mods if "cosmetic" in mod["name"].lower()][:10]
            
            # Update the card sections
            self.update_card_sections(popular_mods, game_changer_mods, funny_mods)
    
    def update_card_sections(self, popular_mods, game_changer_mods, funny_mods):
        """Update the card sections with the provided mods"""
        # Get all card sections
        card_sections = self.findChildren(CardSection)
        
        # Update popular mods section (first section)
        if card_sections and len(card_sections) > 0:
            popular_section = card_sections[0]
            self.populate_card_section(popular_section, popular_mods)
        
        # Update game changer mods section (second section)
        if card_sections and len(card_sections) > 1:
            game_changer_section = card_sections[1]
            self.populate_card_section(game_changer_section, game_changer_mods)
        
        # Update funny mods section (third section)
        if card_sections and len(card_sections) > 2:
            funny_section = card_sections[2]
            self.populate_card_section(funny_section, funny_mods)
    
    def populate_card_section(self, card_section, mods):
        """Populate a card section with the provided mods"""
        # Get the cards widget and its layout
        cards_widget = card_section.scroll_area.widget()
        cards_layout = cards_widget.layout()
        
        # Clear existing cards
        while cards_layout.count():
            item = cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new cards for each mod
        for i, mod in enumerate(mods):
            # Create card
            card = QFrame()
            card.setFixedSize(200, 200)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setStyleSheet("""
                QFrame {
                    background-color: transparent;
                }
            """)
            
            # Make card clickable
            card.mousePressEvent = lambda event, m=mod: self.show_mod_details(m)
            
            main_layout = QVBoxLayout(card)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)
            
            # Create image container with hover effect
            image_container = HoverFrame()
            image_layout = QVBoxLayout(image_container)
            image_layout.setContentsMargins(0, 0, 0, 0)
            image_layout.setSpacing(0)
            
            # Create icon label
            icon_label = QLabel()
            icon_label.setStyleSheet("""
                QLabel {
                    border-radius: 10px;
                }
            """)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setFixedSize(200, 200)
            icon_label.setCursor(Qt.CursorShape.PointingHandCursor)
            image_layout.addWidget(icon_label)
            
            # Create name overlay
            name_overlay = QFrame()
            name_overlay.setStyleSheet("""
                QFrame {
                    background-color: rgba(0, 0, 0, 0.7);
                    border-bottom-left-radius: 10px;
                    border-bottom-right-radius: 10px;
                }
            """)
            name_overlay.setFixedHeight(35)
            name_overlay.setCursor(Qt.CursorShape.PointingHandCursor)
            
            name_layout = QHBoxLayout(name_overlay)
            name_layout.setContentsMargins(10, 0, 10, 0)
            
            # Create name label with elided text
            name_label = QLabel()
            name_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 13px;
                    font-weight: 500;
                    letter-spacing: 0.5px;
                    background-color: transparent;
                    border: none;
                }
            """)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setFixedWidth(180)
            name_label.setFixedHeight(35)
            name_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            name_label.setToolTip(mod["name"])
            name_label.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Use QFontMetrics to elide the text
            metrics = QFontMetrics(name_label.font())
            char_width = metrics.averageCharWidth()
            elided_text = metrics.elidedText(mod["name"], Qt.TextElideMode.ElideRight, char_width * 20)
            name_label.setText(elided_text)
            
            name_layout.addWidget(name_label)
            
            # Add widgets to main layout
            main_layout.addWidget(image_container)
            main_layout.addWidget(name_overlay)
            
            # Add card to layout
            cards_layout.addWidget(card, 0, i)
            
            # Create a closure for this specific card's image processing
            def create_image_handler(label):
                def handle_image(url, pixmap, key):
                    label.setPixmap(pixmap)
                return handle_image
            
            # Start image processing in background
            processor = ImageProcessor(mod["icon"], f"mod_{i}")
            processor.imageProcessed.connect(create_image_handler(icon_label))
            processor.finished.connect(lambda p=processor: self.cleanup_processors())
            self.active_processors.append(processor)
            processor.start()
        
        # Update the minimum width of the cards widget
        min_width = (len(mods) * 200) + ((len(mods) - 1) * 15) + 40  # cards * 200px + spaces * 15px + 40px margins
        cards_widget.setMinimumWidth(min_width)

    def setup_ui(self):
        # Main layout that contains everything
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 30, 0, 0)
        main_layout.setSpacing(0)  # Changed to 0 to prevent spacing between search and content
        
        # Search bar (outside of scroll area)
        search_container = QWidget()
        search_container.setContentsMargins(20, 0, 20, 0)
        search_container.setFixedHeight(80)  # Fixed height to prevent movement
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_wrapper = QFrame()
        self.search_wrapper.setFixedHeight(50)
        self.search_wrapper.setStyleSheet("""
            QFrame {
                background-color: #181414;
                border: none;
                border-radius: 25px;
            }
        """)
        
        search_wrapper_layout = QHBoxLayout(self.search_wrapper)
        search_wrapper_layout.setContentsMargins(30, 0, 30, 0)
        search_wrapper_layout.setSpacing(0)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search for mods...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 18px;
                padding: 12px 0;
            }
            QLineEdit:focus {
                outline: none;
            }
        """)
        
        # Connect signals
        self.search_bar.textChanged.connect(self.handle_search)
        self.search_bar.focusInEvent = lambda event: self.handle_search_focus(True)
        self.search_bar.focusOutEvent = lambda event: self.handle_search_focus(False)
        
        search_wrapper_layout.addWidget(self.search_bar)
        search_layout.addWidget(self.search_wrapper)
        main_layout.addWidget(search_container)
        
        # Create container for both original content and search results
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(20)
        
        # Create sections for original content
        sections = [
            ("Popular mods", 5),
            ("Game changer mods", 5),
            ("Funny mods", 5)
        ]
        
        for section_title, num_cards in sections:
            # Section header
            section_label = QLabel(section_title)
            section_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 24px;
                    font-weight: bold;
                    padding-left: 20px;
                }
            """)
            self.content_layout.addWidget(section_label)
            
            # Create a CardSection for each section
            card_section = CardSection()
            
            # Clear the existing cards and add new ones
            cards_widget = card_section.scroll_area.widget()
            cards_layout = cards_widget.layout()
            
            # Remove existing cards
            while cards_layout.count():
                item = cards_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Add new cards
            for i in range(num_cards):
                card = QWidget()
                card.setFixedSize(200, 200)
                card.setCursor(Qt.CursorShape.PointingHandCursor)
                card.setStyleSheet("""
                    QWidget {
                        background-color: #333;
                        border-radius: 10px;
                    }
                    QWidget:hover {
                        background-color: #444;
                    }
                """)
                cards_layout.addWidget(card, 0, i)
            
            # Update minimum width
            min_width = (num_cards * 200) + ((num_cards - 1) * 15) + 40
            cards_widget.setMinimumWidth(min_width)
            
            self.content_layout.addWidget(card_section)
        
        # Create search results container
        self.search_results_container = QWidget()
        self.search_results_layout = FlowLayout(self.search_results_container, margin=20, spacing=15)
        self.search_results_container.setLayout(self.search_results_layout)
        self.search_results_container.hide()
        
        # Create scroll content widget
        scroll_content = QWidget()
        scroll_content_layout = QVBoxLayout(scroll_content)
        scroll_content_layout.setContentsMargins(0, 0, 0, 0)
        scroll_content_layout.setSpacing(20)
        
        # Add both containers to the scroll content
        scroll_content_layout.addWidget(self.content_container)
        scroll_content_layout.addWidget(self.search_results_container)
        
        # Main scroll area
        scroll = QScrollArea()
        scroll.setWidget(scroll_content)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            CardSection {
                background-color: transparent;
            }
            CardSection QWidget {
                background-color: transparent;
            }
            CardSection QFrame {
                background-color: rgba(0, 0, 0, 0.7);
            }
            CardSection QFrame:hover {
                background-color: rgba(0, 0, 0, 0.8);
            }
        """)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll)
        
        # Set the main layout
        self.setLayout(main_layout)
    
    def handle_search_focus(self, has_focus):
        if has_focus:
            self.content_container.hide()
            self.search_results_container.show()
        else:
            if not self.search_bar.text():
                self.search_results_container.hide()
                self.content_container.show()
    
    def handle_search(self, query):
        if len(query) < 3:
            self.search_results_container.hide()
            self.content_container.show()
            return
        
        # Debounce the search
        self.search_timer.stop()
        self.search_timer.start(300)  # Wait 300ms before performing search
    
    def perform_search(self):
        query = self.search_bar.text()
        if len(query) < 3:
            return
            
        # Clear existing search results and active labels
        self.active_labels.clear()
        while self.search_results_layout.count():
            item = self.search_results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Split query into words for more precise matching
        query_words = query.lower().split()
        
        # Get matching mods with scores
        matches = []
        for mod in self.all_mods:
            mod_name = mod["name"].lower()
            mod_desc = mod["description"].lower()
            
            # Calculate various match scores
            name_exact_score = 100 if any(word in mod_name for word in query_words) else 0
            name_fuzzy_score = max(fuzz.partial_ratio(word, mod_name) for word in query_words)
            name_token_score = fuzz.token_sort_ratio(query, mod_name)
            
            desc_exact_score = 100 if any(word in mod_desc for word in query_words) else 0
            desc_fuzzy_score = max(fuzz.partial_ratio(word, mod_desc) for word in query_words)
            desc_token_score = fuzz.token_sort_ratio(query, mod_desc)
            
            desc_word_matches = sum(1 for word in query_words if word in mod_desc)
            desc_word_score = (desc_word_matches / len(query_words)) * 100
            
            total_score = (
                (name_exact_score * 0.35) +
                (name_fuzzy_score * 0.15) +
                (name_token_score * 0.1) +
                (desc_exact_score * 0.2) +
                (desc_fuzzy_score * 0.1) +
                (desc_token_score * 0.05) +
                (desc_word_score * 0.05)
            )
            
            if mod_name.startswith(query.lower()):
                total_score *= 1.5
            
            if all(word in mod_desc for word in query_words):
                total_score *= 1.3
            
            if total_score > 35:
                matches.append((mod, total_score))
        
        matches.sort(key=lambda x: x[1], reverse=True)
        matches = matches[:20]
        
        for mod, score in matches:
            card = QFrame()
            card.setFixedSize(200, 200)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setStyleSheet("""
                QFrame {
                    background-color: transparent;
                }
            """)
            
            card.mousePressEvent = lambda event, m=mod: self.show_mod_details(m)
            
            main_layout = QVBoxLayout(card)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)
            
            image_container = HoverFrame()
            image_layout = QVBoxLayout(image_container)
            image_layout.setContentsMargins(0, 0, 0, 0)
            image_layout.setSpacing(0)
            
            icon_label = QLabel()
            icon_label.setStyleSheet("""
                QLabel {
                    border-radius: 10px;
                }
            """)
            
            # Store the label in active_labels with a unique key
            label_key = f"{mod['icon']}_{id(icon_label)}"
            self.active_labels[label_key] = icon_label
            
            # Check cache first
            if mod["icon"] in self.image_cache:
                icon_label.setPixmap(self.image_cache[mod["icon"]])
            else:
                # Start image processing in background
                processor = ImageProcessor(mod["icon"], label_key)
                processor.imageProcessed.connect(self.update_image_cache)
                processor.finished.connect(lambda p=processor: self.active_processors.remove(p))
                self.active_processors.append(processor)
                processor.start()
            
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setFixedSize(200, 200)
            image_layout.addWidget(icon_label)
            
            # Create name overlay
            name_overlay = QFrame()
            name_overlay.setStyleSheet("""
                QFrame {
                    background-color: rgba(0, 0, 0, 0.7);
                    border-bottom-left-radius: 10px;
                    border-bottom-right-radius: 10px;
                }
            """)
            name_overlay.setFixedHeight(35)
            
            name_layout = QHBoxLayout(name_overlay)
            name_layout.setContentsMargins(10, 0, 10, 0)
            
            name_label = QLabel()
            name_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 13px;
                    font-weight: 500;
                    letter-spacing: 0.5px;
                    background-color: transparent;
                    border: none;
                }
            """)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setFixedWidth(180)
            name_label.setFixedHeight(35)
            name_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            name_label.setToolTip(mod["name"])
            
            # Use QFontMetrics to elide the text
            metrics = QFontMetrics(name_label.font())
            # Calculate width for 12 characters based on average character width
            char_width = metrics.averageCharWidth()
            elided_text = metrics.elidedText(mod["name"], Qt.TextElideMode.ElideRight, char_width * 20)
            name_label.setText(elided_text)
            
            name_layout.addWidget(name_label)
            
            main_layout.addWidget(image_container)
            main_layout.addWidget(name_overlay)
            
            self.search_results_layout.addWidget(card)
        
        self.search_results_container.show()
        self.content_container.hide()
    
    def update_image_cache(self, url, pixmap, label_key):
        # Update the cache
        self.image_cache[url] = pixmap
        
        # Update the label if it still exists
        if label_key in self.active_labels:
            label = self.active_labels[label_key]
            if label is not None:
                label.setPixmap(pixmap)
    
    def show_mod_details(self, mod_data):
        # Create overlay
        overlay = ModalOverlay(self)
        overlay.setFixedSize(900, 500)  # Landscape size
        
        # Create content with repo path
        content = ModDetailsContent(
            mod_data=mod_data,
            repo_path=self.repo_path,
            parent=self,
            is_library=False
        )
        overlay.set_content(content)
        
        # Show overlay
        overlay.show()

    def cleanup_processors(self):
        for processor in self.active_processors:
            if processor.isRunning():
                processor.quit()
                processor.wait()
        self.active_processors.clear()

    def closeEvent(self, event):
        self.cleanup_processors()
        super().closeEvent(event)

class HomeModDetailsContent(ModDetailsContent):
    def __init__(self, mod_data, parent=None):
        super().__init__(mod_data=mod_data, repo_path=None, parent=parent, is_library=False)
        # Override any specific behavior for home tab modals here if needed

class HomeTab(QWidget):
    def __init__(self):
        super().__init__()
        self.active_processors = []  # Track active processors
        self.config = ConfigManager()
        self.repo_path = self.config.get('repo_path')  # Get repo path from config
        self.setup_ui()
        self.load_new_mods()  # Load new mods on initialization
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 30, 0, 0)  # Added 30px top margin
        layout.setSpacing(20)  # Keep spacing between sections
        
        # Add sections
        sections = ["New mods", "R.E.P.O. moments"]
        for section in sections:
            # Section header
            section_label = QLabel(section)
            section_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 24px;
                    font-weight: bold;
                    padding-left: 20px;
                }
            """)
            layout.addWidget(section_label)
            
            # Add card section
            card_section = CardSection()
            
            # For R.E.P.O. moments, add a second row with 16:9 cards
            if section == "R.E.P.O. moments":
                # Get the cards widget and its layout
                cards_widget = card_section.scroll_area.widget()
                cards_layout = cards_widget.layout()
                
                # Calculate 16:9 width based on 200px height
                card_width = int(200 * (16/9))
                
                # Update existing cards in first row
                for i in range(5):
                    card = cards_layout.itemAtPosition(0, i).widget()
                    card.setFixedSize(card_width, 200)  # 16:9 aspect ratio
                
                # Add second row of cards
                for i in range(5):
                    card = QWidget()
                    card.setFixedSize(card_width, 200)  # 16:9 aspect ratio
                    card.setStyleSheet("background-color: #333; border-radius: 10px;")
                    cards_layout.addWidget(card, 1, i)  # Add to second row (row index 1)
                
                # Update minimum width to account for both rows
                min_width = (5 * card_width) + (4 * 15) + 40  # 5 cards * card_width + 4 spaces * 15px + 40px margins
                cards_widget.setMinimumWidth(min_width)
                
                # Update scroll area height to show both rows
                card_section.scroll_area.setFixedHeight(435)  # 220px per row + 15px spacing
            
            layout.addWidget(card_section)
        
        # Scroll area for content
        scroll = QScrollArea()
        content = QWidget()
        content.setLayout(layout)
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            CardSection {
                background-color: transparent;
            }
            CardSection QWidget {
                background-color: transparent;
            }
            CardSection QFrame {
                background-color: rgba(0, 0, 0, 0.7);
            }
            CardSection QFrame:hover {
                background-color: rgba(0, 0, 0, 0.8);
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
    
    def load_new_mods(self):
        try:
            # Fetch all mods from the API
            url = "https://thunderstore.io/c/repo/api/v1/package/"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                # Sort mods by date_created (newest first) and take top 10
                newest_mods = sorted(data, key=lambda x: x.get('date_created', ''), reverse=True)[:10]
                
                # Get the cards widget and its layout from the first CardSection
                card_section = self.findChild(CardSection)
                if card_section:
                    cards_widget = card_section.scroll_area.widget()
                    cards_layout = cards_widget.layout()
                    
                    # Clear existing cards
                    while cards_layout.count():
                        item = cards_layout.takeAt(0)
                        if item.widget():
                            item.widget().deleteLater()
                    
                    # Add new cards for each mod
                    for i, mod in enumerate(newest_mods):
                        # Get the latest version
                        newest_version = max(mod["versions"], key=lambda v: v["version_number"])
                        
                        # Create card
                        card = QFrame()
                        card.setFixedSize(200, 200)
                        card.setCursor(Qt.CursorShape.PointingHandCursor)
                        card.setStyleSheet("""
                            QFrame {
                                background-color: transparent;
                            }
                        """)
                        
                        # Make card clickable
                        mod_data = {
                            "name": mod["name"],
                            "creator": mod["owner"],
                            "description": newest_version["description"],
                            "version": newest_version["version_number"],
                            "downloads": newest_version["downloads"],
                            "icon": newest_version["icon"],
                            "file_size": newest_version.get("file_size", 0),
                            "dependencies": newest_version.get("dependencies", []),
                            "download_url": newest_version["download_url"]
                        }
                        
                        # Create main layout for the card
                        main_layout = QVBoxLayout(card)
                        main_layout.setContentsMargins(0, 0, 0, 0)
                        main_layout.setSpacing(0)
                        
                        # Create image container with hover effect
                        image_container = HoverFrame()
                        image_layout = QVBoxLayout(image_container)
                        image_layout.setContentsMargins(0, 0, 0, 0)
                        image_layout.setSpacing(0)
                        
                        # Create icon label
                        icon_label = QLabel()
                        icon_label.setStyleSheet("""
                            QLabel {
                                border-radius: 10px;
                            }
                        """)
                        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        icon_label.setFixedSize(200, 200)
                        icon_label.setCursor(Qt.CursorShape.PointingHandCursor)
                        image_layout.addWidget(icon_label)
                        
                        # Create name overlay
                        name_overlay = QFrame()
                        name_overlay.setStyleSheet("""
                            QFrame {
                                background-color: rgba(0, 0, 0, 0.7);
                                border-bottom-left-radius: 10px;
                                border-bottom-right-radius: 10px;
                            }
                        """)
                        name_overlay.setFixedHeight(35)
                        name_overlay.setCursor(Qt.CursorShape.PointingHandCursor)
                        
                        name_layout = QHBoxLayout(name_overlay)
                        name_layout.setContentsMargins(10, 0, 10, 0)
                        
                        # Create name label with elided text
                        name_label = QLabel()
                        name_label.setStyleSheet("""
                            QLabel {
                                color: white;
                                font-size: 13px;
                                font-weight: 500;
                                letter-spacing: 0.5px;
                                background-color: transparent;
                                border: none;
                            }
                        """)
                        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        name_label.setFixedWidth(180)
                        name_label.setFixedHeight(35)
                        name_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                        name_label.setToolTip(mod["name"])
                        name_label.setCursor(Qt.CursorShape.PointingHandCursor)
                        
                        # Use QFontMetrics to elide the text
                        metrics = QFontMetrics(name_label.font())
                        char_width = metrics.averageCharWidth()
                        elided_text = metrics.elidedText(mod["name"], Qt.TextElideMode.ElideRight, char_width * 20)
                        name_label.setText(elided_text)
                        
                        name_layout.addWidget(name_label)
                        
                        # Add widgets to main layout
                        main_layout.addWidget(image_container)
                        main_layout.addWidget(name_overlay)
                        
                        # Set up click handling for all components
                        def create_click_handler(mod_data):
                            def show_mod_modal():
                                self.show_mod_details(mod_data)
                            return show_mod_modal
                        
                        click_handler = create_click_handler(mod_data)
                        
                        # Attach click handlers
                        image_container.on_click = click_handler
                        card.mousePressEvent = lambda event, handler=click_handler: handler()
                        name_overlay.mousePressEvent = lambda event, handler=click_handler: handler()
                        icon_label.mousePressEvent = lambda event, handler=click_handler: handler()
                        name_label.mousePressEvent = lambda event, handler=click_handler: handler()
                        
                        # Add card to layout
                        cards_layout.addWidget(card, 0, i)
                        
                        # Create a closure for this specific card's image processing
                        def create_image_handler(label):
                            def handle_image(url, pixmap, key):
                                label.setPixmap(pixmap)
                            return handle_image
                        
                        # Start image processing in background
                        processor = ImageProcessor(newest_version["icon"], f"new_mod_{i}")
                        processor.imageProcessed.connect(create_image_handler(icon_label))
                        processor.finished.connect(lambda p=processor: self.cleanup_processor(p))
                        self.active_processors.append(processor)
                        processor.start()
                        
                    # Update the minimum width of the cards widget to ensure proper spacing
                    min_width = (10 * 200) + (9 * 15) + 40  # 10 cards * 200px + 9 spaces * 15px + 40px margins
                    cards_widget.setMinimumWidth(min_width)
        except Exception as e:
            print(f"Error loading new mods: {str(e)}")
    
    def update_card_image(self, label, pixmap):
        """Update the card's image label with the processed pixmap"""
        label.setPixmap(pixmap)
    
    def cleanup_processor(self, processor):
        """Remove a processor from the active list when it's finished"""
        if processor in self.active_processors:
            self.active_processors.remove(processor)
    
    def cleanup_processors(self):
        """Clean up all active processors"""
        for processor in self.active_processors:
            if processor.isRunning():
                processor.quit()
                processor.wait()
        self.active_processors.clear()
    
    def closeEvent(self, event):
        """Clean up processors when the widget is closed"""
        self.cleanup_processors()
        super().closeEvent(event)
    
    def show_mod_details(self, mod_data):
        # Create overlay
        overlay = ModalOverlay(self)
        overlay.setFixedSize(900, 500)  # Landscape size
        
        # Create content using ModDetailsContent
        content = ModDetailsContent(
            mod_data=mod_data,
            repo_path=self.repo_path,
            parent=self,
            is_library=False
        )
        overlay.set_content(content)
        
        # Show overlay
        overlay.show()

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=15):
        super().__init__(parent)
        self.setSpacing(spacing)
        self.setContentsMargins(margin, margin, margin, margin)
        self.item_list = []

    def addItem(self, item):
        self.item_list.append(item)
        self.update()

    def count(self):
        return len(self.item_list)

    def itemAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())
        margin = self.contentsMargins()
        size += QSize(margin.left() + margin.right(), margin.top() + margin.bottom())
        return size

    def doLayout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()
        margin = self.contentsMargins()
        effective_rect = rect.adjusted(margin.left(), margin.top(), -margin.right(), -margin.bottom())
        x = effective_rect.x()
        y = effective_rect.y()

        for item in self.item_list:
            wid = item.widget()
            if not wid:
                continue
                
            space_x = spacing
            space_y = spacing
            next_x = x + item.sizeHint().width() + space_x
            
            if next_x - space_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y() + margin.bottom()

class LibraryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.repo_path = self.config.get('repo_path')
        self.setup_ui()
        self.load_installed_mods()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 30, 0, 0)
        layout.setSpacing(20)
        
        # REPO not found message
        self.message_frame = QFrame()
        self.message_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_message_frame_style()
        message_layout = QHBoxLayout(self.message_frame)
        message_layout.setContentsMargins(20, 15, 20, 15)
        
        self.message_label = QLabel(self.get_message_text())
        self.message_label.setStyleSheet("""
            QLabel {
                color: #F6F5F6;
                font-size: 18px;
                font-weight: normal;
                background: transparent;
                border: none;
            }
        """)
        self.message_label.setCursor(Qt.CursorShape.PointingHandCursor)
        message_layout.addWidget(self.message_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Make the frame clickable
        self.message_frame.mousePressEvent = self.select_repo_path
        layout.addWidget(self.message_frame)
        
        # BepInEx not found message
        self.bepinex_frame = QFrame()
        self.bepinex_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_bepinex_frame_style()
        bepinex_layout = QHBoxLayout(self.bepinex_frame)
        bepinex_layout.setContentsMargins(20, 15, 20, 15)
        
        self.bepinex_label = QLabel("BepInEx not found. Click here to download and install.")
        self.bepinex_label.setStyleSheet("""
            QLabel {
                color: #F6F5F6;
                font-size: 18px;
                font-weight: normal;
                background: transparent;
                border: none;
            }
        """)
        self.bepinex_label.setCursor(Qt.CursorShape.PointingHandCursor)
        bepinex_layout.addWidget(self.bepinex_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Make the frame clickable
        self.bepinex_frame.mousePressEvent = self.download_bepinex
        layout.addWidget(self.bepinex_frame)
        
        # "My mods" header
        header_label = QLabel("My mods")
        header_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding-left: 20px;
            }
        """)
        layout.addWidget(header_label)
        
        # Create a scroll area for the mod cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # Create a widget to hold the mod cards
        self.mod_cards_widget = QWidget()
        self.mod_cards_layout = FlowLayout(self.mod_cards_widget, margin=20, spacing=15)
        self.mod_cards_widget.setLayout(self.mod_cards_layout)
        
        # Set a minimum size for the mod cards widget
        self.mod_cards_widget.setMinimumSize(800, 400)
        
        scroll.setWidget(self.mod_cards_widget)
        layout.addWidget(scroll)
        
    def update_message_frame_style(self):
        if self.repo_path:
            self.message_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(40, 167, 69, 0.2);
                    border: 1px solid #28a745;
                    border-radius: 10px;
                    margin: 0 20px;
                }
                QFrame:hover {
                    background-color: rgba(40, 167, 69, 0.3);
                }
            """)
        else:
            self.message_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(169, 68, 66, 0.2);
                    border: 1px solid #a94442;
                    border-radius: 10px;
                    margin: 0 20px;
                }
                QFrame:hover {
                    background-color: rgba(169, 68, 66, 0.3);
                }
            """)
    
    def update_bepinex_frame_style(self):
        if self.repo_path and not os.path.exists(os.path.join(self.repo_path, "BepInEx")):
            self.bepinex_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(247, 177, 12, 0.2);
                    border: 1px solid #F7B10C;
                    border-radius: 10px;
                    margin: 0 20px;
                }
                QFrame:hover {
                    background-color: rgba(247, 177, 12, 0.3);
                }
            """)
            self.bepinex_frame.show()
        else:
            self.bepinex_frame.hide()
    
    def get_message_text(self):
        if self.repo_path:
            return f"R.E.P.O. found at: {self.repo_path}"
        return "R.E.P.O. not found, click here to set the path"
    
    def select_repo_path(self, event):
        # Open folder selection dialog
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select R.E.P.O. Directory",
            self.repo_path or "",  # Start at current path if exists
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            if self.validate_repo_path(folder):
                self.update_bepinex_frame_style()
                return
            
            # Show error message
            error_dialog = QMessageBox(self)
            error_dialog.setWindowTitle("Error")
            error_dialog.setText("REPO.exe not found in the selected directory!")
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.exec()
    
    def download_bepinex(self, event):
        if not self.repo_path:
            return
            
        # Create a progress dialog
        progress = QProgressDialog("Downloading BepInEx...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle("Installing BepInEx")
        
        try:
            # Download BepInEx directly from repomods.net
            url = "https://repomods.net/download/47"
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Get the total file size
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            downloaded = 0
            
            # Create a temporary file
            temp_file = get_temp_file_path("bepinex.zip")
            with open(temp_file, 'wb') as f:
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    progress.setValue(int((downloaded / total_size) * 100))
                    QApplication.processEvents()
            
            # Extract to the game directory
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(self.repo_path)
            
            # Clean up
            os.remove(temp_file)
            
            # Update UI
            self.update_bepinex_frame_style()
            
            QMessageBox.information(
                self,
                "Success",
                "BepInEx has been successfully installed!",
                QMessageBox.StandardButton.Ok
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to install BepInEx: {str(e)}",
                QMessageBox.StandardButton.Ok
            )
        finally:
            progress.close()
    
    def validate_repo_path(self, path):
        repo_exe = os.path.join(path, "REPO.exe")
        bepinex_path = os.path.join(path, "BepInEx")
        
        if os.path.exists(repo_exe):
            self.repo_path = path
            self.config.set('repo_path', path)
            self.update_message_frame_style()
            self.message_label.setText(self.get_message_text())
            
            if not os.path.exists(bepinex_path):
                # Show warning message about missing BepInEx
                warning_dialog = QMessageBox(self)
                warning_dialog.setWindowTitle("Warning")
                warning_dialog.setText("BepInEx folder not found in the selected directory. Some features may not work properly.")
                warning_dialog.setIcon(QMessageBox.Icon.Warning)
                warning_dialog.exec()
            
            return True
        else:
            self.repo_path = None
            self.config.set('repo_path', None)
            self.update_message_frame_style()
            self.message_label.setText(self.get_message_text())
            
            # Show error message
            error_dialog = QMessageBox(self)
            error_dialog.setWindowTitle("Error")
            error_dialog.setText("REPO.exe not found in the selected directory!")
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.exec()
            return False
            
    def load_installed_mods(self):
        print("Starting to load installed mods...")  # Debug print
        
        # Clear existing mod cards
        while self.mod_cards_layout.count():
            item = self.mod_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Load and add all installed mods
        config = ConfigManager()
        installed_mods = config.get_installed_mods()
        
        print(f"Found {len(installed_mods)} mods in config")  # Debug print
        
        # Add each mod card to the layout
        for mod_name, mod_data in installed_mods.items():
            print(f"Processing mod: {mod_name}")  # Debug print
            self.add_mod_card(mod_name, mod_data)
        
        # Force layout update
        self.mod_cards_widget.updateGeometry()
        self.mod_cards_layout.update()
        self.update()
        
        print("Finished loading mods")  # Debug print
    
    def add_mod_card(self, mod_name, mod_data):
        print(f"Creating card for mod: {mod_name}")  # Debug print
        
        # Create a card widget
        card = QFrame()
        card.setFixedSize(200, 200)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
        """)
        
        # Make the card clickable to show mod details
        card.mousePressEvent = lambda event, m=mod_data: self.show_mod_details(m)
        
        main_layout = QVBoxLayout(card)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Image container with hover effect
        image_container = HoverFrame()
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(0)
        
        # Icon label
        icon_label = QLabel()
        icon_label.setStyleSheet("""
            QLabel {
                border-radius: 10px;
            }
        """)
        
        try:
            # If icon is a URL, download it
            if isinstance(mod_data['icon'], str) and mod_data['icon'].startswith('http'):
                response = requests.get(mod_data['icon'])
                if response.status_code == 200:
                    # Process image using PIL
                    image = Image.open(io.BytesIO(response.content))
                    image = image.resize((200, 200), Image.Resampling.LANCZOS)
                    
                    # Create a mask for rounded corners
                    mask = Image.new('L', (200, 200), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.rounded_rectangle([(0, 0), (200, 200)], 10, fill=255)
                    
                    # Apply the mask
                    output = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
                    output.paste(image, mask=mask)
                    
                    # Convert to QPixmap
                    img_byte_arr = io.BytesIO()
                    output.save(img_byte_arr, format='PNG')
                    img_byte_arr = img_byte_arr.getvalue()
                    
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_byte_arr)
                    icon_label.setPixmap(pixmap)
                else:
                    icon_data = None
            else:
                icon_data = mod_data['icon']
                if icon_data:
                    pixmap = QPixmap()
                    pixmap.loadFromData(icon_data)
                    icon_label.setPixmap(pixmap)
        except Exception as e:
            print(f"Error loading icon for {mod_name}: {str(e)}")
        
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(200, 200)
        image_layout.addWidget(icon_label)
        
        # Name overlay
        name_overlay = QFrame()
        name_overlay.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.7);
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        name_overlay.setFixedHeight(35)
        
        name_layout = QHBoxLayout(name_overlay)
        name_layout.setContentsMargins(10, 0, 10, 0)
        
        # Name label with elided text
        name_label = QLabel()
        name_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 13px;
                font-weight: 500;
                letter-spacing: 0.5px;
                background-color: transparent;
                border: none;
            }
        """)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFixedWidth(180)
        name_label.setFixedHeight(35)
        name_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        name_label.setToolTip(mod_data['name'])
        
        # Use QFontMetrics to elide the text
        metrics = QFontMetrics(name_label.font())
        char_width = metrics.averageCharWidth()
        elided_text = metrics.elidedText(mod_data['name'], Qt.TextElideMode.ElideRight, char_width * 20)
        name_label.setText(elided_text)
        
        name_layout.addWidget(name_label)
        
        main_layout.addWidget(image_container)
        main_layout.addWidget(name_overlay)
        
        # Add the card to the layout
        self.mod_cards_layout.addWidget(card)
        print(f"Successfully added card for {mod_name}")  # Debug print
    
    def show_mod_details(self, mod_data):
        # Create overlay
        overlay = ModalOverlay(self)
        overlay.setFixedSize(900, 500)  # Landscape size
        
        # Create content with repo path
        content = ModDetailsContent(
            mod_data=mod_data,
            repo_path=self.repo_path,
            parent=self,
            is_library=True
        )
        overlay.set_content(content)
        
        # Show overlay
        overlay.show()
        
    def remove_mod(self, mod_name, card):
        reply = QMessageBox.question(
            self,
            "Remove Mod",
            f"Are you sure you want to remove {mod_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            config = ConfigManager()
            config.remove_installed_mod(mod_name)
            self.mod_cards_layout.removeWidget(card)
            card.deleteLater()

class RepoHub(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("R.E.P.O. HUB")
        self.setMinimumSize(1200, 800)
        
        # Set window icon
        self.setWindowIcon(QIcon(resource_path("static/img/repo-hub-logo.ico")))
        
        # Set window flags for custom title bar
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QWidget#titleBar {
                background-color: #1a1a1a;
                height: 40px;
            }
            QWidget#titleBar QLabel {
                color: white;
                font-size: 14px;
                padding-left: 15px;
            }
            QWidget#titleBar QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 18px;
                padding: 0px 15px;
                min-width: 40px;
            }
            QWidget#titleBar QPushButton:hover {
                background-color: #333;
            }
            QWidget#titleBar QPushButton#closeButton:hover {
                background-color: #dc3545;
            }
            QScrollBar:vertical {
                border: none;
                background: #181414;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #333;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #444;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QWidget#sidebarWidget QPushButton {
                background-color: #F7B10C;
                color: #F6F5F6;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 18px;
                width: 200px;
                text-align: center;
                margin: 10px 20px;
                font-weight: 600;
            }
            QWidget#sidebarWidget QPushButton:hover {
                background-color: #FF8C00;
            }
            QWidget#sidebarWidget QPushButton#startButton {
                background-color: #F7B10C;
                margin-bottom: 20px;
                padding: 15px;
                height: 60px;
            }
            QWidget#sidebarWidget QPushButton#startButton:hover {
                background-color: #FFC000;
            }
            QWidget#sidebarWidget QPushButton#startButton:disabled {
                background-color: #666;
                color: #999;
            }
            QWidget#sidebarWidget QPushButton#activeButton {
                background-color: #D47104;
            }
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
            QWidget#contentWidget {
                background-color: #1a1a1a;
            }
            QWidget#sidebarWidget {
                background-color: #181414;
            }
        """)

        # Create title bar
        self.title_bar = QWidget()
        self.title_bar.setObjectName("titleBar")
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        # Title label
        title_label = QLabel("R.E.P.O. HUB")
        title_label.setObjectName("titleLabel")
        title_layout.addWidget(title_label)

        # Spacer
        title_layout.addStretch()

        # Window buttons
        minimize_button = QPushButton("─")
        minimize_button.setObjectName("minimizeButton")
        minimize_button.clicked.connect(self.showMinimized)
        title_layout.addWidget(minimize_button)

        close_button = QPushButton("×")
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self.close)
        title_layout.addWidget(close_button)

        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add title bar to main layout
        main_layout.addWidget(self.title_bar)
        
        # Create content layout
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Create sidebar
        sidebar = QWidget()
        sidebar.setObjectName("sidebarWidget")
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Logo
        logo_label = QLabel()
        logo_pixmap = QPixmap(resource_path("static/img/repo-hub-logo.png")).scaled(200, 150, Qt.AspectRatioMode.KeepAspectRatio)
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("background-color: #181414; margin-bottom: 20px;")
        sidebar_layout.addWidget(logo_label)
        
        # Create stacked widget for content
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: #1a1a1a;")
        
        # Create and add pages
        home_page = HomeTab()
        explore_page = ExploreTab()
        library_page = LibraryTab()  # Use the new LibraryTab instead of placeholder
        
        self.stacked_widget.addWidget(home_page)
        self.stacked_widget.addWidget(explore_page)
        self.stacked_widget.addWidget(library_page)
        
        # Store buttons to manage active state
        self.nav_buttons = {}
        
        # Navigation buttons
        nav_buttons = [
            ("Home", 0),
            ("Explore", 1),
            ("Library", 2)
        ]
        
        for button_text, index in nav_buttons:
            button = QPushButton(button_text)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            if button_text == "Home":
                button.setObjectName("activeButton")  # Set Home as initially active
            button.clicked.connect(lambda checked, idx=index, btn=button: self.handle_navigation(idx, btn))
            sidebar_layout.addWidget(button)
            self.nav_buttons[index] = button
        
        # Add spacer
        sidebar_layout.addStretch()
        
        # Start button with play icon
        self.start_button = QPushButton()
        self.start_button.setObjectName("startButton")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.clicked.connect(self.start_game)
        self.start_button.setStyleSheet("""
            QPushButton#startButton {
                background-color: #F7B10C;
                margin-bottom: 20px;
                padding: 15px;
                height: 60px;
            }
            QPushButton#startButton:hover {
                background-color: #FFC000;
            }
            QPushButton#startButton:disabled {
                background-color: #666;
                color: #999;
            }
        """)
        
        # Create layout for the button content
        button_layout = QHBoxLayout(self.start_button)
        button_layout.setContentsMargins(15, 5, 15, 5)
        button_layout.setSpacing(10)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add play icon using SVG widget
        self.play_icon = create_svg_widget("static/img/play.svg", 24, 24)
        self.play_icon.setStyleSheet("""
            QSvgWidget {
                background-color: transparent;
                padding-right: 2px;
                margin: -4px;
            }
        """)
        button_layout.addWidget(self.play_icon)
        
        # Add text
        self.start_text = QLabel("Start R.E.P.O.")
        self.start_text.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
                background-color: transparent;
                padding: 0;
                margin: 0;
                margin-top: -6px;
            }
        """)
        self.start_text.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        button_layout.addWidget(self.start_text)
        
        # Add status check timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_game_status)
        self.status_timer.start(5000)  # Check every 5 seconds
        
        sidebar_layout.addWidget(self.start_button)
        
        sidebar.setLayout(sidebar_layout)
        sidebar.setFixedWidth(250)
        
        # Add widgets to content layout
        content_layout.addWidget(sidebar)
        content_layout.addWidget(self.stacked_widget)
        
        # Add content layout to main layout
        main_layout.addLayout(content_layout)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Enable window dragging
        self.title_bar.mousePressEvent = self.mousePressEvent
        self.title_bar.mouseMoveEvent = self.mouseMoveEvent
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def handle_navigation(self, index, clicked_button):
        # Update button styles
        for button in self.nav_buttons.values():
            button.setObjectName("")
            button.style().unpolish(button)
            button.style().polish(button)
        
        clicked_button.setObjectName("activeButton")
        clicked_button.style().unpolish(clicked_button)
        clicked_button.style().polish(clicked_button)
        
        # Change page
        self.stacked_widget.setCurrentIndex(index)

    def start_game(self):
        # Disable the button and update text
        self.start_button.setEnabled(False)
        self.start_text.setText("Starting...")
        self.play_icon.hide()  # Hide the play icon
        
        # Replace this with the App ID of the game you want to launch
        STEAM_APP_ID = "3241660"  # Example: CS:GO
        launch_game(STEAM_APP_ID)
    
    def check_game_status(self):
        if is_game_running():
            # Game is running, update button state
            self.start_button.setEnabled(False)
            self.start_text.setText("Playing")
            self.play_icon.hide()
        else:
            # Game is not running, reset button state
            self.start_button.setEnabled(True)
            self.start_text.setText("Start R.E.P.O.")
            self.play_icon.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application icon
    app_icon = QIcon(resource_path("static/img/repo-hub-logo.ico"))
    app.setWindowIcon(app_icon)
    
    # Set application name and organization
    app.setApplicationName("RepoHub")
    app.setOrganizationName("RepoHub")
    app.setOrganizationDomain("repohub.com")
    
    # Set application style
    app.setStyle('Fusion')
    
    window = RepoHub()
    window.setWindowIcon(app_icon)  # Set icon for the main window
    window.show()
    sys.exit(app.exec()) 