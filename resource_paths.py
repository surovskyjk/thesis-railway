# Shared helpers for locating bundled read-only resources and writable config in dev and frozen builds
import sys
from pathlib import Path


# True when running inside a PyInstaller-frozen executable
def isFrozen():
    return getattr(sys, "_MEIPASS", None) is not None


# Root directory holding read-only bundled resources such as translations and default config
def getBundleRoot():
    if isFrozen():
        return Path(sys._MEIPASS)
    return Path(__file__).parent


# Root directory the app can write to, e.g. a user-edited shortcuts config
def getWritableRoot():
    if isFrozen():
        return Path(sys.executable).parent
    return Path(__file__).parent
