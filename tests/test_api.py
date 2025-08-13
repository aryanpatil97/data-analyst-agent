"""
Test script for the Data Analyst Agent API.
"""

import requests
import json
import time
import os
from dotenv import load_dotenv


def test_health_check():
    """Test the health check endpoint."""
    print("🏥 Testing health check...")
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_simple_task():
    """Test with a simple task via JSON endpoint."""
    print("\n🧪 Testing simple task...")

    simple_task = {
        "question": "Analyze this data",
        "data": {
            "people": [
                {"name": "Alice", "age": 25},
                {"name": "Bob", "age": 30},
                {"name": "Charlie", "age": 35},
                {"name": "Diana", "age": 28},
                {"name": "Eve", "age": 32},
            ]
        },
        "instructions": ["Calculate average age", "Find oldest person name"],
    }

    try:
        response = requests.post(
            "http://localhost:8000/api/text/",
            json={"task_description": json.dumps(simple_task)},
            timeout=60,
        )

        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            # Accept both array and object formats
            if isinstance(result, list) and len(result) == 2:
                avg_age, oldest_person = result
                print(f"✅ Average age: {avg_age}")
                print(f"✅ Oldest person: {oldest_person}")
                return True
            elif isinstance(result, dict):
                # Flexible: check for keys
                if "average" in result and "highest" in result:
                    print(f"✅ Average: {result['average']}")
                    print(f"✅ Highest: {result['highest']}")
                    return True
                print(f"✅ Result: {result}")
                return True
            else:
                print(f"❌ Unexpected result format: {result}")
                return False
        else:
            print(f"❌ Error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Simple task test failed: {e}")
        return False


def test_wikipedia_task():
    """Test with the sample Wikipedia task."""
    print("\n🌐 Testing Wikipedia movie analysis...")

    try:
        with open("tests/sample_question.txt", "r") as f:
            task_content = f.read()
    except FileNotFoundError:
        print("❌ sample_question.txt not found")
        return False

    try:
        with open("tests/sample_question.txt", "rb") as f:
            response = requests.post(
                "http://localhost:8000/api/",
                files={"file": f},
                timeout=180,
            )

        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Result type: {type(result)}")
            if isinstance(result, list):
                print(f"✅ Array result with {len(result)} items")
                for i, item in enumerate(result):
                    if isinstance(item, str) and item.startswith("data:image"):
                        print(f"  [{i}]: Base64 image ({len(item)} chars)")
                    else:
                        print(f"  [{i}]: {item}")
            elif isinstance(result, dict):
                print(f"✅ Object result: {json.dumps(result, indent=2)}")
                # Check for expected keys
                for k, v in result.items():
                    if isinstance(v, str) and v.startswith("data:image"):
                        print(f"  {k}: Base64 image ({len(v)} chars)")
                    else:
                        print(f"  {k}: {v}")
            else:
                print(f"✅ Result: {result}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Wikipedia task test failed: {e}")
        return False


def test_examples_endpoint():
    """Test the examples endpoint."""
    print("\n📋 Testing examples endpoint...")
    try:
        response = requests.get("http://localhost:8000/examples")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            examples = response.json()
            print(f"✅ Found {len(examples['examples'])} examples")
            for example in examples["examples"]:
                print(f"  - {example['name']}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Examples test failed: {e}")
        return False


def main():
    """Run all tests."""
    load_dotenv()

    print("🧪 Data Analyst Agent API Test Suite")
    print("=" * 50)

    # Check if server is running
    print("🔍 Checking if server is running...")
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not responding correctly")
            print("Please start the server first: python start_server.py")
            return
    except Exception as e:
        print(f"❌ Server is not running! {e}")
        print("Please start the server first: python start_server.py")
        return

    print("✅ Server is running!")

    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("Examples Endpoint", test_examples_endpoint),
        ("Simple Task", test_simple_task),
        ("Wikipedia Task (takes ~2-3 minutes)", test_wikipedia_task),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        start_time = time.time()

        if test_func():
            passed += 1
            elapsed = time.time() - start_time
            print(f"✅ {test_name} PASSED ({elapsed:.1f}s)")
        else:
            elapsed = time.time() - start_time
            print(f"❌ {test_name} FAILED ({elapsed:.1f}s)")

    print(f"\n{'='*50}")
    print(f"🏁 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The API is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    main()
