"""Scripts for package installation and setup."""
import subprocess
import sys


def install_playwright_deps():
    """Install Playwright dependencies after package installation."""
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], 
                      check=True)
        print("Successfully installed Playwright Chromium dependencies")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Playwright dependencies: {e}", file=sys.stderr)
        sys.exit(1)
