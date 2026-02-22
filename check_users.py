from database import supabase_admin

result = supabase_admin.table('users').select('*').execute()
print(f"\nTotal users in database: {len(result.data)}\n")

for user in result.data:
    print(f"Email: {user['email']}")
    print(f"Role: {user['role']}")
    print(f"Active: {user['is_active']}")
    print(f"Hash: {user['password_hash'][:50]}...")
    print("-" * 50)
