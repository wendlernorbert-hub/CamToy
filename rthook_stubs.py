"""PyInstaller runtime hook: mediapipe imports matplotlib.pyplot at import time but only
uses it in its drawing helpers, which this game never calls. A stub lets us leave
matplotlib (and its dependencies) out of the exe."""
import sys
import types

for _name in ("matplotlib", "matplotlib.pyplot"):
    sys.modules.setdefault(_name, types.ModuleType(_name))
