#!/usr/bin/env python3
"""
Test script for GitHub Repository Analyzer API
"""
import httpx
import asyncio
import json

async def test_api():
    """Test the GitHub analyzer API"""
    
    # Test repository (using a small, well-known repo)
    test_repos = [
        "https://github.com/microsoft/vscode-hello-world",
        "https://github.com/facebook/create-react-app",
        "https://github.com/vercel/next.js"
    ]
    
    print("🧪 Testing GitHub Repository Analyzer API")
    print("=" * 50)
    
    # Test health endpoint
    print("\n1. Testing health endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                print("✅ Health check passed")
                print(f"   Response: {response.json()}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return
    except Exception as e:
        print(f"❌ Failed to connect to API: {e}")
        print("   Make sure the API is running on http://localhost:8000")
        return
    
    # Test repository analysis
    print(f"\n2. Testing repository analysis...")
    
    for i, repo_url in enumerate(test_repos[:1], 1):  # Test just the first one
        print(f"\n   Test {i}: Analyzing {repo_url}")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "http://localhost:8000/analyze",
                    json={
                        "github_url": repo_url,
                        "github_token": None
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print("   ✅ Analysis successful!")
                    print(f"   📊 Repository: {result['repository_info']['name']}")
                    print(f"   🌟 Stars: {result['repository_info']['stars']}")
                    print(f"   💻 Language: {result['repository_info']['language']}")
                    print(f"   🔍 Authenticity Score: {result['authenticity_score']['overall_score']}/100")
                    print(f"   🛠️  Skills: {', '.join(result['extracted_skills'][:5])}...")
                    print(f"   📝 Summary: {result['generated_summary'][:100]}...")
                else:
                    print(f"   ❌ Analysis failed: {response.status_code}")
                    print(f"   Error: {response.text}")
                    
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 API testing completed!")

if __name__ == "__main__":
    asyncio.run(test_api())
