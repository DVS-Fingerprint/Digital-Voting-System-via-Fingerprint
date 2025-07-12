# Fingerprint-Based Digital Voting System

A complete fingerprint-based digital voting system using ESP32 with AS608 fingerprint sensor and Django backend.

## System Overview

This system consists of:
- **ESP32 Microcontroller** with AS608 fingerprint sensor for voter identification
- **Django Backend** for voter management and vote processing
- **Admin Dashboard** for voter registration with live fingerprint scanning
- **Voting Interface** for casting votes after fingerprint verification

## Features

### Hardware (ESP32 + AS608)
- WiFi connectivity for communication with Django backend
- Fingerprint scanning and identification
- HTTP POST requests to Django API endpoints
- Error handling and status feedback
- Serial debugging output

### Django Backend
- Voter registration with fingerprint ID auto-fill
- Temporary storage of fingerprint scans
- Fingerprint verification for voting
- Admin interface with live polling
- RESTful API endpoints

### Admin Interface
- Live fingerprint ID polling from ESP32
- Auto-fill fingerprint ID field during voter registration
- Visual feedback for fingerprint detection
- Real-time status updates

## Project Structure

```
Project-I/
├── core/                          # Django project
│   ├── core/                      # Django settings
│   ├── voting/                    # Main voting app
│   │   ├── models.py             # Database models
│   │   ├── views.py              # API endpoints and views
│   │   ├── urls.py               # URL routing
│   │   ├── admin.py              # Admin interface customization
│   │   └── static/               # Static files
│   │       └── admin/
│   │           ├── js/
│   │           │   └── fingerprint_polling.js
│   │           └── css/
│   │               └── fingerprint_admin.css
│   └── manage.py
└── Hardware/
    └── ESP32_Fingerprint_Voting_System/
        ├── ESP32_Fingerprint_Voting_System.ino
        ├── ESP32_Fingerprint_Voting_System_Simplified.ino
        └── curl_test_commands.md
```

## Installation and Setup

### 1. Django Backend Setup

#### Prerequisites
- Python 3.8+
- pip
- virtualenv (recommended)

#### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Project-I
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations:**
   ```bash
   cd core
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

### 2. ESP32 Setup

#### Prerequisites
- Arduino IDE
- ESP32 board support
- Required libraries:
  - WiFi.h (built-in)
  - HTTPClient.h (built-in)
  - ArduinoJson.h (install via Library Manager)
  - SoftwareSerial.h (built-in)

#### Installation Steps

1. **Install Arduino IDE and ESP32 support:**
   - Download Arduino IDE from https://arduino.cc
   - Add ESP32 board support via Board Manager
   - Install ArduinoJson library via Library Manager

2. **Connect AS608 Fingerprint Sensor:**
   ```
   AS608 Sensor -> ESP32
   VCC -> 3.3V
   GND -> GND
   TX -> GPIO 16 (RX2)
   RX -> GPIO 17 (TX2)
   ```

3. **Configure the code:**
   - Open `ESP32_Fingerprint_Voting_System_Simplified.ino`
   - Update WiFi credentials:
     ```cpp
     const char* ssid = "YOUR_WIFI_SSID";
     const char* password = "YOUR_WIFI_PASSWORD";
     ```
   - Update Django server URL:
     ```cpp
     const char* serverUrl = "http://YOUR_SERVER_IP:8000";
     ```

4. **Upload to ESP32:**
   - Select ESP32 board in Arduino IDE
   - Upload the code to your ESP32

## Usage

### 1. Voter Registration Process

1. **Start the Django server:**
   ```bash
   python manage.py runserver
   ```

2. **Access Django admin:**
   - Go to `http://localhost:8000/admin/`
   - Login with your superuser credentials

3. **Register a new voter:**
   - Navigate to "Voters" section
   - Click "Add Voter"
   - Fill in name and email
   - The fingerprint ID field will auto-fill when ESP32 scans a fingerprint

4. **ESP32 fingerprint scanning:**
   - The ESP32 will continuously scan for fingerprints
   - When a fingerprint is detected, it sends the ID to Django
   - The admin interface polls for new fingerprints every 2 seconds
   - The fingerprint ID field auto-fills with the scanned ID

### 2. Voting Process

1. **Voter approaches voting station with ESP32**

2. **ESP32 scans voter's fingerprint:**
   - Sends fingerprint ID to `/api/verify-fingerprint/`
   - Receives verification status and redirect URL

3. **If verified:**
   - Voter is redirected to voting interface
   - Can cast their vote
   - Vote is recorded in database

4. **If not verified:**
   - Error message displayed
   - Voter cannot proceed to voting

### 3. API Endpoints

