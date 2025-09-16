#!/usr/bin/env python3
"""
Masterdata Processing Test Suite
Comprehensive validation of the Better-Bahn masterdata processing pipeline.
"""

import sys
import os
import json
from datetime import datetime

# Add the parent directory to the path to import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main

def test_masterdata_processing():
    """Test the complete masterdata processing pipeline."""
    print("🚀 Better-Bahn Masterdata Processing Test Suite")
    print("=" * 50)
    
    # Test 1: Schema Loading
    print("\n📋 Test 1: Schema Loading")
    schema = main.load_masterdata_schema()
    assert schema is not None, "Schema should load successfully"
    assert schema['title'] == 'Better-Bahn Masterdata Schema', "Schema title should match"
    print("✅ Schema loading: PASSED")
    
    # Test 2: Version Management
    print("\n📦 Test 2: Version Management")
    version_info = main.load_timetables_version()
    assert version_info is not None, "Version info should load successfully"
    assert 'version' in version_info, "Version should contain version field"
    assert 'file_sha256' in version_info, "Version should contain hash field"
    print("✅ Version management: PASSED")
    
    # Test 3: Station Name Normalization
    print("\n🔤 Test 3: Station Name Normalization")
    test_cases = [
        ("München Hauptbahnhof", "munchen hauptbahnhof"),
        ("Köln Hbf", "koln hbf"),
        ("Düsseldorf Flughafen", "dusseldorf flughafen"),
        ("Würzburg Hbf", "wurzburg hbf"),
        ("François Mitterrand", "francois mitterrand"),
        ("  Extra   Spaces  ", "extra spaces"),
    ]
    
    for original, expected in test_cases:
        normalized = main.normalize_station_name(original)
        assert normalized == expected, f"Normalization failed: '{original}' → '{normalized}' (expected '{expected}')"
        print(f"  ✓ {original} → {normalized}")
    print("✅ Station name normalization: PASSED")
    
    # Test 4: EVA Number Validation
    print("\n🔢 Test 4: EVA Number Validation")
    valid_evas = [8000261, 8011160, 1000000, 9999999]
    invalid_evas = [123, 999999, 10000000, "invalid", None]
    
    for eva in valid_evas:
        assert main.validate_eva_number(eva), f"EVA {eva} should be valid"
    
    for eva in invalid_evas:
        assert not main.validate_eva_number(eva), f"EVA {eva} should be invalid"
    
    print("✅ EVA number validation: PASSED")
    
    # Test 5: Station Data Validation
    print("\n📍 Test 5: Station Data Validation")
    
    # Valid station
    valid_station = {
        'id': 'TEST_STATION_001',
        'name': 'München Hauptbahnhof',
        'name_normalized': main.normalize_station_name('München Hauptbahnhof'),
        'eva': 8000261,
        'lat': 48.1400,
        'lon': 11.5583,
        'ds100': 'MH',
        'platforms': ['1', '2', '3', '4'],
        'external_ids': {'hafas': 'test_id'},
        'metadata': {'state': 'Bayern', 'category': '1'}
    }
    
    is_valid, errors = main.validate_station_data(valid_station)
    assert is_valid, f"Valid station should pass validation: {errors}"
    print("  ✓ Valid station data: PASSED")
    
    # Invalid station (missing required fields)
    invalid_station = {
        'id': '',
        'name': '',
        'eva': 123  # Invalid EVA
    }
    
    is_valid, errors = main.validate_station_data(invalid_station)
    assert not is_valid, "Invalid station should fail validation"
    assert len(errors) > 0, "Invalid station should have errors"
    print(f"  ✓ Invalid station rejected with {len(errors)} errors")
    print("✅ Station data validation: PASSED")
    
    # Test 6: Service Data Validation
    print("\n🚆 Test 6: Service Data Validation")
    
    # Valid service
    valid_service = {
        'id': 'ICE_123_20240101',
        'product': 'ICE',
        'stops': [
            {
                'station_id': 'TEST_STATION_001',
                'sequence': 0,
                'departure_planned': '2024-01-01T08:00:00Z',
                'platform': '1'
            },
            {
                'station_id': 'TEST_STATION_002',
                'sequence': 1,
                'arrival_planned': '2024-01-01T10:00:00Z',
                'platform': '2'
            }
        ],
        'operating_days': {
            'monday': True, 'tuesday': True, 'wednesday': True,
            'thursday': True, 'friday': True, 'saturday': False, 'sunday': False
        }
    }
    
    is_valid, errors = main.validate_service_data(valid_service)
    assert is_valid, f"Valid service should pass validation: {errors}"
    print("  ✓ Valid service data: PASSED")
    
    # Invalid service (invalid sequence)
    invalid_service = {
        'id': 'ICE_INVALID',
        'product': 'ICE',
        'stops': [
            {
                'station_id': 'TEST_STATION_001',
                'sequence': 0,
                'departure_planned': '2024-01-01T10:00:00Z'
            },
            {
                'station_id': 'TEST_STATION_002',
                'sequence': 2,  # Invalid sequence (should be 1)
                'arrival_planned': '2024-01-01T08:00:00Z'  # Invalid time (before departure)
            }
        ],
        'operating_days': {
            'monday': True, 'tuesday': True, 'wednesday': True,
            'thursday': True, 'friday': True, 'saturday': False, 'sunday': False
        }
    }
    
    is_valid, errors = main.validate_service_data(invalid_service)
    assert not is_valid, "Invalid service should fail validation"
    print(f"  ✓ Invalid service rejected with {len(errors)} errors")
    print("✅ Service data validation: PASSED")
    
    # Test 7: Adjacency Computation
    print("\n🗺️ Test 7: Adjacency Computation")
    
    stations = [
        {'id': 'STA', 'name': 'Station A'},
        {'id': 'STB', 'name': 'Station B'},
        {'id': 'STC', 'name': 'Station C'}
    ]
    
    services = [
        {
            'id': 'SERVICE_1',
            'product': 'ICE',
            'stops': [
                {'station_id': 'STA', 'sequence': 0, 'departure_planned': '08:00:00Z'},
                {'station_id': 'STB', 'sequence': 1, 'arrival_planned': '09:00:00Z', 'departure_planned': '09:05:00Z'},
                {'station_id': 'STC', 'sequence': 2, 'arrival_planned': '10:00:00Z'}
            ],
            'operating_days': {'monday': True, 'tuesday': True, 'wednesday': True, 'thursday': True, 'friday': True, 'saturday': False, 'sunday': False}
        }
    ]
    
    routing_data = main.precompute_adjacency_data(stations, services)
    
    assert 'adjacency' in routing_data, "Routing data should contain adjacency"
    assert 'route_segments' in routing_data, "Routing data should contain route segments"
    assert len(routing_data['route_segments']) == 2, "Should have 2 route segments (A→B, B→C)"
    assert 'STA' in routing_data['adjacency'], "Station A should be in adjacency"
    assert 'STB' in routing_data['adjacency']['STA'], "Station A should connect to B"
    
    print(f"  ✓ Generated adjacency for {routing_data['total_stations']} stations")
    print(f"  ✓ Generated {routing_data['total_segments']} route segments")
    print("✅ Adjacency computation: PASSED")
    
    # Test 8: Version Update with Statistics
    print("\n📊 Test 8: Version Update with Statistics")
    
    stats = {
        'total_stations': len(stations),
        'total_services': len(services),
        'last_updated': datetime.utcnow().isoformat() + "Z"
    }
    
    updated = main.update_timetables_version(stats)
    assert updated, "Version update should succeed"
    
    # Verify the update
    updated_version = main.load_timetables_version()
    assert updated_version['statistics']['total_stations'] == len(stations), "Statistics should be updated"
    assert updated_version['statistics']['total_services'] == len(services), "Statistics should be updated"
    
    print(f"  ✓ Updated version with {stats['total_stations']} stations, {stats['total_services']} services")
    print("✅ Version update with statistics: PASSED")
    
    # Test 9: Hash Computation
    print("\n🔐 Test 9: Hash Computation")
    
    timetables_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "Timetables-1.0.213.yaml")
    file_hash = main.compute_file_hash(timetables_path)
    
    assert file_hash is not None, "Hash computation should succeed"
    assert len(file_hash) == 64, "SHA256 hash should be 64 characters"
    assert updated_version['file_sha256'] == file_hash, "Version file should contain correct hash"
    
    print(f"  ✓ Computed SHA256: {file_hash[:16]}...")
    print("✅ Hash computation: PASSED")
    
    print("\n🎉 All tests passed! Masterdata processing pipeline is working correctly.")
    return True

if __name__ == "__main__":
    try:
        success = test_masterdata_processing()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)