# HypeMyOS
Utility for spoofing device class to unlock flagship features on any device with HyperOS
## How to use it?

You will need a PC with Windows or Linux, an USB cable that supports data transfer, and a phone with HyperOS.

Enable USB debbugging on your phone (Settings -> Additional Settings -> Developer options -> Debugging -> USB debugging) and connect it to your PC.

Download HypeMyOS from [Releases](https://github.com/fishcheese/hypemyos/releases), open it, select options you want to apply, click "Apply" and then "Reboot". That's it!

## How to build it manually?

Clone the repo, donwload SDK platform tools for your OS (Windows or Linux) and place it in the folder `./platform-sdk-<windows/linux>`, install dependencies: `pip install PySide6 pyinstaller`. On Windows, use command `pyinstaller --onefile .\hypemyos.py --add-data "platform-tools-windows;platform-tools-windows"`, and on Linux use `pyinstaller --onefile hypemyos.py --add-data "platform-tools-linux:platform-tools-linux"`.
