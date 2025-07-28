# Scanner Authentication Guide

## Overview
The scanner page (`/scanner/`) is the entry point for voter authentication. Voters must successfully authenticate through fingerprint verification to access `voter_home`.

## How the Scanner Authentication Works

### 1. **Voter Access Flow**
```
Voter visits /scanner/ → Places finger on ESP32 → Authentication → Redirect to voter_home
```

### 2. **Technical Process**

#### **Frontend (Scanner Page)**
1. **Page Load**: Scanner page loads with fingerprint verification modal
2. **Scan Simulation**: JavaScript simulates fingerprint scanning process
3. **API Call**: Sends template_hex to `/voting/api/scanner-authenticate/`
4. **Response Handling**: Processes authentication result
5. **Redirect**: On success, redirects to `/voting/voter-home/`

#### **Backend (Django Server)**
1. **Receive Template**: Gets fingerprint template from ESP32
2. **Similarity Matching**: Uses fingerprint_matcher to find best match
3. **Session Creation**: Sets authenticated_voter_id in session
4. **Response**: Returns authentication status and voter info

#### **Hardware (ESP32)**
1. **Finger Detection**: Continuously monitors for finger placement
2. **Template Creation**: Converts fingerprint image to template
3. **Data Transmission**: Sends template_hex to Django server
4. **Response Processing**: Handles authentication response

### 3. **Authentication States**

#### **✅ Success (Status: "ok")**
- Voter authenticated successfully
- Session created with voter_id
- Redirects to `voter_home`
- Console: "✅ Scanner authentication successful: John Doe (confidence: 0.95)"

#### **⚠️ Already Voted (Status: "already_voted")**
- Voter found but has already voted
- Redirects to `already_voted` page
- Console: "⚠️ Voter has already voted"

#### **❌ Not Found (Status: "not_found")**
- Fingerprint not recognized
- Shows error message
- Voter must contact administrator

#### **❌ Connection Error**
- Network/server communication failed
- Shows "Connection error. Please try again."
- Retry button appears

### 4. **API Endpoints**

#### **Scanner Authentication**
```http
POST /voting/api/scanner-authenticate/
Content-Type: application/json

{
    "template_hex": "a1b2c3d4e5f6..."
}
```

**Response (Success):**
```json
{
    "status": "ok",
    "name": "John Doe",
    "confidence": 0.95
}
```

**Response (Already Voted):**
```json
{
    "status": "already_voted",
    "name": "John Doe",
    "confidence": 0.95
}
```

**Response (Not Found):**
```json
{
    "status": "not_found"
}
```

### 5. **Session Management**

#### **Successful Authentication**
```python
# Sets session for authenticated voter
request.session['authenticated_voter_id'] = voter.id
request.session.modified = True
```

#### **Session Usage**
- `voter_home` checks for `authenticated_voter_id`
- Voting functions require authenticated session
- Session persists until logout or vote completion

### 6. **ESP32 Integration**

#### **Hardware Requirements**
- ESP32 with fingerprint sensor (R307/R308)
- WiFi connection
- Arduino IDE with required libraries

#### **Required Libraries**
```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Adafruit_Fingerprint.h>
```

#### **Configuration**
```cpp
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* serverUrl = "http://192.168.1.100:8000";
const char* scannerAuthUrl = "/voting/api/scanner-authenticate/";
```

### 7. **Testing the Authentication**

#### **Without ESP32 (Demo Mode)**
1. Start Django server: `python manage.py runserver`
2. Visit: `http://127.0.0.1:8000/scanner/`
3. Watch console for simulated authentication
4. Check for redirect to `voter_home`

#### **With ESP32 (Production Mode)**
1. Upload `ESP32_Scanner_Authentication.ino` to ESP32
2. Configure WiFi settings in Arduino code
3. Connect ESP32 to fingerprint sensor
4. Place finger on sensor
5. Check Serial Monitor for authentication process
6. Verify redirect to `voter_home`

### 8. **Troubleshooting**

#### **Connection Error**
- Check ESP32 WiFi connection
- Verify Django server is running
- Check network connectivity
- Ensure correct server URL in ESP32 code

#### **Authentication Failed**
- Verify fingerprint template format
- Check fingerprint_matcher configuration
- Ensure voter exists in database
- Check similarity threshold settings

#### **Session Issues**
- Clear browser cookies/session
- Restart Django server
- Check session configuration in settings.py

### 9. **Security Considerations**

#### **Template Security**
- Fingerprint templates are stored as hex strings
- Templates are compared using similarity matching
- No raw fingerprint images are stored

#### **Session Security**
- Sessions are managed by Django
- Authentication required for voting
- Sessions cleared after voting

#### **Network Security**
- Use HTTPS in production
- Implement proper authentication
- Monitor for unauthorized access

### 10. **Complete Flow Example**

#### **Step 1: Voter Approaches Scanner**
```
Voter → Places finger on ESP32 sensor
```

#### **Step 2: ESP32 Processing**
```
ESP32 → Captures fingerprint → Converts to template → Sends to Django
```

#### **Step 3: Django Authentication**
```
Django → Receives template → Matches with database → Creates session
```

#### **Step 4: Frontend Response**
```
Frontend → Receives response → Shows success message → Redirects to voter_home
```

#### **Step 5: Voter Access**
```
Voter → Successfully authenticated → Can access voting interface
```

### 11. **Database Requirements**

#### **Voter Table**
```sql
CREATE TABLE voting_voter (
    id INTEGER PRIMARY KEY,
    voter_id VARCHAR(50) UNIQUE,
    name VARCHAR(255),
    fingerprint_id VARCHAR(100),
    has_voted BOOLEAN DEFAULT FALSE,
    created_at DATETIME
);
```

#### **FingerprintTemplate Table**
```sql
CREATE TABLE voting_fingerprinttemplate (
    id INTEGER PRIMARY KEY,
    voter_id INTEGER REFERENCES voting_voter(id),
    template_hex TEXT,
    created_at DATETIME
);
```

### 12. **Configuration Files**

#### **Django Settings**
```python
# settings.py
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    # ... other middleware
]

INSTALLED_APPS = [
    'voting',
    # ... other apps
]
```

#### **URL Configuration**
```python
# urls.py
path('scanner/', views.scanner, name='scanner'),
path('voter-home/', views.voter_home, name='voter_home'),
path('api/scanner-authenticate/', views.scanner_authenticate, name='scanner_authenticate'),
```

## Summary

The scanner authentication system provides a secure, user-friendly way for voters to access the voting interface. The complete flow involves:

1. **Hardware Integration**: ESP32 with fingerprint sensor
2. **Backend Processing**: Django with similarity matching
3. **Frontend Interface**: Real-time feedback and redirects
4. **Session Management**: Secure voter authentication

This system ensures that only registered voters with valid fingerprints can access the voting interface, maintaining the integrity of the voting process. 