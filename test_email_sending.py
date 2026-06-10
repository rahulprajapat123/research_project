"""
Test email sending with Resend to verify configuration works
"""
import asyncio
from research_intelligence.daily_service import DailyIntelligenceService
from loguru import logger

async def test_email():
    print("📧 Testing Daily Intelligence Email...\n")
    
    service = DailyIntelligenceService()
    
    print("📝 Generating report and sending email...")
    try:
        result = await service.send_now(topics=["RAG", "LLM", "vector search"])
        
        report = result.get("report", {})
        email_log = result.get("email_log", {})
        
        print("\n" + "="*60)
        print("📊 REPORT GENERATED")
        print("="*60)
        print(f"Subject: {report.get('subject')}")
        print(f"Recommendations: {len(report.get('recommendations', []))}")
        print(f"Sources: {report.get('sources_count', 0)}")
        
        print("\n" + "="*60)
        print("📬 EMAIL STATUS")
        print("="*60)
        print(f"Status: {email_log.get('status')}")
        print(f"Recipient: {email_log.get('recipient_email')}")
        print(f"Provider: {email_log.get('provider')}")
        
        if email_log.get('status') == 'sent':
            print(f"✅ Sent At: {email_log.get('sent_at')}")
            print("\n🎉 SUCCESS! Email sent successfully!")
            print("📬 Check your inbox: rahulprajapat.tech123@gmail.com")
        else:
            print(f"❌ Error: {email_log.get('error_message')}")
            print("\n⚠️  Email failed to send")
        
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Email test failed")

if __name__ == "__main__":
    asyncio.run(test_email())
