# Better-Bahn Technische Dokumentation

## Architektur-Übersicht

Better-Bahn ist eine Dual-Plattform-Anwendung, die darauf ausgelegt ist, günstigere Split-Ticket-Kombinationen für Deutsche Bahn-Fahrten zu finden. Das Projekt besteht aus zwei Hauptkomponenten:

1. **Python CLI-Tool** (`main.py`) - Kernlogik und API-Interaktionen
2. **Flutter Mobile App** (`flutter-app/`) - Benutzerfreundliche mobile Oberfläche

## Kernfunktionalität

### Split-Ticket-Analyse-Algorithmus

Die Anwendung implementiert einen Dynamic Programming-Ansatz, um die optimale Kombination von Tickets zu finden:

1. **Routen-Extraktion**: Parst DB-URLs (sowohl kurze vbid-Links als auch lange URLs) um Fahrtdetails zu extrahieren
2. **Bahnhofs-Entdeckung**: Identifiziert alle Zwischenstationen entlang der Route
3. **Preis-Matrix**: Fragt Preise für alle möglichen Sub-Routen zwischen Stationen ab
4. **Optimierung**: Verwendet Dynamic Programming um die günstigste Kombination von Tickets zu finden

### API-Integrationsstrategie

**Wichtig**: Better-Bahn verwendet keine offiziellen Deutsche Bahn APIs. Stattdessen simuliert es Browser-Anfragen an `bahn.de` um Preisdaten zu sammeln.

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

#### Wichtige Funktionen:

- `resolve_vbid_to_connection()`: Wandelt kurze Links in vollständige Verbindungsdaten um
- `get_connection_details()`: Ruft Routen- und Preisinformationen ab
- `get_segment_data()`: Analysiert einzelne Routensegmente
- `find_cheapest_split()`: Dynamic Programming-Optimierungsalgorithmus
- `generate_booking_link()`: Erstellt Deep Links für Ticket-Käufe

#### Unterstützte Features:
- BahnCard-Rabatte (25/50, 1./2. Klasse)
- Deutschland-Ticket-Integration
- Altersbasierte Preisgestaltung
- Direkte Buchungslink-Generierung

### Flutter Frontend

#### Architektur:
- Material Design 3 mit DB-Unternehmensfarben
- Responsive Design für mobile Geräte
- HTTP-Client für API-Kommunikation
- URL-Launcher für externe Buchungslinks

#### Wichtige Features:
- Link-Eingabe und -Validierung
- Einstellungen für BahnCard und Deutschland-Ticket
- Ergebnisanzeige mit Einsparungsberechnung
- Direkte Buchungslink-Integration

## Datenfluss

```
Benutzereingabe (DB URL) 
    ↓
URL-Parsing & Validierung
    ↓
API-Anfrage an bahn.de
    ↓
Routen- & Stationsextraktion
    ↓
Preis-Matrix-Generierung (N² API-Aufrufe)
    ↓
Dynamic Programming-Optimierung
    ↓
Ergebnisse & Buchungslinks
```

## Rate Limiting & Performance

### Aktuelle Einschränkungen:
- 0,5 Sekunden Verzögerung zwischen API-Anfragen
- Keine Proxy-Rotation oder erweiterte Rate Limiting-Umgehung
- Sequentielle Verarbeitung von Preisabfragen

### Performance-Charakteristika:
- Für N Stationen: O(N²) API-Aufrufe erforderlich
- Verarbeitungszeit: ~(N² × 0,5) Sekunden
- Speicherverbrauch: O(N²) für Preis-Matrix-Speicherung

## Sicherheitsüberlegungen

### Web-Scraping-Ethik:
- Simuliert legitime Browser-Anfragen
- Respektiert Rate Limits um Server-Überlastung zu vermeiden
- Kein Versuch, Anti-Bot-Maßnahmen zu umgehen
- Verteilt Last auf individuelle Benutzergeräte

### Datenschutz:
- Keine Daten auf externen Servern gespeichert
- Alle Verarbeitung erfolgt lokal
- Kein Benutzer-Tracking oder Analytics
- Keine Authentifizierung oder Benutzerkonten erforderlich

## Fehlerbehandlung

### Robustes Fehler-Management:
- Netzwerkanfrage-Timeouts und Wiederholungen
- Ungültige URL-Erkennung und Benutzer-Feedback
- Angemessene Verschlechterung bei fehlenden Preisdaten
- Verbindungsfehler-Wiederherstellung

### Logging & Debugging:
- Detaillierte Konsolenausgabe für Fehlerbehebung
- Schritt-für-Schritt-Analyse-Fortschrittsberichte
- Klare Fehlermeldungen für häufige Probleme

## Deployment-Architektur

### Vorteile der lokalen Verarbeitung:
1. **Keine Serverkosten**: Eliminiert Hosting- und Wartungskosten
2. **Skalierbarkeit**: Last verteilt auf Benutzergeräte
3. **Privatsphäre**: Keine zentrale Datensammelstelle
4. **Zuverlässigkeit**: Nicht abhängig von Server-Uptime
5. **Rate Limit-Vermeidung**: Individuelle Benutzeranfragen werden weniger wahrscheinlich blockiert

