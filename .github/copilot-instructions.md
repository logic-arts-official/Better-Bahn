# Better-Bahn Development Instructions

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Project Overview

Better-Bahn is a dual-platform application for finding cheaper split-ticket options for Deutsche Bahn journeys:

1. **Python CLI tool** (`main.py`) - Core split-ticket analysis logic
2. **Flutter mobile app** (`flutter-app/`) - Cross-platform UI for Android/iOS  
3. **Documentation site** - GitHub Pages deployment from `docs/`

**CRITICAL**: This application uses web scraping of Deutsche Bahn APIs (NOT official APIs). Network requests will fail in sandboxed environments but the application logic works correctly.

## Working Effectively

### Bootstrap and Setup
- **Python 3.12** is required (check `.python-version`)
- Install uv package manager: `pip install uv` (takes ~4 seconds)
- Setup Python environment: `export PATH="$HOME/.local/bin:$PATH" && uv sync` (takes ~0.1 seconds)
- **Flutter SDK 3.8.1+** required for mobile development

### Essential Commands

#### Python CLI Development
- **Help command**: `uv run python main.py --help`
- **Test with example URL**: `uv run python main.py "https://www.bahn.de/buchung/start?vbid=9dd9db26-4ffc-411c-b79c-e82bf5338989" --age 30`
  - Expected: Network error in sandboxed environments, but command parsing works
- **Test departure board demo**: `uv run python main.py --departure-board --station "Berlin" --demo` (works offline)
- **Standalone departure board CLI**: `./departure_board_cli.py --help` (separate executable)
- **Syntax check**: `python -m py_compile main.py`
- **Install linting**: `pip install ruff` (takes ~2 seconds)
- **Lint code**: `ruff check main.py` 
- **Format code**: `ruff format main.py`
- **Install tests**: `uv add pytest` (takes ~69ms)
- **Run tests**: `uv run python -m pytest test_masterdata_loader.py -v` (13 tests in ~0.43 seconds)

#### Flutter App Development  
- **Change to Flutter directory**: `cd flutter-app`
- **Install Flutter dependencies**: `flutter pub get` (NEVER CANCEL: takes ~5.5 seconds first time, 2-5 minutes on slower systems)
- **Run Flutter linting**: `flutter analyze` (takes ~12 seconds)
- **Build for Android (debug)**: `flutter build apk --debug` (NEVER CANCEL: takes ~4 minutes. Set timeout to 10+ minutes)
- **Build for Android (release)**: `flutter build apk` (NEVER CANCEL: takes 10-15 minutes. Set timeout to 30+ minutes)
- **Run app**: `flutter run` (requires Android emulator or device)

**NOTE**: Flutter commands may fail in environments without proper SDK installation. Document network access requirements.

## Validation Requirements

### Manual Testing Checklist
After making any code changes, ALWAYS run:

1. **Python CLI validation**:
   - `uv run python main.py --help` - Verify help text displays correctly
   - `uv run python main.py "invalid-url"` - Verify error handling works ("Der lange URL ist unvollständig.")
   - `uv run python main.py "https://www.bahn.de/buchung/start?vbid=test" --bahncard BC25_2 --deutschland-ticket` - Verify parameter parsing
   - `uv run python main.py "https://www.bahn.de/buchung/start?vbid=abc123" --age 25 --bahncard BC50_2 --deutschland-ticket` - Test all parameter combinations
   - `uv run python main.py --departure-board --station "Berlin" --demo` - Test departure board demo mode

2. **Code quality validation**:
   - `python -m py_compile main.py` - Check syntax (should complete silently)
   - `ruff check main.py` - Check for code issues (may show fixable issues) 
   - `ruff check main.py --fix` - Auto-fix issues (should show "Found X errors (X fixed, 0 remaining)")
   - `ruff format main.py` - Format code consistently
   - Verify `ruff check main.py` passes after auto-fix

3. **Flutter validation** (when modifying Flutter app):
   - `cd flutter-app && flutter analyze` - Check Dart code quality (~12 seconds)
   - `flutter pub get` - Ensure dependencies resolve (~5.5 seconds)
   - Verify `pubspec.yaml` dependencies are compatible
   - Check that all asset paths exist (fonts in `assets/fonts/`, icons in `assets/icon/`)
   - `flutter build apk --debug` - Test debug build (~4 minutes, NEVER CANCEL)

