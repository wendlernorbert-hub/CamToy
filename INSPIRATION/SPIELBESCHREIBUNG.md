# CamToy: Spielbeschreibung und Umsetzung

Webcam-Bewegungsspiele für Kinder von 3 bis 6 Jahren. Python, Pygame, MediaPipe (Pose),
läuft auf einem normalen Laptop (i5, 11. Gen) ohne Grafikkarte.

## 1. Gestaltungsregeln für kleine Kinder

| Regel | Umsetzung |
|---|---|
| Lesen ist nicht nötig | Alles läuft über Bilder, Symbole, Töne und gesprochene Ansagen. Text ist nur für Eltern da. |
| Kein Verlieren | Es gibt kein Game Over und keine Strafpunkte. Wer eine Aufgabe nicht schafft, bekommt trotzdem einen Stern und geht weiter. |
| Große Ziele | Trefferzonen sind größer als die Grafik (Hände zählen schon bei Berührung der Randzone). |
| Kurze Runden | 45 Sekunden (Blasen, Kung-Fu) bzw. 5 Aufgaben (Tier-Yoga). Verkleiden ist Freispiel. |
| Sofortige Belohnung | Jede Aktion hat Ton, Partikel oder Animation. Am Rundenende Konfetti, Sterne, Fanfare. |
| Steuerung ohne Maus | Alle Knöpfe werden durch Hand-Halten ausgelöst: Hand auf einen Kreis, ein gelber Ring füllt sich. |
| Eltern-Regler | Tasten `1` `2` `3` stellen Größe, Tempo und Strenge aller Spiele ein. |

## 2. Steuerung

* Beide Hände erscheinen als leuchtende Punkte (links rosa, rechts blau). So sieht das Kind, was es steuert.
* **Dwell-Knöpfe**: Hand auf den Kreis halten. Menü 1,1 s, Zurück 1,2 s, Kacheln beim Verkleiden 0,75 s,
  Foto 1,0 s. Danach muss die Hand den Kreis kurz verlassen, bevor er erneut auslöst.
* Haus-Symbol oben links bringt in jedem Spiel zurück ins Menü.
* Wenn der Körper nicht erkannt wird, zeigt das Menü "Stell dich vor die Kamera und winke!".

## 3. Spiel 1: Seifenblasen

**Idee.** Bunte Seifenblasen steigen auf, das Kind platzt sie mit den Händen. Verwandt mit Bubble Pop
und Wishi Washi aus EyeToy: Play, aber ohne Fehlerzustand.

**Ablauf.** Intro (2,6 s, Ansage "Seifenblasen! Platze sie mit deinen Händen!"), 45 Sekunden Spiel, Ergebnis.

**Regeln.**
* Blasen starten unter dem Bild, steigen auf und schwanken seitlich (Sinus, Amplitude 12-32 px).
* Berührung: Handgelenk oder Zeigefinger näher als Radius + 12 px. Die Blase platzt mit Ring-Welle,
  Funken in Blasenfarbe und "Plopp".
* **Goldene Blase** (alle 10-16 s, 15 % größer, langsamer): Sie platzt alle anderen Blasen auf einmal,
  mit Sternen und Glockenklang.
* **Sanfte Hilfe**: Nach 6 Sekunden ohne Treffer schwebt eine Blase direkt zur Hand des Kindes.
* Anzeige: 10 Sternplätze oben, alle 3 geplatzten Blasen füllt sich einer. Darunter ein Zeitbalken.
* Ergebnis: 1 + (Blasen / 8) Sterne, höchstens 5.

| Stufe | Radius | Steiggeschwindigkeit | Max. gleichzeitig | Neue Blase alle |
|---|---|---|---|---|
| 1 (3-4 J.) | 70-100 px | 55-95 px/s | 6 | ca. 0,9 s |
| 2 | 52-80 px | 85-135 px/s | 8 | ca. 0,65 s |
| 3 (6+ J.) | 40-62 px | 120-190 px/s | 10 | ca. 0,45 s |

**Umsetzung.** `bubbles.py`. Jede Blase bekommt beim Erzeugen ein vorgerendertes Sprite
(halbtransparente Füllung, Rand, Glanzlicht), das spart Rechenzeit. Treffertest ist ein Abstandsvergleich
pro Blase und Handpunkt.

