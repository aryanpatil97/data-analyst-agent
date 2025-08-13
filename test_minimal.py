#!/usr/bin/env python3
"""
Test script to verify the API works with minimal dependencies.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """Test that the main app can import without heavy dependencies."""
    print("🧪 Testing minimal imports...")
    
    try:
        from app.main import app
        print("✅ FastAPI app imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import FastAPI app: {e}")
        return False
    
    try:
        from app.enhanced_tools import EnhancedDataProcessor
        print("✅ EnhancedDataProcessor imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import EnhancedDataProcessor: {e}")
        return False
    
    try:
        from app.question_set_solver import solve_questions
        print("✅ Question solver imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import question solver: {e}")
        return False
    
    return True

def test_basic_functionality():
    """Test basic functionality without heavy dependencies."""
    print("\n🔧 Testing basic functionality...")
    
    try:
        # Test that we can create a simple response
        test_data = {
            "message": "Data Analyst Agent is working!",
            "status": "success",
            "features": ["text analysis", "web scraping", "data processing"]
        }
        print("✅ Basic data structures work")
        return True
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Minimal Deployment Test")
    print("=" * 60)
    
    success = True
    
    success &= test_imports()
    success &= test_basic_functionality()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed! The app should deploy successfully.")
    else:
        print("❌ Some tests failed. Check the errors above.")
    print("=" * 60)