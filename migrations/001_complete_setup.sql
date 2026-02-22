-- ============================================================
-- SAREE BUSINESS — COMPLETE DATABASE SETUP
-- Version: Combined v1.0 + v2.0
-- Includes: Base tables + Authentication + Invoices + Security
-- Run this file once in Supabase SQL Editor
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- PART 1: BASE TABLES
-- ============================================================

-- 1. SAREES
CREATE TABLE IF NOT EXISTS sarees (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name          TEXT NOT NULL,
  fabric_type   TEXT,
  color         TEXT,
  occasion      TEXT[],
  cost_price    NUMERIC(10,2),
  selling_price NUMERIC(10,2) NOT NULL,
  stock_count   INTEGER DEFAULT 0,
  images        TEXT[],
  description   TEXT,
  is_published  BOOLEAN DEFAULT FALSE,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 2. CUSTOMERS
CREATE TABLE IF NOT EXISTS customers (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name       TEXT NOT NULL,
  phone      TEXT,
  email      TEXT,
  address    TEXT,
  notes      TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. ORDERS
CREATE TABLE IF NOT EXISTS orders (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  customer_id       UUID REFERENCES customers(id) ON DELETE SET NULL,
  status            TEXT DEFAULT 'pending'
                      CHECK (status IN ('pending','confirmed','delivered','cancelled')),
  payment_type      TEXT DEFAULT 'full'
                      CHECK (payment_type IN ('full','installment')),
  payment_status    TEXT DEFAULT 'due'
                      CHECK (payment_status IN ('paid','partial','due')),
  total_amount      NUMERIC(10,2) DEFAULT 0,
  amount_paid       NUMERIC(10,2) DEFAULT 0,
  installment_count INTEGER,
  due_date          DATE,
  notes             TEXT,
  delivery_date     DATE,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- 4. ORDER ITEMS
CREATE TABLE IF NOT EXISTS order_items (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  order_id   UUID REFERENCES orders(id) ON DELETE CASCADE,
  saree_id   UUID REFERENCES sarees(id) ON DELETE SET NULL,
  quantity   INTEGER DEFAULT 1,
  unit_price NUMERIC(10,2) NOT NULL,
  discount   NUMERIC(10,2) DEFAULT 0
);

-- 5. PAYMENTS
CREATE TABLE IF NOT EXISTS payments (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  order_id     UUID REFERENCES orders(id) ON DELETE CASCADE,
  amount       NUMERIC(10,2) NOT NULL,
  method       TEXT CHECK (method IN ('cash','upi','bank_transfer','other')),
  reference_no TEXT,
  paid_at      TIMESTAMPTZ DEFAULT NOW(),
  notes        TEXT
);

-- 6. INSTALLMENT PLAN
CREATE TABLE IF NOT EXISTS installment_plan (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  order_id        UUID REFERENCES orders(id) ON DELETE CASCADE,
  installment_no  INTEGER NOT NULL,
  due_date        DATE NOT NULL,
  expected_amount NUMERIC(10,2) NOT NULL,
  status          TEXT DEFAULT 'pending'
                    CHECK (status IN ('pending','paid','overdue')),
  paid_at         TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- PART 2: AUTHENTICATION & INVOICES
-- ============================================================

-- 7. USERS TABLE (Authentication)
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

-- 8. INVOICES TABLE
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

-- 9. REFRESH TOKENS TABLE
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. AUDIT LOG TABLE
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

-- ============================================================
-- ADD TRACKING COLUMNS TO EXISTING TABLES
-- ============================================================
ALTER TABLE orders 
ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id);

ALTER TABLE payments 
ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id);

-- ============================================================
-- INDEXES
-- ============================================================

-- Base table indexes
CREATE INDEX IF NOT EXISTS idx_sarees_fabric      ON sarees(fabric_type);
CREATE INDEX IF NOT EXISTS idx_sarees_published   ON sarees(is_published);
CREATE INDEX IF NOT EXISTS idx_sarees_stock       ON sarees(stock_count);
CREATE INDEX IF NOT EXISTS idx_orders_customer    ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status      ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created     ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_order_items_order  ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_saree  ON order_items(saree_id);
CREATE INDEX IF NOT EXISTS idx_payments_order     ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_installment_order  ON installment_plan(order_id);
CREATE INDEX IF NOT EXISTS idx_installment_status ON installment_plan(status);
CREATE INDEX IF NOT EXISTS idx_installment_due    ON installment_plan(due_date);

-- User and auth indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);

-- Invoice indexes
CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoices_order ON invoices(order_id);
CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_issue_date ON invoices(issue_date);

-- Audit log indexes
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at);

