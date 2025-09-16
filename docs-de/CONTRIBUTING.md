# Better-Bahn Entwickler-Beitragsleitfaden

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
├── docs/                # Dokumentation (technisch, Benutzerhandbücher)
├── docs-de/             # Deutsche Dokumentation
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
git clone https://github.com/gkrost/Better-Bahn.git
cd Better-Bahn
```

#### 2. Python-Umgebung einrichten
```bash
# Mit uv (empfohlen)
uv sync

# Oder mit pip
pip install -r requirements.txt  # falls requirements.txt existiert
pip install requests>=2.32.4
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
python main.py --help

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

#### Zweck des Dev-Branches
Der `dev`-Branch dient als Integrationspunkt für:
- **Masterdata-Updates**: Änderungen an Stationsdaten, Preisstrukturen oder Deutsche Bahn Datenformaten
- **API-Integration-Verbesserungen**: Updates für Deutsche Bahn API-Interaktionen, neue Endpunkte oder Request-Behandlung
- **Experimentelle Features**: Neue Funktionalitäten, die umfangreiches Testen vor dem Produktions-Release erfordern

Dieser Branch ermöglicht kollaborative Entwicklung und einfachere Review komplexer Änderungen, bevor sie in den stabilen `main`-Branch gemergt werden.

### Coding-Standards