### Vertriebskanäle:
- GitHub Releases für Android APK
- Python-Paket für CLI-Nutzung
- Quellcode für benutzerdefinierte Builds

## Code-Qualitätsbewertung

### Stärken:
- Klare Trennung der Concerns
- Umfassende Fehlerbehandlung
- Gut dokumentierte API-Interaktionen
- Benutzerfreundliche Kommandozeilen-Schnittstelle

### Verbesserungsbereiche:
- Begrenzte Unit-Test-Abdeckung
- Hardcodierte API-Endpunkte
- Minimale Konfigurationsoptionen
- Kein Caching-Mechanismus für wiederholte Abfragen

## Zukünftige Verbesserungsmöglichkeiten

### Technische Verbesserungen:
1. **Caching-System**: Preisdaten speichern um API-Aufrufe zu reduzieren
2. **Parallele Verarbeitung**: Gleichzeitige Preisabfragen wo möglich
3. **Proxy-Unterstützung**: Erweiterte Rate Limiting-Umgehung
4. **Konfigurationssystem**: Benutzer-anpassbare Einstellungen
5. **Test-Abdeckung**: Umfassende Unit- und Integrationstests

### Feature-Ergänzungen:
1. **Historische Preisverfolgung**: Preistrends über Zeit überwachen
2. **Fahrplan-Integration**: Abfahrtszeiten in Optimierung berücksichtigen
3. **Multi-Passagier-Unterstützung**: Gruppenbuchungs-Optimierung
4. **Alternative Routenvorschläge**: Verschiedene Reisewege vergleichen

## Implementierungsdetails

### Dynamic Programming-Algorithmus

```python
def find_cheapest_split(price_matrix, stations):
    """
    Findet die günstigste Split-Ticket-Kombination mit Dynamic Programming.
    
    Args:
        price_matrix: N×N-Matrix mit Preisen zwischen allen Stationspaaren
        stations: Liste der Stationen in Reihenfolge
        
    Returns:
        Optimale Ticket-Kombination mit minimalen Kosten
    """
    n = len(stations)
    # dp[i] = minimale Kosten um Station i zu erreichen
    dp = [float('inf')] * n
    # parent[i] = vorherige Station für optimalen Pfad zu Station i
    parent = [-1] * n
    
    dp[0] = 0  # Startstation kostet nichts
    
    for i in range(1, n):
        for j in range(i):
            if price_matrix[j][i] is not None:
                cost = dp[j] + price_matrix[j][i]
                if cost < dp[i]:
                    dp[i] = cost
                    parent[i] = j
    
    # Pfad rekonstruieren
    path = []
    current = n - 1
    while current != -1:
        path.append(current)
        current = parent[current]
    path.reverse()
    
    return path, dp[n-1]
```

### API-Anfrage-Wrapper

```python
def safe_api_request(url, payload=None, max_retries=3):
    """
    Robuste API-Anfrage mit Retry-Logik und Rate Limiting.
    
    Args:
        url: Ziel-URL
        payload: JSON-Payload für POST-Anfragen
        max_retries: Maximale Anzahl Wiederholungsversuche
        
    Returns:
        API-Antwort oder None bei Fehler
    """
    for attempt in range(max_retries):
        try:
            time.sleep(0.5)  # Rate Limiting
            
            if payload:
                response = requests.post(url, json=payload, timeout=30)
            else:
                response = requests.get(url, timeout=30)
                
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                print(f"API-Anfrage fehlgeschlagen nach {max_retries} Versuchen: {e}")
                return None
            time.sleep(2 ** attempt)  # Exponential backoff
    
    return None
```

### Preis-Matrix-Aufbau

```python
def build_price_matrix(stations, traveller_payload, deutschland_ticket):
    """
    Erstellt eine N×N-Matrix mit Preisen zwischen allen Stationspaaren.
    
    Args:
        stations: Liste der Stationen mit IDs und Namen
        traveller_payload: Reisenden-Konfiguration
        deutschland_ticket: Deutschland-Ticket-Status
        
    Returns:
        Matrix mit Preisen oder None bei fehlenden Verbindungen
    """
    n = len(stations)
    price_matrix = [[None for _ in range(n)] for _ in range(n)]
    
    for i in range(n):
        for j in range(i + 1, n):
            price = get_segment_price(
                stations[i]['id'], 
                stations[j]['id'],
                traveller_payload,
                deutschland_ticket
            )
            price_matrix[i][j] = price
            
    return price_matrix
```

## Wartung und Monitoring

### Überwachung der API-Stabilität
- Automatische Tests für API-Endpunkt-Verfügbarkeit
- Überwachung von Response-Format-Änderungen
- Logging von Fehlschlägen und Erfolgsraten

### Wartungsstrategien
- Regelmäßige Updates bei API-Änderungen
- Community-getriebene Bug-Reports und Fixes
- Dokumentation von Workarounds für temporäre Probleme

### Performance-Monitoring
- Verfolgung der durchschnittlichen Analysezeit
- Überwachung der API-Rate-Limit-Einhaltung
- Messung der Erfolgsrate bei der Einsparungsfindung