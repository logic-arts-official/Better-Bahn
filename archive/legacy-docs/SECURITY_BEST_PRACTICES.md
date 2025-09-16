# Security Best Practices for Better-Bahn

This document establishes security guidelines and best practices for the Better-Bahn project to prevent vulnerabilities and maintain secure development practices.

## Code Security Guidelines

### 1. HTTP Request Security

#### Always Use Timeouts
```python
# ✅ GOOD - With timeout
response = requests.get(url, headers=headers, timeout=30)

# ❌ BAD - No timeout (DoS vulnerability)
response = requests.get(url, headers=headers)
```

```dart
// ✅ GOOD - With timeout
final response = await http.get(uri).timeout(Duration(seconds: 30));

// ❌ BAD - No timeout
final response = await http.get(uri);
```

#### Use Secure Headers
```python
# ✅ GOOD - Security headers
headers = {
    "User-Agent": "Better-Bahn/1.0 (https://github.com/logic-arts-official/Better-Bahn)",
    "Accept": "application/json",
    "Content-Type": "application/json; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest"
}

# ❌ BAD - Minimal headers
headers = {"User-Agent": "Mozilla/5.0"}
```

#### HTTPS Only
```python
# ✅ GOOD - HTTPS enforced
def validate_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_DOMAINS

# ❌ BAD - HTTP allowed
if url.startswith("http://") or url.startswith("https://"):
```

### 2. Input Validation

#### URL Validation
```python
ALLOWED_DOMAINS = ["www.bahn.de", "bahn.de"]

def validate_bahn_url(url: str) -> bool:
    """Validate that URL is from Deutsche Bahn and uses HTTPS"""
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https" and
            parsed.hostname in ALLOWED_DOMAINS and
            len(url) < 2048  # Prevent excessively long URLs
        )
    except Exception:
        return False
```

#### Data Sanitization
```python
def sanitize_user_input(data: str) -> str:
    """Sanitize user input to prevent injection attacks"""
    if not isinstance(data, str):
        raise ValueError("Input must be string")
    
    # Remove potentially dangerous characters
    dangerous_chars = ["<", ">", "\"", "'", "&", ";", "(", ")", "|", "`"]
    for char in dangerous_chars:
        data = data.replace(char, "")
    
    return data.strip()[:500]  # Limit length
```

### 3. Error Handling

#### Secure Error Messages
```python
# ✅ GOOD - Generic error for users, detailed logging
def handle_api_error(response, debug=False):
    if debug:
        logger.error(f"API Error: {response.status_code} - {response.text}")
    
    # Generic message for users
    if response.status_code == 404:
        return "Verbindung nicht gefunden"
    elif response.status_code >= 500:
        return "Serverfehler, bitte später versuchen"
    else:
        return "Ein Fehler ist aufgetreten"

# ❌ BAD - Exposing internal details
return f"API Error: {response.text}"
```

#### Exception Handling
```python
# ✅ GOOD - Specific exception handling
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
except requests.exceptions.Timeout:
    logger.warning("Request timeout for URL: %s", url)
    raise ConnectionError("Verbindung zeitüberschritten")
except requests.exceptions.ConnectionError:
    logger.warning("Connection failed for URL: %s", url)
    raise ConnectionError("Verbindung fehlgeschlagen")
except requests.exceptions.HTTPError as e:
    logger.error("HTTP error: %s", e)
    raise APIError("API-Fehler aufgetreten")

# ❌ BAD - Generic exception handling
try:
    response = requests.get(url)
except Exception as e:
    print(f"Error: {e}")
```

## Android Security Configuration

### 1. Production Signing
```kotlin
// build.gradle.kts
android {
    signingConfigs {
        create("release") {
            storeFile = file("../keystore/release.jks")
            storePassword = System.getenv("KEYSTORE_PASSWORD")
            keyAlias = System.getenv("KEY_ALIAS")
            keyPassword = System.getenv("KEY_PASSWORD")
        }
    }
    
    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}
```

### 2. Network Security Config
```xml
<!-- android/app/src/main/res/xml/network_security_config.xml -->
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="false">
        <domain includeSubdomains="true">bahn.de</domain>
        <domain includeSubdomains="true">www.bahn.de</domain>
    </domain-config>
    <base-config cleartextTrafficPermitted="false" />
</network-security-config>
```

### 3. Manifest Security
```xml
<!-- AndroidManifest.xml -->
<application
    android:allowBackup="false"
    android:networkSecurityConfig="@xml/network_security_config"
    android:usesCleartextTraffic="false">
</application>
```

## Dependency Management

### 1. Regular Updates
```bash
# Python dependencies
pip install --upgrade pip
pip-audit  # Check for vulnerabilities
pip list --outdated

