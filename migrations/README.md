# Migrations

This folder contains SQL migration scripts for the Saree Business API database.

## Migration Files

1. **001_initial.sql** - Initial database setup (see DB Setup.sql in root)
2. **002_auth_invoices.sql** - Authentication tables, invoices, and security

## Running Migrations

Execute these migrations in order in your Supabase SQL Editor:

```sql
-- Run each migration file in order
-- Make sure to backup your database before running migrations
```

## Default Admin User

After running migration 002, a default admin user is created:
- **Email:** admin@sareeelegance.com
- **Password:** Admin@123

⚠️ **IMPORTANT:** Change this password immediately after first login!

## Security Features

- Row Level Security (RLS) enabled on sensitive tables
- Audit logging for tracking changes
- Refresh token table for secure token management
