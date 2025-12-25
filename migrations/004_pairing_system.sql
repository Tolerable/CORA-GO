-- CORA-GO Pairing System
-- Enables QR code pairing between PC anchor and mobile devices

-- Users table (mobile users)
CREATE TABLE IF NOT EXISTS cora_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW()
);

-- Devices table (links users to PC anchors)
CREATE TABLE IF NOT EXISTS cora_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES cora_users(id) ON DELETE CASCADE,
    anchor_id TEXT NOT NULL,  -- PC anchor identifier
    device_name TEXT DEFAULT 'Mobile',
    paired_at TIMESTAMPTZ DEFAULT NOW(),
    last_connected TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    UNIQUE(user_id, anchor_id)
);

-- Pairing codes (temporary, expire after 5 mins)
CREATE TABLE IF NOT EXISTS cora_pairing (
    code TEXT PRIMARY KEY,  -- e.g., "CORA-7X9K"
    anchor_id TEXT NOT NULL,
    anchor_name TEXT DEFAULT 'PC Anchor',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '5 minutes'),
    claimed_by UUID REFERENCES cora_users(id),
    claimed_at TIMESTAMPTZ
);

-- Magic links for email verification
CREATE TABLE IF NOT EXISTS cora_magic_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    pairing_code TEXT REFERENCES cora_pairing(code),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '15 minutes'),
    used_at TIMESTAMPTZ
);

-- Enable RLS
ALTER TABLE cora_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE cora_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE cora_pairing ENABLE ROW LEVEL SECURITY;
ALTER TABLE cora_magic_links ENABLE ROW LEVEL SECURITY;

-- Policies: Allow anon to create/read pairing codes
CREATE POLICY "Pairing codes are public" ON cora_pairing FOR SELECT USING (true);
CREATE POLICY "Anyone can create pairing codes" ON cora_pairing FOR INSERT WITH CHECK (true);
CREATE POLICY "Anyone can claim pairing codes" ON cora_pairing FOR UPDATE USING (true);

-- Policies: Magic links
CREATE POLICY "Magic links insertable" ON cora_magic_links FOR SELECT USING (true);
CREATE POLICY "Magic links creatable" ON cora_magic_links FOR INSERT WITH CHECK (true);
CREATE POLICY "Magic links updatable" ON cora_magic_links FOR UPDATE USING (true);

-- Policies: Users/devices need token
CREATE POLICY "Users readable with valid session" ON cora_users FOR SELECT USING (true);
CREATE POLICY "Users insertable" ON cora_users FOR INSERT WITH CHECK (true);
CREATE POLICY "Users updatable" ON cora_users FOR UPDATE USING (true);

CREATE POLICY "Devices readable" ON cora_devices FOR SELECT USING (true);
CREATE POLICY "Devices insertable" ON cora_devices FOR INSERT WITH CHECK (true);
CREATE POLICY "Devices updatable" ON cora_devices FOR UPDATE USING (true);

