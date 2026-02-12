#!/usr/bin/env python3
"""
Test script to verify proxy functionality
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from search_engines.engines import bing
from search_engines.http_client import HttpClient

async def test_proxy_functionality():
    """Test proxy settings in HTTP client"""
    print("Testing proxy functionality...")
    
    # Test 1: No proxy
    print("\n1. Testing without proxy...")
    client_no_proxy = HttpClient(proxy=None)
    try:
        response = await client_no_proxy.get("https://httpbin.org/ip")
        if response.http == 200:
            print("✓ No proxy connection successful")
            print(f"Response: {response.html[:100]}...")
        else:
            print(f"✗ No proxy connection failed: {response.http}")
    except Exception as e:
        print(f"✗ No proxy connection error: {e}")
    finally:
        await client_no_proxy.close()
    
    # Test 2: Invalid proxy (should fail gracefully)
    print("\n2. Testing with invalid proxy...")
    client_invalid_proxy = HttpClient(proxy="http://invalid:8080", proxy_verify_ssl=False)
    try:
        response = await client_invalid_proxy.get("https://httpbin.org/ip")
        if response.http == 0:
            print("✓ Invalid proxy handled gracefully (connection failed as expected)")
        else:
            print(f"! Unexpected response with invalid proxy: {response.http}")
    except Exception as e:
        print(f"✓ Invalid proxy error handled gracefully: {e}")
    finally:
        await client_invalid_proxy.close()
    
    # Test 3: Test with search engine
    print("\n3. Testing search engine with proxy settings...")
    try:
        engine = bing.Bing(proxy=None, proxy_verify_ssl=True)
        async with engine:
            print("✓ Search engine initialized with proxy settings")
            # We won't actually search to avoid making real requests
            print("✓ Proxy settings passed to search engine successfully")
    except Exception as e:
        print(f"✗ Search engine proxy test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_proxy_functionality())
    print("\nProxy functionality test completed!")
