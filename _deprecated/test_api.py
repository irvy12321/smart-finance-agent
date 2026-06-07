#!/usr/bin/env python3
"""
Simple test script for Smart Finance Agent API
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_api():
    """Test the API endpoints"""
    print("Testing Smart Finance Agent API...")
    print("=" * 50)
    
    # Test root endpoint
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✓ Root endpoint: {response.status_code}")
        print(f"  Response: {response.json()}")
    except Exception as e:
        print(f"✗ Root endpoint failed: {e}")
        return
    
    # Test system status
    try:
        response = requests.get(f"{BASE_URL}/api/system/status")
        print(f"✓ System status: {response.status_code}")
        print(f"  Response: {response.json()}")
    except Exception as e:
        print(f"✗ System status failed: {e}")
    
    # Test health check
    try:
        response = requests.get(f"{BASE_URL}/api/system/health")
        print(f"✓ Health check: {response.status_code}")
        print(f"  Response: {response.json()}")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
    
    # Test create task
    try:
        task_data = {
            "query": "Analyze the impact of AI on semiconductor stocks",
            "priority": 1
        }
        response = requests.post(f"{BASE_URL}/api/task/create", json=task_data)
        print(f"✓ Create task: {response.status_code}")
        task_response = response.json()
        print(f"  Task ID: {task_response.get('task_id')}")
        
        task_id = task_response.get('task_id')
        if task_id:
            # Test get task status
            response = requests.get(f"{BASE_URL}/api/task/{task_id}/status")
            print(f"✓ Task status: {response.status_code}")
            print(f"  Status: {response.json()}")
            
            # Test list tasks
            response = requests.get(f"{BASE_URL}/api/task/list")
            print(f"✓ List tasks: {response.status_code}")
            print(f"  Tasks count: {len(response.json().get('tasks', []))}")
    except Exception as e:
        print(f"✗ Task operations failed: {e}")
    
    print("=" * 50)
    print("API testing completed!")

if __name__ == "__main__":
    test_api()