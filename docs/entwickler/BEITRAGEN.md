# Better-Bahn Entwicklerleitfaden

## Willkommen Mitwirkende! 🎉

Vielen Dank für Ihr Interesse, zu Better-Bahn beizutragen! Dieser Leitfaden hilft Ihnen beim Einstieg in die Entwicklung, das Testen und das Einreichen von Verbesserungen für das Projekt.

## Projektstruktur

```
Better-Bahn/
├── main.py                 # Python CLI-Tool (Kernlogik)
├── pyproject.toml         # Python-Abhängigkeiten
├── uv.lock               # Abhängigkeits-Lock-Datei
├── flutter-app/          # Mobile App-Quellcode
│   ├── lib/main.dart     # Flutter App Hauptdatei
│   ├── pubspec.yaml      # Flutter-Abhängigkeiten
│   └── android/          # Android Build-Konfiguration
├── testing/              # Test-Utilities
├── assets/              # App-Icons und Screenshots
├── docs/                # Einheitliche deutsche Dokumentation
└── README.md           # Hauptprojektbeschreibung
```

## Einrichtung der Entwicklungsumgebung

### Voraussetzungen

#### Python-Entwicklung
- **Python 3.12+** (prüfen Sie `.python-version`)
- **uv-Paketmanager** (empfohlen) oder pip
- **Git** für Versionskontrolle

#### Flutter-Entwicklung (für mobile App)
- **Flutter SDK 3.8.1+**
- **Android Studio** (für Android-Entwicklung)
- **Xcode** (für iOS-Entwicklung, falls verfügbar)
- **VS Code** oder **IntelliJ** mit Flutter-Plugins

### Setup-Anweisungen

#### 1. Repository klonen
```bash
git clone https://github.com/logic-arts-official/Better-Bahn.git
cd Better-Bahn
```

#### 2. Python-Umgebung einrichten
```bash
# uv installieren
pip install uv

# Abhängigkeiten installieren
export PATH="$HOME/.local/bin:$PATH"
uv sync

# Linting-Tools installieren
pip install ruff
```

#### 3. Flutter-Umgebung einrichten
```bash
cd flutter-app
flutter pub get
flutter doctor  # Auf Probleme prüfen
```

#### 4. Setup testen
```bash
# Python CLI testen
uv run main.py --help

# Flutter-App testen (mit verbundenem Gerät/Emulator)
cd flutter-app
flutter run
```

## Entwicklungsworkflow

### Branch-Management

#### Repository-Branches
- **`main`**: Produktions-Branch für stabile Releases
- **`dev`**: Entwicklungs-Branch für neue Masterdata- und API-Integrationsfunktionen

#### Entwicklungsworkflow
1. **Forken** Sie das Repository auf GitHub
2. **Klonen** Sie Ihren Fork lokal
3. **Basis-Branch wählen**:
   - Verwenden Sie `main` für Bugfixes und allgemeine Verbesserungen
   - Verwenden Sie `dev` für Masterdata-Updates, API-Änderungen und experimentelle Features
4. **Erstellen** Sie einen Feature-Branch: `git checkout -b feature/ihr-feature-name`
5. **Entwickeln** Sie Ihre Änderungen
6. **Testen** Sie gründlich
7. **Committen** Sie mit klaren Nachrichten
8. **Pushen** Sie zu Ihrem Fork
9. **Erstellen** Sie einen Pull Request auf den entsprechenden Basis-Branch

### Coding-Standards

#### Python-Code-Stil
- **PEP 8**-Konformität (verwenden Sie `ruff format`)
- **Type Hints** für Funktionsparameter und Rückgabewerte
- **Docstrings** für alle Funktionen und Klassen
- **Fehlerbehandlung** für alle externen API-Aufrufe
- **BahnCard-Validierung**: Nur BC25_1, BC25_2, BC50_1, BC50_2 sind unterstützt

```python
def get_connection_details(
    from_station_id: str, 
    to_station_id: str, 
    date: str, 
    departure_time: str,
    traveller_payload: list,
    deutschland_ticket: bool
) -> Optional[dict]:
    """
    Verbindungsdetails von der Deutsche Bahn API abrufen.
    
    Args:
        from_station_id: Herkunfts-Bahnhof-ID
        to_station_id: Ziel-Bahnhof-ID
        date: Reisedatum im Format YYYY-MM-DD
        departure_time: Abfahrtszeit im Format HH:MM
        traveller_payload: Reisenden-Konfigurationsdaten
        deutschland_ticket: Ob Deutschland-Ticket verfügbar ist
        
    Returns:
        Verbindungsdaten-Dictionary oder None bei Anfragefehler
    """
    try:
        # Implementierung hier
        pass
    except requests.RequestException as e:
        # Netzwerkfehler sind in sandboxed Umgebungen normal
        logging.error(f"API-Fehler: {e}")
        return None
```

