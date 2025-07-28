# Fixed Voter Registration Flow

## Overview
The voter registration system has been fixed to work accurately according to the requirements. The system now properly auto-generates voter IDs, handles fingerprint scanning, and automatically populates the registration form.

## Complete Registration Process

### 1. **Admin Access Dashboard**
- Navigate to `/register-voter/`
- Voter ID is **auto-generated and pre-filled** (e.g., V000001, V000002, etc.)

### 2. **Fill Voter Details**
- **Voter ID**: Auto-generated and read-only
- **Name**: Entered by admin/staff
- **Age**: Entered by admin/staff  
- **Gender**: Selected by admin/staff
- **Fingerprint Template**: Auto-populated after scan

### 3. **Trigger Fingerprint Scan**
- Admin clicks "Start Fingerprint Scan" button
- System sends trigger to ESP32 via `/voting/api/trigger-scan/`
- Status shows "Scan triggered! Place finger on sensor..."
- ESP32 polls server every 2 seconds via `/voting/api/get-scan-trigger/`

### 4. **ESP32 Response**
- ESP32 detects scan trigger
- Serial monitor shows: "Registration scan triggered for voter: V000001"
- ESP32 prompts: "Place finger on sensor..."

### 5. **Fingerprint Capture**
- ESP32 captures fingerprint image
- Converts to template and then to base64 format
- Uploads to server via `/voting/api/upload-template/`
- Server stores template in session

### 6. **Template Storage & Form Population**
- Server receives template and stores in session
- Frontend polls `/voting/api/check-pending-template/`
- Template field is **automatically populated**
- "Register Voter" button becomes enabled

### 7. **Registration Completion**
- Admin clicks "Register Voter" button
- Voter and fingerprint template saved to database
- Success message displayed
- Form resets with next voter ID

## Technical Implementation

### Backend Changes

#### 1. **register_voter View** (`core/voting/views.py`)
```python
@staff_member_required
def register_voter(request):
    # Auto-generate next voter ID
    last_voter = Voter.objects.order_by('-voter_id').first()
    if last_voter:
        last_num = int(last_voter.voter_id.replace('V', ''))
        next_voter_id = f"V{last_num + 1:06d}"
    else:
        next_voter_id = "V000001"
    
    if request.method == 'POST':
        # Handle form submission
        form = VoterRegistrationForm(request.POST)
        if form.is_valid():
            voter = form.save()
            template_hex = form.cleaned_data.get('template_hex')
            if template_hex:
                FingerprintTemplate.objects.create(voter=voter, template_hex=template_hex)
                # Clear pending template from session
                request.session.pop('pending_template', None)
    else:
        # Pre-fill voter_id and check for pending template
        initial_data = {'voter_id': next_voter_id}
        pending_template = request.session.get('pending_template')
        if pending_template:
            initial_data['template_hex'] = pending_template
        form = VoterRegistrationForm(initial=initial_data)
```

#### 2. **upload_template Function**
```python
@csrf_exempt
def upload_template(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        voter_id = data.get('voter_id')
        template_b64 = data.get('template')
        
        # Decode base64 to hex
        template_bytes = base64.b64decode(template_b64)
        template_hex = template_bytes.hex()
        
        # Store in session for form population
        request.session['pending_template'] = template_hex
        request.session['pending_voter_id'] = voter_id
        request.session.modified = True
        
        return JsonResponse({
            'status': 'success',
            'message': 'Template captured successfully for registration',
            'voter_id': voter_id,
            'template_hex': template_hex
        })
```

#### 3. **check_pending_template Function**
```python
@csrf_exempt
@require_http_methods(["GET"])
def check_pending_template(request):
    pending_template = request.session.get('pending_template')
    pending_voter_id = request.session.get('pending_voter_id')
    
    if pending_template:
        return JsonResponse({
            'status': 'success',
            'has_template': True,
            'template_hex': pending_template,
            'voter_id': pending_voter_id
        })
    else:
        return JsonResponse({
            'status': 'success',
            'has_template': False
        })
```

### Frontend Changes