# Flutter dependencies  
flutter pub upgrade
flutter pub deps
```

### 2. Version Pinning
```toml
# pyproject.toml - Pin major versions
dependencies = [
    "requests>=2.32.0,<3.0.0",
    "pyyaml>=6.0,<7.0",
]
```

```yaml
# pubspec.yaml - Pin versions
dependencies:
  http: ^1.1.0  # Allow minor updates
  url_launcher: ^6.1.12
```

## CI/CD Security

### 1. Security Scanning Workflow
```yaml
# .github/workflows/security.yml
name: Security Scan

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'  # Weekly scan

jobs:
  security:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
          
      - name: Install security tools
        run: |
          pip install bandit safety pip-audit
          
      - name: Run Bandit
        run: bandit -r . -f json -o bandit-report.json
        
      - name: Check dependencies
        run: |
          pip-audit --format=json --output=pip-audit-report.json
          safety check --json --output=safety-report.json
          
      - name: Upload security reports
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: security-reports
          path: "*-report.json"
```

### 2. Secrets Management
```yaml
# Use GitHub Secrets for sensitive data
env:
  KEYSTORE_PASSWORD: ${{ secrets.KEYSTORE_PASSWORD }}
  KEY_ALIAS: ${{ secrets.KEY_ALIAS }}
  KEY_PASSWORD: ${{ secrets.KEY_PASSWORD }}
```

## Development Guidelines

### 1. Code Review Checklist

Before merging any code, verify:
- [ ] All HTTP requests have timeout configurations
- [ ] Input validation is implemented for user data
- [ ] Error messages don't expose sensitive information
- [ ] New dependencies are from trusted sources
- [ ] Security headers are included in API calls
- [ ] No hardcoded secrets or credentials
- [ ] HTTPS is enforced for all external calls

### 2. Security Testing

#### Unit Tests for Security
```python
def test_url_validation():
    # Valid URLs
    assert validate_bahn_url("https://www.bahn.de/buchung/start?vbid=123")
    assert validate_bahn_url("https://bahn.de/path")
    
    # Invalid URLs
    assert not validate_bahn_url("http://www.bahn.de/path")  # HTTP
    assert not validate_bahn_url("https://evil.com/path")   # Wrong domain
    assert not validate_bahn_url("javascript:alert(1)")     # Malicious

def test_request_timeout():
    with patch('requests.get') as mock_get:
        make_api_request("https://www.bahn.de/api/test")
        mock_get.assert_called_with(
            "https://www.bahn.de/api/test",
            headers=ANY,
            timeout=30
        )
```

#### Integration Tests
```python
def test_api_error_handling():
    """Test that API errors are handled securely"""
    with requests_mock.Mocker() as m:
        m.get("https://www.bahn.de/api/test", status_code=500)
        
        result = make_api_request("https://www.bahn.de/api/test")
        
        # Should not expose internal error details
        assert "500" not in result["error"]
        assert "internal" not in result["error"].lower()
```

## Incident Response

### 1. Security Issue Response
When a security issue is discovered:

1. **Immediate:** Stop using affected code/systems
2. **Within 1 hour:** Assess impact and create incident ticket
3. **Within 4 hours:** Develop and test fix
4. **Within 24 hours:** Deploy fix and notify users if needed
5. **Within 1 week:** Conduct post-incident review

### 2. Disclosure Policy
- **Internal issues:** Fix immediately, document in changelog
- **User-affecting issues:** Security advisory + coordinated disclosure
- **Critical vulnerabilities:** Immediate patch release

## Tools and Resources

### Security Tools
- **Bandit:** Python security linter
- **Safety:** Python dependency vulnerability scanner
- **pip-audit:** Python package vulnerability scanner
- **Flutter Analyze:** Dart/Flutter static analysis
- **OWASP ZAP:** Web application security scanner

### Security Resources
- [OWASP Mobile Security](https://owasp.org/www-project-mobile-security/)
- [Android Security Best Practices](https://developer.android.com/training/best-security)
- [Flutter Security Best Practices](https://docs.flutter.dev/security)
- [Python Security Guidelines](https://python.org/dev/security/)

## Regular Security Tasks

### Weekly
- [ ] Review new dependencies for vulnerabilities
- [ ] Check security scanner outputs in CI/CD
- [ ] Review access logs for suspicious activity

### Monthly  
- [ ] Update all dependencies
- [ ] Review and rotate any secrets/keys
- [ ] Security scan of built applications

### Quarterly
- [ ] Full security audit of codebase
- [ ] Penetration testing (if applicable)
- [ ] Review and update security policies
- [ ] Security training for team members

---

**Remember:** Security is everyone's responsibility. When in doubt, choose the more secure option and consult with security-focused team members.