-- =============================================================
-- RPC: Generate pairing code (called by PC anchor)
-- =============================================================
CREATE OR REPLACE FUNCTION generate_pairing_code(
    p_anchor_id TEXT,
    p_anchor_name TEXT DEFAULT 'PC Anchor'
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $fn$
DECLARE
    v_code TEXT;
    v_chars TEXT := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    i INT;
BEGIN
    -- Generate unique code like CORA-XXXX
    LOOP
        v_code := 'CORA-';
        FOR i IN 1..4 LOOP
            v_code := v_code || substr(v_chars, floor(random() * length(v_chars) + 1)::int, 1);
        END LOOP;

        -- Check if code exists and not expired
        IF NOT EXISTS (
            SELECT 1 FROM cora_pairing
            WHERE code = v_code AND expires_at > NOW()
        ) THEN
            EXIT;
        END IF;
    END LOOP;

    -- Clean up old codes for this anchor
    DELETE FROM cora_pairing
    WHERE anchor_id = p_anchor_id
    AND (expires_at < NOW() OR claimed_by IS NOT NULL);

    -- Insert new code
    INSERT INTO cora_pairing (code, anchor_id, anchor_name)
    VALUES (v_code, p_anchor_id, p_anchor_name);

    RETURN v_code;
END;
$fn$;

-- =============================================================
-- RPC: Get pairing info (called by mobile to validate code)
-- =============================================================
CREATE OR REPLACE FUNCTION get_pairing_info(p_code TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $fn$
DECLARE
    v_pairing RECORD;
BEGIN
    SELECT * INTO v_pairing
    FROM cora_pairing
    WHERE code = UPPER(p_code)
    AND expires_at > NOW()
    AND claimed_by IS NULL;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'Invalid or expired code');
    END IF;

    RETURN jsonb_build_object(
        'code', v_pairing.code,
        'anchor_id', v_pairing.anchor_id,
        'anchor_name', v_pairing.anchor_name,
        'expires_at', v_pairing.expires_at
    );
END;
$fn$;

-- =============================================================
-- RPC: Start pairing (creates user if needed, sends magic link)
-- =============================================================
CREATE OR REPLACE FUNCTION start_pairing(
    p_code TEXT,
    p_email TEXT,
    p_name TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $fn$
DECLARE
    v_pairing RECORD;
    v_user_id UUID;
    v_token TEXT;
    v_chars TEXT := 'abcdefghijklmnopqrstuvwxyz0123456789';
    i INT;
BEGIN
    -- Validate pairing code
    SELECT * INTO v_pairing
    FROM cora_pairing
    WHERE code = UPPER(p_code)
    AND expires_at > NOW()
    AND claimed_by IS NULL;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'Invalid or expired pairing code');
    END IF;

    -- Get or create user
    SELECT id INTO v_user_id FROM cora_users WHERE email = LOWER(p_email);

    IF v_user_id IS NULL THEN
        INSERT INTO cora_users (email, name)
        VALUES (LOWER(p_email), p_name)
        RETURNING id INTO v_user_id;
    END IF;

    -- Generate magic link token
    v_token := '';
    FOR i IN 1..32 LOOP
        v_token := v_token || substr(v_chars, floor(random() * length(v_chars) + 1)::int, 1);
    END LOOP;

    -- Create magic link
    INSERT INTO cora_magic_links (email, token, pairing_code)
    VALUES (LOWER(p_email), v_token, v_pairing.code);

    RETURN jsonb_build_object(
        'success', true,
        'user_id', v_user_id,
        'token', v_token,
        'message', 'Check your email for verification link'
    );
END;
$fn$;

-- =============================================================
-- RPC: Complete pairing (called when magic link clicked)
-- =============================================================
CREATE OR REPLACE FUNCTION complete_pairing(p_token TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $fn$
DECLARE
    v_link RECORD;
    v_user_id UUID;
    v_pairing RECORD;
    v_device_id UUID;
BEGIN
    -- Get magic link
    SELECT * INTO v_link
    FROM cora_magic_links
    WHERE token = p_token
    AND expires_at > NOW()
    AND used_at IS NULL;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'Invalid or expired link');
    END IF;

    -- Get user
    SELECT id INTO v_user_id FROM cora_users WHERE email = v_link.email;

    IF v_user_id IS NULL THEN
        RETURN jsonb_build_object('error', 'User not found');
    END IF;

    -- Get pairing code
    SELECT * INTO v_pairing
    FROM cora_pairing
    WHERE code = v_link.pairing_code;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'Pairing code not found');
    END IF;

    -- Mark magic link as used
    UPDATE cora_magic_links SET used_at = NOW() WHERE token = p_token;

    -- Mark pairing code as claimed
    UPDATE cora_pairing
    SET claimed_by = v_user_id, claimed_at = NOW()
    WHERE code = v_link.pairing_code;

    -- Create or update device link
    INSERT INTO cora_devices (user_id, anchor_id, device_name)
    VALUES (v_user_id, v_pairing.anchor_id, 'Mobile')
    ON CONFLICT (user_id, anchor_id)
    DO UPDATE SET last_connected = NOW(), is_active = true
    RETURNING id INTO v_device_id;

    -- Update user last seen
    UPDATE cora_users SET last_seen = NOW() WHERE id = v_user_id;

    RETURN jsonb_build_object(
        'success', true,
        'user_id', v_user_id,
        'device_id', v_device_id,
        'anchor_id', v_pairing.anchor_id,
        'anchor_name', v_pairing.anchor_name
    );
END;
$fn$;

-- =============================================================
-- RPC: Check if anchor has connected devices
-- =============================================================
CREATE OR REPLACE FUNCTION get_anchor_devices(p_anchor_id TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $fn$
BEGIN
    RETURN (
        SELECT COALESCE(jsonb_agg(jsonb_build_object(
            'device_id', d.id,
            'user_name', u.name,
            'user_email', u.email,
            'paired_at', d.paired_at,
            'last_connected', d.last_connected,
            'is_active', d.is_active
        )), '[]'::jsonb)
        FROM cora_devices d
        JOIN cora_users u ON u.id = d.user_id
        WHERE d.anchor_id = p_anchor_id
        AND d.is_active = true
    );
END;
$fn$;

-- =============================================================
-- RPC: Check pairing status (poll from mobile)
-- =============================================================
CREATE OR REPLACE FUNCTION check_pairing_status(p_code TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $fn$
DECLARE
    v_pairing RECORD;
BEGIN
    SELECT * INTO v_pairing
    FROM cora_pairing
    WHERE code = UPPER(p_code);

    IF NOT FOUND THEN
        RETURN jsonb_build_object('status', 'not_found');
    END IF;

    IF v_pairing.claimed_by IS NOT NULL THEN
        RETURN jsonb_build_object(
            'status', 'claimed',
            'anchor_id', v_pairing.anchor_id,
            'anchor_name', v_pairing.anchor_name
        );
    END IF;

    IF v_pairing.expires_at < NOW() THEN
        RETURN jsonb_build_object('status', 'expired');
    END IF;

    RETURN jsonb_build_object(
        'status', 'pending',
        'expires_at', v_pairing.expires_at
    );
END;
$fn$;
