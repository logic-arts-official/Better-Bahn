#!/usr/bin/env python3
"""
Demonstration of v6.db.transport.rest API Integration in Better-Bahn

This script demonstrates the new real-time features that have been integrated
into Better-Bahn using the v6.db.transport.rest API.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_transport_api import DBTransportAPIClient
from main import get_real_time_journey_info, enhance_connection_with_real_time


def demo_real_time_features():
    """Demonstrate the new real-time API features."""
    print("🚀 Better-Bahn Real-time API Integration Demo")
    print("=" * 60)
    
    # Initialize the API client
    print("\n1️⃣  Initializing v6.db.transport.rest API Client...")
    client = DBTransportAPIClient(rate_limit_delay=0.1)
    print("   ✓ Client initialized with 100ms rate limiting")
    
    # Demonstrate station search
    print("\n2️⃣  Demonstrating Station Search...")
    try:
        locations = client.find_locations("Hamburg Hbf", results=3)
        print(f"   📍 Found {len(locations)} stations for 'Hamburg Hbf':")
        for i, loc in enumerate(locations[:2], 1):
            coords = f"({loc.latitude:.4f}, {loc.longitude:.4f})" if loc.latitude else "N/A"
            print(f"      {i}. {loc.name} (ID: {loc.id}) - {coords}")
    except Exception as e:
        print(f"   ⚠️  Station search error: {e}")
    
    # Demonstrate journey planning with real-time data
    print("\n3️⃣  Demonstrating Real-time Journey Planning...")
    try:
        journeys = client.get_journeys(
            from_station="8002549",  # Hamburg Hbf
            to_station="8011160",    # Berlin Hbf  
            results=2,
            stopovers=True
        )
        
        if journeys and 'journeys' in journeys:
            print(f"   🚂 Found {len(journeys['journeys'])} journey options:")
            
            for i, journey in enumerate(journeys['journeys'][:2], 1):
                duration_min = journey.get('duration', 0) // 60000 if journey.get('duration') else 0
                legs_count = len(journey.get('legs', []))
                
                print(f"      Journey {i}: {duration_min}min, {legs_count} leg(s)")
                
                # Extract real-time status
                status = client.get_real_time_status(journey)
                if status['has_delays']:
                    print(f"         ⚠️  Delays: {status['total_delay_minutes']} minutes total")
                if status['cancelled_legs'] > 0:
                    print(f"         ❌ Cancellations: {status['cancelled_legs']} legs affected")
                if not status['has_delays'] and status['cancelled_legs'] == 0:
                    print(f"         ✅ On time, no delays or cancellations")
        else:
            print("   ⚠️  No journey data available")
            
    except Exception as e:
        print(f"   ⚠️  Journey planning error: {e}")
    
    # Demonstrate integration with main Better-Bahn logic
    print("\n4️⃣  Demonstrating Integration with Better-Bahn Logic...")
    try:
        real_time_info = get_real_time_journey_info(
            "Frankfurt(Main)Hbf", 
            "Köln Hbf"
        )
        
        if real_time_info:
            print("   🔗 Real-time integration successful:")
            print(f"      Available: {real_time_info['available']}")
            print(f"      Journeys found: {real_time_info['journeys_count']}")
            
            if real_time_info['journeys']:
                first_journey = real_time_info['journeys'][0]
                rt_status = first_journey['real_time_status']
                print(f"      First journey status:")
                print(f"         Duration: {first_journey['duration_minutes']} minutes")
                print(f"         Transfers: {first_journey['transfers']}")
                print(f"         Delays: {rt_status['has_delays']} ({rt_status['total_delay_minutes']}min)")
        else:
            print("   ⚠️  Real-time data not available")
            
    except Exception as e:
        print(f"   ⚠️  Integration error: {e}")
    
    # Show command line usage
    print("\n5️⃣  Command Line Usage Examples...")
    print("   💻 With real-time features (default):")
    print("      python main.py 'https://bahn.de/...' --age 30 --bahncard BC25_1")
    print("   ")
    print("   💻 Without real-time features:")
    print("      python main.py 'https://bahn.de/...' --no-real-time")
    print("   ")
    print("   💻 Help with all options:")
    print("      python main.py --help")
    
    print("\n" + "=" * 60)
    print("✨ Demo Complete!")
    print("\nNew Features Summary:")
    print("📊 Real-time delay information for all journey legs")
    print("🚫 Cancellation detection for affected services")
    print("🗺️  Enhanced station search with geographic coordinates")
    print("⚡ Fast API with respectful rate limiting (200ms)")
    print("🔄 Graceful fallback when real-time data unavailable")
    print("🎛️  User control via --real-time/--no-real-time flags")
    print("🧪 Comprehensive test suite for reliability")


def demo_api_comparison():
    """Compare the two APIs used by Better-Bahn."""
    print("\n📊 API Comparison: Deutsche Bahn Web API vs v6.db.transport.rest")
    print("=" * 70)
    
    comparison = [
        ("Purpose", "Pricing & Split-tickets", "Real-time & Journey data"),
        ("Status", "Unofficial (reverse-engineered)", "Community-maintained"),
        ("Rate Limit", "500ms delays", "200ms delays"),
        ("Data Type", "Pricing, connections", "Live delays, cancellations"),
        ("Stability", "May change without notice", "Stable API interface"),
        ("Use Case", "Core split-ticket analysis", "Enhanced user experience"),
    ]
    
    print(f"{'Feature':<15} {'Deutsche Bahn Web API':<30} {'v6.db.transport.rest':<25}")
    print("-" * 70)
    
    for feature, web_api, transport_api in comparison:
        print(f"{feature:<15} {web_api:<30} {transport_api:<25}")
    
    print("\n🏗️  Integration Strategy:")
    print("   • Use both APIs in complementary roles")
    print("   • Deutsche Bahn Web API for pricing and split-ticket discovery")
    print("   • v6.db.transport.rest for real-time journey enhancement")
    print("   • Graceful degradation when either API unavailable")
    print("   • User control over real-time features")


if __name__ == "__main__":
    try:
        demo_real_time_features()
        demo_api_comparison()
        print("\n🎯 Ready to use! Try the new real-time features in Better-Bahn.")
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("\nNote: Network errors are expected in sandboxed environments")