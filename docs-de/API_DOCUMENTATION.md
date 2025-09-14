# Better-Bahn API-Dokumentation

## Übersicht

Dieses Dokument beschreibt die inoffiziellen Deutsche Bahn API-Endpunkte, die Better-Bahn verwendet, um Preis- und Verbindungsinformationen zu sammeln. Diese Endpunkte wurden durch Reverse Engineering von Browser-Interaktionen mit bahn.de ermittelt.

⚠️ **Wichtig**: Dies sind inoffizielle APIs, die sich ohne Vorankündigung ändern können. Die Endpunkte werden nicht offiziell von der Deutschen Bahn unterstützt.

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
- `{vbid}`: Die vbid-Kennung aus kurzen Links

#### Beispiel-Anfrage
```http
GET https://www.bahn.de/web/api/angebote/verbindung/9dd9db26-4ffc-411c-b79c-e82bf5338989
Accept: application/json
User-Agent: Mozilla/5.0
```

#### Antwort-Struktur
```json
{
  "hinfahrtRecon": "¶HKI¶T$A=1@O=Berlin...",
  "startOrt": "Berlin Hbf",
  "zielOrt": "München Hbf",
  "hinfahrtDatum": "2024-03-15T08:30:00.000Z",
  "klasse": "KLASSE_2",
  "reisende": [...],
  "verbindungsId": "..."
}
```

#### Wichtige Felder
- `hinfahrtRecon`: Kodierte Verbindungszeichenkette für nachfolgende API-Aufrufe
- `startOrt`: Name des Abfahrtsbahnhofs
- `zielOrt`: Name des Zielbahnhofs
- `hinfahrtDatum`: Abfahrtsdatum/-zeit

### 2. Recon-Verarbeitung

**Zweck**: Detaillierte Verbindungsinformationen mit Recon-String abrufen

#### Endpunkt
```http
POST /angebote/recon
```

#### Anfrage-Payload
```json
{
  "klasse": "KLASSE_2",
  "reisende": [
    {
      "typ": "ERWACHSENER",
      "ermaessigungen": [
        {
          "art": "BAHNCARD25",
          "klasse": "KLASSE_2"
        }
      ],
      "anzahl": 1,
      "alter": []
    }
  ],
  "ctxRecon": "¶HKI¶T$A=1@O=Berlin...",
  "deutschlandTicketVorhanden": false
}
```

#### Passagiertypen
- `ERWACHSENER`: Erwachsener Passagier
- `KIND`: Kindpassagier
- `JUGENDLICHER`: Jugendlicher Passagier

#### Rabatttypen
```json
{
  "art": "BAHNCARD25|BAHNCARD50|KEINE_ERMAESSIGUNG",
  "klasse": "KLASSE_1|KLASSE_2|KLASSENLOS"
}
```

#### Antwort-Struktur
```json
{
  "verbindungen": [
    {
      "angebotsPreis": {
        "betrag": 49.90,
        "waehrung": "EUR"
      },
      "verbindungsAbschnitte": [
        {
          "verkehrsmittel": {
            "typ": "ICE",
            "nummer": "123",
            "zugattribute": [
              {"key": "9G", "value": "Deutschland-Ticket berechtigt"}
            ]
          },
          "halte": [
            {
              "id": "8011160",
              "name": "Berlin Hbf",
              "abfahrtsZeitpunkt": "2024-03-15T08:30:00.000Z",
              "ankunftsZeitpunkt": null
            }
          ]
        }
      ]
    }
  ]
}
```

### 3. Fahrplan-Suche

**Zweck**: Direkte Suche nach Verbindungen zwischen Bahnhöfen

#### Endpunkt
```http
POST /angebote/fahrplan
```

#### Anfrage-Payload
```json
{
  "abfahrtsOrt": "Berlin Hbf",
  "ankunftsOrt": "München Hbf",
  "abfahrtsDatum": "2024-03-15",
  "abfahrtsZeit": "08:30",
  "ankunftsDatum": null,
  "ankunftsZeit": null,
  "verkehrsmittel": ["ICE", "IC", "RE", "RB"],
  "klasse": "KLASSE_2",
  "reisende": [...],
  "deutschlandTicketVorhanden": false
}
```

#### Verkehrsmittel-Typen
- `ICE`: Inter City Express
- `IC`: Inter City
- `EC`: Euro City
- `RE`: Regional Express
- `RB`: Regionalbahn
- `S`: S-Bahn

