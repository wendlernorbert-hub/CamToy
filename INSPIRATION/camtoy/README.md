# CamToy

Webcam-Bewegungsspiele für Kinder (3-6 Jahre), Idee wie EyeToy (2003), Technik von heute:
Pygame + MediaPipe-Ganzkörper-Pose. Vier Spiele: Seifenblasen, Verkleiden, Tier-Yoga, Kung-Fu-Meister.
Details zu Spielen und Umsetzung: `SPIELBESCHREIBUNG.md`.

## Installation (Windows, PowerShell)

```powershell
cd C:\Users\gg\Documents\camtoy
py -3.12 -m venv .venv          # Python 3.10 bis 3.13 geht
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Beim ersten Start lädt das Programm einmalig das Pose-Modell (ca. 6 MB) nach `models/`.
Klappt der Download nicht, die Datei von Hand holen und dort ablegen:
https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task

Alternativ `start.bat` doppelklicken.

## Aufstellung

- Kamera auf Brusthöhe des Kindes, Kind etwa 2 m entfernt, ganzer Körper sichtbar.
- Helles Licht von vorn, keine Lampe oder Fenster im Rücken.
- Für Tier-Yoga (Storch) müssen die Füße im Bild sein, sonst erscheint "Geh ein Stück zurück".

## Bedienung

Die Hände leuchten als Punkte. Hand auf einen Kreis halten, bis der gelbe Ring voll ist.
Für Eltern: `ESC` zurück/Ende, `1` `2` `3` Schwierigkeit (leicht/mittel/schwer),
`F11` Vollbild, `D` Skelett und Bildrate anzeigen.

## Optionen

| Option | Wirkung |
|---|---|
| `--kamera 1` | andere Kamera |
| `--maus` | ohne Kamera testen (Maus = rechte Hand, gedrückte Taste = beide Hände) |
| `--leise` | ohne Ton |
| `--keine-sprache` | ohne Sprachausgabe |
| `--vollbild` | Vollbild |
| `--hoehe 900` | Fensterhöhe |

Fotos aus dem Verkleiden-Spiel landen in `fotos/`.

## Tests

`python test_headless.py` simuliert Körperposen ohne Kamera und prüft Erkennung und alle Spiele.
Es schreibt Screenshots nach `test_out/`.

## Sprachausgabe

Läuft offline über pyttsx3 und nutzt eine deutsche Windows-Stimme, falls installiert
(Einstellungen > Zeit & Sprache > Sprache > Deutsch > Sprachausgabe). Ohne deutsche Stimme klingt es
englisch oder bleibt stumm. Alle Spiele funktionieren auch ohne Ton.