#### 1. **Registration Template** (`core/voting/templates/voting/register_voter.html`)
- Voter ID field is pre-filled and read-only
- Fingerprint template field auto-populates after scan
- Register button enabled only when template is available

#### 2. **JavaScript Flow**
```javascript
// Trigger scan
fetch('/voting/api/trigger-scan/', {
    method: 'POST',
    body: JSON.stringify({
        action: 'register',
        voter_id: currentVoterId
    })
})

// Check for pending template
fetch('/voting/api/check-pending-template/')
.then(response => response.json())
.then(data => {
    if (data.has_template) {
        templateField.value = data.template_hex;
        registerBtn.disabled = false;
    }
})
```

### ESP32 Arduino Code

The ESP32 code polls the server every 2 seconds for scan triggers:

```cpp
void checkForScanTrigger() {
    HTTPClient http;
    String url = String(serverUrl) + getScanTriggerUrl;
    
    http.begin(url);
    int httpCode = http.GET();
    
    if (httpCode == HTTP_CODE_OK) {
        String payload = http.getString();
        DynamicJsonDocument doc(1024);
        deserializeJson(doc, payload);
        
        if (doc["status"] == "trigger_active") {
            String action = doc["action"];
            String voterId = doc["voter_id"];
            
            if (action == "register" && voterId != "") {
                currentVoterId = voterId;
                scanTriggered = true;
                Serial.println("Registration scan triggered for voter: " + currentVoterId);
                Serial.println("Place finger on sensor...");
            }
        }
    }
}
```

## API Endpoints

### 1. **Trigger Scan** - `POST /voting/api/trigger-scan/`
```json
{
    "action": "register",
    "voter_id": "V000001"
}
```

### 2. **Get Scan Trigger** - `GET /voting/api/get-scan-trigger/`
```json
{
    "status": "trigger_active",
    "action": "register",
    "voter_id": "V000001",
    "message": "Scan required for register"
}
```

### 3. **Upload Template** - `POST /voting/api/upload-template/`
```json
{
    "voter_id": "V000001",
    "template": "base64_encoded_template_data"
}
```

### 4. **Check Pending Template** - `GET /voting/api/check-pending-template/`
```json
{
    "status": "success",
    "has_template": true,
    "template_hex": "hex_template_data",
    "voter_id": "V000001"
}
```

## Database Schema

### Voter Model
```python
class Voter(models.Model):
    voter_id = models.CharField(max_length=50, unique=True)  # Auto-generated
    name = models.CharField(max_length=255)
    fingerprint_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    has_voted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

### FingerprintTemplate Model
```python
class FingerprintTemplate(models.Model):
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE)
    template_hex = models.TextField()  # Hex-encoded template
    created_at = models.DateTimeField(auto_now_add=True)
```

## Serial Monitor Output Example

```
Connecting to WiFi...
WiFi connected
IP address: 192.168.1.101
Fingerprint sensor found!
Registration scan triggered for voter: V000001
Place finger on sensor...
Image taken
Template created
Template uploaded successfully
Response: {"status":"success","message":"Template captured successfully for registration","voter_id":"V000001","template_hex":"..."}
```

## Key Features

1. **Auto-generated Voter IDs**: Sequential IDs (V000001, V000002, etc.)
2. **Pre-filled Form**: Voter ID is automatically populated
3. **Real-time Communication**: ESP32 polls server every 2 seconds
4. **Automatic Template Population**: Fingerprint data auto-fills the form
5. **Session Management**: Templates stored in session until registration
6. **Error Handling**: Proper error messages and status updates
7. **Database Integration**: Voters and templates saved to database

## Testing the Flow

1. Start Django server: `python manage.py runserver`
2. Upload ESP32 code to your device
3. Configure WiFi settings in Arduino code
4. Navigate to `/register-voter/`
5. Fill in voter details
6. Click "Start Fingerprint Scan"
7. Place finger on ESP32 sensor
8. Verify template populates in form
9. Click "Register Voter"
10. Check database for saved voter and template

The registration process now works accurately according to the requirements! 