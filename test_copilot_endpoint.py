"""
Test the copilot endpoint directly
"""
import requests
import json

API_URL = "http://localhost:8000/api/v1/copilot/analyze"

# Test data
test_data = {
    "project_name": "Healthcare RAG Assistant",
    "project_brief": "We want to build an AI assistant for doctors that can answer clinical questions using latest research papers. The system should retrieve relevant studies from PubMed and medical journals, then generate evidence-based answers with proper citations."
}

print("=" * 70)
print("🧪 TESTING COPILOT ENDPOINT")
print("=" * 70)
print(f"\nEndpoint: {API_URL}")
print(f"Request Data:")
print(json.dumps(test_data, indent=2))
print("\n" + "=" * 70)
print("⏳ Sending request (this may take 30-60 seconds)...")
print("=" * 70)

try:
    response = requests.post(
        API_URL,
        json=test_data,
        timeout=120  # 2 minutes timeout
    )
    
    print(f"\n📊 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ SUCCESS!\n")
        data = response.json()
        
        print(f"Project Name: {data.get('project_name', 'N/A')}")
        print(f"\nProject Understanding ({len(data.get('project_understanding', []))} points):")
        for i, point in enumerate(data.get('project_understanding', [])[:3], 1):
            print(f"  {i}. {point}")
        
        print(f"\nArXiv Papers Found: {len(data.get('arxiv_papers', []))}")
        if data.get('arxiv_papers'):
            print(f"  First paper: {data['arxiv_papers'][0]['title'][:60]}...")
        
        print(f"\nFunctional Requirements: {len(data.get('functional_requirements', {}).keys())} categories")
        print(f"Architecture Decision: {data.get('architecture_decision', {}).get('chosen_architecture', 'N/A')}")
        
        print("\n✅ ENDPOINT IS WORKING CORRECTLY!")
        
    elif response.status_code == 500:
        print("❌ INTERNAL SERVER ERROR (500)")
        print("\nError details:")
        try:
            error_data = response.json()
            print(json.dumps(error_data, indent=2))
        except:
            print(response.text[:500])
        
        print("\n⚠️ Check the server logs for more details")
        
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(response.text[:500])
        
except requests.exceptions.Timeout:
    print("⏰ REQUEST TIMED OUT (> 2 minutes)")
    print("This is normal for first request. The LLM is analyzing your project.")
    
except requests.exceptions.ConnectionError:
    print("❌ CONNECTION ERROR")
    print("Is the server running? Start with: uvicorn main:app --reload")
    
except Exception as e:
    print(f"❌ ERROR: {e}")

print("\n" + "=" * 70)
