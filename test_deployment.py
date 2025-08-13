#!/usr/bin/env python3
"""
Test script to verify the deployed API meets IIT Madras requirements.
"""

import requests
import json
import time

def test_api_endpoint(base_url):
    """Test the API endpoint with a sample request."""
    
    print(f"🧪 Testing API at: {base_url}")
    
    # Test 1: Health check
    try:
        response = requests.get(f"{base_url.rstrip('/api/')}/health", timeout=30)
        print(f"✅ Health check: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
    
    # Test 2: Main API endpoint with sample data
    try:
        # Create a test file
        test_content = """Question: What is the capital of France?
Data: France is a country in Europe. Paris is its capital city with a population of about 2.2 million people."""
        
        files = {
            'file': ('test_question.txt', test_content, 'text/plain')
        }
        
        print("\n🔄 Testing main API endpoint...")
        start_time = time.time()
        
        response = requests.post(
            f"{base_url}",
            files=files,
            timeout=300  # 5 minutes
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"⏱️  Processing time: {processing_time:.2f} seconds")
        print(f"📊 Status code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print("✅ JSON response received")
                print(f"📄 Response keys: {list(result.keys())}")
                print(f"📝 Sample response: {json.dumps(result, indent=2)[:500]}...")
            except json.JSONDecodeError:
                print("❌ Response is not valid JSON")
                print(f"Raw response: {response.text[:200]}...")
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ API test failed: {e}")

if __name__ == "__main__":
    # Test with local server first
    print("=" * 60)
    print("🚀 API Deployment Test Script")
    print("=" * 60)
    
    # You can test locally first
    local_url = "http://localhost:8000/api/"
    print("\n1. Testing local server (if running):")
    test_api_endpoint(local_url)
    
    # Then test deployed version
    deployed_url = input("\n2. Enter your deployed API URL (e.g., https://your-app.onrender.com/api/): ").strip()
    if deployed_url:
        test_api_endpoint(deployed_url)
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")
    print("📋 For IIT Madras submission, you need:")
    print("   1. GitHub repo URL (public with MIT license)")
    print("   2. API endpoint URL (must respond within 5 minutes)")
    print("=" * 60)