#### Flutter-Code-Stil
- **Dart-Style-Guide**-Konformität
- **flutter_lints** Regeln befolgen
- **Widget-Trennung** - komplexe Widgets in kleinere Komponenten aufteilen
- **DB Design System v3.1.1** mit DB Sans und DB Head Schriftarten verwenden
- **Fehlerbehandlung** - angemessene Behandlung von Netzwerkfehlern

## Validierung und Tests

### Python-Validierung
```bash
# Syntaxprüfung
python -m py_compile main.py

# Code-Linting und -Formatierung
ruff check main.py
ruff format main.py
ruff check main.py --fix

# CLI-Tests
uv run main.py --help
uv run main.py "https://www.bahn.de/buchung/start?vbid=test-vbid" --age 30 --bahncard BC25_1
```

### Flutter-Validierung
```bash
cd flutter-app

# Abhängigkeiten installieren (NIEMALS ABBRECHEN: 2-5 Minuten)
flutter pub get

# Code-Analyse (ca. 30 Sekunden)
flutter analyze

# App für Android kompilieren (NIEMALS ABBRECHEN: 10-15 Minuten)
flutter build apk
```

### Erwartete Ausführungszeiten
- **uv sync**: ~0.03 Sekunden
- **pip install uv**: ~4 Sekunden  
- **pip install ruff**: ~2 Sekunden
- **flutter pub get**: 2-5 Minuten (Timeout auf 10+ Minuten setzen)
- **flutter analyze**: ~30 Sekunden
- **flutter build apk**: 10-15 Minuten (Timeout auf 30+ Minuten setzen)
- **ruff check/format**: ~0.01 Sekunden
- **uv run main.py Befehle**: ~0.15 Sekunden

### Manuelle Test-Checkliste

#### Python CLI-Tests
- [ ] Hilfe-Befehl funktioniert: `uv run main.py --help`
- [ ] Ungültige URL-Behandlung: `uv run main.py "ungueltige-url"`
- [ ] Netzwerkfehler-Behandlung: Test mit ungültigen vbid (erwartet: Netzwerkfehler)
- [ ] BahnCard-Optionen: Alle BC25_1, BC25_2, BC50_1, BC50_2 testen
- [ ] Deutschland-Ticket-Integration
- [ ] Altersparameter-Variationen

#### Flutter App-Tests
- [ ] App kompiliert und läuft auf Android
- [ ] URL-Eingabe-Validierung
- [ ] Einstellungs-Persistenz
- [ ] Netzwerkfehler-Behandlung
- [ ] Ergebnisanzeige-Formatierung
- [ ] Buchungslink-Funktionalität

## Netzwerk-Zugriffsbeschränkungen

**KRITISCH**: Diese Anwendung verwendet Web Scraping von Deutsche Bahn APIs (KEINE offiziellen APIs). 

### Erwartete Verhalten in CI/Sandbox-Umgebungen:
- **Alle Deutsche Bahn API-Aufrufe werden fehlschlagen**
- **Erwartete Fehler**: `NameResolutionError` und `HTTPSConnectionPool` sind normal
- **Anwendungslogik testen ohne Netzwerkzugriff**
- **Fehlerbehandlungspfade validieren**

### API-Endpunkte (für Referenz):
- **Base URL**: `www.bahn.de/web/api/angebote/*`
- **Algorithmus**: O(N²) Zeitkomplexität für N Stationen mittels dynamischer Programmierung

## Sicherheitsüberlegungen

### Von root .md Dateien konsolidierte Sicherheitshinweise:
- **HTTP-Request-Timeouts** implementieren (von SECURITY_AUDIT_REPORT.md)
- **Eingabevalidierung** für alle Benutzereingaben
- **Rate Limiting** respektieren um DB-Server nicht zu überlasten
- **Keine Geheimnisse** in Quellcode committen
- **Lokale Verarbeitung** - alle Analysen geschehen auf dem Gerät des Benutzers

## Häufige Entwicklungsaufgaben

