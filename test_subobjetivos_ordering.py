#!/usr/bin/env python3
"""
Test script to verify that completed subobjetivos always appear at the bottom
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_subobjetivos_ordering():
    """Test that completed subobjetivos are always ordered at the bottom"""
    
    # First, we need to login (assuming we have a test user)
    session = requests.Session()
    
    # Test the API endpoint directly
    print("🧪 Testing subobjetivos ordering...")
    
    # We'll test with a known objetivo_id (you'll need to replace this with an actual ID)
    objetivo_id = 1  # Replace with actual objetivo ID
    
    try:
        # Get current subobjetivos
        response = session.get(f"{BASE_URL}/api/objetivos/{objetivo_id}/subobjetivos")
        
        if response.status_code == 200:
            subobjetivos = response.json()
            print(f"📋 Found {len(subobjetivos)} subobjetivos")
            
            # Check ordering: all non-completed should come before completed
            completed_found = False
            for i, sub in enumerate(subobjetivos):
                print(f"  {i+1}. {sub['titulo']} - {'✅' if sub['completado'] else '⏳'}")
                
                if sub['completado']:
                    completed_found = True
                elif completed_found:
                    print("❌ ERROR: Found non-completed subobjetivo after completed one!")
                    return False
            
            print("✅ Ordering is correct: all completed subobjetivos are at the bottom")
            return True
            
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    test_subobjetivos_ordering()