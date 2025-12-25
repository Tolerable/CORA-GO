-- CORA-GO Relay Tables
-- Enables PC<->Mobile communication via Supabase

-- PC status (heartbeat)
CREATE TABLE IF NOT EXISTS cora_status (
    id TEXT PRIMARY KEY DEFAULT 'anchor',
    online BOOLEAN DEFAULT false,
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    system_info JSONB DEFAULT '{}',
    active_tools JSONB DEFAULT '[]'
);

-- Commands from mobile to PC
CREATE TABLE IF NOT EXISTS cora_commands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id TEXT NOT NULL DEFAULT 'mobile',
    command TEXT NOT NULL,
    params JSONB DEFAULT '{}',
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'done', 'error')),
    result JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Enable RLS
ALTER TABLE cora_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE cora_commands ENABLE ROW LEVEL SECURITY;

-- Policies - allow all for now (can restrict later)
DROP POLICY IF EXISTS "cora_status_all" ON cora_status;
CREATE POLICY "cora_status_all" ON cora_status FOR ALL USING (true);

DROP POLICY IF EXISTS "cora_commands_all" ON cora_commands;
CREATE POLICY "cora_commands_all" ON cora_commands FOR ALL USING (true);

-- Index for faster polling
CREATE INDEX IF NOT EXISTS idx_cora_commands_pending 
ON cora_commands(status, created_at) 
WHERE status = 'pending';

-- RPC to send command (used by mobile)
CREATE OR REPLACE FUNCTION send_cora_command(
    p_command TEXT,
    p_params JSONB DEFAULT '{}'
) RETURNS UUID AS $fn$
DECLARE
    v_id UUID;
BEGIN
    INSERT INTO cora_commands (command, params)
    VALUES (p_command, p_params)
    RETURNING id INTO v_id;
    
    RETURN v_id;
END;
$fn$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC to get PC status (used by mobile)
CREATE OR REPLACE FUNCTION get_cora_status()
RETURNS JSONB AS $fn$
DECLARE
    v_status JSONB;
BEGIN
    SELECT row_to_json(s)::JSONB INTO v_status
    FROM cora_status s
    WHERE id = 'anchor';
    
    RETURN COALESCE(v_status, '{"online": false}'::JSONB);
END;
$fn$ LANGUAGE plpgsql SECURITY DEFINER;
