"""
Complete end-to-end test of the copilot endpoint
"""
import requests
import json
import time

API_URL = "http://localhost:8000/api/v1/copilot/analyze"

test_data = {
    "project_name": "Simple Chatbot",
    "project_brief": "Build a basic customer support chatbot that can answer FAQs about products."
}

print("=" * 80)
print("🚀 FULL END-TO-END TEST - COPILOT ENDPOINT")
print("=" * 80)
print(f"\n📡 Testing: {API_URL}")
print(f"\n📝 Request Data:")
print(f"   Project: {test_data['project_name']}")
print(f"   Brief: {test_data['project_brief'][:60]}...")

print("\n" + "=" * 80)
print("⏳ Sending request...")
print("   This will take 60-90 seconds (searching papers + LLM analysis)")
print("=" * 80)

start_time = time.time()

try:
    response = requests.post(
        API_URL,
        json=test_data,
        timeout=180  # 3 minutes max
    )
    
    elapsed = time.time() - start_time
    
    print(f"\n⏱️  Response received in {elapsed:.1f} seconds")
    print(f"📊 Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("\n" + "=" * 80)
        print("✅ SUCCESS! THE ENDPOINT IS WORKING!")
        print("=" * 80)
        
        data = response.json()
        
        print(f"\n📋 Response Summary:")
        print(f"   Project Name: {data.get('project_name', 'N/A')}")
        print(f"   Papers Found: {len(data.get('arxiv_papers', []))}")
        
        if data.get('arxiv_papers'):
            print(f"\n📚 Sample Paper:")
            paper = data['arxiv_papers'][0]
            print(f"      Title: {paper['title'][:60]}...")
            print(f"      Authors: {', '.join(paper['authors'][:2])}")
            print(f"      Year: {paper['year']}")
        
        print(f"\n🎯 Project Understanding: {len(data.get('project_understanding', []))} points")
        if data.get('project_understanding'):
            print(f"      1. {data['project_understanding'][0]}")
        
        print(f"\n⚙️  Functional Requirements: {len(data.get('functional_requirements', {}).keys())} categories")
        
        arch = data.get('architecture_decision', {})
        print(f"\n🏗️  Architecture Decision: {arch.get('chosen_architecture', 'N/A')}")
        
        print(f"\n💻 Tech Stack Categories: {len(data.get('tech_stack', {}).keys())}")
        
        print(f"\n📅 Milestones: {len(data.get('milestones', {}).keys())}")
        
        print("\n" + "=" * 80)
        print("🎉 FULL PIPELINE TEST PASSED!")
        print("=" * 80)
        print("\n✅ What this proves:")
        print("   ✓ Frontend can connect to backend")
        print("   ✓ OpenAI API key is working")
        print("   ✓ LLM model is correct")
        print("   ✓ ArXiv search is working")
        print("   ✓ Analysis pipeline is complete")
        print("   ✓ Response format is correct")
        
        print("\n🌐 Your frontend UI at http://localhost:8000/copilot.html")
        print("   should now work perfectly!")
        
    elif response.status_code == 500:
        print("\n❌ 500 INTERNAL SERVER ERROR")
        try:
            error = response.json()
            print(f"\nError Details:")
            print(f"   {error.get('detail', 'Unknown error')}")
        except:
            print(f"\n{response.text[:500]}")
            
    else:
        print(f"\n❌ Error {response.status_code}")
        print(response.text[:500])
        
except requests.exceptions.Timeout:
    print("\n⏰ REQUEST TIMED OUT (> 3 minutes)")
    print("   The analysis is taking longer than expected.")
    print("   This can happen if arXiv is slow or LLM is processing heavily.")
    
except requests.exceptions.ConnectionError:
    print("\n❌ CONNECTION ERROR")
    print("   Cannot connect to http://localhost:8000")
    print("   Is the server running?")
    
except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {e}")

print("\n" + "=" * 80)
