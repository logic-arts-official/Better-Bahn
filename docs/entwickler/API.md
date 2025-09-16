# Better-Bahn API-Dokumentation

## Übersicht

Dieses Dokument beschreibt die inoffiziellen Deutsche Bahn API-Endpunkte, die Better-Bahn verwendet, um Preis- und Verbindungsinformationen zu sammeln. Diese Endpunkte wurden durch Reverse Engineering von Browser-Interaktionen mit bahn.de ermittelt.

⚠️ **Wichtig**: Dies sind **inoffizielle APIs**, die sich ohne Vorankündigung ändern können. Die Endpunkte werden nicht offiziell von der Deutschen Bahn unterstützt.

## Basis-Konfiguration

### API-Basis-URL
```
https://www.bahn.de/web/api
```

### Gemeinsame Header
```http
User-Agent: Mozilla/5.0 (kompatible Browser-Zeichenkette)
Accept: application/json
Content-Type: application/json; charset=UTF-8
Accept-Language: de
```

### Rate Limiting
- **Aktuelle Implementierung**: 0,5 Sekunden Verzögerung zwischen Anfragen
- **Empfehlung**: Respektieren Sie Server-Ressourcen, vermeiden Sie aggressive Abfragen
- **Risiko**: Zu viele Anfragen können zu IP-Blockierung führen

## API-Endpunkte

### 1. vbid-Auflösung

**Zweck**: Kurze vbid-Links in vollständige Verbindungsdetails umwandeln

#### Endpunkt
```http
GET /angebote/verbindung/{vbid}
```

#### Parameter
- `{vbid}`: Die vbid-Kennung aus kurzen Links (z.B. `9dd9db26-4ffc-411c-b79c-e82bf5338989`)

#### Beispiel-Anfrage
```http
GET https://www.bahn.de/web/api/angebote/verbindung/9dd9db26-4ffc-411c-b79c-e82bf5338989
Accept: application/json
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)
```

#### Antwort-Struktur
```json
{
  "verbindung": {
    "id": "vbid-string",
    "abfahrtsOrt": {
      "bahnhofCode": "8011160",
      "name": "Berlin Hbf"
    },
    "ankunftsOrt": {
      "bahnhofCode": "8000261",
      "name": "München Hbf"
    },
    "abfahrtsDatum": "2024-03-15",
    "abfahrtsZeit": "08:30",
    "ankunftsDatum": "2024-03-15",
    "ankunftsZeit": "13:30"
  }
}
```

#### Fehlerbehandlung
```json
{
  "error": {
    "code": "VBID_NOT_FOUND",
    "message": "Die angegebene Verbindung wurde nicht gefunden"
  }
}
```

### 2. Fahrplan-Abfrage

**Zweck**: Verbindungsdetails und Preise für spezifische Routen abrufen

#### Endpunkt
```http
POST /angebote/fahrplan
```

#### Request-Payload
```json
{
  "fahrplanRecherche": {
    "abfahrtsOrt": {
      "bahnhofCode": "8011160"
    },
    "ankunftsOrt": {
      "bahnhofCode": "8000261"
    },
    "reiseDatum": "2024-03-15",
    "reiseZeit": "08:30",
    "anfrageStelle": "STANDARD"
  },
  "reisende": [
    {
      "typ": "ERWACHSENER",
      "alter": 30,
      "ermaessigungen": [
        {
          "art": "BAHNCARD25",
          "klasse": "KLASSE_2"
        }
      ]
    }
  ],
  "sparpreisAnfrageParameter": {
    "klassenFilter": ["KLASSE_2"],
    "produktKategorieDeutschlandTicket": true
  }
}
```

#### Antwort-Struktur
```json
{
  "angebote": [
    {
      "preis": {
        "betrag": 2990,
        "waehrung": "EUR",
        "endpreis": 29.90
      },
      "verbindung": {
        "dauer": "PT5H00M",
        "umstiege": 1,
        "teilverbindungen": [
          {
            "abfahrtsOrt": {
              "bahnhofCode": "8011160",
              "name": "Berlin Hbf"
            },
            "ankunftsOrt": {
              "bahnhofCode": "8000261",
              "name": "München Hbf"
            },
            "abfahrtsZeit": "08:30",
            "ankunftsZeit": "13:30",
            "verkehrsmittel": {
              "typ": "ICE",
              "nummer": "525"
            }
          }
        ]
      },
      "buchungsLink": {
        "url": "https://www.bahn.de/buchung/...",
        "gueltigkeitsdauer": "PT15M"
      }
    }
  ],
  "deutschlandTicketKompatibel": false
}
```