### 4. Buchungslink-Generierung

**Zweck**: Direkte Buchungslinks für spezifische Verbindungen erstellen

#### URL-Format
```
https://www.bahn.de/buchung/fahrplan/suche#{parameter}
```

#### Parameter
- `sts=true`: Startet Suchprozess
- `so={start_ort}`: Startbahnhof
- `zo={ziel_ort}`: Zielbahnhof
- `soid={start_id}`: Start-Bahnhof-ID
- `zoid={ziel_id}`: Ziel-Bahnhof-ID
- `hd={datum}T{zeit}`: Abfahrtsdatum und -zeit
- `dltv=false`: Keine verspäteten Züge

#### Beispiel
```
https://www.bahn.de/buchung/fahrplan/suche#sts=true&so=Berlin%20Hbf&zo=München%20Hbf&soid=8011160&zoid=8000261&hd=2024-03-15T08:30&dltv=false
```

## Deutschland-Ticket-Integration

### Prüfung der Berechtigung

Die API prüft automatisch, ob Züge für das Deutschland-Ticket berechtigt sind:

```json
{
  "zugattribute": [
    {"key": "9G", "value": "Deutschland-Ticket berechtigt"}
  ]
}
```

### Implementation
```python
def is_deutschlandticket_eligible(train_attributes):
    for attr in train_attributes:
        if attr.get("key") == "9G":
            return True
    return False
```

## Fehlerbehandlung

### HTTP-Statuscodes
- `200`: Erfolgreiche Anfrage
- `400`: Fehlerhafte Anfrage (ungültige Parameter)
- `429`: Zu viele Anfragen (Rate Limit erreicht)
- `500`: Serverfehler
- `503`: Service nicht verfügbar

### Typische Fehlerszenarien

#### 1. Leere Verbindungen
```json
{
  "verbindungen": [],
  "meldungen": ["Keine Verbindungen gefunden"]
}
```

#### 2. Ungültige Bahnhof-IDs
```json
{
  "fehler": "Bahnhof nicht gefunden",
  "code": "STATION_NOT_FOUND"
}
```

#### 3. Rate Limiting
```json
{
  "fehler": "Zu viele Anfragen",
  "retry_after": 60
}
```

## Implementierungsbeispiele

### Python-Implementierung
```python
import requests
import time
from typing import Optional, Dict, Any

class DBApiClient:
    def __init__(self):
        self.base_url = "https://www.bahn.de/web/api"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'de'
        })
    
    def resolve_vbid(self, vbid: str) -> Optional[Dict[str, Any]]:
        """VBid in Verbindungsdetails auflösen"""
        try:
            response = self.session.get(f"{self.base_url}/angebote/verbindung/{vbid}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Fehler beim Auflösen der VBid: {e}")
            return None
    
    def get_connection_details(self, recon: str, travellers: list, 
                              deutschland_ticket: bool = False) -> Optional[Dict[str, Any]]:
        """Verbindungsdetails mit Recon-String abrufen"""
        payload = {
            "klasse": "KLASSE_2",
            "reisende": travellers,
            "ctxRecon": recon,
            "deutschlandTicketVorhanden": deutschland_ticket
        }
        
        try:
            time.sleep(0.5)  # Rate Limiting
            response = self.session.post(f"{self.base_url}/angebote/recon", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Fehler beim Abrufen der Verbindungsdetails: {e}")
            return None
    
    def search_connections(self, from_station: str, to_station: str, 
                          date: str, time: str) -> Optional[Dict[str, Any]]:
        """Direkte Verbindungssuche"""
        payload = {
            "abfahrtsOrt": from_station,
            "ankunftsOrt": to_station,
            "abfahrtsDatum": date,
            "abfahrtsZeit": time,
            "klasse": "KLASSE_2",
            "verkehrsmittel": ["ICE", "IC", "RE", "RB"]
        }
        
        try:
            time.sleep(0.5)  # Rate Limiting
            response = self.session.post(f"{self.base_url}/angebote/fahrplan", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Fehler bei der Verbindungssuche: {e}")
            return None
```