-- ============================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sarees_updated_at
  BEFORE UPDATE ON sarees
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER orders_updated_at
  BEFORE UPDATE ON orders
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Auto-decrease stock when order_item is inserted
CREATE OR REPLACE FUNCTION decrease_stock()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE sarees
  SET stock_count = stock_count - NEW.quantity
  WHERE id = NEW.saree_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER order_item_decrease_stock
  AFTER INSERT ON order_items
  FOR EACH ROW EXECUTE FUNCTION decrease_stock();

-- Auto-restore stock when order is cancelled
CREATE OR REPLACE FUNCTION restore_stock_on_cancel()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = 'cancelled' AND OLD.status != 'cancelled' THEN
    UPDATE sarees s
    SET stock_count = s.stock_count + oi.quantity
    FROM order_items oi
    WHERE oi.order_id = NEW.id AND oi.saree_id = s.id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER restore_stock_on_cancel
  AFTER UPDATE ON orders
  FOR EACH ROW EXECUTE FUNCTION restore_stock_on_cancel();

-- Auto-sync payment status
CREATE OR REPLACE FUNCTION sync_payment_status()
RETURNS TRIGGER AS $$
DECLARE
  v_order_id     UUID;
  v_total        NUMERIC;
  v_paid         NUMERIC;
  v_pstatus      TEXT;
BEGIN
  IF TG_OP = 'DELETE' THEN
    v_order_id := OLD.order_id;
  ELSE
    v_order_id := NEW.order_id;
  END IF;

  SELECT total_amount, COALESCE(SUM(p.amount), 0)
  INTO v_total, v_paid
  FROM orders o
  LEFT JOIN payments p ON p.order_id = o.id
  WHERE o.id = v_order_id
  GROUP BY o.total_amount;

  IF v_paid >= v_total THEN
    v_pstatus := 'paid';
  ELSIF v_paid > 0 THEN
    v_pstatus := 'partial';
  ELSE
    v_pstatus := 'due';
  END IF;

  UPDATE orders
  SET amount_paid    = v_paid,
      payment_status = v_pstatus
  WHERE id = v_order_id;

  UPDATE installment_plan ip
  SET status  = 'paid',
      paid_at = NOW()
  WHERE ip.order_id = v_order_id
    AND ip.status != 'paid'
    AND ip.expected_amount <= (
      v_paid - COALESCE((
        SELECT SUM(ip2.expected_amount)
        FROM installment_plan ip2
        WHERE ip2.order_id = v_order_id
          AND ip2.installment_no < ip.installment_no
      ), 0)
    );

  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sync_payment_status
  AFTER INSERT OR UPDATE OR DELETE ON payments
  FOR EACH ROW EXECUTE FUNCTION sync_payment_status();

-- Mark overdue installments
CREATE OR REPLACE FUNCTION mark_overdue_installments()
RETURNS VOID AS $$
BEGIN
  UPDATE installment_plan
  SET status = 'overdue'
  WHERE status = 'pending'
    AND due_date < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;

-- Invoice number generator
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

