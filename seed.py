"""
Seed Script - Create Initial Admin User
Run this script to create the first admin user for the system
"""
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import supabase_admin
from core.security import hash_password
from datetime import datetime, timezone


async def create_admin_user():
    """Create initial admin user"""
    
    # Admin user details - CHANGE THESE!
    admin_email = "admin@amalavastra.com"
    admin_password = "Admin@123"  # Must meet password policy
    admin_name = "Administrator"
    admin_phone = "+91 7829984959"
    
    # Check if admin already exists (using admin client)
    existing = supabase_admin.table("users").select("id").eq("email", admin_email.lower()).execute()
    
    if existing.data:
        print(f"Admin user already exists: {admin_email}")
        return existing.data[0]
    
    # Truncate password to 72 chars for bcrypt
    safe_password = admin_password[:72]
    hashed_password = hash_password(safe_password)
    
    # Create admin user
    user_data = {
        "email": admin_email.lower(),
        "password_hash": hashed_password,
        "full_name": admin_name,
        "phone": admin_phone,
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = supabase_admin.table("users").insert(user_data).execute()
    
    if result.data:
        print(f"✅ Admin user created successfully!")
        print(f"   Email: {admin_email}")
        print(f"   Password: {admin_password}")
        print(f"   Role: admin")
        print(f"\n⚠️  IMPORTANT: Change this password after first login!")
        return result.data[0]
    else:
        print("❌ Failed to create admin user")
        return None


async def create_sample_data():
    """Create some sample data for testing"""
    
    # Check if sample data exists (using admin client)
    existing_sarees = supabase_admin.table("sarees").select("id", count="exact").execute()
    
    if existing_sarees.count and existing_sarees.count > 0:
        print(f"Sample data already exists ({existing_sarees.count} sarees found)")
        return
    
    # Sample sarees
    sarees = [
        {
            "name": "Kanchipuram Silk Saree - Royal Blue",
            "fabric_type": "Silk",
            "color": "Royal Blue",
            "cost_price": 8500,
            "selling_price": 12500,
            "stock_count": 5,
            "description": "Traditional Kanchipuram silk saree with golden zari border",
            "is_published": True
        },
        {
            "name": "Banarasi Silk Saree - Maroon",
            "fabric_type": "Silk",
            "color": "Maroon",
            "cost_price": 7500,
            "selling_price": 11000,
            "stock_count": 8,
            "description": "Elegant Banarasi silk with intricate brocade work",
            "is_published": True
        },
        {
            "name": "Cotton Handloom Saree - Yellow",
            "fabric_type": "Cotton",
            "color": "Yellow",
            "cost_price": 1500,
            "selling_price": 2500,
            "stock_count": 15,
            "description": "Lightweight cotton saree perfect for daily wear",
            "is_published": True
        },
        {
            "name": "Chiffon Georgette Saree - Pink",
            "fabric_type": "Georgette",
            "color": "Pink",
            "cost_price": 2500,
            "selling_price": 4200,
            "stock_count": 10,
            "description": "Flowing chiffon georgette with delicate embroidery",
            "is_published": True
        },
        {
            "name": "Mysore Silk Saree - Green",
            "fabric_type": "Silk",
            "color": "Green",
            "cost_price": 6000,
            "selling_price": 9500,
            "stock_count": 3,
            "description": "Pure Mysore silk with traditional motifs",
            "is_published": True
        }
    ]
    
    for saree in sarees:
        saree["created_at"] = datetime.now(timezone.utc).isoformat()
        saree["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = supabase_admin.table("sarees").insert(sarees).execute()
    
    if result.data:
        print(f"✅ Created {len(result.data)} sample sarees")
    
    # Sample customers
    customers = [
        {
            "name": "Priya Sharma",
            "email": "priya.sharma@email.com",
            "phone": "+91 9876543210",
            "address": "123 MG Road, Bangalore, Karnataka - 560001",
            "notes": "VIP customer"
        },
        {
            "name": "Lakshmi Venkatesh",
            "email": "lakshmi.v@email.com",
            "phone": "+91 9876543211",
            "address": "45 Anna Nagar, Chennai, Tamil Nadu - 600040",
            "notes": "Regular customer"
        },
        {
            "name": "Anjali Patel",
            "email": "anjali.patel@email.com",
            "phone": "+91 9876543212",
            "address": "78 Jubilee Hills, Hyderabad, Telangana - 500033",
            "notes": "Wedding orders"
        }
    ]
    
    for customer in customers:
        customer["created_at"] = datetime.now(timezone.utc).isoformat()
    
    result = supabase_admin.table("customers").insert(customers).execute()
    
    if result.data:
        print(f"✅ Created {len(result.data)} sample customers")


async def main():
    print("=" * 50)
    print("Amalavastra - Database Seeding Script")
    print("=" * 50)
    print()
    
    # Create admin user
    await create_admin_user()
    print()
    
    # Ask about sample data
    create_samples = input("Would you like to create sample data? (y/n): ").strip().lower()
    if create_samples == 'y':
        await create_sample_data()
    
    print()
    print("=" * 50)
    print("Seeding complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
