# CamToy – Manifest

Was CamToy sein soll und woran sich jedes Spiel messen lassen muss.
Wenn eine Idee oder eine Änderung diesem Dokument widerspricht, gilt das Dokument – oder es wird bewusst geändert.

## Wozu

CamToy ist ein Kamera-Spielzeug für ein Kind von 3–4 Jahren. Es soll ihm vier Dinge geben:

| Ziel | Das heißt |
|---|---|
| **Bewegung** | Das Kind bewegt Arme und Oberkörper, gern auch kräftig und schnell. Bewegung ist das Steuern, nicht eine Pflichtübung. |
| **Spaß** | Jede Bewegung bekommt sofort eine lustige, sichtbare und hörbare Antwort. Lachen ist wichtiger als Punkte. |
| **Kreativität** | Das Kind macht etwas Eigenes – ein Kostüm, eine Pizza, ein Foto –, das es so nur einmal gibt. |
| **Erkunden** | Das Kind findet selbst heraus, was passiert, wenn es etwas tut. Es gibt Überraschungen und mehr als einen richtigen Weg. |

## Wer spielt

* **Ein Kind spielt allein.** Es startet, spielt und beendet ein Spiel ohne Hilfe eines Erwachsenen.
* **Andere Personen im Bild sind Störung, nicht Mitspieler.** Ein Elternteil, das danebensteht, oder ein Geschwister, das
  durchs Bild läuft, darf nichts auslösen, nichts übernehmen und nichts kaputt machen.
* **Spieler ist die kleinste Person im Bild** – erkannt an Körperproportionen (großer Kopf im Verhältnis zu den
  Schultern), nicht nur an der Größe im Bild. Wer Spieler ist, bleibt es, bis eine andere Person über mehrere Sekunden
  eindeutig besser passt.
* **Die Haltung wechselt.** Mal sitzt das Kind nah vor der Kamera, mal steht es, mal ist der ganze Körper zu sehen.
  Jedes Spiel funktioniert mit dem Oberkörper allein. Beine sind höchstens ein Bonus, wenn sie sichtbar sind.

## Grundsätze

1. **Kein Lesen, keine Sprache nötig.** Alles wird über Bilder, Töne und Vormachen verstanden. Zahlen sind erlaubt.
2. **Kein Scheitern.** Kein Game Over, keine Strafpunkte, keine traurigen Gesichter, kein „Fehlgeschlagen“.
   Wer etwas nicht schafft, wird freundlich weitergeführt.
3. **Sofortige Antwort.** Jede Berührung, jeder Schlag, jede Geste hat in Sekundenbruchteilen Ton und Bewegung zur Folge.
4. **Comic statt Brutalität.** Gegner purzeln, drehen sich, sehen Sterne. Comic-Schaden wie im Zeichentrick ist
   erlaubt (blaues Auge, Pflaster, Zahnlücke, Nasenbluten im Stil von Doom 1993); nichts Realistisches oder Grausames.
5. **Erkunden wird belohnt.** Auch Dinge abseits der Aufgabe reagieren. Seltene Überraschungen (Riesenblase,
   Regenbogen) machen neugierig. Freie Spiele haben keine „falsche“ Bedienung.
6. **Eigenes bleibt.** Was das Kind gestaltet, wird gezeigt und, wo es passt, gespeichert (Foto, fertige Pizza).
7. **Kurz und selbstständig.** Runden mit Wertung dauern etwa eine Minute; Gestalten und Freispiel dauern, so lange das
   Kind will. Bewegt sich eine Minute lang niemand, kehrt das Spiel von selbst ins Menü zurück.
8. **Große Ziele, langsame Knöpfe.** Trefferzonen sind großzügig. Knöpfe lösen erst nach kurzem Halten aus, damit
   nichts aus Versehen passiert.
9. **Hochwertiger Kinder-Look.** Runde, glänzende, liebevoll gezeichnete Figuren. Ein Erwachsener soll es schön finden,
   ein Kind soll es sofort verstehen.
10. **Eltern stellen ein, Kinder spielen.** Schwierigkeit und Kamera sind Sache der Erwachsenen (Tastatur); das Kind sieht
    davon nichts.

## Die Spiele

Jedes Spiel hat einen Schwerpunkt. Die Buchstaben zeigen, welche Ziele es vor allem bedient:
**B**ewegung, **S**paß, **K**reativität, **E**rkunden.

