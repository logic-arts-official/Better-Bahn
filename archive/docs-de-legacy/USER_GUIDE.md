# Better-Bahn Benutzerhandbuch

## Was ist Better-Bahn?

Better-Bahn ist eine kostenlose, quelloffene Anwendung, die Ihnen hilft, Geld bei Deutsche Bahn-Fahrten zu sparen, indem sie günstigere Split-Ticket-Kombinationen findet. Anstatt ein teures Direktticket zu kaufen, analysiert die App Ihre Route und schlägt vor, mehrere günstigere Tickets zu kaufen, die dieselbe Fahrt abdecken.

## Wie es funktioniert

### Das Split-Ticket-Konzept

Bei einer Fahrt von A nach C über B ist es manchmal günstiger zu kaufen:
- Ein Ticket von A nach B
- Ein weiteres Ticket von B nach C

Anstatt eines einzelnen Direkttickets von A nach C.

Better-Bahn automatisiert:
1. Die Analyse Ihrer geplanten Fahrt
2. Die Preisüberprüfung für alle möglichen Ticketkombinationen
3. Das Finden der günstigsten Option
4. Die Bereitstellung direkter Buchungslinks

### Beispiel für Einsparungen

**Traditionelle Buchung**: Berlin → München = €89,90
**Split-Ticket-Option**: 
- Berlin → Nürnberg = €29,90
- Nürnberg → München = €19,90
- **Gesamt: €49,80 (Sparen Sie €40,10!)**

## Installation

### Mobile App (Android)