## 4. Spiel 2: Verkleiden

**Idee.** Das Kind sieht sich selbst im Spiegelbild und zieht sich an: Hut, Brille, Nase, Umhang, Flügel,
Handobjekt. Dazu ein Foto-Knopf.

**Bedienung.** Je drei Kreise links und rechts am Rand. Hand 0,75 s auf einen Kreis: das nächste Teil
dieser Kategorie (mit Wölkchen-Effekt und gesprochenem Namen). Das letzte Teil führt zurück auf "nichts".

| Kategorie | Teile |
|---|---|
| Hut | Krone, Zauberhut, Zylinder, Hasenohren |
| Brille | Sonnenbrille, Herzbrille, Sternbrille |
| Gesicht | Clownsnase, Schnurrbart, Katzennase mit Schnurrhaaren |
| Umhang | Superheld (rot), König (lila), Wald (grün) |
| Flügel | Fee, Schmetterling, Engel (mit Flügelschlag) |
| Hand | Zauberstab (mit Funken), Schwert, Luftballon (schwebt verzögert hinterher) |

**Foto.** Knopf oben rechts, 1 s halten, dann Countdown 3-2-1 mit Ansage, Blitz, Verschluss-Klang.
Das Bild wird ohne Knöpfe und Hände-Punkte in `fotos/camtoy_JJJJMMTT_HHMMSS.png` gespeichert
und als kleines Foto unten rechts eingeblendet.

**Umsetzung.** `dressup.py` (Spiel), `costumes.py` (alle Teile per Polygon gezeichnet, keine Bilddateien).
* Kopf: Augenlinie gibt Neigung, Ohrabstand gibt Größe, daraus ein Koordinatensystem (`Xf`), in dem
  Hut, Brille und Nase proportional sitzen und mitkippen.
* Umhang und Flügel hängen an Schultern und Rumpflänge.
* **Hinter dem Kind**: Solange das Spiel läuft, schaltet der Tracker die Personen-Segmentierung ein.
  Das Spiel zeichnet Umhang und Flügel auf das Kamerabild, danach das Kind als Ausschnitt (Alpha aus der
  Maske) wieder darüber. So wirken Umhang und Flügel wie hinter dem Körper. Ohne Maske (z. B. Modell
  liefert keine) werden sie halbtransparent über den Körper gelegt.
* Handobjekte folgen dem Unterarm (Ellbogen zu Handgelenk, nach oben gebogen, damit der Stab nie nach unten zeigt).

## 5. Spiel 3: Tier-Yoga

**Idee.** Eine Trainer-Figur macht ein Tier oder eine Bewegung vor, das Kind macht es nach.
Deckt die Wünsche Hampelmann, Armkreisen und Kniebeugen ab, aber als Tiere verpackt.

**Ablauf.** 5 zufällige Aufgaben aus 7. Pro Aufgabe: Ansage und Vormachen (2,2 s), dann das Kind.
Oben links das Tierbild mit gelbem Fortschrittsring, darunter die Trainer-Figur (spielt die Bewegung
in Endlosschleife), oben rechts 5 Sterne für die Aufgaben. Das Skelett des Kindes wird weiß eingeblendet
und wird grün, solange die Pose stimmt. Erfolg: Konfetti und "Super!". Zeitüberschreitung: "Fast geschafft!"
und weiter.

| Aufgabe | Bewegung | Erkennung (Armlängen in Rumpfeinheiten) |
|---|---|---|
| Baum | beide Arme gestreckt nach oben, Hände nah beieinander | Handgelenke deutlich über Schulter (< -0,55 bis -0,8), Arm gestreckt (Länge > 0,78 bis 0,9), Handabstand < 1,7 bis 2,3 Schulterbreiten |
| Storch | auf einem Bein stehen | ein Knöchel höher als der andere: Höhenunterschied > 12 bis 22 % der Beinlänge |
| Frosch | Kniebeuge, 2 bis 4 Mal | Schultern sinken um > 0,22 bis 0,38 Rumpflängen unter die zu Beginn gemessene Standhöhe, dann wieder hoch |
| Stern | Hampelmann (Arme hoch/runter), 2 bis 4 Mal | beide Handgelenke über Schulterhöhe (0,2 bis 0,5 Rumpflängen), danach wieder deutlich darunter (> 0,45) |
| Schmetterling | Arme waagerecht zur Seite | Arm nach außen > 0,55 bis 0,8, Höhenabweichung < 0,5 bis 0,3 |
| Hase | Hände wie Hasenohren am Kopf | Handgelenke etwa auf Augenhöhe oder höher, nah an der Nase (1,0 bis 1,5 Schulterbreiten), Arme gebeugt (Länge < 1,0) |
| Windmühle | Arme im Kreis drehen | aufsummierter Drehwinkel des Handgelenks um die Schulter, 1,5 bis 3 Umdrehungen |

