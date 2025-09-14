import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'package:url_launcher/url_launcher.dart';

// 12-Factor App imports
import 'config/app_config.dart';
import 'services/logging_service.dart';
import 'services/app_state_service.dart';
import 'services/bahn_api_service.dart';
import 'debug/debug_menu.dart';

void main() {
  // Factor 3: Validate configuration at startup
  try {
    AppConfig.validateConfig();
    LoggingService.info('App starting with environment: ${AppConfig.environment}');
    LoggingService.logAppLifecycle('app_start');
  } catch (e) {
    LoggingService.fatal('Configuration validation failed', error: e);
    // In a real app, you might want to show an error dialog here
  }
  
  runApp(const SplitTicketApp());
}

class SplitTicketApp extends StatelessWidget {
  const SplitTicketApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Better Bahn',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFFEC0016), // DB Red
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFFEC0016), // DB Red
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      themeMode: ThemeMode.system,
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() =>
      _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final TextEditingController _urlController = TextEditingController();
  final TextEditingController _ageController = TextEditingController(text: "30");
  final TextEditingController _delayController = TextEditingController(
    text: AppConfig.defaultDelayMs.toString(),
  );
  final ScrollController _scrollController = ScrollController();
  
  // 12-Factor: Use proper state management service
  late final AppStateService _stateService;
  late final BahnApiService _apiService;
  
  bool _hasDeutschlandTicket = false;
  String? _selectedBahnCard;

  // BahnCard options
  final List<Map<String, String?>> _bahnCardOptions = [
    {'value': null, 'label': 'Keine BahnCard'},
    {'value': 'BC25_1', 'label': 'BahnCard 25, 1. Klasse'},
    {'value': 'BC25_2', 'label': 'BahnCard 25, 2. Klasse'},
    {'value': 'BC50_1', 'label': 'BahnCard 50, 1. Klasse'},
    {'value': 'BC50_2', 'label': 'BahnCard 50, 2. Klasse'},
  ];

  @override
  void initState() {
    super.initState();
    
    // Initialize services following 12-Factor principles
    _stateService = AppStateService();
    _apiService = HttpBahnApiService();
    
    LoggingService.logAppLifecycle('home_page_init');
  }

  @override
  void dispose() {
    // Factor 9: Clean disposal of resources
    LoggingService.info('Disposing HomePage resources');
    
    _urlController.dispose();
    _ageController.dispose();
    _delayController.dispose();
    _scrollController.dispose();
    _stateService.dispose();
    
    if (_apiService is HttpBahnApiService) {
      (_apiService as HttpBahnApiService).dispose();
    }
    
    LoggingService.logAppLifecycle('home_page_dispose');
    super.dispose();
  }

  void _addLog(String message) {
    _stateService.addLogMessage(message);
  }

  void _updateProgress(int processed, int total) {
    _stateService.updateProgress(processed, total);
  }

  // Create traveller payload based on age and BahnCard
  List<Map<String, dynamic>> _createTravellerPayload() {
    Map<String, dynamic> ermaessigung = {
      "art": "KEINE_ERMAESSIGUNG",
      "klasse": "KLASSENLOS",
    };

    if (_selectedBahnCard != null) {
      final parts = _selectedBahnCard!.split('_');
      final bcTyp = parts[0].substring(2); // Extract '25' or '50'
      final klasse = parts[1];

      ermaessigung = {
        "art": "BAHNCARD$bcTyp",
        "klasse": "KLASSE_$klasse",
      };
    }

    return [
      {
        "typ": "ERWACHSENER",
        "ermaessigungen": [ermaessigung],
        "anzahl": 1,
        "alter": [],
      },
    ];
  }

  String _generateBookingLink(SplitTicket ticket) {
    final baseUrl = "https://www.bahn.de/buchung/fahrplan/suche";

    final so = Uri.encodeComponent(ticket.from);
    final zo = Uri.encodeComponent(ticket.to);
    final soid = Uri.encodeComponent(ticket.fromId);
    final zoid = Uri.encodeComponent(ticket.toId);
    final hd = Uri.encodeComponent(ticket.departureIso.split('.')[0]);
    final dltv = _hasDeutschlandTicket.toString().toLowerCase();
    String rParam = "";

    if (_selectedBahnCard != null) {
      final bcMap = {
        'BC25_2': '13:25:KLASSE_2:1',
        'BC25_1': '13:25:KLASSE_1:1',
        'BC50_2': '13:50:KLASSE_2:1',
        'BC50_1': '13:50:KLASSE_1:1',
      };
      final rCode = bcMap[_selectedBahnCard];
      if (rCode != null) {
        rParam = "&r=${Uri.encodeComponent(rCode)}";
      }
    }

    return "$baseUrl#sts=true&so=$so&zo=$zo&soid=$soid&zoid=$zoid&hd=$hd&dltv=$dltv$rParam";
  }

  Future<void> _analyzeUrl(String url) async {
    if (url.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Bitte gib einen DB-Link ein')),
      );
      return;
    }

    // Start analysis using state service
    _stateService.startAnalysis();

    try {
      _addLog("Starte Analyse für URL: $url");

      // Get traveller payload
      final travellerPayload = _createTravellerPayload();
      final int age = int.tryParse(_ageController.text) ?? 30;

      _addLog(
        "Reisender: Alter $age" +
            (_selectedBahnCard != null ? ", mit $_selectedBahnCard" : ", ohne BahnCard") +
            (_hasDeutschlandTicket ? ", mit Deutschland-Ticket" : ", ohne Deutschland-Ticket"),
      );

      // Parse URL to extract vbid or station IDs
      String urlToParse = url;
      if (url.contains("/buchung/start")) {
        final Uri uri = Uri.parse(url);
        final vbid = uri.queryParameters['vbid'];
        if (vbid != null) {
          urlToParse = "https://www.bahn.de?vbid=$vbid";
        }
      }

      final Uri uri = Uri.parse(urlToParse);
      Map<String, dynamic> connectionData;
      String dateStr;

      if (urlToParse.contains('vbid=')) {
        // Handle short URL with vbid
        final String vbid = uri.queryParameters['vbid'] ?? '';
        _addLog("VBID erkannt: $vbid");
        
        connectionData = await _apiService.resolveVbidToConnection(
          vbid,
          travellerPayload,
          _hasDeutschlandTicket,
        );

        if (connectionData.isEmpty) {
          throw Exception("Konnte keine Verbindungsdaten für VBID abrufen");
        }

        final firstStop = connectionData['verbindungen'][0]['verbindungsAbschnitte'][0]['halte'][0]['abfahrtsZeitpunkt'];
        dateStr = firstStop.split('T')[0];
      } else {
        // Handle long URL with fragment parameters
        _addLog("Langer URL erkannt, extrahiere Parameter");
        final Map<String, String> params = {};
        if (uri.fragment.isNotEmpty) {
          uri.fragment.split('&').forEach((element) {
            final parts = element.split('=');
            if (parts.length == 2) {
              params[parts[0]] = parts[1];
            }
          });
        }

        if (!params.containsKey('soid') || !params.containsKey('zoid') || !params.containsKey('hd')) {
          throw Exception("URL enthält nicht alle benötigten Parameter");
        }

        final fromStationId = params['soid']!;
        final toStationId = params['zoid']!;
        final dateTimeStr = params['hd']!;
        final dateParts = dateTimeStr.split('T');
        dateStr = dateParts[0];
        final timeStr = dateParts[1];

        _addLog("Von: $fromStationId, Nach: $toStationId, Datum: $dateStr, Zeit: $timeStr");
        
        connectionData = await _apiService.getConnectionDetails(
          fromStationId,
          toStationId,
          dateStr,
          timeStr,
          travellerPayload,
          _hasDeutschlandTicket,
        );
      }

      if (connectionData.isEmpty || !connectionData.containsKey('verbindungen') || connectionData['verbindungen'].isEmpty) {
        throw Exception("Keine Verbindungsdaten gefunden");
      }

      _addLog("Verbindungsdaten erfolgreich abgerufen");

      // Extract direct price
      final firstConnection = connectionData['verbindungen'][0];
      final directPrice = firstConnection['angebotsPreis']?['betrag'];

      if (directPrice == null) {
        throw Exception("Konnte den Direktpreis nicht ermitteln");
      }

      // Convert to double explicitly
      final double directPriceDouble = directPrice is int ? directPrice.toDouble() : directPrice;

      _addLog("Direktpreis gefunden: $directPriceDouble €");

      // Extract all stops
      List<Map<String, dynamic>> allStops = [];
      _addLog("Extrahiere alle Haltestellen der Verbindung");

      for (var section in firstConnection['verbindungsAbschnitte']) {
        if (section['verkehrsmittel']['typ'] != 'WALK') {
          for (var halt in section['halte']) {
            if (!allStops.any((stop) => stop['id'] == halt['id'])) {
              allStops.add({
                'name': halt['name'],
                'id': halt['id'],
                'departure_time': halt['abfahrtsZeitpunkt']?.split('T')[1] ?? '',
                'arrival_time': halt['ankunftsZeitpunkt']?.split('T')[1] ?? '',
                'departure_iso': halt['abfahrtsZeitpunkt'] ?? '',
              });
            }
          }
        }
      }

      if (allStops.isNotEmpty) {
        allStops.last['departure_time'] = allStops.last['arrival_time'];
      }

      _addLog("${allStops.length} eindeutige Haltestellen gefunden:");
      for (var stop in allStops) {
        _addLog("  - ${stop['name']}");
      }

      // Find cheapest split
      final result = await _findCheapestSplit(
        allStops,
        dateStr,
        directPriceDouble,
        travellerPayload,
      );

      // Complete analysis with results
      _stateService.completeAnalysis(
        directPrice: directPriceDouble,
        splitPrice: result.splitPrice,
        splitTickets: result.tickets,
      );

    } catch (e) {
      _addLog("Fehler: $e");
      _stateService.completeAnalysisWithError(e.toString());
    }
  }

  Future<Map<String, dynamic>?> _getSegmentData(
    Map<String, dynamic> fromStop,
    Map<String, dynamic> toStop,
    String date,
    List<Map<String, dynamic>> travellerPayload,
  ) async {
    _addLog("Frage Daten an für: ${fromStop['name']} -> ${toStop['name']}...");

    final delayMs = int.tryParse(_delayController.text) ?? AppConfig.defaultDelayMs;
    await Future.delayed(Duration(milliseconds: delayMs)); // Rate limiting

    final departureTimeStr = fromStop['departure_time'];
    if (departureTimeStr.isEmpty) {
      return null;
    }

    try {
      final connections = await _apiService.getConnectionDetails(
        fromStop['id'],
        toStop['id'],
        date,
        departureTimeStr,
        travellerPayload,
        _hasDeutschlandTicket,
      );

      if (connections.isNotEmpty &&
          connections.containsKey('verbindungen') &&
          connections['verbindungen'].isNotEmpty) {
        final firstConnection = connections['verbindungen'][0];
        final price = firstConnection['angebotsPreis']?['betrag'];

        // Get the actual departure time of the found train for this segment
        final departureIso = firstConnection['verbindungsAbschnitte']?[0]?['halte']?[0]?['abfahrtsZeitpunkt'];

        bool isCoveredByDTicket = false;
        if (_hasDeutschlandTicket) {
          for (var section in firstConnection['verbindungsAbschnitte'] ?? []) {
            final attributes = section['verkehrsmittel']?['zugattribute'] ?? [];
            for (var attr in attributes) {
              if (attr['key'] == '9G') {
                isCoveredByDTicket = true;
                break;
              }
            }
            if (isCoveredByDTicket) break;
          }
        }

        double finalPrice;
        if (isCoveredByDTicket) {
          _addLog(" -> Deutschland-Ticket gültig! Preis wird auf 0.00 € gesetzt.");
          finalPrice = 0.0;
        } else if (price != null) {
          finalPrice = price is int ? price.toDouble() : price;
          _addLog(" -> Preis gefunden: $finalPrice €");
        } else {
          _addLog(" -> Kein Preis für dieses Segment verfügbar.");
          return null;
        }

        if (departureIso != null) {
          return {
            "price": finalPrice,
            "start_name": fromStop['name'],
            "end_name": toStop['name'],
            "start_id": fromStop['id'],
            "end_id": toStop['id'],
            "departure_iso": departureIso,
          };
        }
      }

      _addLog(" -> Keine Verbindungsdaten erhalten.");
      return null;
    } catch (e) {
      LoggingService.error("Error getting segment data", error: e);
      _addLog(" -> Fehler beim Abrufen der Segmentdaten: $e");
      return null;
    }
  }

  Future<TicketAnalysisResult> _findCheapestSplit(
    List<Map<String, dynamic>> stops,
    String date,
    double directPrice,
    List<Map<String, dynamic>> travellerPayload,
  ) async {
    final int n = stops.length;
    final Map<
      String,
      Map<String, dynamic>
    >
    segmentsData = {};

    _addLog(
      "\n--- Preise und Daten für alle möglichen Teilstrecken werden abgerufen ---",
    );

    // Calculate total number of combinations to check
    int totalCombinations = 0;
    for (int i = 0; i < n; i++) {
      for (int j = i + 1; j < n; j++) {
        if (stops[i]['departure_time']
            .isNotEmpty) {
          totalCombinations++;
        }
      }
    }

    _updateProgress(
      0,
      totalCombinations,
    );
    int processedCombinations = 0;

    // Get data for all possible segments
    for (int i = 0; i < n; i++) {
      for (int j = i + 1; j < n; j++) {
        final fromStop = stops[i];
        final toStop = stops[j];

        if (fromStop['departure_time']
            .isEmpty) {
          continue;
        }

        final data =
            await _getSegmentData(
              fromStop,
              toStop,
              date,
              travellerPayload,
            );

        // Update progress
        processedCombinations++;
        _updateProgress(
          processedCombinations,
          totalCombinations,
        );

        if (data != null) {
          final key = "${i}_$j";
          segmentsData[key] = data;
        }
      }
    }

    // Dynamic programming to find cheapest path
    List<double> dp = List.filled(
      n,
      double.infinity,
    );
    dp[0] = 0;
    List<int> pathReconstruction =
        List.filled(n, -1);

    for (int i = 1; i < n; i++) {
      for (int j = 0; j < i; j++) {
        final key = "${j}_$i";
        if (segmentsData.containsKey(
          key,
        )) {
          final cost =
              dp[j] +
              segmentsData[key]!['price'];
          if (cost < dp[i]) {
            dp[i] = cost;
            pathReconstruction[i] = j;
          }
        }
      }
    }

    final cheapestSplitPrice =
        dp[n - 1];

    _addLog(
      "\n=== ERGEBNIS DER ANALYSE ===",
    );

    List<SplitTicket> splitTickets = [];

    if (cheapestSplitPrice <
            directPrice &&
        cheapestSplitPrice !=
            double.infinity) {
      final savings =
          directPrice -
          cheapestSplitPrice;
      _addLog(
        "\n🎉 Günstigere Split-Ticket-Option gefunden! 🎉",
      );
      _addLog(
        "Direktpreis: $directPrice €",
      );
      _addLog(
        "Bester Split-Preis: $cheapestSplitPrice €",
      );
      _addLog(
        "💰 Ersparnis: $savings €",
      );

      List<Map<String, dynamic>> path =
          [];
      int current = n - 1;

      while (current > 0 &&
          pathReconstruction[current] !=
              -1) {
        final prev =
            pathReconstruction[current];
        final key = "${prev}_$current";

        if (segmentsData.containsKey(
          key,
        )) {
          path.add(segmentsData[key]!);
        }

        current = prev;
      }

      path = path.reversed.toList();

      _addLog(
        "\nEmpfohlene Tickets zum Buchen:",
      );
      for (
        int i = 0;
        i < path.length;
        i++
      ) {
        final segment = path[i];
        _addLog(
          "Ticket ${i + 1}: Von ${segment['start_name']} nach ${segment['end_name']} für ${segment['price']} €",
        );

        final ticket = SplitTicket(
          from: segment['start_name'],
          to: segment['end_name'],
          price: segment['price'],
          fromId: segment['start_id'],
          toId: segment['end_id'],
          departureIso:
              segment['departure_iso'],
          coveredByDeutschlandTicket:
              segment['price'] == 0,
        );

        splitTickets.add(ticket);

        if (segment['price'] > 0) {
          final bookingLink =
              _generateBookingLink(
                ticket,
              );
          _addLog(
            "      -> Buchungslink: $bookingLink",
          );
        } else {
          _addLog(
            "      -> (Fahrt durch Deutschland-Ticket abgedeckt)",
          );
        }
      }

      return TicketAnalysisResult(
        directPrice: directPrice,
        splitPrice: cheapestSplitPrice,
        tickets: splitTickets,
      );
    } else {
      _addLog(
        "\nKeine günstigere Split-Option gefunden.",
      );
      _addLog(
        "Das Direktticket für $directPrice € ist die beste Option.",
      );

      return TicketAnalysisResult(
        directPrice: directPrice,
        splitPrice: double.infinity,
        tickets: [],
      );
    }
  }

  Future<void> _launchUrl(String url) async {
    final Uri uri = Uri.parse(url);
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Konnte URL nicht öffnen: $url')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Better Bahn'),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Theme.of(context).colorScheme.onPrimary,
        actions: [
          // Factor 12: Debug menu for admin processes
          if (AppConfig.shouldShowDebugMenu)
            IconButton(
              icon: const Icon(Icons.bug_report),
              onPressed: () {
                LoggingService.logFeatureUsage('debug_menu_opened');
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (context) => const DebugMenu(),
                  ),
                );
              },
              tooltip: 'Debug Menu',
            ),
        ],
      ),
      body: ListenableBuilder(
        listenable: _stateService,
        builder: (context, child) {
          return SingleChildScrollView(
            controller: _scrollController,
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // URL input field
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _urlController,
                          decoration: InputDecoration(
                            labelText: 'DB-Link einfügen',
                            hintText: 'https://www.bahn.de/buchung/start?vbid=...',
                            border: const OutlineInputBorder(),
                            suffixIcon: IconButton(
                              icon: const Icon(Icons.clear),
                              onPressed: () {
                                _urlController.clear();
                              },
                            ),
                          ),
                          keyboardType: TextInputType.url,
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton(
                        onPressed: () async {
                          final data = await Clipboard.getData('text/plain');
                          if (data != null && data.text != null) {
                            final text = data.text!;
                            if (text.contains('bahn.de')) {
                              setState(() {
                                _urlController.text = text;
                              });
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Link aus Zwischenablage eingefügt'),
                                ),
                              );
                            }
                          }
                        },
                        icon: const Icon(Icons.paste),
                        tooltip: 'Aus Zwischenablage einfügen',
                      ),
                    ],
                  ),

                  const SizedBox(height: 16),

                  // Options section
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(12.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Reisende & Rabatte',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                            ),
                          ),
                          const SizedBox(height: 12),

                          // Age and Delay input
                          Row(
                            children: [
                              const Text('Alter:'),
                              const SizedBox(width: 8),
                              SizedBox(
                                width: 60,
                                child: TextField(
                                  controller: _ageController,
                                  keyboardType: TextInputType.number,
                                  inputFormatters: [
                                    FilteringTextInputFormatter.digitsOnly,
                                  ],
                                  decoration: const InputDecoration(
                                    border: OutlineInputBorder(),
                                    contentPadding: EdgeInsets.symmetric(
                                      horizontal: 8,
                                      vertical: 8,
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 16),
                              const Text('Delay (ms):'),
                              const SizedBox(width: 8),
                              SizedBox(
                                width: 80,
                                child: TextField(
                                  controller: _delayController,
                                  keyboardType: TextInputType.number,
                                  inputFormatters: [
                                    FilteringTextInputFormatter.digitsOnly,
                                  ],
                                  decoration: const InputDecoration(
                                    border: OutlineInputBorder(),
                                    contentPadding: EdgeInsets.symmetric(
                                      horizontal: 8,
                                      vertical: 8,
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),

                          const SizedBox(height: 12),

                          // Deutschland-Ticket checkbox
                          CheckboxListTile(
                            title: const Text('Deutschland-Ticket'),
                            value: _hasDeutschlandTicket,
                            onChanged: (value) {
                              setState(() {
                                _hasDeutschlandTicket = value ?? false;
                              });
                            },
                            controlAffinity: ListTileControlAffinity.leading,
                            contentPadding: EdgeInsets.zero,
                            dense: true,
                          ),

                          const SizedBox(height: 12),

                          // BahnCard dropdown
                          DropdownButtonFormField<String?>(
                            decoration: const InputDecoration(
                              labelText: 'BahnCard',
                              border: OutlineInputBorder(),
                              contentPadding: EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 12,
                              ),
                            ),
                            value: _selectedBahnCard,
                            items: _bahnCardOptions.map((option) {
                              return DropdownMenuItem<String?>(
                                value: option['value'],
                                child: Text(option['label']!),
                              );
                            }).toList(),
                            onChanged: (value) {
                              setState(() {
                                _selectedBahnCard = value;
                              });
                            },
                          ),
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 16),

                  // Search button
                  ElevatedButton.icon(
                    onPressed: _stateService.isAnalyzing
                        ? null
                        : () => _analyzeUrl(_urlController.text),
                    icon: const Icon(Icons.search),
                    label: const Text('Verbindung analysieren'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),

                  const SizedBox(height: 16),

                  // Progress indicator during loading
                  if (_stateService.isAnalyzing) ...[
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: LinearProgressIndicator(
                                value: _stateService.progress > 0 
                                    ? _stateService.progress 
                                    : null,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              '${_stateService.processedStations}/${_stateService.totalStations} (${(_stateService.progress * 100).toInt()}%)',
                              style: const TextStyle(fontSize: 12),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Suche nach günstigeren Split-Tickets...',
                          style: TextStyle(fontSize: 14),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                  ],

                  // Results or welcome message
                  _stateService.isAnalyzing
                      ? _buildLogsSection()
                      : _stateService.hasResult
                      ? _buildResultsSection()
                      : _stateService.logMessages.isNotEmpty
                      ? _buildLogsSection()
                      : const Center(
                          child: Padding(
                            padding: EdgeInsets.all(32.0),
                            child: Text(
                              'Füge einen DB-Link ein, um günstigere Split-Ticket-Optionen zu finden.\n\n'
                              'Unterstützte Links:\n'
                              '• Kurze Links: https://www.bahn.de/buchung/start?vbid=...\n'
                              '• Lange Links: https://www.bahn.de/...',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: Colors.grey),
                            ),
                          ),
                        ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildLogsSection() {
    return Column(
      children: [
        // Collapsible logs section
        InkWell(
          onTap: () {
            _stateService.toggleLogVisibility();
          },
          child: Container(
            padding: const EdgeInsets.symmetric(
              vertical: 8,
              horizontal: 12,
            ),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceVariant,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                Icon(
                  _stateService.showLogs
                      ? Icons.keyboard_arrow_up
                      : Icons.keyboard_arrow_down,
                  size: 20,
                ),
                const SizedBox(width: 8),
                const Text(
                  'Logs anzeigen/ausblenden',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),

        // Logs content (collapsible)
        if (_stateService.showLogs)
          SizedBox(
            height: 300,
            child: LogConsole(messages: _stateService.logMessages),
          ),

        // If we have results and logs are shown, show a compact result
        if (_stateService.hasResult && _stateService.showLogs)
          Card(
            margin: const EdgeInsets.only(top: 8),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _stateService.resultText,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text('Direktpreis: ${_stateService.directPrice.toStringAsFixed(2)} €'),
                  if (_stateService.splitPrice < _stateService.directPrice)
                    Text(
                      'Split-Preis: ${_stateService.splitPrice.toStringAsFixed(2)} € (Ersparnis: ${(_stateService.directPrice - _stateService.splitPrice).toStringAsFixed(2)} €)',
                      style: const TextStyle(
                        color: Colors.green,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                ],
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildResultsSection() {
    return Column(
      children: [
        // Result summary card
        Card(
          elevation: 4,
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      _stateService.splitPrice < _stateService.directPrice
                          ? Icons.check_circle
                          : Icons.info,
                      color: _stateService.splitPrice < _stateService.directPrice
                          ? Colors.green
                          : Colors.orange,
                      size: 28,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _stateService.resultText,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
                const Divider(height: 24),
                PriceComparison(
                  directPrice: _stateService.directPrice,
                  splitPrice: _stateService.splitPrice,
                  savings: _stateService.directPrice - _stateService.splitPrice,
                ),
              ],
            ),
          ),
        ),

        const SizedBox(height: 16),

        // Logs toggle
        InkWell(
          onTap: () {
            _stateService.toggleLogVisibility();
          },
          child: Container(
            padding: const EdgeInsets.symmetric(
              vertical: 8,
              horizontal: 12,
            ),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceVariant,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                Icon(
                  _stateService.showLogs
                      ? Icons.keyboard_arrow_up
                      : Icons.keyboard_arrow_down,
                  size: 20,
                ),
                const SizedBox(width: 8),
                const Text(
                  'Logs anzeigen/ausblenden',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
        ),

        const SizedBox(height: 8),

        // Either show logs or tickets
        _stateService.showLogs
            ? SizedBox(
                height: 300,
                child: LogConsole(messages: _stateService.logMessages),
              )
            : _stateService.splitPrice < _stateService.directPrice
            ? Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Empfohlene Tickets:',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  ListView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: _stateService.splitTickets.length,
                    itemBuilder: (context, index) {
                      final ticket = _stateService.splitTickets[index];
                      return TicketCard(
                        ticket: ticket,
                        index: index + 1,
                        onBookPressed: () {
                          if (!ticket.coveredByDeutschlandTicket) {
                            final bookingLink = _generateBookingLink(ticket);
                            _launchUrl(bookingLink);
                          }
                        },
                      );
                    },
                  ),
                ],
              )
            : const Center(
                child: Padding(
                  padding: EdgeInsets.all(32.0),
                  child: Text(
                    'Das Direktticket ist die günstigste Option.',
                    style: TextStyle(fontSize: 16),
                  ),
                ),
              ),
      ],
    );
  }
}

class LogConsole
    extends StatelessWidget {
  final List<String> messages;

  const LogConsole({
    super.key,
    required this.messages,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(
          8.0,
        ),
        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            const Text(
              'Log:',
              style: TextStyle(
                fontWeight:
                    FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: ListView.builder(
                itemCount:
                    messages.length,
                itemBuilder: (context, index) {
                  return Padding(
                    padding:
                        const EdgeInsets.symmetric(
                          vertical: 2,
                        ),
                    child: Text(
                      messages[index],
                      style: const TextStyle(
                        fontFamily:
                            'monospace',
                        fontSize: 12,
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class PriceComparison
    extends StatelessWidget {
  final double directPrice;
  final double splitPrice;
  final double savings;

  const PriceComparison({
    super.key,
    required this.directPrice,
    required this.splitPrice,
    required this.savings,
  });

  @override
  Widget build(BuildContext context) {
    final bool hasBetterOption =
        savings > 0;

    return Column(
      children: [
        Row(
          mainAxisAlignment:
              MainAxisAlignment
                  .spaceBetween,
          children: [
            const Text('Direktpreis:'),
            Text(
              '${directPrice.toStringAsFixed(2)} €',
              style: const TextStyle(
                fontWeight:
                    FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment:
              MainAxisAlignment
                  .spaceBetween,
          children: [
            const Text(
              'Split-Ticket-Preis:',
            ),
            Text(
              splitPrice ==
                      double.infinity
                  ? 'N/A'
                  : '${splitPrice.toStringAsFixed(2)} €',
              style: TextStyle(
                fontWeight:
                    FontWeight.bold,
                color: hasBetterOption
                    ? Colors.green
                    : Colors.grey,
              ),
            ),
          ],
        ),
        if (hasBetterOption) ...[
          const Divider(height: 16),
          Row(
            mainAxisAlignment:
                MainAxisAlignment
                    .spaceBetween,
            children: [
              const Text(
                'Deine Ersparnis:',
                style: TextStyle(
                  fontWeight:
                      FontWeight.bold,
                ),
              ),
              Text(
                '${savings.toStringAsFixed(2)} €',
                style: const TextStyle(
                  fontWeight:
                      FontWeight.bold,
                  color: Colors.green,
                  fontSize: 16,
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }
}

class TicketCard
    extends StatelessWidget {
  final SplitTicket ticket;
  final int index;
  final VoidCallback? onBookPressed;

  const TicketCard({
    super.key,
    required this.ticket,
    required this.index,
    this.onBookPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin:
          const EdgeInsets.symmetric(
            vertical: 8,
          ),
      child: Padding(
        padding: const EdgeInsets.all(
          12.0,
        ),
        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 12,
                  backgroundColor:
                      Theme.of(context)
                          .colorScheme
                          .primary,
                  foregroundColor:
                      Theme.of(context)
                          .colorScheme
                          .onPrimary,
                  child: Text('$index'),
                ),
                const SizedBox(
                  width: 8,
                ),
                Text(
                  'Ticket $index',
                  style:
                      const TextStyle(
                        fontWeight:
                            FontWeight
                                .bold,
                      ),
                ),
                const Spacer(),
                Text(
                  '${ticket.price.toStringAsFixed(2)} €',
                  style:
                      const TextStyle(
                        fontWeight:
                            FontWeight
                                .bold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(
                  Icons.train,
                  size: 16,
                ),
                const SizedBox(
                  width: 8,
                ),
                Expanded(
                  child: Text(
                    '${ticket.from} → ${ticket.to}',
                    style:
                        const TextStyle(
                          fontSize: 16,
                        ),
                  ),
                ),
              ],
            ),
            if (ticket
                .coveredByDeutschlandTicket) ...[
              const SizedBox(height: 8),
              const Row(
                children: [
                  Icon(
                    Icons.check_circle,
                    size: 16,
                    color: Colors.green,
                  ),
                  SizedBox(width: 8),
                  Text(
                    'Mit Deutschland-Ticket abgedeckt',
                    style: TextStyle(
                      color:
                          Colors.green,
                    ),
                  ),
                ],
              ),
            ] else ...[
              const SizedBox(
                height: 12,
              ),
              ElevatedButton.icon(
                onPressed:
                    onBookPressed,
                icon: const Icon(
                  Icons.shopping_cart,
                ),
                label: const Text(
                  'Ticket buchen',
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor:
                      Theme.of(context)
                          .colorScheme
                          .primary,
                  foregroundColor:
                      Theme.of(context)
                          .colorScheme
                          .onPrimary,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
