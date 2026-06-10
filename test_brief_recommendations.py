"""
Test script to upload a project brief and verify recommendations are generated
This uses the comprehensive e-commerce brief which mentions many technologies
"""
import asyncio
import sys
from pathlib import Path
from research_intelligence.brief_service import BriefIntelligenceService
from loguru import logger

async def test_brief_upload():
    """Test uploading and analyzing a comprehensive project brief"""
    
    # Choose which brief to test
    brief_files = {
        "1": {
            "path": "sample_ecommerce_brief.md",
            "name": "E-Commerce AI Recommendation System",
            "description": "Comprehensive e-commerce project with RAG, vector search, ML"
        },
        "2": {
            "path": "sample_healthcare_brief.md", 
            "name": "Healthcare AI Diagnostic Assistant",
            "description": "Medical AI system with HIPAA compliance, EHR integration"
        }
    }
    
    print("="*80)
    print("📋 PROJECT BRIEF RECOMMENDATION TEST")
    print("="*80)
    print()
    print("Available test briefs:")
    for key, brief in brief_files.items():
        print(f"  {key}. {brief['name']}")
        print(f"     {brief['description']}")
        print()
    
    choice = input("Select brief to test (1 or 2) [default: 1]: ").strip() or "1"
    
    if choice not in brief_files:
        print(f"❌ Invalid choice: {choice}")
        return
    
    selected_brief = brief_files[choice]
    brief_path = Path(selected_brief["path"])
    
    if not brief_path.exists():
        print(f"❌ Brief file not found: {brief_path}")
        return
    
    print()
    print("="*80)
    print(f"📄 Loading brief: {selected_brief['name']}")
    print("="*80)
    print()
    
    # Read brief content
    with open(brief_path, 'rb') as f:
        content = f.read()
    
    print(f"✅ Loaded brief: {len(content)} bytes")
    print()
    print("🚀 Uploading brief...")
    
    service = BriefIntelligenceService()
    
    try:
        # Upload the brief
        upload_result = await service.upload_brief(
            file_name=brief_path.name,
            content=content
        )
        
        brief_id = upload_result.get("id")
        print(f"✅ Brief uploaded with ID: {brief_id}")
        print()
        print("🔍 Analyzing brief and generating recommendations...")
        print("   This may take 30-60 seconds (fetching sources, ranking papers)")
        print()
        
        # Analyze the brief
        result = await service.analyze_brief(brief_id=brief_id, refresh_sources=True)
        
        print("="*80)
        print("📊 ANALYSIS RESULTS")
        print("="*80)
        print()
        
        # Processing status
        status = result.get("processing_status", "unknown")
        print(f"Status: {status}")
        print()
        
        # Search terms used
        query_terms = result.get("query_terms", [])
        print(f"🔎 Search Terms Used ({len(query_terms)}):")
        for term in query_terms[:10]:
            print(f"   • {term}")
        if len(query_terms) > 10:
            print(f"   ... and {len(query_terms) - 10} more")
        print()
        
        # Sources fetched
        sources_count = result.get("evidence_sources_count", 0)
        print(f"📚 Evidence Sources Fetched: {sources_count}")
        
        top_sources = result.get("top_evidence_sources", [])
        if top_sources:
            print(f"\n   Top {len(top_sources)} Sources:")
            for i, source in enumerate(top_sources[:5], 1):
                title = source.get("title", "Unknown")[:60]
                source_type = source.get("source_type", "unknown")
                print(f"   {i}. [{source_type}] {title}...")
        print()
        
        # Recommendations generated
        recommendations = result.get("recommended_technologies", [])
        print(f"💡 Recommendations Generated: {len(recommendations)}")
        print()
        
        if recommendations:
            print("="*80)
            print("🎯 TECHNOLOGY RECOMMENDATIONS")
            print("="*80)
            print()
            
            for i, rec in enumerate(recommendations, 1):
                tech = rec.get("technology", "Unknown")
                category = rec.get("category", "Unknown")
                recommendation = rec.get("recommendation", "Unknown")
                evidence_count = rec.get("evidence_count", 0)
                
                # Recommendation status emoji
                status_emoji = {
                    "Adopt Now": "🟢",
                    "Trial": "🔵", 
                    "Assess": "🟡",
                    "Hold": "🔴"
                }.get(recommendation, "⚪")
                
                print(f"{i}. {status_emoji} {tech}")
                print(f"   Category: {category}")
                print(f"   Recommendation: {recommendation}")
                print(f"   Evidence: {evidence_count} supporting papers")
                
                # Show key findings
                key_findings = rec.get("key_findings", [])
                if key_findings:
                    print(f"   Findings:")
                    for finding in key_findings[:2]:
                        print(f"     • {finding}")
                
                # Show citations
                citations = rec.get("citations", [])
                if citations:
                    print(f"   Citations:")
                    for citation in citations[:2]:
                        print(f"     • {citation}")
                
                print()
        else:
            print("⚠️  WARNING: No recommendations generated!")
            print()
            print("Possible reasons:")
            print("  1. Not enough papers fetched (check arXiv rate limits)")
            print("  2. Papers don't mention technologies from catalog")
            print("  3. Search terms too generic or too specific")
            print()
            
            # Show fetch warnings if any
            fetch_warnings = result.get("fetch_warnings", [])
            if fetch_warnings:
                print("📋 Fetch Warnings:")
                for warning in fetch_warnings:
                    print(f"   ⚠️  {warning}")
                print()
            
            # Show source status
            source_status = result.get("source_status", [])
            if source_status:
                print("📊 Source Fetch Status:")
                for status in source_status:
                    source_id = status.get("source_id", "unknown")
                    status_str = status.get("status", "unknown")
                    items = status.get("items_fetched", 0)
                    error = status.get("error", "")
                    
                    if status_str == "success":
                        print(f"   ✅ {source_id}: {items} items")
                    else:
                        print(f"   ❌ {source_id}: {error}")
                print()
        
        # Summary
        print("="*80)
        print("📈 SUMMARY")
        print("="*80)
        print(f"Brief Name: {selected_brief['name']}")
        print(f"Search Terms: {len(query_terms)}")
        print(f"Sources Fetched: {sources_count}")
        print(f"Recommendations: {len(recommendations)}")
        print(f"Status: {status}")
        
        if len(recommendations) > 0:
            print()
            print("✅ SUCCESS! Recommendations were generated!")
            print()
            print("🎯 You can now upload this brief via the frontend:")
            print(f"   1. Go to: http://localhost:8000")
            print(f"   2. Click 'Copilot' or 'Upload Brief'")
            print(f"   3. Upload: {brief_path}")
            print(f"   4. View detailed recommendations with citations")
        else:
            print()
            print("⚠️  No recommendations generated - see warnings above")
        
        print("="*80)
        
    except Exception as e:
        print()
        print("="*80)
        print("❌ ERROR DURING ANALYSIS")
        print("="*80)
        print(f"{e}")
        print()
        logger.exception("Brief analysis failed")
        sys.exit(1)

if __name__ == "__main__":
    print()
    print("🚀 Starting brief recommendation test...")
    print()
    asyncio.run(test_brief_upload())