Stufen: Halten 1,6 / 2,2 / 3,0 s, Wiederholungen 2 / 3 / 4, Zeitlimit pro Aufgabe 32 / 28 / 24 s.
Ergebnis: 3 Punkte pro geschaffter Aufgabe (2 oder 1 bei Zeitablauf, je nach Fortschritt),
Sterne = 1 + gerundet 4 x Punkte / 15.

**Umsetzung.** `animals.py`, `pose.py`.
* Alle Maße sind in **Rumpflängen** (Schulter-Mitte bis Hüft-Mitte) angegeben und unabhängig von Abstand
  und Körpergröße. Fehlen die Hüften, wird die Rumpflänge aus der Schulterbreite geschätzt.
* Die Kniebeuge braucht nur den Oberkörper: Die Standhöhe wird in den ersten 0,8 s gemessen
  (Median), danach zählt jede Senkung und Rückkehr als Wiederholung (mit Hysterese 0,10).
* Halte-Aufgaben füllen den Ring während die Pose stimmt und leeren ihn langsam, wenn sie verloren geht.
* Fehlen für die Aufgabe nötige Körperteile (Storch: Hüften und Knöchel), erscheint "Geh ein Stück zurück"
  mit Ansage.
* Die **Trainer-Figur** entsteht aus demselben Skelett-Generator wie die Tests (`make_skeleton`):
  Arme und Beine per Zwei-Knochen-Kinematik, Parametervektor pro Pose, weich ineinander überblendet.
  Neue Pose = neuer Vektor in `PRESETS`.

## 6. Spiel 4: Kung-Fu-Meister

**Idee.** Whack-a-Mole mit dem ganzen Körper. Ninja-Köpfe tauchen am Bildrand auf, das Kind haut sie
mit Händen weg. Höhere Stufen verlangen echte Schläge und Tritte gegen Holzbretter.

**Regeln.**
* Ninjas poppen mit Überschwinger auf, bleiben kurz und tauchen mit Ton wieder ab. Nichts geht verloren.
* Treffer: "POW!"-Stern, Sternenregen, Ninja fliegt davon. Treffer in Folge (< 1,6 s Abstand)
  geben mehr Funken und ab drei in Folge eine große Zahl ("x3").
* **Holzbretter** unten (ab Stufe 2, nur wenn beide Knöchel sichtbar, 25 % der Ziele): Mit dem Fuß treten.
  Das Brett bricht in zwei Hälften.
* **Gürtel**: Oben rechts ein Gürtel, der mit den Treffern die Farbe wechselt (Fanfare + "Neuer Gürtel!").
  Am Ende wird der erreichte Gürtel groß gezeigt.

| Gürtel | ab Treffern |
|---|---|
| Weiß | 0 |
| Gelb | 4 |
| Orange | 8 |
| Grün | 13 |
| Blau | 18 |
| Braun | 24 |
| Schwarz | 30 |

| Stufe | Ziel bleibt | gleichzeitig | Hand muss schneller sein als | Radius |
|---|---|---|---|---|
| 1 | 3,4 s | 2 | (keine Anforderung, Berühren reicht) | 64 px |
| 2 | 2,5 s | 3 | 260 px/s | 54 px |
| 3 | 1,9 s | 3 | 430 px/s | 46 px |

Sterne am Ende: 1 + (Gürtelnummer x 4 / 6).

**Umsetzung.** `kungfu.py`. Die Handgeschwindigkeit wird über ein 0,14-s-Fenster gemessen (Strecke / Zeit),
damit sie bei 30 fps Kamera und 60 fps Anzeige nicht flackert. Ziele erscheinen nur an festen, frei
gewählten Plätzen am Rand (nicht vor dem Körper), mit Mindestabstand zu anderen Zielen.