### 3. Recon-API (Route Reconstruction)

**Zweck**: Detaillierte Routeninformationen und Zwischenstationen ermitteln

#### Endpunkt
```http
POST /angebote/recon
```

#### Request-Payload
```json
{
  "recon": "recon-string-from-vbid-response",
  "anfrageStelle": "STANDARD"
}
```

#### Antwort-Struktur
```json
{
  "verbindung": {
    "teilverbindungen": [
      {
        "abfahrtsOrt": {"bahnhofCode": "8011160", "name": "Berlin Hbf"},
        "ankunftsOrt": {"bahnhofCode": "8000152", "name": "Hamburg Hbf"},
        "zwischenstationen": [
          {"bahnhofCode": "8010255", "name": "Neustrelitz Hbf"},
          {"bahnhofCode": "8000237", "name": "Ludwigslust"}
        ]
      }
    ]
  }
}
```

## Parameter-Spezifikationen

### Reisenden-Konfiguration

#### Erwachsener mit BahnCard 25 (2. Klasse)
```json
{
  "typ": "ERWACHSENER",
  "alter": 30,
  "ermaessigungen": [
    {
      "art": "BAHNCARD25",
      "klasse": "KLASSE_2"
    }
  ]
}
```

#### BahnCard-Typen
- `BAHNCARD25`: BahnCard 25 (25% Rabatt)
- `BAHNCARD50`: BahnCard 50 (50% Rabatt)

#### Klassen-Optionen
- `KLASSE_1`: Erste Klasse
- `KLASSE_2`: Zweite Klasse

#### Deutschland-Ticket-Integration
```json
{
  "sparpreisAnfrageParameter": {
    "produktKategorieDeutschlandTicket": true,
    "klassenFilter": ["KLASSE_2"]
  }
}
```

### Datum- und Zeit-Formate

#### Datumsformat
```
YYYY-MM-DD (ISO 8601)
Beispiel: "2024-03-15"
```

#### Zeitformat
```
HH:MM (24-Stunden-Format)
Beispiel: "08:30"
```

#### Dauer-Format (ISO 8601)
```
PT{H}H{M}M
Beispiel: "PT5H30M" (5 Stunden, 30 Minuten)
```

## Fehlerbehandlung

### Häufige Fehlercodes

#### HTTP-Statuscodes
- `400 Bad Request`: Ungültige Parameter
- `404 Not Found`: Verbindung/vbid nicht gefunden
- `429 Too Many Requests`: Rate Limit überschritten
- `500 Internal Server Error`: Server-Fehler

#### Anwendungs-Fehlercodes
```json
{
  "error": {
    "code": "KEINE_VERBINDUNG_GEFUNDEN",
    "message": "Für die angegebenen Parameter wurde keine Verbindung gefunden"
  }
}
```

```json
{
  "error": {
    "code": "UNGUELTIGE_STATION",
    "message": "Die angegebene Station existiert nicht"
  }
}
```

### Retry-Strategie

#### Empfohlene Implementierung
```python
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_resilient_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "OPTIONS", "POST"],
        backoff_factor=1
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def safe_api_call(session, url, payload=None, timeout=30):
    try:
        if payload:
            response = session.post(url, json=payload, timeout=timeout)
        else:
            response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API-Fehler: {e}")
        return None
    finally:
        time.sleep(0.5)  # Rate limiting
```

## Implementierungs-Beispiele

### Vollständiger Split-Ticket-Workflow

