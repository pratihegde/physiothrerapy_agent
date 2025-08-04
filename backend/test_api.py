import requests
import json

base_url = "http://localhost:8000"

# Test 1: Check if API is running
print("1. Testing root endpoint...")
try:
    response = requests.get(f"{base_url}/")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: Test start_assessment endpoint
print("\n2. Testing start_assessment endpoint...")
try:
    data = {
        "session_id": "test123",
        "user_name": "Test User"
    }
    response = requests.post(
        f"{base_url}/start_assessment",
        json=data,
        headers={"Content-Type": "application/json"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")
    else:
        print(f"   Error: {response.text}")
except Exception as e:
    print(f"   Error: {e}")