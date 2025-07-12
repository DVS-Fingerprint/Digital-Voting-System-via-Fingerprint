# Fingerprint-Based Digital Voting System - Project Overview

## 🎯 What We Built

A complete **Fingerprint-Based Digital Voting System** with:
- **ESP32 + AS608 Fingerprint Sensor** for voter identification
- **Django Backend** for voter management and vote processing
- **Admin Interface** with live fingerprint scanning
- **Voting Interface** for casting votes after verification

## 📁 Clean Project Structure

```
Project-I/
├── 📂 core/                          # Django Backend
│   ├── 📂 voting/                    # Main Voting App
│   │   ├── 📄 models.py             # Database Models (Voter, Candidate, Vote)
│   │   ├── 📄 views.py              # API Endpoints & Views
│   │   ├── 📄 urls.py               # URL Routing
│   │   ├── 📄 admin.py              # Admin Interface
│   │   ├── 📄 forms.py              # Voter Registration Form
│   │   ├── 📄 serializers.py        # API Data Serialization
│   │   └── 📂 static/admin/         # Admin Interface Files
│   │       ├── 📄 js/fingerprint_polling.js    # Live Fingerprint Polling
│   │       └── 📄 css/fingerprint_admin.css    # Admin Styling
│   ├── 📂 core/                      # Django Settings
│   ├── 📄 manage.py                  # Django Management
│   └── 📄 requirements.txt           # Python Dependencies
│
├── 📂 Hardware/                      # ESP32 Arduino Code
│   └── 📂 ESP32_Fingerprint_Voting_System/
│       ├── 📄 ESP32_Fingerprint_Voting_System_Simplified.ino  # Main ESP32 Code
│       └── 📄 curl_test_commands.md  # Testing Commands
│
└── 📄 README_Fingerprint_Voting_System.md  # Complete Documentation
```

## 🔧 Key Features

### 1. **ESP32 Fingerprint Scanner**
- Scans voter fingerprints using AS608 sensor
- Sends fingerprint IDs to Django backend via HTTP
- Handles WiFi connectivity and error management

### 2. **Django Backend APIs**
- `/api/fingerprint-scan/` - Receives fingerprint scans from ESP32
- `/api/get-latest-fingerprint/` - Provides latest scan for admin auto-fill
- `/api/verify-fingerprint/` - Verifies voter for voting

### 3. **Admin Interface**
- Live fingerprint ID polling every 2 seconds
- Auto-fills fingerprint ID field during voter registration
- Visual feedback for fingerprint detection

### 4. **Voting System**
- Voter verification through fingerprint
- Multiple candidate support
- Vote tracking and results

## 🚀 How to Use

### 1. **Start Django Server**
```bash
cd core
python manage.py runserver
```

### 2. **Access Admin Interface**
- Go to `http://localhost:8000/admin/`
- Login with superuser credentials
- Add voters - fingerprint ID will auto-fill when ESP32 scans

### 3. **Test with ESP32**
- Upload `ESP32_Fingerprint_Voting_System_Simplified.ino` to ESP32
- Update WiFi credentials and server URL
- ESP32 will scan fingerprints and send to Django

### 4. **Test with Curl**
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

## 📋 Database Models

### **Voter Model**
```python
- name: CharField
- email: EmailField (unique)
- fingerprint_id: CharField (unique)
- has_voted: BooleanField
- created_at: DateTimeField
```

### **FingerprintScan Model**
```python
- fingerprint_id: CharField
- timestamp: DateTimeField
- is_used: BooleanField
```

### **Other Models**
- Candidate, Post, Vote, VotingSession, ActivityLog

## 🎯 What Each File Does

### **Core Django Files:**
- `models.py` - Defines database structure
- `views.py` - Handles API requests and business logic
- `urls.py` - Routes URLs to views
- `admin.py` - Customizes admin interface
- `forms.py` - Voter registration form
- `serializers.py` - Converts data for API responses

### **Static Files:**
- `fingerprint_polling.js` - JavaScript for live fingerprint polling
- `fingerprint_admin.css` - Styling for admin interface

### **Hardware:**
- `ESP32_Fingerprint_Voting_System_Simplified.ino` - Complete ESP32 code

## ✅ Project Status

**✅ COMPLETED:**
- Django backend with all APIs
- Admin interface with live fingerprint polling
- ESP32 Arduino code
- Database models and migrations
- Complete documentation

**🎯 READY TO USE:**
- All files are necessary and functional
- No unnecessary files remain
- Clean, organized structure

## 🚀 Next Steps

1. **Configure ESP32** with your WiFi and server details
2. **Start Django server** and access admin
3. **Test fingerprint scanning** with ESP32
4. **Register voters** through admin interface
5. **Test voting process** with fingerprint verification

---

**This is a complete, working fingerprint-based voting system!** 🎉 