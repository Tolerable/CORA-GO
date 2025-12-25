-- CORA-GO Anchor ID Support
-- Updates existing tables to support multiple anchors

-- Add anchor_id column to cora_commands if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'cora_commands' AND column_name = 'anchor_id'
    ) THEN
        ALTER TABLE cora_commands ADD COLUMN anchor_id TEXT DEFAULT 'anchor';
    END IF;
END $$;

-- Create index for anchor-based queries
CREATE INDEX IF NOT EXISTS idx_cora_commands_anchor
ON cora_commands(anchor_id, status, created_at)
WHERE status = 'pending';

-- Update send_cora_command to include anchor_id
CREATE OR REPLACE FUNCTION send_cora_command(
    p_command TEXT,
    p_params JSONB DEFAULT '{}',
    p_anchor_id TEXT DEFAULT 'anchor'
) RETURNS UUID AS $fn$
DECLARE
    v_id UUID;
BEGIN
    INSERT INTO cora_commands (command, params, anchor_id)
    VALUES (p_command, p_params, p_anchor_id)
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$fn$ LANGUAGE plpgsql SECURITY DEFINER;

-- Update get_cora_status to filter by anchor_id
CREATE OR REPLACE FUNCTION get_cora_status(
    p_anchor_id TEXT DEFAULT 'anchor'
)
RETURNS JSONB AS $fn$
DECLARE
    v_status JSONB;
BEGIN
    SELECT row_to_json(s)::JSONB INTO v_status
    FROM cora_status s
    WHERE id = p_anchor_id;

    -- Check if online (last seen within 60 seconds)
    IF v_status IS NOT NULL THEN
        IF v_status->>'last_seen' IS NOT NULL THEN
            IF (NOW() - (v_status->>'last_seen')::TIMESTAMPTZ) > INTERVAL '60 seconds' THEN
                v_status = v_status || '{"online": false}'::JSONB;
            END IF;
        END IF;
    END IF;

    RETURN COALESCE(v_status, '{"online": false}'::JSONB);
END;
$fn$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC: Get pending commands for specific anchor
CREATE OR REPLACE FUNCTION get_pending_commands(
    p_anchor_id TEXT DEFAULT 'anchor',
    p_limit INT DEFAULT 5
)
RETURNS JSONB AS $fn$
BEGIN
    RETURN (
        SELECT COALESCE(jsonb_agg(row_to_json(c)::JSONB), '[]'::JSONB)
        FROM (
            SELECT * FROM cora_commands
            WHERE anchor_id = p_anchor_id
            AND status = 'pending'
            ORDER BY created_at ASC
            LIMIT p_limit
        ) c
    );
END;
$fn$ LANGUAGE plpgsql SECURITY DEFINER;