### Flutter/Dart-Implementierung
```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class DBApiClient {
  static const String baseUrl = 'https://www.bahn.de/web/api';
  
  final http.Client _client = http.Client();
  
  final Map<String, String> _headers = {
    'User-Agent': 'Mozilla/5.0 (compatible Browser)',
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=UTF-8',
    'Accept-Language': 'de',
  };
  
  Future<Map<String, dynamic>?> resolveVbid(String vbid) async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/angebote/verbindung/$vbid'),
        headers: _headers,
      );
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Fehler beim Auflösen der VBid: $e');
      return null;
    }
  }
  
  Future<Map<String, dynamic>?> getConnectionDetails(
    String recon,
    List<Map<String, dynamic>> travellers,
    bool deutschlandTicket,
  ) async {
    final payload = {
      'klasse': 'KLASSE_2',
      'reisende': travellers,
      'ctxRecon': recon,
      'deutschlandTicketVorhanden': deutschlandTicket,
    };
    
    try {
      await Future.delayed(Duration(milliseconds: 500)); // Rate Limiting
      
      final response = await _client.post(
        Uri.parse('$baseUrl/angebote/recon'),
        headers: _headers,
        body: json.encode(payload),
      );
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Fehler beim Abrufen der Verbindungsdetails: $e');
      return null;
    }
  }
}
```

## Bewährte Praktiken

### 1. Rate Limiting
- Implementieren Sie immer Verzögerungen zwischen Anfragen
- Verwenden Sie exponential backoff für Wiederholungen
- Überwachen Sie Rate Limiting-Antworten

### 2. Fehlerbehandlung
- Behandeln Sie Netzwerkfehler angemessen
- Bieten Sie benutzerfreundliche Fehlermeldungen
- Implementieren Sie Retry-Logik für temporäre Fehler

### 3. Datenvalidierung
- Validieren Sie Bahnhof-IDs vor Anfragen
- Überprüfen Sie Antwortstruktur vor Verarbeitung
- Behandeln Sie fehlende oder null-Felder sicher

### 4. Caching
- Cachen Sie Bahnhofsdaten um API-Aufrufe zu reduzieren
- Speichern Sie Verbindungsergebnisse temporär
- Implementieren Sie Cache-Invalidierungsstrategien

### 5. Überwachung
- Protokollieren Sie API-Antwortzeiten
- Verfolgen Sie Erfolgs-/Misserfolgsraten
- Überwachen Sie API-Änderungen

## Sicherheitsüberlegungen

### 1. Keine Authentifizierung erforderlich
- APIs sind öffentlich zugänglich
- Keine API-Schlüssel oder Token erforderlich
- Rate Limiting ist der primäre Schutz

### 2. Datenschutz
- Speichern Sie keine unnötigen Benutzerdaten
- Verarbeiten Sie Anfragen lokal wenn möglich
- Respektieren Sie Benutzerdatenschutz-Einstellungen

### 3. Ethische Nutzung
- Respektieren Sie Server-Ressourcen
- Missbrauchen Sie keine Rate Limits
- Berücksichtigen Sie Auswirkungen auf DB-Infrastruktur

## Fehlerbehebung

### Häufige Probleme

#### 1. Leere Antwort
```json
{"verbindungen": []}
```
**Ursachen**: Ungültige Bahnhof-IDs, keine Verbindungen verfügbar, Zeit zu weit in der Zukunft
**Lösungen**: Eingaben validieren, verschiedene Zeiten probieren, Bahnhofsexistenz prüfen

#### 2. Rate Limiting
**Symptome**: 429-Statuscodes, blockierte Anfragen
**Lösungen**: Verzögerungen erhöhen, exponential backoff implementieren, Proxy-Rotation verwenden

#### 3. Geänderte API-Struktur
**Symptome**: Fehlende Felder, unerwartetes Antwortformat
**Lösungen**: Parsing-Logik aktualisieren, defensive Programmierung hinzufügen, Änderungen überwachen

### Debugging-Tipps

1. **Alle Anfragen protokollieren**: Verfolgen Sie, was Sie senden
2. **Antworten inspizieren**: Verstehen Sie die Datenstruktur
3. **Mit Browser testen**: Vergleichen Sie mit manueller bahn.de-Nutzung
4. **Netzwerk überwachen**: Verwenden Sie Tools wie mitmproxy zur Traffic-Inspektion

## Einschränkungen

1. **Inoffizieller Status**: Keine Garantien für Stabilität oder Verfügbarkeit
2. **Rate Limits**: Aggressive Nutzung kann blockiert werden
3. **Geografischer Umfang**: Begrenzt auf deutsches Bahnnetz
4. **Sprache**: Antworten primär auf Deutsch
5. **Echtzeitdaten**: Begrenzter Zugang zu Live-Verspätungsinformationen