```python
def analyze_split_tickets(vbid, age=30, bahncard="BC25_2", deutschland_ticket=False):
    session = create_resilient_session()
    
    # 1. vbid auflösen
    vbid_data = safe_api_call(
        session, 
        f"https://www.bahn.de/web/api/angebote/verbindung/{vbid}"
    )
    
    if not vbid_data:
        return None
    
    # 2. Fahrplan-Details abrufen
    fahrplan_payload = create_fahrplan_payload(
        vbid_data['verbindung']['abfahrtsOrt']['bahnhofCode'],
        vbid_data['verbindung']['ankunftsOrt']['bahnhofCode'],
        vbid_data['verbindung']['abfahrtsDatum'],
        vbid_data['verbindung']['abfahrtsZeit'],
        age, bahncard, deutschland_ticket
    )
    
    connection_data = safe_api_call(
        session,
        "https://www.bahn.de/web/api/angebote/fahrplan",
        fahrplan_payload
    )
    
    # 3. Segmente analysieren
    segments = extract_route_segments(connection_data)
    
    # 4. Split-Ticket-Optimierung
    cheapest_combination = find_cheapest_split(segments)
    
    return cheapest_combination
```

### URL-Parsing für lange Links

```python
def parse_long_url(url):
    """
    Parst lange bahn.de URLs um Routing-Parameter zu extrahieren
    
    Beispiel URL:
    https://www.bahn.de/buchung/fahrplan/suche#sts=true&so=Berlin&zo=Munich&soid=8011160&zoid=8000261&hd=2024-03-15T08:30
    """
    from urllib.parse import urlparse, parse_qs
    
    parsed_url = urlparse(url)
    
    if '#' in url:
        # Fragment-basierte Parameter
        fragment_params = dict(param.split('=') for param in parsed_url.fragment.split('&'))
        return {
            'source_id': fragment_params.get('soid'),
            'destination_id': fragment_params.get('zoid'),
            'departure_date': fragment_params.get('hd', '').split('T')[0],
            'departure_time': fragment_params.get('hd', '').split('T')[1] if 'T' in fragment_params.get('hd', '') else ''
        }
    else:
        # Query-basierte Parameter
        query_params = parse_qs(parsed_url.query)
        return {
            'source_id': query_params.get('soid', [None])[0],
            'destination_id': query_params.get('zoid', [None])[0],
            'departure_date': query_params.get('hd', [None])[0]
        }
```

## Einschränkungen und Überlegungen

### Technische Einschränkungen
1. **Inoffizielle API**: Kann sich ohne Vorwarnung ändern
2. **Rate Limiting**: Begrenzt Anzahl der parallel verarbeitbaren Routen
3. **Keine Echtzeit-Garantie**: Preise können zwischen Abfrage und Buchung ändern
4. **Regional-Transport-Erkennung**: Heuristik-basiert, nicht 100% zuverlässig

### Rechtliche Überlegungen
1. **Terms of Service**: Verwendung verstößt möglicherweise gegen bahn.de ToS
2. **Data Scraping**: Rechtliche Grauzone in Deutschland
3. **Commercial Use**: Nicht für kommerzielle Nutzung ohne Klärung empfohlen

### Praktische Limitierungen
1. **Netzwerk-Abhängigkeit**: Funktioniert nicht in sandboxed Umgebungen
2. **IP-Blocking**: Risiko bei übermäßiger Nutzung
3. **Server-Verfügbarkeit**: Abhängig von bahn.de Verfügbarkeit
4. **Maintenance-Windows**: DB-APIs können während Wartungsarbeiten nicht verfügbar sein

## Best Practices

### Performance-Optimierung
1. **Connection Pooling**: Wiederverwendung von HTTP-Connections
2. **Caching**: Zwischenspeichern häufig abgefragter Routen
3. **Parallel Processing**: Vorsichtige Parallelisierung mit Rate Limiting
4. **Timeout Configuration**: Angemessene Timeouts für alle Anfragen

### Monitoring und Logging
```python
import logging

# API-Monitoring Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_api_call(url, status_code, response_time):
    logger.info(f"API Call: {url} - Status: {status_code} - Time: {response_time}ms")

def log_api_error(url, error):
    logger.error(f"API Error: {url} - Error: {str(error)}")
```

Diese API-Dokumentation sollte Entwicklern helfen, die Better-Bahn-Integration zu verstehen und zu erweitern, während sie die Grenzen und Risiken der Verwendung inoffizieller APIs berücksichtigen.