### Complete User Workflow Testing
Run this complete scenario after making significant changes:

```bash
# Environment setup (do once)
export PATH="$HOME/.local/bin:$PATH"
pip install uv
uv sync
pip install ruff

# Test workflow
uv run python main.py --help
uv run python main.py "https://www.bahn.de/buchung/start?vbid=test-vbid" --age 30 --bahncard BC25_1
python -m py_compile main.py
ruff check main.py --fix
ruff check main.py  # Should pass after fix
uv run python main.py --departure-board --station "Hamburg" --demo  # Test offline features
```

**Expected Results**:
- Help command shows all options including BahnCard choices and Deutschland-Ticket flag
- Test vbid shows network error but processes parameters correctly  
- Syntax check passes silently
- Ruff auto-fixes any style issues and final check passes

### Expected Timeouts and Durations
- **uv sync**: ~0.1 seconds (very fast!)
- **pip install uv**: ~4 seconds
- **pip install ruff**: ~2 seconds  
- **uv add pytest**: ~69ms (adding dependencies to uv project)
- **flutter pub get**: ~5.5 seconds (first time, 2-5 minutes on slower systems) (NEVER CANCEL - set timeout to 10+ minutes)
- **flutter analyze**: ~12 seconds
- **flutter build apk --debug**: ~4 minutes (debug build, faster than release)
- **flutter build apk**: 10-15 minutes (release build, NEVER CANCEL - set timeout to 30+ minutes)
- **ruff check/format**: ~0.01 seconds
- **uv run python main.py commands**: ~0.6 seconds (includes masterdata loading and network error time)
- **pytest test run**: ~0.43 seconds for 13 tests
- **Complete workflow test**: ~1.2 seconds (full validation scenario)

## Project Structure

```
Better-Bahn/
├── main.py                 # Python CLI tool (core logic)
├── pyproject.toml         # Python dependencies  
├── uv.lock               # Dependency lock file
├── .python-version       # Python 3.12
├── flutter-app/          # Mobile app source
│   ├── lib/main.dart     # Flutter app main file
│   ├── pubspec.yaml      # Flutter dependencies
│   ├── analysis_options.yaml # Flutter linting config
│   └── android/          # Android build configuration
├── departure_board_cli.py   # Standalone departure board CLI
├── tests/              # Test utilities and unit tests
│   ├── run_all_tests.py  # Test runner script
│   └── test_*.py       # Individual test modules
├── test_*.py           # Root-level test files (require pytest)
├── assets/              # App icons and screenshots
├── docs/                # Documentation (technical, user guides)
├── .github/
│   └── workflows/
│       └── jekyll-gh-pages.yml # GitHub Pages deployment
└── README.md           # Main project description (German)
```

## Common Development Patterns

### Python Code Standards
- Follow PEP 8 compliance (use `ruff format`)
- Handle network errors gracefully (requests will fail in sandboxed environments)
- Use type hints for function parameters
- Add docstrings for new functions
- Test CLI argument parsing thoroughly
- **BahnCard validation**: Only BC25_1, BC25_2, BC50_1, BC50_2 are supported (see argparse choices in main.py)
- **URL parsing**: Supports both long URLs and short vbid format links
- **Error handling**: All network requests should include try/catch for connection errors

### Flutter Code Standards  
- Follow Dart style guide
- Use `flutter_lints` rules (configured in `analysis_options.yaml`)
- Break complex widgets into smaller components
- Handle network errors gracefully in UI
- Test on multiple screen sizes
- **Design System**: Uses DB Design System v3.1.1 with Google Fonts Lato (replacing proprietary DB fonts)
- **Theme support**: Implements both light and dark themes (`DBTheme.lightTheme`, `DBTheme.darkTheme`)
- **State management**: Uses StatefulWidget pattern for user interactions

