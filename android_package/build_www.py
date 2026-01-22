"""
Helper: copy Django static assets into android_package/www

Usage (Windows):
    python build_www.py

This script will run `manage.py collectstatic` then copy the contents
of the project's staticfiles (or static) directory into android_package/www.

Note: bundling server-rendered Django templates into a static `index.html`
is non-trivial. For development prefer using Capacitor's `server.url`
pointing to your running dev server (use 10.0.2.2 for emulator).
"""

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WWW = Path(__file__).resolve().parent / "www"

def run_collectstatic():
    print("Running collectstatic...")
    subprocess.check_call([os.path.join(ROOT, ".venv", "Scripts", "python.exe"), "manage.py", "collectstatic", "--noinput"], cwd=ROOT)

def copy_static():
    # Try common static locations
    candidates = [ROOT / "staticfiles", ROOT / "static"]
    WWW.mkdir(exist_ok=True)
    for c in candidates:
        if c.exists():
            print(f"Copying from {c} to {WWW}")
            for item in c.iterdir():
                dest = WWW / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
            return
    print("No staticfiles or static folder found. Run collectstatic or place web assets into android_package/www manually.")

if __name__ == '__main__':
    try:
        run_collectstatic()
    except Exception as e:
        print("collectstatic failed (you can still copy static manually):", e)
    copy_static()
