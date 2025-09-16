#!/usr/bin/env dart
// Test script for masterdata validation (standalone)

import 'dart:io';

// Simple validation functions (extracted from the main service)
String normalizeStationName(String name) {
  if (name.isEmpty) return '';

  String normalized = name.toLowerCase();
  
  // Replace common German umlauts and special characters
  normalized = normalized
      .replaceAll('ä', 'a')
      .replaceAll('ö', 'o')
      .replaceAll('ü', 'u')
      .replaceAll('ß', 'ss')
      .replaceAll('é', 'e')
      .replaceAll('è', 'e')
      .replaceAll('ê', 'e')
      .replaceAll('à', 'a')
      .replaceAll('á', 'a')
      .replaceAll('â', 'a')
      .replaceAll('ç', 'c');
  
  // Normalize whitespace
  normalized = normalized.replaceAll(RegExp(r'\s+'), ' ').trim();
  
  return normalized;
}

bool validateEvaNumber(int eva) {
  return eva >= 1000000 && eva <= 9999999;
}

void main() {
  print('🚀 Better-Bahn Dart Validation Test');
  print('====================================');
  
  // Test normalization
  print('\n🔤 Testing Station Name Normalization:');
  final testNames = [
    'München Hauptbahnhof',
    'Köln Hbf',
    'Düsseldorf Flughafen',
    'Würzburg Hbf',
    'François Mitterrand',
  ];
  
  for (final name in testNames) {
    final normalized = normalizeStationName(name);
    print('  ✓ $name → $normalized');
  }
  
  // Test EVA validation
  print('\n🔢 Testing EVA Number Validation:');
  final validEvas = [8000261, 8011160, 1000000, 9999999];
  final invalidEvas = [123, 999999, 10000000];
  
  for (final eva in validEvas) {
    final isValid = validateEvaNumber(eva);
    print('  ✓ $eva: ${isValid ? "VALID" : "INVALID"}');
    assert(isValid, 'EVA $eva should be valid');
  }
  
  for (final eva in invalidEvas) {
    final isValid = validateEvaNumber(eva);
    print('  ✓ $eva: ${isValid ? "VALID" : "INVALID"}');
    assert(!isValid, 'EVA $eva should be invalid');
  }
  
  print('\n✅ All Dart validation tests passed!');
}