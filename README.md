# Posting Programm (Gaming Penguins)

Lokales Desktop-Tool zur Erstellung von Social-Media-Posts als `.jpg`.

## Features
- Auswahl des Spiels: Counter Strike, Rainbow Six, Rocket League, Call of Duty
- Auswahl der Post-Version: Matchday, Victory, Defeat, Liga-Teilnahme, Spieler-Welcome
- Heim-Logo per Auswahl aus lokalen Presets
- Gegner-Logo per Upload oder URL
- Liga per Auswahl, Upload oder URL
- BO1 / BO3 / BO5 Map-Logik mit automatischer Slot-Anzeige
- Score pro Map im Format `00:00`
- Gewinner-Overlay pro Map (Heim = Grün, Gegner = Rot)
- Live-Vorschau mit Vordergrund-/Template-Layout
- Export als JPG

## Installation
1. Python 3.10+ installieren
2. Im Projektordner installieren:
   ```bash
   pip install -r requirements.txt
   ```

## Start
```bash
python app.py
```

## Standalone Build Fuer GitHub
Damit Nutzer nur einen Download brauchen, kann das Tool als eigenstaendige Windows-EXE gebaut werden. Alle Assets werden dabei direkt in die EXE eingebettet.

### Lokal bauen
Im Projektordner:
```bat
build_release.bat
```

Danach liegen die fertigen Dateien hier:
- `dist/GamingPenguinsPostingTool.exe`
- `dist/GamingPenguinsPostingTool-windows-x64.zip`

Nutzer muessen dann nur das ZIP von GitHub Releases herunterladen, entpacken und die EXE starten.

### GitHub Actions Release
Im Repo ist ein Workflow unter `.github/workflows/build-release.yml` enthalten.

Er kann auf zwei Arten genutzt werden:
1. Manuell ueber `workflow_dispatch`
2. Automatisch bei Tags wie `v1.0.0`

Bei einem Tag-Build wird automatisch ein GitHub Release Asset erzeugt:
- `GamingPenguinsPostingTool-windows-x64.zip`

### Wichtige Hinweise Fuer Die EXE
- `app_settings.json` wird neben der EXE gespeichert
- `startup_error.log` wird im Fehlerfall ebenfalls neben der EXE geschrieben
- Es muessen keine zusaetzlichen Asset-Ordner mit ausgeliefert werden

## Struktur für Vorlagen
- Spiel- und Post-Strukturen: `templates.py`
- Hintergrundbilder (optional): `assets/backgrounds/`
- Vordergründe: `assets/overlays/`
- Heim-Logos: `assets/home_logos/`
- Liga-Bilder: `assets/leagues/`
- Map-Bilder: `assets/maps/<spiel_slug>/`
- Schriftarten: `assets/fonts/`

Details zur Dateibenennung stehen in `assets/ASSET_GUIDE.md`.

## Hinweise
- Das Tool läuft lokal als Desktop-App mit `tkinter`.
- Die finalen Bilder werden in der Größe 1080x1350 exportiert.