#### POST `/voting/api/fingerprint-scan/`
- **Purpose:** Receive fingerprint scans from ESP32
- **Request Body:** `{"fingerprint_id": "FP_001"}`
- **Response:** `{"status": "success", "message": "Fingerprint scan received"}`

#### GET `/voting/api/get-latest-fingerprint/`
- **Purpose:** Get most recent fingerprint scan for admin auto-fill
- **Response:** `{"status": "success", "fingerprint_id": "FP_001", "timestamp": "..."}`

#### POST `/voting/api/verify-fingerprint/`
- **Purpose:** Verify fingerprint for voting
- **Request Body:** `{"fingerprint_id": "FP_001"}`
- **Response:** `{"status": "verified", "voter_name": "John Doe", "redirect_url": "/voting/vote/"}`

## Testing

### 1. Using Curl Commands

See `Hardware/ESP32_Fingerprint_Voting_System/curl_test_commands.md` for detailed testing commands.

**Quick test:**
```bash
# Send fingerprint scan
curl -X POST http://localhost:8000/voting/api/fingerprint-scan/ \
  -H "Content-Type: application/json" \
  -d '{"fingerprint_id": "FP_001"}'

# Verify fingerprint
curl -X POST http://localhost:8000/voting/api/verify-fingerprint/ \
  -H "Content-Type: application/json" \
  -d '{"fingerprint_id": "FP_001"}'
```

### 2. Using ESP32

1. **Upload the simplified code to ESP32**
2. **Open Serial Monitor (115200 baud)**
3. **Watch for fingerprint scan messages**
4. **Check Django admin for auto-filled fingerprint IDs**

### 3. Testing Admin Interface

1. **Open Django admin in browser**
2. **Go to Voters > Add Voter**
3. **Watch fingerprint ID field auto-fill when ESP32 scans**
4. **Verify visual feedback and status messages**

## Database Models

### Voter Model
```python
class Voter(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    fingerprint_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    has_voted = models.BooleanField(default=False)
    last_vote_attempt = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### FingerprintScan Model
```python
class FingerprintScan(models.Model):
    fingerprint_id = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
```

## Configuration

### Django Settings

Update `core/settings.py` to include:

```python
INSTALLED_APPS = [
    # ...
    'voting',
    'rest_framework',
]

# Static files configuration
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
```

### ESP32 Configuration

Update these variables in the Arduino code:

```cpp
// WiFi Configuration
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Django Backend Configuration
const char* serverUrl = "http://YOUR_SERVER_IP:8000";
```

## Troubleshooting

### Common Issues

#### 1. ESP32 WiFi Connection Failed
- **Solution:** Check WiFi credentials and signal strength
- **Debug:** Monitor Serial output for connection status

#### 2. Django Server Not Accessible
- **Solution:** Ensure Django server is running on correct IP/port
- **Debug:** Test with curl commands

#### 3. Fingerprint ID Not Auto-filling
- **Solution:** Check browser console for JavaScript errors
- **Debug:** Verify API endpoint is responding correctly

#### 4. AS608 Sensor Not Responding
- **Solution:** Check wiring connections
- **Debug:** Use simplified code for testing without sensor

#### 5. Database Migration Errors
- **Solution:** Delete migrations and recreate:
  ```bash
  rm voting/migrations/0*.py
  python manage.py makemigrations
  python manage.py migrate
  ```

### Debug Mode

Enable debug output in ESP32 code:
```cpp
#define DEBUG_MODE true
```

Enable Django debug mode:
```python
DEBUG = True
```

## Security Considerations

1. **HTTPS:** Use HTTPS in production for secure communication
2. **Authentication:** Implement proper authentication for admin interface
3. **Rate Limiting:** Add rate limiting to prevent abuse
4. **Input Validation:** Validate all input data
5. **Logging:** Implement comprehensive logging for audit trails

## Production Deployment

### Django Deployment
1. **Use production server (Gunicorn/uWSGI)**
2. **Configure reverse proxy (Nginx)**
3. **Use PostgreSQL for database**
4. **Enable HTTPS with SSL certificates**
5. **Set up proper logging and monitoring**

### ESP32 Deployment
1. **Use stable power supply**
2. **Implement watchdog timer**
3. **Add error recovery mechanisms**
4. **Use secure WiFi network**
5. **Implement OTA updates**

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the curl test commands
3. Check Serial Monitor output for ESP32
4. Check Django logs for backend issues

## Future Enhancements

1. **Multi-factor authentication**
2. **Biometric template encryption**
3. **Real-time vote counting**
4. **Mobile app for voters**
5. **Advanced analytics dashboard**
6. **Blockchain integration for vote immutability** 