### Seifenblasen – S E
Der ruhige Einstieg. Das Kind entdeckt, dass seine Hände etwas bewirken: Blasen platzen, große klingen tief, kleine hoch,
manchmal kommt eine Riesenblase. Kein Ziel, keine Zeit, kein Ende – reines Ursache-und-Wirkung-Spielen.

### Kung-Fu-Meister – B S
Das Toben-Spiel. Schnelle, kräftige Armbewegungen und Reaktion. Das Kind fühlt sich stark: Es wird zum Ninja,
seine Fäuste brennen, Gegner fliegen davon, der Gürtel wird bunter. Der Boss sieht nach jedem Treffer
mitgenommener aus, wie das Spielergesicht im alten Doom – comichaft, nicht grausam.

### Tier-Yoga – B E
Das Nachmach-Spiel. Das Kind lernt seinen Körper kennen, indem es Tiere und Bewegungen nachahmt. Jede Bewegung ist
im Sitzen und im Stehen machbar; die Vormach-Figur zeigt nur, was der Oberkörper tun soll. Wer ein Tier nicht schafft,
bekommt trotzdem ein freundliches Weiter.

### Verkleiden – K E
Das Spiegel-Spiel. Das Kind probiert aus, wer es sein könnte: König, Pirat, Fee, Hund. Alles lässt sich frei
kombinieren, und es gibt viel zu entdecken. Das Foto hält das Ergebnis fest.

### Pizza backen – K E
Das Gestalten-Spiel. Das Kind macht etwas aus der echten Welt nach und belegt seine eigene Pizza. Jeder Schritt muss
ohne Erklärung verständlich sein. Belag, Menge und Reihenfolge sind frei, es gibt keine falsche Pizza. Der Lohn ist der
glückliche Koch, nicht eine Wertung.

### Auto fahren – B E
Das Reise-Spiel. Beide Arme arbeiten zusammen, um zu lenken. Unterwegs gibt es Landschaften, Tiere und Regenbögen zu
sehen. Das Kind selbst lenkt. Hütchen bremsen nur kurz, Verlieren gibt es nicht.

## Abgleich mit dem Code (Stand nach dem Overhaul, 8. Oktober 2026)

**Umgesetzt im Overhaul nach 0.1:**

| Bereich | Vorher (0.1) | Jetzt |
|---|---|---|
| Alle Spiele, Menü | Die Hände aller Personen zählten; „Hauptperson“ war die größte. | `PlayerPicker` (`minigames/pose.py`) wählt das Kind, alle anderen werden ignoriert – auch im Menü. |
| Tracker | Höchstens 2 Personen; bei 3 im Bild konnte das Kind herausfallen. | Bis zu 3 Personen; jede hat ihre eigene Maske, ausgeschnitten wird nur das Kind. |
| Verkleiden, Kung-Fu, Auto | Alle wurden verkleidet bzw. zu Ninjas; lenken konnte jeder. | Nur das Kind. |
| Tier-Yoga | Bei Zeitablauf trauriges Gesicht und Ton nach unten. | Das Tier hüpft winkend herein, dann geht es weiter. |
| Tier-Yoga | Vormach-Figur mit Beinen. | Nur Oberkörper; der Frosch duckt sich weg. |
| Pizza | Messer / Käse musste man erst „greifen“; keine Hilfe. | Werkzeug kommt von selbst in die Hand; nach 4 s ohne Fortschritt macht eine durchsichtige Hand den nächsten Schritt vor. |
| Alle Spiele | Liefen endlos weiter (eine Sitzung lief eine ganze Nacht). | Nach 60 s ohne Bewegung des Spielers zurück ins Menü. |
| Eltern | Schwierigkeit war unsichtbar. | Nach Taste 1/2/3 zeigen kurz 1–3 Sterne die Stufe. |

**Noch offen:**

* Die Kind-Erkennung (Kopf/Schulter-Verhältnis) ist mit simulierten Körpern getestet, nicht mit echten Kamerabildern.
  Beim Play-Test schreibt das Log bei jedem Spielerwechsel die Werte aller Personen (`player … scores=`),
  damit lässt sich die Schwelle nachjustieren.
* Beine als Bonus (z. B. Tritte im Kung-Fu, wenn die Füße sichtbar sind) gibt es noch nicht.
* Ob Pizza für 3–4 Jahre wirklich allein machbar ist, muss der Play-Test zeigen.
* Tier-Yoga kann bei fünf schwierigen Tieren bis etwa zwei Minuten dauern.