### Neue BahnCard-Typen hinzufügen
```python
def create_traveller_payload(age: int, discount_option: str) -> list:
    """BahnCard-Optionen: BC25_1, BC25_2, BC50_1, BC50_2"""
    discount_mapping = {
        'BC25_1': {'typ': 'BAHNCARD25', 'klasse': 'KLASSE_1'},
        'BC25_2': {'typ': 'BAHNCARD25', 'klasse': 'KLASSE_2'},
        'BC50_1': {'typ': 'BAHNCARD50', 'klasse': 'KLASSE_1'},
        'BC50_2': {'typ': 'BAHNCARD50', 'klasse': 'KLASSE_2'},
    }
    # Implementierung hier
```

### Performance-Verbesserungen
```python
from functools import lru_cache
import asyncio

@lru_cache(maxsize=100)
def cached_connection_details(params_hash: str) -> Optional[dict]:
    """Verbindungsdetails cachen um wiederholte API-Aufrufe zu vermeiden"""
    pass

async def get_all_segments_parallel(segments: list) -> list:
    """Mehrere Segmente gleichzeitig verarbeiten"""
    # Async/await für bessere Performance
    pass
```

## Code-Review-Prozess

### Review-Checkliste
- [ ] Code löst das beabsichtigte Problem
- [ ] Grenzfälle werden behandelt
- [ ] Fehlerzustände werden verwaltet
- [ ] Code ist lesbar und gut dokumentiert
- [ ] Keine Code-Duplikation
- [ ] Tests decken neue Funktionalität ab
- [ ] Keine Regression in bestehenden Features
- [ ] Eingabevalidierung implementiert
- [ ] Netzwerkanfragen sind sicher

### Beitragsrichtlinien

#### Was wir suchen
- **Bug-Fixes** für bestehende Funktionalität
- **Leistungsverbesserungen** und Optimierung
- **Neue Features**, die zu den Projektzielen passen
- **Dokumentations**verbesserungen
- **Testabdeckung**serweiterungen
- **Code-Qualität**sverbesserungen

#### Was wir nicht suchen
- **Große Architekturänderungen** ohne vorherige Diskussion
- **Features**, die die Benutzerprivatsphäre kompromittieren
- **Abhängigkeiten**, die die App-Größe erheblich vergrößern
- **Änderungen**, die bestehende Funktionalität brechen

## Debugging-Tipps

### Python-Debugging
```python
# Debug-Logging hinzufügen
import logging
logging.basicConfig(level=logging.DEBUG)

# API-Antworten für Tests mocken
from unittest.mock import patch
@patch('main.requests.post')
def test_with_mock(mock_post):
    mock_post.return_value.json.return_value = {"test": "data"}
```

### Flutter-Debugging
```dart
// Debug-Prints
debugPrint('Verbindungsanalyse gestartet');

// Flutter-Inspector in VS Code
// Hot Reload für schnelle Iteration verwenden
// Flutter-Logs prüfen: flutter logs
```

### Netzwerk-Debugging
```bash
# API-Endpunkte direkt testen (falls nicht blockiert)
curl -X POST "https://www.bahn.de/web/api/angebote/fahrplan" \
  -H "Content-Type: application/json" \
  -d '{"test": "payload"}'
```

## Release-Prozess

### Versionsverwaltung
- **Semantic Versioning**: MAJOR.MINOR.PATCH
- **Flutter**: `pubspec.yaml`-Version aktualisieren
- **Python**: `pyproject.toml`-Version aktualisieren
- **Git-Tags**: Releases für einfache Verfolgung taggen

### Release-Checkliste
- [ ] Alle Tests bestehen
- [ ] Dokumentation aktualisiert
- [ ] Versionsnummern erhöht
- [ ] Changelog aktualisiert
- [ ] APK gebaut und getestet
- [ ] Release-Notes vorbereitet
- [ ] Git-Tag erstellt

## Hilfe erhalten

### Community-Ressourcen
- **GitHub Issues**: Bugs melden und Features anfordern
- **GitHub Discussions**: Fragen stellen und Ideen teilen
- **Code Review**: Feedback zu Ihren Beiträgen erhalten

### Häufige Probleme
1. **"uv not found"**: `pip install uv` ausführen
2. **"Flutter not found"**: Flutter SDK Installation erforderlich
3. **Netzwerkfehler**: In sandboxed Umgebungen erwartet - Fehlerbehandlung testen
4. **Linting-Fehler**: `ruff format main.py && ruff check main.py --fix` ausführen
5. **Flutter Build-Fehler**: Ordnungsgemäße Android SDK-Einrichtung sicherstellen

Vielen Dank für Ihren Beitrag zu Better-Bahn! 🚄💰