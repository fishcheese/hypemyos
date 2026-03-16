import sys
import subprocess
import os
import platform
import argparse
import signal

# SIGABRT handler

def _sigabrt_handler(signum, frame):
    print("\n(˶°ㅁ°) !! Incompatible processor.", file=sys.stderr)
    print("This Qt build requires the following features:", file=sys.stderr)
    print("    sse4.2 popcnt", file=sys.stderr)
    print("consider using --tui instead uwu", file=sys.stderr)
    sys.exit(1)

signal.signal(signal.SIGABRT, _sigabrt_handler)

# shared helpers

def get_adb_path():
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
            try:
                os.chmod(full_path, 0o755)
            except OSError:
                return "adb"
        return full_path
    return "adb"

def check_adb_devices(adb_path):
    """Returns (ok, message)"""
    try:
        subprocess.run([adb_path, "version"], capture_output=True, check=True)
        result = subprocess.run([adb_path, "devices"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        devices = [line for line in lines if '\tdevice' in line]
        if not devices:
            return False, "No devices found. Connect your phone and enable USB debugging."
        return True, f"{len(devices)} device(s) connected."
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False, f"ADB not found at '{adb_path}' or in PATH."

def build_commands(device_checked, device_cpu, device_gpu,
                   cpu_comp, gpu_comp,
                   texture_val, blur_val, recent_checked):
    commands = []
    if device_checked:
        commands.append(f'settings put system deviceLevelList "v:1,c:{device_cpu},g:{device_gpu}"')
    if cpu_comp is not None:
        commands.append(
            f'service call miui.mqsas.IMQSNative 21 i32 1 s16 "setprop" i32 1 '
            f's16 "persist.sys.computility.cpulevel {cpu_comp}" '
            f's16 "/storage/emulated/0/log.txt" i32 600'
        )
    if gpu_comp is not None:
        commands.append(
            f'service call miui.mqsas.IMQSNative 21 i32 1 s16 "setprop" i32 1 '
            f's16 "persist.sys.computility.gpulevel {gpu_comp}" '
            f's16 "/storage/emulated/0/log.txt" i32 600'
        )
    if texture_val is not None:
        bool_val = "true" if texture_val else "false"
        commands.append(
            f'service call miui.mqsas.IMQSNative 21 i32 1 s16 "setprop" i32 1 '
            f's16 "persist.sys.background_blur_supported {bool_val}" '
            f's16 "/storage/emulated/0/log.txt" i32 600'
        )
    if blur_val is not None:
        disable = "0" if blur_val else "1"
        commands.append(f"settings put global disable_window_blurs {disable}")
    if recent_checked:
        commands.append("settings put global task_stack_view_layout_style 2")
    return commands

def run_adb_commands(adb_path, commands):
    success, errors = 0, []
    for cmd in commands:
        try:
            result = subprocess.run([adb_path, "shell", cmd],
                                    capture_output=True, text=True, timeout=10, check=False)
            if result.returncode == 0:
                success += 1
            else:
                errors.append(f"{cmd}\n  -> {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            errors.append(f"{cmd}\n  -> Timeout (10 sec)")
        except Exception as e:
            errors.append(f"{cmd}\n  -> {e}")
    return success, errors

# curses

def run_tui():
    import curses

    adb_path = get_adb_path()

    LEVELS_3 = ["1", "2", "3"]
    LEVELS_6 = ["Don't change", "1", "2", "3", "4", "5", "6"]
    ON_OFF   = ["Don't change", "Enable", "Disable"]

    state = {
        "modify_device": False,
        "device_cpu":    0,
        "device_gpu":    0,
        "cpu_comp":      0,
        "gpu_comp":      0,
        "texture":       0,
        "blur":          0,
        "recents":       False,
    }

    HELP_DEVICE = (
        "deviceLevelList\n\n"
        "Many apps (and naturally Xiaomi system apps) use deviceLevelList to\n"
        "determine the device class, 1 - low class, 3 - high class.\n"
        "By changing the CPU and GPU values in deviceLevelList, you can enable\n"
        "blur and complex animations in different parts of the system\n"
        "(e.g., in recents, folders, and on the lock screen).\n"
        "Usually doesn't cause lag even on weaker devices.\n\n"
        "I recommend using the same values for CPU and GPU."
    )
    HELP_COMP = (
        "computility\n\n"
        "Similar to deviceLevelList, but has a much greater impact on\n"
        "animations and effects in the system.\n"
        "Low-end: 1-2  |  Mid-range: 2-3  |  Flagship: 4-6\n\n"
        "Recommended values:\n"
        "  1 - maximum performance and minimum distractions\n"
        "  3 - ideal balance between beauty and performance\n"
        "  6 - lots of blur effects and animations, may lag on weak devices\n\n"
        "(˶°ㅁ°) !! Advanced textures work strangely with values below 4."
    )
    HELP_OTHER = (
        "Other settings\n\n"
        "Advanced textures - enables the \"Advanced textures\" setting in\n"
        "  Settings -> Display & brightness -> Screen.\n"
        "  Looks very nice, but may consume significantly more power.\n\n"
        "Window-level blur - enables blur effects behind some windows\n"
        "  (e.g., behind warnings and dialogs).\n\n"
        "Stacked recents - enables the iOS-like \"Stacked\" recent apps style.\n"
        "  Requires the latest system launcher.\n"
        "  You can change the style back through settings.\n\n"
        "TUI mode by MalikHw47 uwu"
    )

    # Items list: (type, state_key, label, options_list)
    # type: "header" | "check" | "cycle" | "action"
    ITEMS = [
        ("header", None,           "── deviceLevelList ─────────────────────────────", None),
        ("check",  "modify_device","Modify deviceLevelList",                           None),
        ("cycle",  "device_cpu",   "  CPU",                                            LEVELS_3),
        ("cycle",  "device_gpu",   "  GPU",                                            LEVELS_3),
        ("header", None,           "── computility ─────────────────────────────────", None),
        ("cycle",  "cpu_comp",     "CPU",                                              LEVELS_6),
        ("cycle",  "gpu_comp",     "GPU",                                              LEVELS_6),
        ("header", None,           "── Other ────────────────────────────────────────", None),
        ("cycle",  "texture",      "Advanced textures",                                ON_OFF),
        ("cycle",  "blur",         "Window-level blur",                                ON_OFF),
        ("check",  "recents",      "Enable stacked recents",                           None),
        ("header", None,           "── Actions ──────────────────────────────────────", None),
        ("action", "apply",        "[ Apply ]",                                        None),
        ("action", "reboot",       "[ Reboot ]",                                       None),
        ("action", "help_device",  "[ ? deviceLevelList ]",                            None),
        ("action", "help_comp",    "[ ? computility ]",                                None),
        ("action", "help_other",   "[ ? Other ]",                                      None),
        ("action", "about",        "[ About ]",                                        None),
        ("action", "quit",         "[ Quit ]",                                         None),
    ]

    selectable = [i for i, item in enumerate(ITEMS) if item[0] != "header"]
    status_msg = [""]

    def show_popup(stdscr, title, body):
        h, w = stdscr.getmaxyx()
        lines = body.split("\n")
        bh = min(len(lines) + 4, h - 2)
        bw = min(max((len(l) for l in lines), default=10) + 4, w - 2)
        by = (h - bh) // 2
        bx = (w - bw) // 2
        popup = curses.newwin(bh, bw, by, bx)
        popup.box()
        popup.addstr(0, 2, f" {title} "[:bw - 2], curses.A_BOLD)
        for i, line in enumerate(lines[:bh - 4]):
            popup.addstr(i + 2, 2, line[:bw - 4])
        popup.addstr(bh - 1, 2, " Press any key to close "[:bw - 2])
        popup.refresh()
        popup.getch()

    def confirm_popup(stdscr, msg):
        h, w = stdscr.getmaxyx()
        lines = msg.split("\n")
        bh = len(lines) + 4
        bw = max(max((len(l) for l in lines), default=10) + 4, 32)
        by = (h - bh) // 2
        bx = (w - bw) // 2
        popup = curses.newwin(bh, bw, by, bx)
        popup.box()
        popup.addstr(0, 2, " Confirm ", curses.A_BOLD)
        for i, line in enumerate(lines):
            popup.addstr(i + 2, 2, line[:bw - 4])
        popup.addstr(bh - 1, 2, " [Y]es / [N]o "[:bw - 2])
        popup.refresh()
        while True:
            k = popup.getch()
            if k in (ord('y'), ord('Y')):
                return True
            if k in (ord('n'), ord('N'), 27):
                return False

    def main(stdscr):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN,   -1)
        curses.init_pair(2, curses.COLOR_GREEN,  -1)
        curses.init_pair(3, curses.COLOR_RED,    -1)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)
        curses.init_pair(5, curses.COLOR_BLACK,  curses.COLOR_WHITE)

        ok, adb_msg = check_adb_devices(adb_path)
        sel_pos = 0

        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()

            title = "  HypeMyOS - make HyperOS more hype ᕙ(•̀ ᗜ •́)ᕗ  "
            stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
            stdscr.addstr(0, max(0, (w - len(title)) // 2), title[:w])
            stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

            adb_color = curses.color_pair(2) if ok else curses.color_pair(3)
            stdscr.attron(adb_color)
            stdscr.addstr(1, 2, f"ADB: {adb_msg}"[:w - 2])
            stdscr.attroff(adb_color)

            focused_idx = selectable[sel_pos]
            row = 3

            for i, (itype, ikey, ilabel, ioptions) in enumerate(ITEMS):
                if row >= h - 2:
                    break
                is_focused = (i == focused_idx)
                attr = curses.color_pair(5) if is_focused else 0

                if itype == "header":
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(row, 2, ilabel[:w - 2])
                    stdscr.attroff(curses.color_pair(1))
                elif itype == "check":
                    mark = "X" if state[ikey] else " "
                    stdscr.attron(attr)
                    stdscr.addstr(row, 4, f"[{mark}] {ilabel}"[:w - 4])
                    stdscr.attroff(attr)
                elif itype == "cycle":
                    val = ioptions[state[ikey]]
                    stdscr.attron(attr)
                    stdscr.addstr(row, 4, f"{ilabel}: < {val} >"[:w - 4])
                    stdscr.attroff(attr)
                elif itype == "action":
                    stdscr.attron(attr | curses.A_BOLD)
                    stdscr.addstr(row, 4, ilabel[:w - 4])
                    stdscr.attroff(attr | curses.A_BOLD)

                row += 1

            stdscr.attron(curses.color_pair(4))
            stdscr.addstr(h - 1, 0,
                " ↑↓ navigate   ←→/Space cycle   Enter confirm   Q quit "[:w - 1])
            stdscr.attroff(curses.color_pair(4))
            if status_msg[0]:
                stdscr.addstr(h - 2, 2, status_msg[0][:w - 4])

            stdscr.refresh()
            key = stdscr.getch()

            if key in (curses.KEY_UP, ord('k')):
                sel_pos = (sel_pos - 1) % len(selectable)
                continue
            if key in (curses.KEY_DOWN, ord('j')):
                sel_pos = (sel_pos + 1) % len(selectable)
                continue
            if key in (ord('q'), ord('Q')):
                break

            itype, ikey, ilabel, ioptions = ITEMS[focused_idx]

            if key in (ord(' '), curses.KEY_RIGHT, curses.KEY_LEFT, 10, 13):
                if itype == "check":
                    state[ikey] = not state[ikey]

                elif itype == "cycle":
                    delta = -1 if key == curses.KEY_LEFT else 1
                    state[ikey] = (state[ikey] + delta) % len(ioptions)

                elif itype == "action":
                    if ikey == "quit":
                        break

                    elif ikey == "apply":
                        md = state["modify_device"]
                        dc = LEVELS_3[state["device_cpu"]] if md else None
                        dg = LEVELS_3[state["device_gpu"]] if md else None
                        cc_raw = LEVELS_6[state["cpu_comp"]]
                        gc_raw = LEVELS_6[state["gpu_comp"]]
                        cc = cc_raw if cc_raw != "Don't change" else None
                        gc = gc_raw if gc_raw != "Don't change" else None
                        tex_raw = ON_OFF[state["texture"]]
                        tex = (True if tex_raw == "Enable" else False) if tex_raw != "Don't change" else None
                        bl_raw = ON_OFF[state["blur"]]
                        bl  = (True if bl_raw == "Enable" else False) if bl_raw != "Don't change" else None
                        rec = state["recents"]

                        cmds = build_commands(md, dc, dg, cc, gc, tex, bl, rec)
                        if not cmds:
                            status_msg[0] = "No settings to apply ¯\\_(ツ)_/¯"
                        elif confirm_popup(stdscr, f"∘ ∘ ∘ (°ヮ°) ?\n{len(cmds)} command(s) will be executed."):
                            s, errs = run_adb_commands(adb_path, cmds)
                            if errs:
                                show_popup(stdscr, "Result",
                                           f"Success: {s}, Errors: {len(errs)}\n\n" +
                                           "\n".join(errs[:3]))
                                status_msg[0] = f"Done with {len(errs)} error(s)."
                            else:
                                status_msg[0] = f"◝(ᵔᗜᵔ)◜ All {s} commands OK!"

                    elif ikey == "reboot":
                        if confirm_popup(stdscr, "∘ ∘ ∘ (°ヮ°) ?\nReboot the device?"):
                            try:
                                subprocess.run([adb_path, "reboot"], check=True, timeout=10)
                                status_msg[0] = "◝(ᵔᗜᵔ)◜ Reboot command sent."
                            except Exception as e:
                                status_msg[0] = f"(˶°ㅁ°) !! {e}"

                    elif ikey == "help_device":
                        show_popup(stdscr, "Help: deviceLevelList", HELP_DEVICE)
                    elif ikey == "help_comp":
                        show_popup(stdscr, "Help: computility", HELP_COMP)
                    elif ikey == "help_other":
                        show_popup(stdscr, "Help: Other", HELP_OTHER)

                    elif ikey == "about":
                        show_popup(stdscr, "About",
                                   "HypeMyOS - make HyperOS more hype ᕙ(•̀ ᗜ •́)ᕗ\n\n"
                                   "Utility for spoofing device class to unlock\n"
                                   "flagship features on any device with HyperOS.\n\n"
                                   "TUI mode by MalikHw47\n\n"
                                   "Thanks for using! 𐔌՞. .՞𐦯")

    curses.wrapper(main)

# gui

def run_gui():
    try:
        from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                       QGroupBox, QCheckBox, QComboBox, QLabel, QPushButton,
                                       QMessageBox)
        from PySide6.QtCore import Qt
    except (ImportError, RuntimeError) as e:
        print(f"(˶°ㅁ°) !! Failed to load PySide6: {e}", file=sys.stderr)
        print("consider using --tui instead uwu", file=sys.stderr)
        sys.exit(1)

    class HypeMyOS(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("HypeMyOS")
            self.setMinimumWidth(500)

            self.adb_path = get_adb_path()

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

        def check_adb(self):
            ok, msg = check_adb_devices(self.adb_path)
            if not ok:
                QMessageBox.warning(self, "Warning",
                                    f"(˶°ㅁ°) !!\n{msg}\n"
                                    "Make sure your device is connected and USB debugging is enabled.")

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
            QMessageBox.about(self, "About",
                              "HypeMyOS - make HyperOS more hype ᕙ(•̀ ᗜ •́)ᕗ\n\n"
                              "Utility for spoofing device class to unlock flagship features "
                              "on any device with HyperOS.\n\n"
                              "Thanks for using! 𐔌՞. .՞𐦯")

        def build_commands_gui(self):
            commands = []
            if self.device_checkbox.isChecked():
                cpu_val = self.device_cpu.currentText()
                gpu_val = self.device_gpu.currentText()
                commands.append(f'settings put system deviceLevelList "v:1,c:{cpu_val},g:{gpu_val}"')
            cpu_comp = self.comp_cpu.currentText()
            if cpu_comp != "Don't change":
                commands.append(f"""service call miui.mqsas.IMQSNative 21 i32 1 s16 "setprop" i32 1 s16 "persist.sys.computility.cpulevel {cpu_comp}" s16 "/storage/emulated/0/log.txt" i32 600""")
            gpu_comp = self.comp_gpu.currentText()
            if gpu_comp != "Don't change":
                commands.append(f"""service call miui.mqsas.IMQSNative 21 i32 1 s16 "setprop" i32 1 s16 "persist.sys.computility.gpulevel {gpu_comp}" s16 "/storage/emulated/0/log.txt" i32 600""")
            texture_val = self.texture_combo.currentText()
            if texture_val != "Don't change":
                bool_val = "true" if texture_val == "Enable" else "false"
                commands.append(f"""service call miui.mqsas.IMQSNative 21 i32 1 s16 "setprop" i32 1 s16 "persist.sys.background_blur_supported {bool_val}" s16 "/storage/emulated/0/log.txt" i32 600""")
            blur_val = self.blur_combo.currentText()
            if blur_val != "Don't change":
                disable = "0" if blur_val == "Enable" else "1"
                commands.append(f"settings put global disable_window_blurs {disable}")
            if self.recent_checkbox.isChecked():
                commands.append("settings put global task_stack_view_layout_style 2")
            return commands

        def apply_settings(self):
            commands = self.build_commands_gui()
            if not commands:
                QMessageBox.information(self, "Information", "No settings to apply ¯\\_(ツ)_/¯")
                return
            reply = QMessageBox.question(self, "Confirmation",
                                         f"∘ ∘ ∘ (°ヮ°) ?\n{len(commands)} commands will be executed. Continue?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
            success_count, error_messages = run_adb_commands(self.adb_path, commands)
            if error_messages:
                QMessageBox.warning(self, "Result",
                                    f"Success: {success_count}, Errors: {len(error_messages)}\n\n" +
                                    "\n\n".join(f"(˶°ㅁ°) !!\nCommand: {e}" for e in error_messages[:3]))
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

    app = QApplication(sys.argv)
    window = HypeMyOS()
    window.show()
    sys.exit(app.exec())



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HypeMyOS - make HyperOS more hype")
    parser.add_argument("--tui", action="store_true",
                        help="Run in TUI (curses) mode without requiring PySide6")
    args = parser.parse_args()

    if args.tui:
        run_tui()
    else:
        run_gui()
