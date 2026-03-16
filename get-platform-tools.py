#!/usr/bin/env python3

import urllib.request
import zipfile
import os
import sys
import shutil
import platform

URLS = {
    "windows": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
    "linux":   "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
}

def reporthook(count, block_size, total_size):
    if total_size > 0:
        percent = min(int(count * block_size * 100 / total_size), 100)
        bar = "#" * (percent // 2) + "-" * (50 - percent // 2)
        print(f"\r  [{bar}] {percent}%", end="", flush=True)

def download_and_extract(os_name):
    url = URLS[os_name]
    zip_name = f"platform-tools-{os_name}.zip"
    dest_folder = f"platform-tools-{os_name}"

    if os.path.isdir(dest_folder):
        print(f"[{os_name}] '{dest_folder}' already exists, skipping download.")
        return

    print(f"[{os_name}] Downloading from {url} ...")
    try:
        urllib.request.urlretrieve(url, zip_name, reporthook)
        print()  # newline after progress bar
    except Exception as e:
        print(f"\n[{os_name}] Download failed: {e}")
        sys.exit(1)

    print(f"[{os_name}] Extracting ...")
    try:
        with zipfile.ZipFile(zip_name, 'r') as zf:
            zf.extractall(".")
    except Exception as e:
        print(f"[{os_name}] Extraction failed: {e}")
        os.remove(zip_name)
        sys.exit(1)

    # zip always contains a single top-level folder called "platform-tools"
    extracted = "platform-tools"
    if os.path.isdir(extracted):
        os.rename(extracted, dest_folder)
        print(f"[{os_name}] Renamed '{extracted}' -> '{dest_folder}'")
    else:
        print(f"[{os_name}] WARNING: expected folder '{extracted}' not found after extraction.")

    os.remove(zip_name)
    print(f"[{os_name}] Done! Tools are in './{dest_folder}/'")

def main():
    # decide which OS(es) to download for
    if len(sys.argv) > 1:
        targets = [a.lower() for a in sys.argv[1:] if a.lower() in URLS]
        if not targets:
            print(f"Usage: {sys.argv[0]} [windows] [linux]")
            print("  If no argument is given, downloads for the current OS only.")
            sys.exit(1)
    else:
        current = platform.system().lower()
        if current == "windows":
            targets = ["windows"]
        elif current == "linux":
            targets = ["linux"]
        else:
            # other — let the user pick both
            targets = list(URLS.keys())
            print("Unknown OS detected; downloading both Windows and Linux tools.")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    for target in targets:
        download_and_extract(target)

    print("\nAll done! You can now build HypeMyOS.")

if __name__ == "__main__":
    main()
