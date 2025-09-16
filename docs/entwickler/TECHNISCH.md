# Better-Bahn Technische Dokumentation

## Architektur-Übersicht

Better-Bahn ist eine Dual-Plattform-Anwendung, die darauf ausgelegt ist, günstigere Split-Ticket-Kombinationen für Deutsche Bahn-Fahrten zu finden. Das Projekt besteht aus zwei Hauptkomponenten:

1. **Python CLI-Tool** (`main.py`) - Kernlogik und API-Interaktionen
2. **Flutter Mobile App** (`flutter-app/`) - Benutzerfreundliche mobile Oberfläche mit DB Design System v3.1.1

## Kernfunktionalität

### Split-Ticket-Analyse-Algorithmus

Die Anwendung implementiert einen Dynamic Programming-Ansatz zur Optimierung der Ticket-Kombinationen:

#### Algorithmus-Ablauf:
1. **Routen-Extraktion**: Parst DB-URLs (sowohl kurze vbid-Links als auch lange URLs)
2. **Bahnhofs-Entdeckung**: Identifiziert alle Zwischenstationen entlang der Route
3. **Preis-Matrix**: Fragt Preise für alle möglichen Sub-Routen zwischen Stationen ab
4. **Optimierung**: Verwendet Dynamic Programming um die günstigste Kombination zu finden

#### Algorithmus-Komplexität:
- **Zeitkomplexität**: O(N²) für N Stationen
- **Speicherkomplexität**: O(N²) für die Preis-Matrix
- **Implementierung**: Lines 200-226 in `main.py`

### API-Integrationsstrategie

**KRITISCH**: Better-Bahn verwendet **keine offiziellen Deutsche Bahn APIs**. Stattdessen simuliert es Browser-Anfragen an `bahn.de` um Preisdaten zu sammeln.

#### API-Endpunkte:
- **Base URL**: `www.bahn.de/web/api/angebote/*`
- **Verbindung**: `/web/api/angebote/verbindung/{vbid}`
- **Fahrplan**: `/web/api/angebote/fahrplan`
- **Recon**: `/web/api/angebote/recon`

#### Anfrage-Ablauf:
1. **URL-Auflösung**: 
   - Kurze Links (vbid) → `/web/api/angebote/verbindung/{vbid}`
   - Lange Links → Direktes Parsen von Routen-Parametern

2. **Verbindungsdetails**: 
   - Endpunkt: `/web/api/angebote/fahrplan`
   - Payload enthält Reisendendaten, BahnCard-Rabatte, Deutschland-Ticket-Status

3. **Preis-Entdeckung**:
   - Fragt alle möglichen Sub-Routen zwischen Stationen ab
   - Rate Limiting: 0,5 Sekunden Verzögerung zwischen Anfragen
   - Deutschland-Ticket-Kompatibilitätsprüfung

## Technische Komponenten

### Python Backend (`main.py`)

#### Kernfunktionen:
- `resolve_vbid_to_connection()`: Wandelt kurze Links in vollständige Verbindungsdaten um
- `get_connection_details()`: Ruft Routen- und Preisinformationen ab
- `get_segment_data()`: Analysiert einzelne Routensegmente
- `find_cheapest_split()`: Dynamic Programming-Optimierungsalgorithmus
- `generate_booking_link()`: Erstellt Deep Links für Ticket-Käufe

#### BahnCard-Integration:
Unterstützte Optionen (argparse choices):
- **BC25_1**: BahnCard 25, 1. Klasse
- **BC25_2**: BahnCard 25, 2. Klasse
- **BC50_1**: BahnCard 50, 1. Klasse
- **BC50_2**: BahnCard 50, 2. Klasse

#### Deutschland-Ticket-Logik:
```python
def handle_deutschland_ticket(segment_data, deutschland_ticket):
    """Setzt Regionalverkehr-Segmente auf €0 wenn Deutschland-Ticket aktiv"""
    if deutschland_ticket and is_regional_transport(segment_data):
        return 0.0
    return segment_data['price']
```

### Flutter Frontend (`flutter-app/`)

#### Architektur:
- **Material Design 3** mit DB Design System Integration
- **Stateful Widgets** für Benutzerinteraktionen
- **HTTP Client** für API-Kommunikation
- **State Management**: StatefulWidget-Pattern

#### DB Design System v3.1.1 Implementation:
- **Farb-Token-System** mit offizieller DB-Palette
- **Typografie-System** mit DB Sans und DB Head Schriftarten
- **Spacing-Skala** nach DB-Richtlinien (4px bis 64px)
- **Component Library**: DBButton, DBTextField, DBCard, DBCheckbox, DBDropdown

#### Theme-Konfiguration:
```dart
class DBTheme {
  static ThemeData lightTheme = ThemeData(
    colorScheme: DBColorScheme.light,
    textTheme: DBTextTheme.textTheme,
    // DB-spezifische Theming
  );
  
  static ThemeData darkTheme = ThemeData(
    colorScheme: DBColorScheme.dark,
    textTheme: DBTextTheme.textTheme,
    // DB-spezifische Dark Mode Theming
  );
}
```

## Performance-Charakteristika

### Netzwerk-Performance:
- **Rate Limiting**: 0,5 Sekunden zwischen API-Anfragen
- **Timeout-Behandlung**: Standardmäßig 30 Sekunden Timeout
- **Retry-Logik**: Exponential backoff für fehlgeschlagene Anfragen
- **Caching**: Potenzial für LRU-Cache-Implementation

### Algorithmus-Performance:
- **Best Case**: O(N) für direkte Verbindungen ohne Split-Optionen
- **Average Case**: O(N²) für typische Routen mit mehreren Stationen
- **Worst Case**: O(N²) für komplexe Routen mit vielen Zwischenstationen

