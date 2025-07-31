import requests
import json

print("Testing Django server and endpoints...")

# Test 1: Check if server is running
try:
    response = requests.get("http://127.0.0.1:8000/")
    print(f"✅ Server is running - Status: {response.status_code}")
except Exception as e:
    print(f"❌ Server not running: {e}")
    exit(1)

# Test 2: Check if voting app is accessible
try:
    response = requests.get("http://127.0.0.1:8000/voting/")
    print(f"✅ Voting app accessible - Status: {response.status_code}")
except Exception as e:
    print(f"❌ Voting app not accessible: {e}")

# Test 3: Check cast-vote endpoint
try:
    response = requests.get("http://127.0.0.1:8000/voting/api/cast-vote/")
    print(f"✅ Cast-vote endpoint exists - Status: {response.status_code}")
except Exception as e:
    print(f"❌ Cast-vote endpoint not found: {e}")

# Test 4: Try POST to cast-vote endpoint
test_data = {
    "fingerprint_id": "TEMP_34",
    "votes": [{"post": 1, "candidate": 1}]
}

try:
    response = requests.post(
        "http://127.0.0.1:8000/voting/api/cast-vote/",
        json=test_data,
        headers={'Content-Type': 'application/json'}
    )
    print(f"✅ POST to cast-vote endpoint - Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ POST to cast-vote endpoint failed: {e}") 