1. Gehen Sie zur [GitHub Releases-Seite](https://github.com/gkrost/Better-Bahn/releases)
2. Laden Sie die neueste `.apk`-Datei herunter
3. Installieren Sie sie auf Ihrem Android-Gerät
4. Erlauben Sie bei Bedarf die Installation aus unbekannten Quellen

### Python CLI-Tool

**Voraussetzungen**: Python 3.12+ auf Ihrem System installiert

1. Klonen oder laden Sie das Repository herunter
2. Navigieren Sie zum Projektverzeichnis
3. Führen Sie Befehle mit `python main.py [optionen] <url>` aus

#### Schnellstart:
```bash
# Grundlegende Nutzung
python main.py "https://www.bahn.de/buchung/start?vbid=IHR_LINK_HIER"

# Mit BahnCard 25, 2. Klasse
python main.py --bahncard BC25_2 "IHR_DB_LINK"

# Mit Deutschland-Ticket
python main.py --deutschland-ticket "IHR_DB_LINK"

# Benutzerdefiniertes Alter und vollständige Optionen
python main.py --age 25 --bahncard BC50_1 --deutschland-ticket "IHR_DB_LINK"
```

## Verwendung der App

### Schritt 1: Ihren Fahrt-Link erhalten

#### Aus der DB Navigator App:
1. Planen Sie Ihre Fahrt in der DB Navigator App
2. Suchen Sie den "Teilen" oder "Share"-Button
3. Kopieren Sie den Link (beginnt mit `https://www.bahn.de/`)

#### Von der bahn.de Website:
1. Suchen Sie Ihre Fahrt auf bahn.de
2. Wählen Sie Ihre bevorzugte Verbindung
3. Kopieren Sie die URL aus der Adressleiste Ihres Browsers

### Schritt 2: Ihre Einstellungen konfigurieren

#### BahnCard-Optionen:
- **BC25_1**: BahnCard 25, 1. Klasse
- **BC25_2**: BahnCard 25, 2. Klasse  
- **BC50_1**: BahnCard 50, 1. Klasse
- **BC50_2**: BahnCard 50, 2. Klasse

#### Deutschland-Ticket:
- Aktivieren Sie diese Option, wenn Sie ein Deutschland-Ticket haben
- Die App setzt automatisch Regionalverkehr-Segmente auf €0

#### Alterseinstellung:
- Manche Rabatte sind altersabhängig
- Standard ist 30 Jahre alt

### Schritt 3: Ihre Fahrt analysieren

1. Fügen Sie Ihren DB-Link in die App ein
2. Wählen Sie Ihren BahnCard-Typ (falls zutreffend)
3. Aktivieren Sie die Deutschland-Ticket-Option (falls zutreffend)
4. Tippen Sie auf "Verbindung analysieren"

### Schritt 4: Ergebnisse überprüfen

Die App zeigt:
- **Direktticket-Preis**: Kosten der Buchung der Fahrt als ein Ticket
- **Split-Ticket-Preis**: Kosten der optimierten Kombination
- **Einsparungsbetrag**: Wie viel Geld Sie sparen werden
- **Empfohlene Tickets**: Liste der einzelnen zu kaufenden Tickets

### Schritt 5: Ihre Tickets buchen

Für jedes empfohlene Ticket:
1. Tippen Sie auf den bereitgestellten Buchungslink
2. Sie werden zu bahn.de mit der exakt vorausgefüllten Fahrt weitergeleitet
3. Schließen Sie Ihren Kauf wie gewohnt ab
4. Wiederholen Sie dies für jedes Ticket-Segment

## Unterstützte Link-Typen

### Kurze Links (vbid):
```
https://www.bahn.de/buchung/start?vbid=abc123-def456-ghi789
```

### Lange Links:
```
https://www.bahn.de/buchung/fahrplan/suche#sts=true&so=Berlin&zo=Munich&soid=8011160&zoid=8000261&hd=2024-03-15T08:30&dltv=false
```

## Tipps für maximale Einsparungen

### 1. Flexible Reisezeiten
- Split-Ticket-Möglichkeiten variieren je nach Tageszeit
- Probieren Sie verschiedene Abfahrtszeiten für bessere Angebote

### 2. Routenauswahl
- Längere Routen mit mehr Zwischenstationen bieten mehr Split-Möglichkeiten
- Erwägen Sie alternative Routen durch verschiedene Städte

### 3. Vorabusbuchung
- Wie bei regulären Tickets sind Split-Tickets oft günstiger bei Vorabuchung
- Preise können sich ändern, buchen Sie daher zeitnah, wenn Sie Einsparungen finden

### 4. BahnCard-Integration
- Die App wendet automatisch Ihren BahnCard-Rabatt auf jedes Segment an
- Manchmal bieten Split-Tickets + BahnCard noch größere Einsparungen

## Wichtige Überlegungen

### Rechtliche Konformität
- Split-Tickets sind vollständig legal und entsprechen den DB-Nutzungsbedingungen
- Sie kaufen einfach mehrere gültige Tickets für Ihre Fahrt
- Kein "Hacking" oder Verstoß gegen Bedingungen beteiligt

### Ticket-Gültigkeit
- Jedes Ticket ist für sein spezifisches Segment gültig
- Stellen Sie sicher, dass Sie alle Tickets beim Reisen haben
- Zeigen Sie das entsprechende Ticket für jedes Segment den Schaffnern

### Umsteigehandhabung
- Sie müssen an Umsteigepunkten nicht aus- und wieder einsteigen
- Bleiben Sie im selben Zug, wenn er Ihre Fahrt fortsetzt
- Wechseln Sie Tickets nur, wenn Sie tatsächlich Züge wechseln

### Verbindungsrisiken
- Wenn Sie eine Verbindung aufgrund von Verspätungen verpassen, können spätere Tickets ungültig werden
- Erwägen Sie eine Reiseversicherung für wertvolle Fahrten
- DBs Verspätungsentschädigung gilt weiterhin für einzelne Tickets

## Fehlerbehebung

### "Keine günstigere Option gefunden"
- Split-Tickets sind nicht immer verfügbar
- Probieren Sie verschiedene Zeiten oder alternative Routen
- Direkttickets sind manchmal genuinely das beste Angebot

### "Verbindungsdetails konnten nicht abgerufen werden"
- Überprüfen Sie Ihre Internetverbindung
- Verifizieren Sie, dass der DB-Link vollständig und gültig ist
- Die bahn.de-Server könnten vorübergehend nicht verfügbar sein

### App-Abstürze oder Fehler
- Stellen Sie sicher, dass Sie die neueste Version verwenden
- Probieren Sie einen anderen DB-Link, um das Problem zu isolieren
- Melden Sie Bugs auf der GitHub Issues-Seite

### Ratenbegrenzung / "Zu viele Anfragen"
- Die App enthält Verzögerungen, um DB-Server nicht zu überlasten
- Falls blockiert, warten Sie einige Minuten vor erneutem Versuch
- Erwägen Sie die Nutzung der App zu verkehrsschwachen Zeiten

## Datenschutz & Sicherheit

### Lokale Verarbeitung
- Alle Analysen geschehen auf Ihrem Gerät
- Keine Daten werden an externe Server gesendet (außer bahn.de für Preisanfragen)
- Keine Benutzerkonten oder Tracking

### Datennutzung
- Die App stellt mehrere Anfragen an bahn.de, um Preisdaten zu sammeln
- Jede Analyse erfordert 1 Anfrage pro möglichem Routensegment
- Für N Stationen erwarten Sie bis zu N² Anfragen

### Keine Datensammlung
- Better-Bahn sammelt keine persönlichen Informationen
- Keine Analytik oder Telemetrie
- Keine Werbung oder Monetarisierung

## Hilfe erhalten

### Community-Support
- GitHub Issues: Bugs melden oder Features anfordern
- Discussions: Fragen stellen und Erfahrungen teilen
- Wiki: Community-beigetragene Tipps und Anleitungen

### Selbsthilfe
- Überprüfen Sie dieses Benutzerhandbuch für häufige Fragen
- Lesen Sie die technische Dokumentation für erweiterte Nutzung
- Untersuchen Sie den Quellcode - er ist Open Source!

## Mitwirken

Better-Bahn ist Open Source und begrüßt Beiträge:
- Melden Sie Bugs über GitHub Issues
- Schlagen Sie Features oder Verbesserungen vor
- Reichen Sie Code-Verbesserungen über Pull Requests ein
- Helfen Sie bei der Übersetzung der App in andere Sprachen
- Teilen Sie Ihre Einsparungsgeschichten, um anderen zu helfen

## Rechtlicher Haftungsausschluss

Better-Bahn ist ein inoffizielles Tool, das nicht mit der Deutsche Bahn AG verbunden ist. Nutzung auf eigenes Risiko. Überprüfen Sie immer die Ticket-Gültigkeit und Konformität mit aktuellen DB-Nutzungsbedingungen. Die Entwickler sind nicht verantwortlich für Probleme, die aus Split-Ticket-Buchungen entstehen.