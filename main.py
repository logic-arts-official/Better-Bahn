Fertig. Konflikte entfernt. Läuft mit deinem bereitgestellten `db_transport_api` (ohne `BetterBahnConfig`-Abhängigkeiten für den Client) und nutzt das bereits importierte `get_real_time_journey_info`.

```python
import argparse
import json
import os
import time
from urllib.parse import parse_qs, urlparse, quote

import requests
import yaml

from db_transport_api import DBTransportAPIClient, get_real_time_journey_info
from departure_board import DepartureBoardService


# --- HILFSFUNKTIONEN ---

def load_timetable_masterdata():
    """Lädt die statische Fahrplan-Masterdaten mit robuster Fallback-Logik."""
    try:
        from masterdata_loader import load_timetable_masterdata as load_masterdata_typed
        masterdata_obj = load_masterdata_typed()
        return masterdata_obj.raw_data
    except ImportError:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(current_dir, "data", "Timetables-1.0.213.yaml")
        try:
            with open(yaml_path, "r", encoding="utf-8") as file:
                masterdata = yaml.safe_load(file)
                print(f"✓ Fahrplan-Masterdaten geladen (Version: {masterdata.get('info', {}).get('version', 'unbekannt')})")
                return masterdata
        except FileNotFoundError:
            print(f"⚠️ Warnung: Fahrplan-Masterdaten nicht gefunden unter {yaml_path}")
            return None
        except yaml.YAMLError as e:
            print(f"⚠️ Fehler beim Laden der Fahrplan-Masterdaten: {e}")
            return None
        except Exception as e:
            print(f"⚠️ Unerwarteter Fehler beim Laden der Masterdaten: {e}")
            return None
    except Exception as e:
        print(f"⚠️ Fehler beim Laden der typisierten Masterdaten: {e}")
        print("Fallback auf ursprüngliche Implementierung...")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(current_dir, "data", "Timetables-1.0.213.yaml")
        try:
            with open(yaml_path, "r", encoding="utf-8") as file:
                masterdata = yaml.safe_load(file)
                print(f"✓ Fahrplan-Masterdaten geladen (Version: {masterdata.get('info', {}).get('version', 'unbekannt')})")
                return masterdata
        except FileNotFoundError:
            print(f"⚠️ Warnung: Fahrplan-Masterdaten nicht gefunden unter {yaml_path}")
            return None
        except yaml.YAMLError as e:
            print(f"⚠️ Fehler beim Laden der Fahrplan-Masterdaten: {e}")
            return None
        except Exception as e:
            print(f"⚠️ Unerwarteter Fehler beim Laden der Masterdaten: {e}")
            return None


def get_station_schema():
    """Gibt das Schema für Stationsdaten aus den Masterdaten zurück."""
    masterdata = load_timetable_masterdata()
    if masterdata and "components" in masterdata and "schemas" in masterdata["components"]:
        return masterdata["components"]["schemas"]
    return None


def validate_eva_number(eva_no):
    """Validiert eine EVA-Stationsnummer."""
    if not isinstance(eva_no, (int, str)):
        return False
    try:
        eva_int = int(eva_no)
        return 1000000 <= eva_int <= 9999999
    except (ValueError, TypeError):
        return False


def create_traveller_payload(age, bahncard_option):
    """Erstellt das 'reisende' JSON-Objekt basierend auf der BahnCard-Auswahl."""
    ermaessigung = {"art": "KEINE_ERMAESSIGUNG", "klasse": "KLASSENLOS"}
    if bahncard_option:
        bc_typ_str, klasse_str = bahncard_option.split("_")
        bc_art = f"BAHNCARD{bc_typ_str[2:]}"
        k_art = f"KLASSE_{klasse_str}"
        ermaessigung = {"art": bc_art, "klasse": k_art}
    return [
        {"typ": "ERWACHSENER", "ermaessigungen": [ermaessigung], "anzahl": 1, "alter": []}
    ]


# --- API-FUNKTIONEN ---

def resolve_vbid_to_connection(vbid, traveller_payload, deutschland_ticket):
    """Löst einen kurzen vbid-Link auf, um die vollständigen Verbindungsdetails zu erhalten."""
    print(f"Löse vbid '{vbid}' auf...")
    try:
        vbid_url = f"https://www.bahn.de/web/api/angebote/verbindung/{vbid}"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        response = requests.get(vbid_url, headers=headers)
        response.raise_for_status()
        vbid_data = response.json()
        recon_string = vbid_data.get("hinfahrtRecon")
        if not recon_string:
            print("Fehler: Konnte keinen 'hinfahrtRecon' aus der vbid-Antwort extrahieren.")
            return None

        recon_url = "https://www.bahn.de/web/api/angebote/recon"
        payload = {
            "klasse": "KLASSE_2",
            "reisende": traveller_payload,
            "ctxRecon": recon_string,
            "deutschlandTicketVorhanden": deutschland_ticket,
        }
        headers["Content-Type"] = "application/json; charset=UTF-8"
        print("Rufe vollständige Verbindungsdetails mit dem Recon-String ab...")
        response = requests.post(recon_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Fehler beim Auflösen der vbid '{vbid}': {e}")
        return None


def get_connection_details(
    from_station_id,
    to_station_id,
    date,
    departure_time,
    traveller_payload,
    deutschland_ticket,
):
    """Ruft Verbindungsdetails ab (für lange URLs oder Teilstrecken)."""
    url = "https://www.bahn.de/web/api/angebote/fahrplan"
    payload = {
        "abfahrtsHalt": from_station_id,
        "anfrageZeitpunkt": f"{date}T{departure_time}",
        "ankunftsHalt": to_station_id,
        "ankunftSuche": "ABFAHRT",
        "klasse": "KLASSE_2",
        "produktgattungen": [
            "ICE", "EC_IC", "IR", "REGIONAL", "SBAHN", "BUS",
            "SCHIFF", "UBAHN", "TRAM", "ANRUFPFLICHTIG",
        ],
        "reisende": traveller_payload,
        "schnelleVerbindungen": True,
        "deutschlandTicketVorhanden": deutschland_ticket,
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=UTF-8",
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def get_segment_data(from_stop, to_stop, date, traveller_payload, deutschland_ticket):
    """Fragt Daten für ein Segment an und prüft auf D-Ticket-Abdeckung."""
    time.sleep(0.5)
    departure_time_str = from_stop["departure_time"]
    if not departure_time_str:
        return None

    connections = get_connection_details(
        from_stop["id"], to_stop["id"], date, departure_time_str, traveller_payload, deutschland_ticket
    )
    if connections and connections.get("verbindungen"):
        first_connection = connections["verbindungen"][0]
        price = first_connection.get("angebotsPreis", {}).get("betrag")
        departure_iso = (
            first_connection.get("verbindungsAbschnitte", [{}])[0]
            .get("halte", [{}])[0]
            .get("abfahrtsZeitpunkt")
        )

        is_covered_by_d_ticket = False
        if deutschland_ticket:
            for section in first_connection.get("verbindungsAbschnitte", []):
                attributes = section.get("verkehrsmittel", {}).get("zugattribute", [])
                if any(attr.get("key") == "9G" for attr in attributes):
                    is_covered_by_d_ticket = True
                    break

        if is_covered_by_d_ticket:
            print(" -> Deutschland-Ticket gültig! Preis wird auf 0.00 € gesetzt.")
            price = 0.0
        elif price is not None:
            print(f" -> Preis gefunden: {price:.2f} €")
        else:
            print(" -> Kein Preis für dieses Segment verfügbar.")
            return None

        if price is not None and departure_iso:
            return {
                "price": price,
                "start_name": from_stop["name"],
                "end_name": to_stop["name"],
                "start_id": from_stop["id"],
                "end_id": to_stop["id"],
                "departure_iso": departure_iso,
            }

    print(" -> Keine Verbindungsdaten erhalten.")
    return None


def generate_booking_link(segment, bahncard_option, has_d_ticket):
    """Erstellt einen stabilen, kontextreichen Buchungslink (Deep Link)."""
    base_url = "https://www.bahn.de/buchung/fahrplan/suche"

    so = quote(segment["start_name"])
    zo = quote(segment["end_name"])
    soid = quote(segment["start_id"])
    zoid = quote(segment["end_id"])
    hd = quote(segment["departure_iso"].split(".")[0])  # exakte Abfahrtszeit
    dltv = str(has_d_ticket).lower()
    r_param = ""

    if bahncard_option:
        bc_map = {
            "BC25_2": "13:25:KLASSE_2:1",
            "BC25_1": "13:25:KLASSE_1:1",
            "BC50_2": "13:50:KLASSE_2:1",
            "BC50_1": "13:50:KLASSE_1:1",
        }
        r_code = bc_map.get(bahncard_option)
        if r_code:
            r_param = f"&r={quote(r_code)}"

    return f"{base_url}#sts=true&so={so}&zo={zo}&soid={soid}&zoid={zoid}&hd={hd}&dltv={dltv}{r_param}"


# --- ANALYSE-FUNKTION ---

def find_cheapest_split(stops, date, direct_price, traveller_payload, args):
    """Findet die günstigste Kombination von Tickets und generiert Links."""
    n = len(stops)
    segments_data = {}
    print("\n--- Preise und Daten für alle möglichen Teilstrecken werden abgerufen ---")

    for i in range(n):
        for j in range(i + 1, n):
            from_stop, to_stop = stops[i], stops[j]
            print(f"Frage Daten an für: {from_stop['name']} -> {to_stop['name']}...", end="", flush=True)
            data = get_segment_data(from_stop, to_stop, date, traveller_payload, args.deutschland_ticket)
            if data:
                segments_data[(i, j)] = data

    dp = [float("inf")] * n
    dp[0] = 0
    path_reconstruction = [-1] * n

    for i in range(1, n):
        for j in range(i):
            if (j, i) in segments_data:
                cost = dp[j] + segments_data[(j, i)]["price"]
                if cost < dp[i]:
                    dp[i] = cost
                    path_reconstruction[i] = j

    cheapest_split_price = dp[-1]

    print("\n" + "=" * 50)
    print("--- ERGEBNIS DER ANALYSE ---")
    print("=" * 50)

    if cheapest_split_price < direct_price and cheapest_split_price != float("inf"):
        savings = direct_price - cheapest_split_price
        print("\n🎉 Günstigere Split-Ticket-Option gefunden! 🎉")
        print(f"Direktpreis: {direct_price:.2f} €")
        print(f"Bester Split-Preis: {cheapest_split_price:.2f} €")
        print(f"💰 Ersparnis: {savings:.2f} € 💰")

        path = []
        current = n - 1
        while current > 0 and path_reconstruction[current] != -1:
            prev = path_reconstruction[current]
            path.append(segments_data.get((prev, current)))
            current = prev
        path.reverse()

        print("\nEmpfohlene Tickets zum Buchen:")
        for idx, segment in enumerate(path, 1):
            if segment:
                print(f"  Ticket {idx}: Von {segment['start_name']} nach {segment['end_name']} für {segment['price']:.2f} €")
                if segment["price"] > 0:
                    link = generate_booking_link(segment, args.bahncard, args.deutschland_ticket)
                    print(f"      -> Buchungslink: {link}")
                else:
                    print("      -> (Fahrt durch Deutschland-Ticket abgedeckt)")
    else:
        print("\nKeine günstigere Split-Option gefunden.")
        print(f"Das Direktticket für {direct_price:.2f} € ist die beste Option.")


# --- HAUPTFUNKTION ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Findet günstigere Split-Tickets für eine DB-Verbindung und generiert Buchungslinks.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("url", nargs='?', help="Der vollständige URL (lang oder kurz mit vbid) von bahn.de")
    parser.add_argument("--age", type=int, default=30, help="Alter des Reisenden (Standard: 30).")
    parser.add_argument(
        "--bahncard",
        choices=["BC25_1", "BC25_2", "BC50_1", "BC50_2"],
        help="Wählen Sie eine BahnCard-Option:\nBC25_1, BC25_2, BC50_1, BC50_2",
    )
    parser.add_argument("--deutschland-ticket", action="store_true", help="Deutschland-Ticket vorhanden.")
    parser.add_argument(
        "--real-time", action="store_true", default=True,
        help="Echtzeit-Daten über v6.db.transport.rest API abrufen (Standard: aktiviert).",
    )
    parser.add_argument("--no-real-time", dest="real_time", action="store_false", help="Echtzeit-Daten deaktivieren.")
    parser.add_argument("--departure-board", action="store_true", help="Abfahrtstafel anzeigen (erfordert --station)")
    parser.add_argument("--station", help="Bahnhof für Abfahrtstafel (Name oder EVA-Nummer)")
    parser.add_argument("--demo", action="store_true", help="Demo-Modus für Abfahrtstafel mit Beispieldaten")

    args = parser.parse_args()

    # Abfahrtstafel-Modus
    if args.departure_board:
        if not args.station and not args.demo:
            print("❌ Fehler: --departure-board erfordert --station oder --demo")
            print("💡 Beispiel: main.py 'dummy_url' --departure-board --station 'Berlin Hbf'")
            print("💡 Oder Demo: main.py 'dummy_url' --departure-board --demo")
            raise SystemExit(1)

        print("🚂 Better-Bahn Abfahrtstafel-Modus")
        print("=" * 50)

        departure_service = DepartureBoardService()

        if args.demo:
            print("🎭 Demo-Modus aktiviert - Zeige Beispieldaten")
            board = departure_service.create_demo_departure_board(args.station or "Berlin Hbf")
        else:
            station_id = args.station
            if not args.station.isdigit():
                print(f"Suche Station: {args.station}...")
                station_info = departure_service.find_station_by_name(args.station)
                if not station_info:
                    print(f"❌ Station '{args.station}' nicht gefunden.")
                    raise SystemExit(1)
                station_id = station_info['id']
                print(f"✓ Station gefunden: {station_info['name']} (EVA: {station_id})")

            print(f"\n📡 Lade Abfahrtsdaten für Station {station_id}...")
            board = departure_service.create_departure_board(station_id=station_id)

        if board:
            print("\n" + departure_service.format_departure_board(board, max_entries=15))
        else:
            print("❌ Keine Abfahrtsdaten verfügbar.")
        raise SystemExit(0)

    # URL Pflicht für Split-Analyse
    if not args.url:
        print("❌ Fehler: URL ist erforderlich für Split-Ticket-Analyse")
        print("💡 Verwenden Sie --departure-board für Abfahrtstafeln")
        raise SystemExit(1)

    # Init
    print("--- Initialisierung ---")
    masterdata = load_timetable_masterdata()
    traveller_payload = create_traveller_payload(args.age, args.bahncard)

    connection_data, date_part = None, None
    url_to_parse = args.url

    if "/buchung/start" in url_to_parse:
        parsed_url = urlparse(url_to_parse)
        query_params = parse_qs(parsed_url.query)
        if "vbid" in query_params:
            url_to_parse = f"https://www.bahn.de?vbid={query_params['vbid'][0]}"

    if "vbid=" in url_to_parse:
        print("--- Kurzer Link (vbid) erkannt ---")
        vbid = parse_qs(urlparse(url_to_parse).query)["vbid"][0]
        connection_data = resolve_vbid_to_connection(vbid, traveller_payload, args.deutschland_ticket)
        if connection_data:
            first_stop_departure = connection_data["verbindungen"][0]["verbindungsAbschnitte"][0]["halte"][0]["abfahrtsZeitpunkt"]
            date_part = first_stop_departure.split("T")[0]
    else:
        print("--- Langer Link erkannt ---")
        params = parse_qs(urlparse(url_to_parse).fragment)
        if not all(k in params for k in ["soid", "zoid", "hd"]):
            print("Fehler: Der lange URL ist unvollständig.")
            raise SystemExit(1)
        from_station_id, to_station_id, datetime_str = (params["soid"][0], params["zoid"][0], params["hd"][0])
        date_part, time_part = datetime_str.split("T")
        connection_data = get_connection_details(
            from_station_id, to_station_id, date_part, time_part, traveller_payload, args.deutschland_ticket
        )

    if not connection_data or not connection_data.get("verbindungen"):
        print("Konnte keine Verbindungsdetails für den angegebenen Link abrufen.")
        raise SystemExit(1)

    # --- ECHTZEIT-DATEN INTEGRATION ---
    if args.real_time:
        print("\n--- Integriere Echtzeit-Daten ---")
        first_connection = connection_data["verbindungen"][0]

        if "verbindungsAbschnitte" in first_connection and first_connection["verbindungsAbschnitte"]:
            start_station = first_connection["verbindungsAbschnitte"][0]["halte"][0]["bahnhofsName"]
            end_station = first_connection["verbindungsAbschnitte"][-1]["halte"][-1]["bahnhofsName"]

            print(f"🔍 Suche Echtzeit-Daten für: {start_station} → {end_station}")
            # Nutzt das im Modul bereitgestellte resilient helper
            real_time_info = get_real_time_journey_info(start_station, end_station)

            if real_time_info and real_time_info.get('available'):
                print(f"✓ Echtzeit-Daten integriert ({real_time_info['journeys_count']} Verbindungen)")
                if real_time_info['journeys']:
                    first_journey = real_time_info['journeys'][0]
                    rt_status = first_journey['real_time_status']
                    if rt_status['has_delays']:
                        print(f"⚠️  Aktuelle Verspätungen: {rt_status['total_delay_minutes']} Minuten")
                    if rt_status.get('has_cancellations'):
                        print("❌ Ausfälle: Teilstrecken betroffen")
                    if rt_status.get('has_delays') is False and not rt_status.get('has_cancellations'):
                        print("✅ Aktuell keine Verspätungen oder Ausfälle")
            else:
                error_msg = real_time_info.get('error', 'Unbekannter Fehler') if real_time_info else 'Keine Antwort'
                print(f"⚠️ Echtzeit-Daten momentan nicht verfügbar: {error_msg}")
                print("🔄 Fallback auf bahn.de Basisdaten")
        else:
            print("⚠️ Konnte Stationsnamen für Echtzeit-Abfrage nicht extrahieren")
    else:
        print("\n--- Echtzeit-Daten deaktiviert ---")
        print("💡 Verwenden Sie --real-time um Echtzeit-Informationen zu aktivieren")

    print("\n--- Analysiere die Verbindung ---")
    print(f"Datum: {date_part}")
    if args.bahncard:
        bc_typ, klasse = args.bahncard.split("_")
        print(f"Rabatt: BahnCard {bc_typ[2:]}, {klasse}. Klasse")
    if args.deutschland_ticket:
        print("Deutschland-Ticket: Vorhanden")

    first_connection = connection_data["verbindungen"][0]
    direct_price = first_connection.get("angebotsPreis", {}).get("betrag")

    if direct_price is None:
        print("Konnte den Direktpreis nicht ermitteln. Analyse nicht möglich.")
        raise SystemExit(1)

    print(f"Direktpreis gefunden: {direct_price:.2f} €")

    all_stops = []
    print("\n--- Extrahiere alle Haltestellen der Verbindung ---")
    for section in first_connection["verbindungsAbschnitte"]:
        if section["verkehrsmittel"]["typ"] != "WALK":
            for halt in section["halte"]:
                if not any(stop["id"] == halt["id"] for stop in all_stops):
                    all_stops.append(
                        {
                            "name": halt["name"],
                            "id": halt["id"],
                            "departure_time": halt.get("abfahrtsZeitpunkt", "").split("T")[-1] if halt.get("abfahrtsZeitpunkt") else "",
                            "arrival_time": halt.get("ankunftsZeitpunkt", "").split("T")[-1] if halt.get("ankunftsZeitpunkt") else "",
                        }
                    )
    if all_stops:
        all_stops[-1]["departure_time"] = all_stops[-1]["arrival_time"]

    print(f"{len(all_stops)} eindeutige Haltestellen gefunden:")
    for stop in all_stops:
        print(f"  - {stop['name']}")

    find_cheapest_split(all_stops, date_part, direct_price, traveller_payload, args)
```
