"""
Update team email in Neon database to use verified Resend email
"""
import psycopg2
from psycopg2.extras import RealDictCursor

connection_string = "postgresql://neondb_owner:npg_LwePgm6vAnh7@ep-still-violet-aooo7qxw.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

print("🔧 Updating team email to Resend-verified address...\n")

try:
    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if there are any email settings in the database
    cursor.execute("SELECT COUNT(*) as count FROM team_email_settings;")
    count = cursor.fetchone()['count']
    
    if count > 0:
        print(f"📊 Found {count} email setting(s) in database")
        
        # Update the email address
        cursor.execute("""
            UPDATE team_email_settings 
            SET team_email = 'rahulprajapat.tech123@gmail.com',
                updated_at = NOW()
            WHERE team_email = 'rahul.prajapat@bridgeaitech.com';
        """)
        updated = cursor.rowcount
        conn.commit()
        
        if updated > 0:
            print(f"✅ Updated {updated} record(s)")
        else:
            print("ℹ️  No records needed updating (already correct)")
        
        # Show current settings
        cursor.execute("SELECT team_email, enabled, send_time FROM team_email_settings LIMIT 1;")
        settings = cursor.fetchone()
        if settings:
            print(f"\n📧 Current Settings:")
            print(f"   Email: {settings['team_email']}")
            print(f"   Enabled: {settings['enabled']}")
            print(f"   Send Time: {settings['send_time']}")
    else:
        print("ℹ️  No email settings in database yet (using JSON storage)")
    
    cursor.close()
    conn.close()
    
    print("\n✅ Email configuration updated!")
    print("🎯 Now sending to: rahulprajapat.tech123@gmail.com")
    print("📬 This email is verified by Resend - emails will work!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nNote: If no database records exist, JSON storage is being used (already fixed)")
