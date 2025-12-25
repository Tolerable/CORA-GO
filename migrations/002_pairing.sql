-- CORA-GO Pairing System
-- QR code based mobile device pairing

-- Pairing codes table
CREATE TABLE IF NOT EXISTS cora_pairing_codes (
    code TEXT PRIMARY KEY,
    anchor_id TEXT NOT NULL,
    anchor_name TEXT DEFAULT 'PC Anchor',
    status TEXT DEFAULT 'pending',  -- pending, claimed, expired
    claimed_by TEXT,  -- device_id that claimed it
    claimed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ DEFAULT (now() + interval '5 minutes'),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Paired devices table
CREATE TABLE IF NOT EXISTS cora_devices (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    anchor_id TEXT NOT NULL,
    device_name TEXT,
    user_name TEXT,
    user_email TEXT,
    paired_at TIMESTAMPTZ DEFAULT now(),
    last_seen TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pairing_codes_anchor ON cora_pairing_codes(anchor_id);
CREATE INDEX IF NOT EXISTS idx_pairing_codes_status ON cora_pairing_codes(status);
CREATE INDEX IF NOT EXISTS idx_devices_anchor ON cora_devices(anchor_id);

-- Drop old function versions
DROP FUNCTION IF EXISTS generate_pairing_code(TEXT, TEXT);
DROP FUNCTION IF EXISTS check_pairing_status(TEXT);
DROP FUNCTION IF EXISTS claim_pairing_code(TEXT, TEXT, TEXT, TEXT);
DROP FUNCTION IF EXISTS get_anchor_devices(TEXT);

-- RPC: Generate pairing code
CREATE OR REPLACE FUNCTION generate_pairing_code(
    p_anchor_id TEXT,
    p_anchor_name TEXT DEFAULT 'PC Anchor'
)
RETURNS TEXT AS $$
DECLARE
    new_code TEXT;
BEGIN
    -- Generate 6-char alphanumeric code
    new_code := upper(substring(md5(random()::text || now()::text) from 1 for 6));

    -- Expire old codes for this anchor
    UPDATE cora_pairing_codes
    SET status = 'expired'
    WHERE anchor_id = p_anchor_id AND status = 'pending';

    -- Insert new code
    INSERT INTO cora_pairing_codes (code, anchor_id, anchor_name)
    VALUES (new_code, p_anchor_id, p_anchor_name);

    RETURN new_code;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC: Check pairing status
CREATE OR REPLACE FUNCTION check_pairing_status(p_code TEXT)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
    pc cora_pairing_codes;
BEGIN
    SELECT * INTO pc FROM cora_pairing_codes WHERE code = p_code;

    IF pc IS NULL THEN
        RETURN jsonb_build_object('status', 'not_found');
    END IF;

    -- Check if expired
    IF pc.expires_at < now() AND pc.status = 'pending' THEN
        UPDATE cora_pairing_codes SET status = 'expired' WHERE code = p_code;
        RETURN jsonb_build_object('status', 'expired');
    END IF;

    RETURN jsonb_build_object(
        'status', pc.status,
        'anchor_id', pc.anchor_id,
        'anchor_name', pc.anchor_name,
        'device_name', pc.claimed_by
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC: Claim pairing code (called from mobile)
CREATE OR REPLACE FUNCTION claim_pairing_code(
    p_code TEXT,
    p_device_id TEXT,
    p_device_name TEXT DEFAULT NULL,
    p_user_name TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    pc cora_pairing_codes;
BEGIN
    SELECT * INTO pc FROM cora_pairing_codes WHERE code = upper(p_code);

    IF pc IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Invalid code');
    END IF;

    IF pc.status != 'pending' THEN
        RETURN jsonb_build_object('success', false, 'error', 'Code already used or expired');
    END IF;

    IF pc.expires_at < now() THEN
        UPDATE cora_pairing_codes SET status = 'expired' WHERE code = upper(p_code);
        RETURN jsonb_build_object('success', false, 'error', 'Code expired');
    END IF;

    -- Claim the code
    UPDATE cora_pairing_codes
    SET status = 'claimed',
        claimed_by = p_device_id,
        claimed_at = now()
    WHERE code = upper(p_code);

    -- Register device
    INSERT INTO cora_devices (id, anchor_id, device_name, user_name)
    VALUES (p_device_id, pc.anchor_id, p_device_name, p_user_name)
    ON CONFLICT (id) DO UPDATE SET
        anchor_id = pc.anchor_id,
        device_name = COALESCE(p_device_name, cora_devices.device_name),
        last_seen = now();

    RETURN jsonb_build_object(
        'success', true,
        'anchor_id', pc.anchor_id,
        'anchor_name', pc.anchor_name
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC: Get devices paired to anchor
CREATE OR REPLACE FUNCTION get_anchor_devices(p_anchor_id TEXT)
RETURNS JSONB AS $$
BEGIN
    RETURN (
        SELECT jsonb_agg(jsonb_build_object(
            'id', id,
            'device_name', device_name,
            'user_name', user_name,
            'paired_at', paired_at,
            'last_seen', last_seen
        ))
        FROM cora_devices
        WHERE anchor_id = p_anchor_id
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Enable RLS
ALTER TABLE cora_pairing_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE cora_devices ENABLE ROW LEVEL SECURITY;

-- Allow public access
DROP POLICY IF EXISTS cora_pairing_all ON cora_pairing_codes;
CREATE POLICY cora_pairing_all ON cora_pairing_codes FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS cora_devices_all ON cora_devices;
CREATE POLICY cora_devices_all ON cora_devices FOR ALL USING (true) WITH CHECK (true);

-- Grant permissions
GRANT ALL ON cora_pairing_codes TO anon, authenticated;
GRANT ALL ON cora_devices TO anon, authenticated;
GRANT EXECUTE ON FUNCTION generate_pairing_code TO anon, authenticated;
GRANT EXECUTE ON FUNCTION check_pairing_status TO anon, authenticated;
GRANT EXECUTE ON FUNCTION claim_pairing_code TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_anchor_devices TO anon, authenticated;
