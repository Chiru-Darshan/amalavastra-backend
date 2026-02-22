-- Migration: Add vendor and batch tracking to sarees
-- Description: Adds vendor_name, batch_number, and purchase_date columns to track stock sources

-- Add columns to sarees table
ALTER TABLE sarees ADD COLUMN IF NOT EXISTS vendor_name VARCHAR(200);
ALTER TABLE sarees ADD COLUMN IF NOT EXISTS batch_number VARCHAR(100);
ALTER TABLE sarees ADD COLUMN IF NOT EXISTS purchase_date DATE;

-- Add index for vendor lookup
CREATE INDEX IF NOT EXISTS idx_sarees_vendor_name ON sarees(vendor_name);
CREATE INDEX IF NOT EXISTS idx_sarees_batch_number ON sarees(batch_number);

-- Comment the columns
COMMENT ON COLUMN sarees.vendor_name IS 'Name of the vendor or supplier from whom the saree was purchased';
COMMENT ON COLUMN sarees.batch_number IS 'Batch or lot number for stock tracking';
COMMENT ON COLUMN sarees.purchase_date IS 'Date when the saree batch was purchased';
