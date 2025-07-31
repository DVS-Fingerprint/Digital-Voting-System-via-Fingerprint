import requests
import json

# Test the cast_vote API endpoint
url = "http://127.0.0.1:8000/voting/api/cast-vote/"

# Test data
test_data = {
    "fingerprint_id": "TEMP_34",
    "votes": [
        {
            "post": 1,
            "candidate": 1
        }
    ]
}

print("Testing vote API endpoint...")
print(f"URL: {url}")
print(f"Data: {json.dumps(test_data, indent=2)}")

try:
    response = requests.post(url, json=test_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}") 