#### Python-Code-Stil
- **PEP 8**-Konformität
- **Type Hints** für Funktionsparameter und Rückgabewerte
- **Docstrings** für alle Funktionen und Klassen
- **Fehlerbehandlung** für alle externen API-Aufrufe
- **Logging** anstatt print-Anweisungen wo angebracht

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
        
    Raises:
        requests.RequestException: Bei API-Anfragefehler
    """
    # Implementierung hier
```

#### Flutter-Code-Stil
- **Dart-Style-Guide**-Konformität
- **Widget-Trennung** - komplexe Widgets in kleinere Komponenten aufteilen
- **State Management** - angemessene State-Management-Patterns verwenden
- **Fehlerbehandlung** - angemessene Behandlung von Netzwerkfehlern
- **Barrierefreiheit** - ordnungsgemäße Labels und semantische Widgets

```dart
class ConnectionAnalysisWidget extends StatefulWidget {
  const ConnectionAnalysisWidget({
    Key? key,
    required this.url,
    required this.settings,
  }) : super(key: key);

  final String url;
  final UserSettings settings;

  @override
  State<ConnectionAnalysisWidget> createState() => 
      _ConnectionAnalysisWidgetState();
}
```

## Test-Richtlinien

### Python-Tests

#### Unit-Tests (zu implementieren)
```python
# tests/test_main.py
import unittest
from unittest.mock import patch, MagicMock
from main import get_connection_details, create_traveller_payload

class TestConnectionDetails(unittest.TestCase):
    @patch('main.requests.post')
    def test_get_connection_details_success(self, mock_post):
        # Test-Implementierung
        pass
    
    def test_create_traveller_payload_bc25(self):
        result = create_traveller_payload(30, 'BC25_2')
        expected = [{"typ": "ERWACHSENER", ...}]
        self.assertEqual(result, expected)
```

#### Integrationstests
```python
# Tests mit echten API-Aufrufen (sparsam verwenden)
def test_real_api_integration():
    # Nur für kritischen Pfad-Tests
    pass
```

### Flutter-Tests

#### Widget-Tests
```dart
// test/widget_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:better_bahn/main.dart';

void main() {
  testWidgets('App lädt korrekt', (WidgetTester tester) async {
    await tester.pumpWidget(const SplitTicketApp());
    expect(find.text('Better Bahn'), findsOneWidget);
  });
}
```

### Manuelle Test-Checkliste

#### Python CLI-Tests
- [ ] Hilfe-Befehl funktioniert: `python main.py --help`
- [ ] Ungültige URL-Behandlung: `python main.py "ungueltige-url"`
- [ ] Netzwerkfehler-Behandlung: Test im Flugmodus
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

## Häufige Entwicklungsaufgaben

### Neue Features hinzufügen

#### 1. API-Endpunkt-Änderungen
```python
# config.py (erstellen falls nötig)
class APIConfig:
    BASE_URL = "https://www.bahn.de/web/api"
    ENDPOINTS = {
        'connection': '/angebote/verbindung',
        'timetable': '/angebote/fahrplan',
        'recon': '/angebote/recon'
    }
    RATE_LIMIT_DELAY = 0.5
```

#### 2. Neue Rabatttypen
```python
def create_traveller_payload(age: int, discount_option: str) -> list:
    """Erweitert um neue Rabatttypen zu unterstützen"""
    # Neue Rabatt-Mappings hier hinzufügen
    pass
```

#### 3. Verbesserte Fehlerbehandlung
```python
import logging
from typing import Optional
from dataclasses import dataclass

@dataclass
class APIError:
    code: str
    message: str
    retryable: bool

def safe_api_call(func):
    """Decorator für robuste API-Aufrufe mit Retry-Logik"""
    def wrapper(*args, **kwargs):
        # Implementierung mit exponential backoff
        pass
    return wrapper
```

### Leistungsverbesserungen

#### 1. Caching-Implementierung
```python
from functools import lru_cache
import hashlib
import json

@lru_cache(maxsize=100)
def cached_connection_details(params_hash: str) -> Optional[dict]:
    """Verbindungsdetails cachen um wiederholte API-Aufrufe zu vermeiden"""
    pass
```

#### 2. Parallele Verarbeitung
```python
import asyncio
import aiohttp

async def get_all_segments_parallel(segments: list) -> list:
    """Mehrere Segmente gleichzeitig verarbeiten"""
    async with aiohttp.ClientSession() as session:
        tasks = [get_segment_data_async(session, segment) for segment in segments]
        return await asyncio.gather(*tasks, return_exceptions=True)
```

## Code-Review-Prozess

### Review-Checkliste

#### Funktionalität
- [ ] Code löst das beabsichtigte Problem
- [ ] Grenzfälle werden behandelt
- [ ] Fehlerzustände werden verwaltet
- [ ] Leistung ist akzeptabel

#### Code-Qualität
- [ ] Code ist lesbar und gut dokumentiert
- [ ] Funktionen haben angemessene Größe
- [ ] Variablennamen sind beschreibend
- [ ] Keine Code-Duplikation

#### Tests
- [ ] Unit-Tests decken neue Funktionalität ab
- [ ] Integrationstests bestehen
- [ ] Manuelle Tests abgeschlossen
- [ ] Keine Regression in bestehenden Features

#### Sicherheit
- [ ] Eingabevalidierung implementiert
- [ ] Keine hartcodierten Geheimnisse
- [ ] Netzwerkanfragen sind sicher
- [ ] Fehlermeldungen geben keine sensiblen Infos preis

### Review-Richtlinien

#### Für Reviewer
1. **Konstruktiv sein**: Spezifisches, umsetzbares Feedback geben
2. **Fragen stellen**: Bei Unklarheiten um Klärung bitten
3. **Verbesserungen vorschlagen**: Bessere Ansätze anbieten wenn möglich
4. **Änderungen testen**: Code beim Review tatsächlich ausführen

#### Für Mitwirkende
1. **Kleine PRs**: Änderungen fokussiert und reviewbar halten
2. **Klare Beschreibungen**: Was und Warum in PR-Beschreibung erklären
3. **Feedback addressieren**: Auf alle Review-Kommentare antworten
4. **Dokumentation aktualisieren**: Docs mit Code-Änderungen synchron halten

## Debugging-Tipps

### Python-Debugging
```python
# Debug-Logging hinzufügen
import logging
logging.basicConfig(level=logging.DEBUG)

# pdb für interaktives Debugging verwenden
import pdb; pdb.set_trace()

# API-Antworten für Tests mocken
@patch('main.requests.post')
def test_with_mock(mock_post):
    mock_post.return_value.json.return_value = {"test": "data"}
    # Ihre Funktion testen
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
# HTTP-Anfragen überwachen
mitmproxy  # Anfragen abfangen und inspizieren

# API-Endpunkte direkt testen
curl -X POST "https://www.bahn.de/web/api/angebote/fahrplan" \
  -H "Content-Type: application/json" \
  -d '{"test": "payload"}'
```

## Beitragsrichtlinien

### Was wir suchen
- **Bug-Fixes** für bestehende Funktionalität
- **Leistungsverbesserungen** und Optimierung
- **Neue Features**, die zu den Projektzielen passen
- **Dokumentations**verbesserungen und Übersetzungen
- **Testabdeckung**serweiterungen
- **Code-Qualität**sverbesserungen

### Was wir nicht suchen
- **Große Architekturänderungen** ohne vorherige Diskussion
- **Features**, die die Benutzerprivatsphäre kompromittieren
- **Abhängigkeiten**, die die App-Größe erheblich vergrößern
- **Änderungen**, die bestehende Funktionalität brechen

### Ihren PR angenommen bekommen
1. **Zuerst diskutieren**: Für große Änderungen zuerst ein Issue öffnen
2. **Richtlinien befolgen**: Coding-Standards und Test-Anforderungen einhalten
3. **Änderungen dokumentieren**: Relevante Dokumentation aktualisieren
4. **Gründlich testen**: Sicherstellen, dass Änderungen wie erwartet funktionieren
5. **Geduldig sein**: Zeit für Review und Iteration einplanen

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

### Mentoring
Neue Mitwirkende sind willkommen! Zögern Sie nicht:
- Fragen in Issues oder Discussions zu stellen
- Code Review zum Lernen anzufordern
- Mit kleinen, fokussierten Beiträgen zu beginnen
- Der Community beizutreten und anderen zu helfen

## Anerkennung

Mitwirkende werden anerkannt durch:
- **GitHub Contributors**-Liste
- **Release Notes**-Danksagungen
- **Besondere Erwähnungen** in der Dokumentation
- **Community-Reputation**saufbau

Vielen Dank für Ihren Beitrag zu Better-Bahn! Ihre Bemühungen helfen Tausenden von Reisenden, Geld bei ihren Fahrten zu sparen. 🚄💰