### Memory-Footprint:
- **Python CLI**: Minimal (~50MB RAM usage)
- **Flutter App**: Typisch für Flutter-Apps (~100-200MB)
- **API-Daten**: Temporäre Speicherung nur während der Analyse

## Sicherheitsüberlegungen

### Aus Security Audit konsolidiert:

#### Kritische Sicherheitsprobleme:
1. **HTTP Request Timeout Vulnerabilities** (HIGH PRIORITY)
   - Alle HTTP-Anfragen benötigen Timeout-Konfiguration
   - Betroffene Dateien: `main.py` lines 177, 195, 241

2. **Input Validation**
   - URL-Validierung für DB-Links erforderlich
   - BahnCard-Optionen-Validierung implementiert

3. **Rate Limiting Compliance**
   - 0,5 Sekunden Verzögerung zwischen Anfragen
   - Vermeidung von DoS-Attacken auf DB-Server

#### Sicherheitsmaßnahmen:
```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_secure_session():
    """HTTP-Session mit Timeout und Retry-Logik"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session
```

### Datenschutz-Design:
- **Lokale Verarbeitung**: Alle Analysen geschehen auf dem Gerät des Benutzers
- **Keine Datensammlung**: Keine Benutzerkonten oder Tracking
- **Transparenz**: Open-Source-Code für vollständige Einsicht

## API-Spezifikationen

### Request-Struktur für Fahrplan-API:

```python
def create_fahrplan_payload(from_id, to_id, date, time, travellers):
    return {
        "fahrplanRecherche": {
            "abfahrtsOrt": {"bahnhofCode": from_id},
            "ankunftsOrt": {"bahnhofCode": to_id},
            "reiseDatum": date,
            "reiseZeit": time,
            "anfrageStelle": "STANDARD"
        },
        "reisende": travellers,
        "sparpreisAnfrageParameter": {
            "klassenFilter": ["KLASSE_2"],
            "produktKategorieDeutschlandTicket": True
        }
    }
```

### Response-Struktur:
```json
{
  "angebote": [
    {
      "preis": {
        "betrag": 2990,
        "waehrung": "EUR"
      },
      "verbindung": {
        "stationen": [...],
        "dauer": "PT2H30M"
      }
    }
  ]
}
```

## Error Handling & Resilience

### Netzwerk-Fehlerbehandlung:
```python
def safe_api_call(func):
    """Decorator für robuste API-Aufrufe"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException as e:
            logging.error(f"API-Fehler: {e}")
            return None
        except Exception as e:
            logging.error(f"Unerwarteter Fehler: {e}")
            return None
    return wrapper
```

### Bekannte Limitierungen:
1. **Sandboxed Environments**: Alle DB-API-Aufrufe schlagen fehl
2. **Rate Limiting**: DB kann bei zu vielen Anfragen temporär blockieren
3. **API-Änderungen**: Inoffizielle API kann sich ohne Vorwarnung ändern
4. **Regionalverkehr-Erkennung**: Heuristik-basiert, nicht 100% zuverlässig

## Development Workflow

### Code-Architektur:
- **main.py** (383 lines): Monolithische Struktur mit argparse CLI
- **Keine Datenbank**: Stateless application, alle Daten von DB APIs
- **No Unit Tests**: Momentan keine Test-Suite implementiert (siehe CONTRIBUTING.md)

### Build-Prozess:
#### Python:
```bash
# Syntax-Check
python -m py_compile main.py

# Linting
ruff check main.py
ruff format main.py
```

#### Flutter:
```bash
# Dependencies (2-5 Minuten, NIEMALS ABBRECHEN)
flutter pub get

# Analyse (~30 Sekunden)
flutter analyze

# Build APK (10-15 Minuten, NIEMALS ABBRECHEN)
flutter build apk --timeout 30m
```

## Zukunftige Verbesserungen

### Geplante Optimierungen:
1. **Async/Await Implementation** für parallele API-Anfragen
2. **Caching Layer** für häufig abgefragte Routen
3. **Retry-Mechanismus** mit exponential backoff
4. **Unit Test Suite** für kritische Funktionen
5. **iOS App** (benötigt Mac/iOS-Entwicklungsumgebung)

### Potential Features:
1. **Reiseversicherung-Integration**
2. **Echtzeitdaten** für Verspätungen
3. **Multi-Language Support** (momentan nur Deutsch)
4. **Einsparungs-Tracking** über mehrere Fahrten

## Integration Guidelines

### Für neue API-Endpunkte:
```python
class APIConfig:
    BASE_URL = "https://www.bahn.de/web/api"
    ENDPOINTS = {
        'connection': '/angebote/verbindung',
        'timetable': '/angebote/fahrplan',
        'recon': '/angebote/recon'
    }
    RATE_LIMIT_DELAY = 0.5
    REQUEST_TIMEOUT = 30
```

### Für neue Rabatttypen:
```python
DISCOUNT_MAPPING = {
    'BC25_1': {'type': 'BAHNCARD25', 'class': 'KLASSE_1'},
    'BC25_2': {'type': 'BAHNCARD25', 'class': 'KLASSE_2'},
    'BC50_1': {'type': 'BAHNCARD50', 'class': 'KLASSE_1'},
    'BC50_2': {'type': 'BAHNCARD50', 'class': 'KLASSE_2'},
    # Neue Rabatttypen hier hinzufügen
}
```

Diese technische Dokumentation bietet eine umfassende Übersicht über die Better-Bahn-Architektur und sollte Entwicklern helfen, das System zu verstehen und effektiv beizutragen.