-- Stock management functions
CREATE OR REPLACE FUNCTION decrement_stock(saree_id UUID, qty INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE sarees 
    SET stock_count = GREATEST(0, stock_count - qty)
    WHERE id = saree_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION increment_stock(saree_id UUID, qty INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE sarees 
    SET stock_count = stock_count + qty
    WHERE id = saree_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- VIEWS
-- ============================================================

-- Order summary
CREATE OR REPLACE VIEW order_summary AS
SELECT
  o.id,
  o.created_at,
  o.status,
  o.payment_type,
  o.payment_status,
  o.total_amount,
  o.amount_paid,
  o.total_amount - o.amount_paid AS balance_due,
  o.installment_count,
  o.due_date,
  c.name  AS customer_name,
  c.phone AS customer_phone,
  COUNT(oi.id) AS item_count
FROM orders o
LEFT JOIN customers c  ON c.id  = o.customer_id
LEFT JOIN order_items oi ON oi.order_id = o.id
GROUP BY o.id, c.name, c.phone;

-- Overdue installments
CREATE OR REPLACE VIEW overdue_installments AS
SELECT
  i.id,
  i.order_id,
  i.installment_no,
  i.due_date,
  i.expected_amount,
  CURRENT_DATE - i.due_date AS days_overdue,
  o.total_amount,
  o.amount_paid,
  o.total_amount - o.amount_paid AS balance_due,
  c.name  AS customer_name,
  c.phone AS customer_phone
FROM installment_plan i
JOIN orders   o ON o.id = i.order_id
JOIN customers c ON c.id = o.customer_id
WHERE i.status = 'overdue'
ORDER BY i.due_date ASC;

-- Upcoming installments
CREATE OR REPLACE VIEW upcoming_installments AS
SELECT
  i.id,
  i.order_id,
  i.installment_no,
  i.due_date,
  i.expected_amount,
  i.due_date - CURRENT_DATE AS days_until_due,
  c.name  AS customer_name,
  c.phone AS customer_phone
FROM installment_plan i
JOIN orders    o ON o.id = i.order_id
JOIN customers c ON c.id = o.customer_id
WHERE i.status = 'pending'
  AND i.due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
ORDER BY i.due_date ASC;

-- Low stock sarees
CREATE OR REPLACE VIEW low_stock_sarees AS
SELECT id, name, fabric_type, color, stock_count, selling_price
FROM sarees
WHERE stock_count <= 2
ORDER BY stock_count ASC;

-- Monthly revenue
CREATE OR REPLACE VIEW monthly_revenue AS
SELECT
  DATE_TRUNC('month', created_at) AS month,
  COUNT(*)            AS total_orders,
  SUM(total_amount)   AS gross_revenue,
  SUM(amount_paid)    AS collected,
  SUM(total_amount - amount_paid) AS outstanding
FROM orders
WHERE status != 'cancelled'
GROUP BY 1
ORDER BY 1 DESC;

-- Public sarees
CREATE OR REPLACE VIEW public_sarees AS
SELECT id, name, fabric_type, color, occasion,
       selling_price, images, description, stock_count
FROM sarees
WHERE is_published = TRUE AND stock_count > 0;

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE sarees           ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers        ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders           ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items      ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments         ENABLE ROW LEVEL SECURITY;
ALTER TABLE installment_plan ENABLE ROW LEVEL SECURITY;
ALTER TABLE users            ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices         ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log        ENABLE ROW LEVEL SECURITY;

-- Base table policies (Admin only for authenticated users)
CREATE POLICY "Admin only" ON sarees
  FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Admin only" ON customers
  FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Admin only" ON orders
  FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Admin only" ON order_items
  FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Admin only" ON payments
  FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Admin only" ON installment_plan
  FOR ALL USING (auth.role() = 'authenticated');

-- Public can read published sarees
CREATE POLICY "Public read published sarees" ON sarees
  FOR SELECT USING (is_published = TRUE AND stock_count > 0);

-- User policies
CREATE POLICY users_view_own ON users
    FOR SELECT
    USING (auth.uid() = id OR auth.jwt() ->> 'role' IN ('admin', 'manager'));

CREATE POLICY users_admin_all ON users
    FOR ALL
    USING (auth.jwt() ->> 'role' = 'admin');

-- Invoice policies
CREATE POLICY invoices_view ON invoices
    FOR SELECT
    USING (auth.jwt() ->> 'role' IN ('admin', 'manager', 'staff', 'viewer'));

CREATE POLICY invoices_create ON invoices
    FOR INSERT
    WITH CHECK (auth.jwt() ->> 'role' IN ('admin', 'manager', 'staff'));

CREATE POLICY invoices_update ON invoices
    FOR UPDATE
    USING (auth.jwt() ->> 'role' IN ('admin', 'manager'));

-- ============================================================
-- DEFAULT DATA
-- ============================================================

-- Insert default admin user
-- Password: Admin@123 (CHANGE IMMEDIATELY!)
INSERT INTO users (email, password_hash, full_name, role, is_active)
VALUES (
    'admin@amalavastra.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.M0tJwXqq0uBgOi',
    'System Administrator',
    'admin',
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- ============================================================
-- GRANTS
-- ============================================================

GRANT ALL ON sarees TO authenticated;
GRANT ALL ON customers TO authenticated;
GRANT ALL ON orders TO authenticated;
GRANT ALL ON order_items TO authenticated;
GRANT ALL ON payments TO authenticated;
GRANT ALL ON installment_plan TO authenticated;
GRANT ALL ON users TO authenticated;
GRANT ALL ON invoices TO authenticated;
GRANT ALL ON refresh_tokens TO authenticated;
GRANT ALL ON audit_log TO authenticated;

GRANT EXECUTE ON FUNCTION generate_invoice_number() TO authenticated;
GRANT EXECUTE ON FUNCTION decrement_stock(UUID, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION increment_stock(UUID, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION mark_overdue_installments() TO authenticated;

-- ============================================================
-- COMPLETE ✓
-- ============================================================
-- Run this entire file in Supabase SQL Editor
-- All tables, indexes, triggers, views, and security are now set up!
-- 
-- Default admin user:
--   Email: admin@sareeelegance.com
--   Password: Admin@123 (CHANGE IMMEDIATELY!)
-- ============================================================
