-- CORA-GO Relay Tables
-- PC Anchor <-> Mobile communication via Supabase

-- PC Status (heartbeat from anchor)
CREATE TABLE IF NOT EXISTS cora_status (
    id TEXT PRIMARY KEY DEFAULT 'anchor',
    online BOOLEAN DEFAULT true,
    last_seen TIMESTAMPTZ DEFAULT now(),
    system_info JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Commands from mobile to PC
CREATE TABLE IF NOT EXISTS cora_commands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anchor_id TEXT DEFAULT 'anchor',
    command TEXT NOT NULL,
    params JSONB DEFAULT '{}'::jsonb,
    status TEXT DEFAULT 'pending',  -- pending, running, done, error
    result JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- Index for pending commands
CREATE INDEX IF NOT EXISTS idx_cora_commands_status ON cora_commands(status);
CREATE INDEX IF NOT EXISTS idx_cora_commands_anchor ON cora_commands(anchor_id);

-- Drop ALL old versions first (handle various signatures)
DROP FUNCTION IF EXISTS get_cora_status();
DROP FUNCTION IF EXISTS get_cora_status(TEXT);
DROP FUNCTION IF EXISTS send_cora_command();
DROP FUNCTION IF EXISTS send_cora_command(TEXT);
DROP FUNCTION IF EXISTS send_cora_command(TEXT, JSONB);
DROP FUNCTION IF EXISTS send_cora_command(TEXT, JSONB, TEXT);
DROP FUNCTION IF EXISTS send_cora_command(TEXT, TEXT);
DROP FUNCTION IF EXISTS send_cora_command(JSONB);

-- RPC: Get PC status
CREATE OR REPLACE FUNCTION get_cora_status(p_anchor_id TEXT DEFAULT 'anchor')
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'id', id,
        'online', online AND (last_seen > now() - interval '60 seconds'),
        'last_seen', last_seen,
        'system_info', system_info
    ) INTO result
    FROM cora_status
    WHERE id = p_anchor_id;

    IF result IS NULL THEN
        RETURN jsonb_build_object('online', false, 'error', 'Anchor not found');
    END IF;

    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC: Send command to PC
CREATE OR REPLACE FUNCTION send_cora_command(
    p_command TEXT,
    p_params JSONB DEFAULT '{}'::jsonb,
    p_anchor_id TEXT DEFAULT 'anchor'
)
RETURNS UUID AS $$
DECLARE
    cmd_id UUID;
BEGIN
    INSERT INTO cora_commands (anchor_id, command, params, status)
    VALUES (p_anchor_id, p_command, p_params, 'pending')
    RETURNING id INTO cmd_id;

    RETURN cmd_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Enable RLS
ALTER TABLE cora_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE cora_commands ENABLE ROW LEVEL SECURITY;

-- Allow public access (anon key can read/write)
DROP POLICY IF EXISTS cora_status_all ON cora_status;
CREATE POLICY cora_status_all ON cora_status FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS cora_commands_all ON cora_commands;
CREATE POLICY cora_commands_all ON cora_commands FOR ALL USING (true) WITH CHECK (true);

-- Grant permissions
GRANT ALL ON cora_status TO anon, authenticated;
GRANT ALL ON cora_commands TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_cora_status TO anon, authenticated;
GRANT EXECUTE ON FUNCTION send_cora_command TO anon, authenticated;
