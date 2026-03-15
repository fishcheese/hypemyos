import sys
import subprocess
import os
import platform
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QGroupBox, QCheckBox, QComboBox, QLabel, QPushButton,
                               QMessageBox)
from PySide6.QtCore import Qt

class HypeMyOS(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HypeMyOS")
        self.setMinimumWidth(500)

        self.adb_path = self.get_adb_path()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        group_device = QGroupBox("deviceLevelList")
        device_main_layout = QVBoxLayout(group_device)

        device_top_layout = QHBoxLayout()
        self.device_checkbox = QCheckBox("Modify deviceLevelList")
        device_top_layout.addWidget(self.device_checkbox)

        device_help_btn = QPushButton("?")
        device_help_btn.setFixedSize(24, 24)
        device_help_btn.clicked.connect(lambda: self.show_help("device"))
        device_top_layout.addWidget(device_help_btn)
        device_top_layout.addStretch()
        device_main_layout.addLayout(device_top_layout)

        device_settings_layout = QHBoxLayout()
        device_settings_layout.addWidget(QLabel("CPU:"))
        self.device_cpu = QComboBox()
        self.device_cpu.addItems(["1", "2", "3"])
        device_settings_layout.addWidget(self.device_cpu)

        device_settings_layout.addWidget(QLabel("GPU:"))
        self.device_gpu = QComboBox()
        self.device_gpu.addItems(["1", "2", "3"])
        device_settings_layout.addWidget(self.device_gpu)
        device_settings_layout.addStretch()

        device_main_layout.addLayout(device_settings_layout)
        main_layout.addWidget(group_device)

        group_comp = QGroupBox("computility")
        comp_main_layout = QVBoxLayout(group_comp)

        comp_top_layout = QHBoxLayout()
        comp_top_layout.addWidget(QLabel("computility settings:"))
        comp_help_btn = QPushButton("?")
        comp_help_btn.setFixedSize(24, 24)
        comp_help_btn.clicked.connect(lambda: self.show_help("comp"))
        comp_top_layout.addWidget(comp_help_btn)
        comp_top_layout.addStretch()
        comp_main_layout.addLayout(comp_top_layout)

        comp_settings_layout = QHBoxLayout()
        comp_settings_layout.addWidget(QLabel("CPU:"))
        self.comp_cpu = QComboBox()
        self.comp_cpu.addItems(["Don't change", "1", "2", "3", "4", "5", "6"])
        comp_settings_layout.addWidget(self.comp_cpu)

        comp_settings_layout.addWidget(QLabel("GPU:"))
        self.comp_gpu = QComboBox()
        self.comp_gpu.addItems(["Don't change", "1", "2", "3", "4", "5", "6"])
        comp_settings_layout.addWidget(self.comp_gpu)
        comp_settings_layout.addStretch()

        comp_main_layout.addLayout(comp_settings_layout)
        main_layout.addWidget(group_comp)

        group_other = QGroupBox("Other")
        other_main_layout = QVBoxLayout(group_other)

        other_top_layout = QHBoxLayout()
        other_top_layout.addWidget(QLabel("Additional settings:"))
        other_help_btn = QPushButton("?")
        other_help_btn.setFixedSize(24, 24)
        other_help_btn.clicked.connect(lambda: self.show_help("other"))
        other_top_layout.addWidget(other_help_btn)
        other_top_layout.addStretch()
        other_main_layout.addLayout(other_top_layout)

        tex_layout = QHBoxLayout()
        tex_layout.addWidget(QLabel("Advanced textures:"))
        self.texture_combo = QComboBox()
        self.texture_combo.addItems(["Don't change", "Enable", "Disable"])
        tex_layout.addWidget(self.texture_combo)
        tex_layout.addStretch()
        other_main_layout.addLayout(tex_layout)

        blur_layout = QHBoxLayout()
        blur_layout.addWidget(QLabel("Window-level blur:"))
        self.blur_combo = QComboBox()
        self.blur_combo.addItems(["Don't change", "Enable", "Disable"])
        blur_layout.addWidget(self.blur_combo)
        blur_layout.addStretch()
        other_main_layout.addLayout(blur_layout)

        self.recent_checkbox = QCheckBox("Enable stacked recents")
        other_main_layout.addWidget(self.recent_checkbox)

        main_layout.addWidget(group_other)

        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_settings)
        self.reboot_button = QPushButton("Reboot")
        self.reboot_button.clicked.connect(self.reboot_device)

        about_button = QPushButton("About")
        about_button.clicked.connect(self.show_about)

        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.reboot_button)
        button_layout.addWidget(about_button)
        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        self.check_adb()

    def get_adb_path(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        system = platform.system().lower()

        if system == "windows":
            rel_path = os.path.join("platform-tools-windows", "adb.exe")
        elif system == "linux":
            rel_path = os.path.join("platform-tools-linux", "adb")
        else:
            return "adb"

        full_path = os.path.join(script_dir, rel_path)
        if os.path.isfile(full_path):
            if system != "windows" and not os.access(full_path, os.X_OK):
                return "adb"
            return full_path
        else:
            return "adb"

    def check_adb(self):
        try:
            subprocess.run([self.adb_path, "version"], capture_output=True, check=True)
            result = subprocess.run([self.adb_path, "devices"], capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')
            devices = [line for line in lines if '\tdevice' in line]
            if not devices:
                QMessageBox.warning(self, "Warning",
                                    "(˶°ㅁ°) !!\n"
                                    "No devices found in device mode.\n"
                                    "Make sure your device is connected and USB debugging is enabled.")
        except subprocess.CalledProcessError:
            QMessageBox.critical(self, "Error",
                                 "(˶°ㅁ°) !!\n"
                                 f"ADB not found at '{self.adb_path}' or in PATH.\n"
                                 "Please place platform-tools in the appropriate folder:\n"
                                 " - Windows: .\\platform-tools-windows\\adb.exe\n"
                                 " - Linux: ./platform-tools-linux/adb\n"
                                 "or install Android SDK Platform Tools and add adb to PATH.")
        except FileNotFoundError:
            QMessageBox.critical(self, "Error",
                                 "(˶°ㅁ°) !!\n"
                                 f"ADB not found at '{self.adb_path}' or in PATH.\n"
                                 "Please place platform-tools in the appropriate folder:\n"
                                 " - Windows: .\\platform-tools-windows\\adb.exe\n"
                                 " - Linux: ./platform-tools-linux/adb\n"
                                 "or install Android SDK Platform Tools and add adb to PATH.")

    def show_help(self, section):
        help_texts = {
            "device": """deviceLevelList

Many apps (and naturally Xiaomi system apps) use deviceLevelList to determine the device class, 1 - low class, 3 - high class. By changing the CPU and GPU values in deviceLevelList, you can enable blur and complex animations in different parts of the system (e.g., in recents, folders, and on the lock screen). Usually doesn't cause lag even on weaker devices.

I recommend using the same values for CPU and GPU.""",

            "comp": """computility

Similar to deviceLevelList, but has a much greater impact on animations and effects in the system. Low-end models typically use values 1-2, mid-range devices use 2-3, and flagships use 4-6.

Recommended values:
- 1 - maximum performance and minimum distractions
- 3 - ideal balance between beauty and performance
- 6 - lots of blur effects and animations, but may cause lag on weaker devices

(˶°ㅁ°) !! Advanced textures work strangely with values below 4.""",

            "other": """Other settings

Advanced textures - enables the "Advanced textures" setting in Settings -> Display & brightness -> Screen. Advanced textures enable even more animations and blur effects in the system. Looks very nice, but may consume significantly more power.

Window-level blur - the name speaks for itself - enables blur effects behind some windows (e.g., behind warnings and dialogs).

Stacked recents - enables the iOS-like "Stacked" recent apps style. To use this, you need to update the system launcher to the latest version. You can change the recents style back to one of the old ones through settings."""
        }

        QMessageBox.information(self, "Help", help_texts.get(section, "No information available"))

    def show_about(self):
        about_text = """HypeMyOS - make HyperOS more hype ᕙ(•̀ ᗜ •́)ᕗ

Utility for spoofing device class to unlock flagship features on any device with HyperOS.

Thanks for using! 𐔌՞. .՞𐦯"""

        QMessageBox.about(self, "About", about_text)

    def build_commands(self):
        commands = []

        if self.device_checkbox.isChecked():
            cpu_val = self.device_cpu.currentText()
            gpu_val = self.device_gpu.currentText()
            cmd = f'settings put system deviceLevelList "v:1,c:{cpu_val},g:{gpu_val}"'
            commands.append(cmd)

        cpu_comp = self.comp_cpu.currentText()
        if cpu_comp != "Don't change":
            cmd = f"""service call miui.mqsas.IMQSNative 21 i32 1 s16 "setprop" i32 1 s16 "persist.sys.computility.cpulevel {cpu_comp}" s16 "/storage/emulated/0/log.txt" i32 600"""
            commands.append(cmd)

        gpu_comp = self.comp_gpu.currentText()
        if gpu_comp != "Don't change":
            cmd = f"""service call miui.mqsas.IMQSNative 21 i32 1 s16 "setprop" i32 1 s16 "persist.sys.computility.gpulevel {gpu_comp}" s16 "/storage/emulated/0/log.txt" i32 600"""
            commands.append(cmd)

        texture_val = self.texture_combo.currentText()
        if texture_val != "Don't change":
            bool_val = "true" if texture_val == "Enable" else "false"
            cmd = f"""service call miui.mqsas.IMQSNative 21 i32 1 s16 "setprop" i32 1 s16 "persist.sys.background_blur_supported {bool_val}" s16 "/storage/emulated/0/log.txt" i32 600"""
            commands.append(cmd)

        blur_val = self.blur_combo.currentText()
        if blur_val != "Don't change":
            if blur_val == "Enable":
                disable = "0"
            else:
                disable = "1"
            cmd = f"settings put global disable_window_blurs {disable}"
            commands.append(cmd)

        if self.recent_checkbox.isChecked():
            cmd = "settings put global task_stack_view_layout_style 2"
            commands.append(cmd)

        return commands

    def apply_settings(self):
        commands = self.build_commands()
        if not commands:
            QMessageBox.information(self, "Information", "No settings to apply ¯\\_(ツ)_/¯")
            return

        reply = QMessageBox.question(self, "Confirmation",
                                     f"∘ ∘ ∘ (°ヮ°) ?\n{len(commands)} commands will be executed. Continue?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        success_count = 0
        error_messages = []
        for cmd in commands:
            try:
                full_cmd = [self.adb_path, "shell", cmd]
                result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=10, check=False)
                if result.returncode == 0:
                    success_count += 1
                else:
                    error_messages.append(f"(˶°ㅁ°) !!\nCommand: {cmd}\nError: {result.stderr.strip()}")
            except subprocess.TimeoutExpired:
                error_messages.append(f"(˶°ㅁ°) !!\nCommand: {cmd}\nTimeout (10 sec)")
            except Exception as e:
                error_messages.append(f"(˶°ㅁ°) !!\nCommand: {cmd}\nException: {str(e)}")

        if error_messages:
            QMessageBox.warning(self, "Result",
                                f"Success: {success_count}, Errors: {len(error_messages)}\n\n" + "\n\n".join(error_messages[:3]))
        else:
            QMessageBox.information(self, "Success!", f"◝(ᵔᗜᵔ)◜\nAll {success_count} commands executed successfully.")

    def reboot_device(self):
        reply = QMessageBox.question(self, "Confirmation",
                                     "∘ ∘ ∘ (°ヮ°) ?\nAre you sure you want to reboot the device?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                subprocess.run([self.adb_path, "reboot"], check=True, timeout=10)
                QMessageBox.information(self, "Reboot", "◝(ᵔᗜᵔ)◜\nReboot command sent.")
            except subprocess.TimeoutExpired:
                QMessageBox.warning(self, "Error", "(˶°ㅁ°) !!\nTimeout while sending reboot command.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"(˶°ㅁ°) !!\nFailed to reboot: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HypeMyOS()
    window.show()
    sys.exit(app.exec())