## 7. Technik

```
Webcam -> Tracker-Thread -> Landmarks (33 x [x, y, Sicht]) -> Pose-Objekt -> Spiel.update/draw -> Pygame
          (OpenCV, MediaPipe PoseLandmarker lite, 640x480)       (Pixelgeometrie, Hilfsmaße)
```

| Datei | Inhalt |
|---|---|
| `main.py` | Fenster, Hauptschleife (60 fps), Menü, Tasten, Kamera-/Masken-Oberflächen |
| `tracker.py` | Kamera + MediaPipe in eigenem Thread, Modell-Download, `MockTracker` (Maus) |
| `pose.py` | Landmark-Namen, `Pose`-Klasse, Skelett-Generator, Figur-Zeichner |
| `common.py` | Spiel-Grundklasse (Intro/Spiel/Ergebnis), Dwell-Knöpfe, Partikel, Klänge, Sprache |
| `bubbles.py`, `dressup.py`, `animals.py`, `kungfu.py` | die vier Spiele |
| `costumes.py` | alle Kostümteile per Code gezeichnet |
| `test_headless.py` | Tests mit simulierten Körpern |

**Wichtige Entscheidungen.**
* **Tracking entkoppelt vom Rendering.** Der Tracker-Thread liefert ca. 30 Posen/s, die Anzeige läuft mit 60 fps.
  Kurze Aussetzer (< 0,3 s) werden mit der letzten Pose überbrückt.
* **Spiegelbild.** Das Bild wird gespiegelt angezeigt. Die Pose wird auf dem *ungespiegelten* Bild berechnet
  und danach die x-Koordinate gespiegelt, damit "links" im Code immer die linke Hand des Kindes auf der linken
  Bildschirmseite ist.
* **Neue MediaPipe-API.** Aktuelle MediaPipe-Versionen haben die alte `mp.solutions.pose` nicht mehr.
  Genutzt wird `PoseLandmarker` (Tasks-API, Lite-Modell, Videomodus).
* **Alles ohne Dateien.** Grafik und Klänge werden im Code erzeugt (Polygone, synthetische Töne mit NumPy).
* **Sprachausgabe optional** (pyttsx3, offline, eigener Thread, jede neue Ansage verwirft die wartende).
* **Kamera-Seitenverhältnis bestimmt das Fenster** (4:3 oder 16:9), alle Koordinaten sind Pixel dieses Fensters.
  Vollbild (`F11`) skaliert mit schwarzen Balken.

## 8. Anpassen

* Neue Pose: Vektor in `pose.py` (`PRESETS`), Prüffunktion und Eintrag in `animals.py` (`INFO`, `make_task`), Tierbild
  `pic_...`. Den Test in `test_headless.py` um die neue Pose ergänzen.
* Neues Kostümteil: Zeichenfunktion in `costumes.py`, Eintrag in `SLOTS` (`dressup.py`) und `NAMES`.
* Schwierigkeit: Tabellen `LEVELS`, `HOLD`, `REPS`, `TIMEOUT` ganz oben in den Spieldateien.
* Erkennung zu streng oder zu lasch: die Schwellwerte stehen direkt in den `chk_...`-Funktionen und in `RepTask`.

## 9. Ehrlicher Stand

* Spiellogik, Erkennung und Grafik sind mit simulierten Skeletten getestet (`python test_headless.py`:
  Erkennung aller Posen in drei Stufen, keine falschen Treffer beim ruhigen Stehen, Rundenabläufe, Foto).
  Der Kameraweg ist mit einer Attrappe geprüft.
* **Nicht getestet** mit echter Webcam und echtem MediaPipe-Modell (in der Entwicklungsumgebung gab es weder
  Kamera noch Modell-Download). Die Schwellwerte für Storch, Kniebeuge und Hase sind begründete Startwerte
  und sollten einmal mit dem Kind ausprobiert und nachjustiert werden.
* Die Personen-Maske für Umhang/Flügel kostet etwas CPU. Wenn es auf dem Laptop ruckelt: Kamera auf
  480 x 360 stellen (in `main.py` `Tracker(args.kamera, 480, 360)` statt `Tracker(args.kamera)`) oder Flügel/Umhang weglassen.
