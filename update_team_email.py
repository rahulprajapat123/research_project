"""
Update team email to @bridgeaitech.com after domain verification
Run this AFTER you've verified bridgeaitech.com domain in Resend
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import json

connection_string = "postgresql://neondb_owner:npg_LwePgm6vAnh7@ep-still-violet-aooo7qxw.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

print("="*70)
print("📧 TEAM EMAIL UPDATE SCRIPT")
print("="*70)
print()
print("⚠️  IMPORTANT: Only run this AFTER verifying bridgeaitech.com in Resend!")
print()
print("Current email: rahulprajapat.tech123@gmail.com")
print("New email:     rahul.prajapat@bridgeaitech.com")
print()

# Ask for confirmation
confirm = input("Have you verified bridgeaitech.com domain in Resend? (yes/no): ").strip().lower()

if confirm not in ['yes', 'y']:
    print()
    print("❌ Cancelled - Domain not verified yet")
    print()
    print("📋 Next Steps:")
    print("1. Follow RESEND_DOMAIN_VERIFICATION.md guide")
    print("2. Add DNS records to your domain")
    print("3. Verify domain in Resend dashboard")
    print("4. Come back and run this script again")
    exit(0)

print()
print("🔄 Updating email configuration...")

try:
    # Update database
    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        UPDATE team_email_settings 
        SET team_email = 'rahul.prajapat@bridgeaitech.com',
            updated_at = NOW()
        WHERE team_email = 'rahulprajapat.tech123@gmail.com';
    """)
    db_updated = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    
    # Update JSON storage (fallback)
    json_path = "storage/intelligence_store.json"
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'team_email_settings' in data:
            data['team_email_settings']['team_email'] = 'rahul.prajapat@bridgeaitech.com'
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            json_updated = True
        else:
            json_updated = False
    except Exception as e:
        print(f"⚠️  JSON update warning: {e}")
        json_updated = False
    
    print()
    print("="*70)
    print("✅ EMAIL CONFIGURATION UPDATED!")
    print("="*70)
    print()
    print(f"📊 Results:")
    print(f"   Database records updated: {db_updated}")
    print(f"   JSON storage updated: {'Yes' if json_updated else 'No'}")
    print()
    print("📧 New Configuration:")
    print(f"   From: onboarding@resend.dev")
    print(f"   To:   rahul.prajapat@bridgeaitech.com")
    print(f"   Via:  Resend API")
    print()
    print("🎯 Next Steps:")
    print("1. Restart server if running (Ctrl+C then python main.py)")
    print("2. Test email: python test_email_sending.py")
    print("3. Check inbox at rahul.prajapat@bridgeaitech.com")
    print()
    print("="*70)
    
except Exception as e:
    print()
    print("❌ Error updating configuration:")
    print(f"   {e}")
    print()
    print("💡 Manual fix:")
    print("1. Go to: http://localhost:8000")
    print("2. Daily Intelligence → Email Settings")
    print("3. Change email to: rahul.prajapat@bridgeaitech.com")
    print("4. Click Save")
    exit(1)
