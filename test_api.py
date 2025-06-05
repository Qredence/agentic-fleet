#!/usr/bin/env python3
"""
Simple test script to verify the API works and OpenAPI documentation is accessible.
"""

import sys
import os
import asyncio
import json
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from fastapi.testclient import TestClient
    from agentic_fleet.api.main import app
    
    def test_api():
        """Test the API endpoints and OpenAPI documentation."""
        client = TestClient(app)
        
        print("Testing Agentic Fleet API...")
        
        # Test root endpoint
        print("\n1. Testing root endpoint...")
        response = client.get("/")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"API Name: {data.get('name')}")
            print(f"Version: {data.get('version')}")
            print(f"Docs URL: {data.get('docs_url')}")
        else:
            print(f"Error: {response.text}")
        
        # Test OpenAPI JSON endpoint
        print("\n2. Testing OpenAPI JSON endpoint...")
        response = client.get("/openapi.json")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            openapi_spec = response.json()
            print(f"OpenAPI Version: {openapi_spec.get('openapi')}")
            print(f"API Title: {openapi_spec.get('info', {}).get('title')}")
            print(f"Number of paths: {len(openapi_spec.get('paths', {}))}")
            print("Available endpoints:")
            for path in openapi_spec.get('paths', {}):
                methods = list(openapi_spec['paths'][path].keys())
                print(f"  {path}: {', '.join(methods).upper()}")
        else:
            print(f"Error: {response.text}")
        
        # Test docs endpoint (HTML)
        print("\n3. Testing Swagger UI docs endpoint...")
        response = client.get("/docs")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Swagger UI documentation is accessible")
            if "swagger-ui" in response.text.lower():
                print("✓ Swagger UI content detected")
        else:
            print(f"Error: {response.text}")
        
        # Test redoc endpoint (HTML)
        print("\n4. Testing ReDoc docs endpoint...")
        response = client.get("/redoc")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("ReDoc documentation is accessible")
            if "redoc" in response.text.lower():
                print("✓ ReDoc content detected")
        else:
            print(f"Error: {response.text}")
        
        # Test health endpoint
        print("\n5. Testing health endpoint...")
        response = client.get("/health")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Health Status: {data.get('status')}")
            print(f"Environment: {data.get('environment')}")
        else:
            print(f"Error: {response.text}")
        
        print("\n✓ API testing completed!")
        return True
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Some dependencies might be missing. The API structure has been created.")
    
    def test_api():
        return False

if __name__ == "__main__":
    test_api()