# PyInstaller spec - size-optimised single-file build (see build_exe.bat)
from PyInstaller.utils.hooks import collect_all

datas = [
    ("models", "models"),
    # the kung fu song is the only music file; everything else is composed in code
    ("assets/music/AgenChicken - Japanese DnB.ogg", "assets/music"),
    ("assets/music/italy.mp3", "assets/music"),           # the pizza song
    ("assets/fonts", "assets/fonts"),
    ("assets/sfx/frog", "assets/sfx/frog"),           # CC0 frog ribbits (Tier-Yoga)
    ("assets/sfx/pizza", "assets/sfx/pizza"),         # CC0 knife, grater, bites (Pizza)
]
binaries, hiddenimports = [], []
for pkg in ("mediapipe", "numpy"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# mediapipe's bundled test files / unused legacy solution graphs
datas = [d for d in datas
         if "/test" not in d[1].replace("\\", "/") + "/"
         and "testdata" not in d[0]]

a = Analysis(
    ["main.py"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    runtime_hooks=["rthook_stubs.py"],
    excludes=["tkinter", "matplotlib", "scipy", "IPython", "jax", "jaxlib"],
)

# FFmpeg is only needed to read video files; the webcam uses DirectShow
a.binaries = [b for b in a.binaries if "ffmpeg" not in b[0].lower()]

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas,
    name="CamToy",
    console=False,
    upx=False,
)
