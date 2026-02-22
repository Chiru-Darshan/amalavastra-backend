-- ============================================
-- SAREE BUSINESS API - DATABASE MIGRATION
-- Version: 2.0.0
-- Adds: User authentication, Invoices, Security
-- ============================================

-- ============================================
-- USERS TABLE (Authentication)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(20) NOT NULL DEFAULT 'staff' CHECK (role IN ('admin', 'manager', 'staff', 'viewer')),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Create index for email lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- ============================================
-- INVOICES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    order_id UUID REFERENCES orders(id),
    customer_id UUID REFERENCES customers(id),
    
    -- Customer details snapshot
    customer_name VARCHAR(200),
    customer_address TEXT,
    customer_phone VARCHAR(20),
    customer_email VARCHAR(255),
    
    -- Company details
    company_name VARCHAR(200) NOT NULL,
    company_address TEXT NOT NULL,
    company_phone VARCHAR(20) NOT NULL,
    company_email VARCHAR(255) NOT NULL,
    company_gst VARCHAR(50),
    
    -- Invoice items (stored as JSONB for flexibility)
    items JSONB DEFAULT '[]',
    
    -- Amounts
    subtotal DECIMAL(12, 2) NOT NULL DEFAULT 0,
    discount_amount DECIMAL(12, 2) DEFAULT 0,
    tax_amount DECIMAL(12, 2) DEFAULT 0,
    total_amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
    paid_amount DECIMAL(12, 2) DEFAULT 0,
    due_amount DECIMAL(12, 2) DEFAULT 0,
    
    -- Status and dates
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'issued', 'paid', 'partially_paid', 'overdue', 'cancelled')),
    issue_date TIMESTAMPTZ DEFAULT NOW(),
    due_date DATE,
    
    -- Additional info
    notes TEXT,
    terms TEXT,
    
    -- Metadata
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Create indexes for invoices
CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoices_order ON invoices(order_id);
CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_issue_date ON invoices(issue_date);

-- ============================================
-- ADD TRACKING COLUMNS TO EXISTING TABLES
-- ============================================

-- Add created_by to orders
ALTER TABLE orders 
ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id);

-- Add created_by to payments
ALTER TABLE payments 
ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id);

-- ============================================
-- REFRESH TOKENS TABLE (For token revocation)
-- ============================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);

-- ============================================
-- AUDIT LOG TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to generate invoice number
CREATE OR REPLACE FUNCTION generate_invoice_number()
RETURNS VARCHAR(50) AS $$
DECLARE
    prefix VARCHAR(10) := 'INV';
    date_part VARCHAR(10);
    seq_num INTEGER;
    result VARCHAR(50);
BEGIN
    date_part := TO_CHAR(NOW(), 'YYYYMMDD');
    
    SELECT COALESCE(MAX(
        CAST(SUBSTRING(invoice_number FROM LENGTH(prefix) + 10) AS INTEGER)
    ), 0) + 1
    INTO seq_num
    FROM invoices
    WHERE invoice_number LIKE prefix || '-' || date_part || '-%';
    
    result := prefix || '-' || date_part || '-' || LPAD(seq_num::TEXT, 4, '0');
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to decrement stock
CREATE OR REPLACE FUNCTION decrement_stock(saree_id UUID, qty INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE sarees 
    SET stock_count = GREATEST(0, stock_count - qty)
    WHERE id = saree_id;
END;
$$ LANGUAGE plpgsql;

-- Function to increment stock
CREATE OR REPLACE FUNCTION increment_stock(saree_id UUID, qty INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE sarees 
    SET stock_count = stock_count + qty
    WHERE id = saree_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Enable RLS on sensitive tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Users can view their own profile
CREATE POLICY users_view_own ON users
    FOR SELECT
    USING (auth.uid() = id OR auth.jwt() ->> 'role' IN ('admin', 'manager'));

-- Only admins can modify users
CREATE POLICY users_admin_all ON users
    FOR ALL
    USING (auth.jwt() ->> 'role' = 'admin');

-- Staff and above can view invoices
CREATE POLICY invoices_view ON invoices
    FOR SELECT
    USING (auth.jwt() ->> 'role' IN ('admin', 'manager', 'staff', 'viewer'));

-- Staff and above can create invoices
CREATE POLICY invoices_create ON invoices
    FOR INSERT
    WITH CHECK (auth.jwt() ->> 'role' IN ('admin', 'manager', 'staff'));

-- Managers and above can update invoices
CREATE POLICY invoices_update ON invoices
    FOR UPDATE
    USING (auth.jwt() ->> 'role' IN ('admin', 'manager'));

-- ============================================
-- INSERT DEFAULT ADMIN USER
-- Password: Admin@123 (change immediately!)
-- ============================================
INSERT INTO users (email, password_hash, full_name, role, is_active)
VALUES (
    'admin@amalavastra.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.M0tJwXqq0uBgOi',  -- Admin@123
    'System Administrator',
    'admin',
    true
) ON CONFLICT (email) DO NOTHING;

-- ============================================
-- GRANTS FOR API ACCESS
-- ============================================
GRANT ALL ON users TO authenticated;
GRANT ALL ON invoices TO authenticated;
GRANT ALL ON refresh_tokens TO authenticated;
GRANT ALL ON audit_log TO authenticated;

GRANT EXECUTE ON FUNCTION generate_invoice_number() TO authenticated;
GRANT EXECUTE ON FUNCTION decrement_stock(UUID, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION increment_stock(UUID, INTEGER) TO authenticated;
