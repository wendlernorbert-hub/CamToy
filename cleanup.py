"""Removes temp folders left behind by earlier runs of the single-file exe.

The exe unpacks itself to %TEMP%\\_MEI<number> on every start and deletes that folder on
a clean exit. After a crash / kill it stays (~250 MB). On each start we delete such
leftovers, but only ones that (a) are our own and (b) are not in use by a running copy.
"""
import os
import re
import shutil
import sys

_NAME = re.compile(r"^_MEI\d+(_del)?$")
# a file that only this game ships, so other PyInstaller programs' folders are never touched
_MARKER = os.path.join("models", "selfie_segmenter.tflite")


def remove_stale_temp_dirs() -> int:
    """Returns the number of folders removed. Does nothing when not running as exe."""
    current = getattr(sys, "_MEIPASS", None)
    if not current:
        return 0
    current = os.path.normcase(os.path.abspath(current))
    root = os.path.dirname(current)

    removed = 0
    try:
        names = os.listdir(root)
    except OSError:
        return 0

    for name in names:
        path = os.path.join(root, name)
        if (not _NAME.match(name) or os.path.normcase(path) == current
                or not os.path.isdir(path)
                or not os.path.exists(os.path.join(path, _MARKER))):
            continue
        trash = path if name.endswith("_del") else path + "_del"
        try:
            # Windows refuses to rename a directory that contains open files
            # (e.g. the DLLs of a running instance) -> in-use folders are skipped
            if trash != path:
                os.rename(path, trash)
        except OSError:
            continue
        shutil.rmtree(trash, ignore_errors=True)
        if not os.path.exists(trash):
            removed += 1
    return removed
