#!/usr/bin/env python3
"""
Departure Board CLI for Better-Bahn

Command-line interface for viewing real-time departure boards
that combine static timetable data with live departure information.
"""

import argparse
import sys
from departure_board import DepartureBoardService, DepartureStatus


def main():
    """Main CLI function for departure board functionality."""
    parser = argparse.ArgumentParser(
        description="Zeigt Abfahrtstafeln mit Echtzeit-Daten für Deutsche Bahn Stationen an.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    
    parser.add_argument(
        "station",
        help="Stationsname oder EVA-Nummer (z.B. 'Berlin Hbf' oder '8011160')"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=120,
        help="Zeitspanne in Minuten für Abfahrten (Standard: 120)"
    )
    
    parser.add_argument(
        "--results",
        type=int,
        default=20,
        help="Maximale Anzahl der Ergebnisse (Standard: 20)"
    )
    
    parser.add_argument(
        "--max-display",
        type=int,
        default=15,
        help="Maximale Anzahl der angezeigten Abfahrten (Standard: 15)"
    )
    
    parser.add_argument(
        "--delayed-only",
        action="store_true",
        help="Nur verspätete Züge anzeigen"
    )
    
    parser.add_argument(
        "--min-delay",
        type=int,
        default=5,
        help="Minimale Verspätung in Minuten für --delayed-only (Standard: 5)"
    )
    
    parser.add_argument(
        "--status",
        choices=["ON_TIME", "DELAYED", "CANCELLED", "UNKNOWN"],
        help="Filter nach Status"
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Demo-Modus mit Beispieldaten (funktioniert ohne Internetverbindung)"
    )
    
    args = parser.parse_args()
    
    # Initialize service
    print("🚂 Better-Bahn Abfahrtstafel")
    print("=" * 50)
    
    service = DepartureBoardService()
    
    # Handle demo mode
    if args.demo:
        print("🎭 Demo-Modus aktiviert - Zeige Beispieldaten")
        board = service.create_demo_departure_board(args.station)
        
        # Apply filters for demo
        departures_to_show = board.departures
        
        if args.delayed_only:
            departures_to_show = board.get_delayed_departures(args.min_delay)
            if not departures_to_show:
                print(f"ℹ️ Keine Verspätungen über {args.min_delay} Minuten in den Demodaten.")
                return 0
        
        if args.status:
            status_filter = DepartureStatus(args.status)
            departures_to_show = board.get_departures_by_status(status_filter)
            if not departures_to_show:
                print(f"ℹ️ Keine Abfahrten mit Status {args.status} in den Demodaten.")
                return 0
        
        # Update board with filtered departures for display
        board.departures = departures_to_show
        
        # Display the board
        print("\n" + service.format_departure_board(board, args.max_display))
        return 0
    
    # Determine if input is station name or EVA number
    station_id = args.station
    station_info = None
    
    # If not numeric, try to find by name
    if not args.station.isdigit():
        print(f"Suche Station: {args.station}...")
        station_info = service.find_station_by_name(args.station)
        if not station_info:
            print(f"❌ Station '{args.station}' nicht gefunden.")
            print("💡 Versuchen Sie einen anderen Namen oder die EVA-Nummer.")
            return 1
        
        station_id = station_info['id']
        print(f"✓ Station gefunden: {station_info['name']} (EVA: {station_id})")
    
    # Create departure board
    print(f"\n📡 Lade Abfahrtsdaten für Station {station_id}...")
    
    board = service.create_departure_board(
        station_id=station_id,
        duration=args.duration,
        results=args.results
    )
    
    if not board:
        print("❌ Keine Abfahrtsdaten verfügbar.")
        return 1
    
    # Apply filters
    departures_to_show = board.departures
    
    if args.delayed_only:
        departures_to_show = board.get_delayed_departures(args.min_delay)
        if not departures_to_show:
            print(f"ℹ️ Keine Verspätungen über {args.min_delay} Minuten gefunden.")
            return 0
    
    if args.status:
        status_filter = DepartureStatus(args.status)
        departures_to_show = board.get_departures_by_status(status_filter)
        if not departures_to_show:
            print(f"ℹ️ Keine Abfahrten mit Status {args.status} gefunden.")
            return 0
    
    # Update board with filtered departures for display
    board.departures = departures_to_show
    
    # Display the board
    print("\n" + service.format_departure_board(board, args.max_display))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())