### Network Access Limitations
- **CRITICAL**: All Deutsche Bahn API calls will fail in sandboxed environments
- Test application logic without relying on actual network responses
- Verify error handling paths work correctly
- Use mock data for UI testing when needed
- **Expected errors**: `NameResolutionError` and `HTTPSConnectionPool` errors are normal in CI
- **API endpoints**: Uses `www.bahn.de/web/api/angebote/*` endpoints (see main.py lines 35-47)

### Code Architecture 
- **main.py** (383 lines): Contains core logic with argparse CLI, dynamic programming algorithm for split-ticket optimization
- **Flutter app**: Material Design app with URL input, age/BahnCard configuration, results display
- **No database**: Stateless application, all data fetched from Deutsche Bahn APIs
- **Algorithm**: O(N²) time complexity for N stations using dynamic programming (see lines 200-226)

## Key Files to Monitor

### When changing main.py:
- Always run `ruff check main.py` before committing
- Test with `uv run python main.py --help` to verify CLI still works
- Check that new BahnCard options follow existing pattern: `BC25_1`, `BC25_2`, `BC50_1`, `BC50_2`
- Run related tests: `uv run python -m pytest test_masterdata_loader.py -v`

### When changing Flutter app:
- Always run `cd flutter-app && flutter analyze`
- Verify `pubspec.yaml` version constraints are compatible
- Check that asset paths in `pubspec.yaml` are correct
- Test that app builds: `flutter build apk --debug` (allow 10+ minutes) or `flutter build apk` for release (allow 30+ minutes)
- **CRITICAL**: NEVER CANCEL Flutter builds - they may take up to 15+ minutes but will complete successfully

### When updating documentation:
- Check links in `docs/README.md` still work
- Verify German documentation consistency in README.md
- Update `docs/CONTRIBUTING.md` if development process changes

## Repository-Specific Notes

- **Language**: Primary documentation is in German
- **No official API**: Uses web scraping, so network calls fail in CI
- **BahnCard options**: Limited to BC25_1, BC25_2, BC50_1, BC50_2
- **Deutschland-Ticket**: Boolean flag for ticket integration
- **GitHub Pages**: Documentation automatically deployed via Jekyll
- **Test infrastructure**: pytest-based tests exist (run with `uv add pytest` first)
- **Executable scripts**: `departure_board_cli.py` for standalone departure board functionality
- **Demo modes**: Both main CLI and departure board support `--demo` for offline testing

## Troubleshooting

### Common Issues:
1. **"uv not found"**: Run `pip install uv` first
2. **"Flutter not found"**: Flutter SDK installation required for mobile development  
3. **Network errors**: Expected in sandboxed environments - verify error handling works
4. **Linting errors**: Run `ruff format main.py` and `ruff check main.py --fix` to auto-fix formatting issues
5. **Flutter build failures**: Ensure proper Android SDK setup, allow 15+ minute timeouts
6. **Import errors**: Check `pyproject.toml` dependencies and run `uv sync`
7. **Permission errors**: Ensure PATH includes `$HOME/.local/bin` for user-installed packages
8. **Test failures**: Run `uv add pytest` to install test dependencies, then `uv run python -m pytest test_*.py -v`

### Quick Fixes:
- **Python syntax error**: `python -m py_compile main.py`
- **Import error**: Check `pyproject.toml` dependencies and run `uv sync`
- **Flutter dependency error**: `cd flutter-app && flutter pub get`
- **Formatting issues**: `ruff format main.py` then `ruff check main.py --fix`
- **CLI parsing issues**: Check argparse configuration in main.py (lines 269-290)
- **Test command**: Run `uv run python -m pytest test_masterdata_loader.py -v` to verify test infrastructure

### CI/CD and Automation Considerations:
- **Test infrastructure exists**: pytest-based tests available - install with `uv add pytest`
- **No Flutter CI**: Flutter builds must be done manually (no GitHub Actions workflow)
- **Documentation only**: Only GitHub Pages deployment is automated (Jekyll from `docs/`)
- **Manual validation required**: All changes require manual testing as documented above
- **Sandboxed limitations**: Network requests to Deutsche Bahn APIs will always fail in CI environments
- **Demo modes available**: Use `--demo` flags for offline testing and validation

Remember: NEVER CANCEL long-running Flutter commands. They may take 15+ minutes but will complete successfully.