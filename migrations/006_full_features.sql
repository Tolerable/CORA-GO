-- CORA-GO Full Features Migration
-- Run in EZTUNES-LIVE Supabase SQL Editor

-- Screen sharing for TeamViewer mode
CREATE TABLE IF NOT EXISTS cora_screens (
    id TEXT PRIMARY KEY,
    image_data TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    width INT DEFAULT 1920,
    height INT DEFAULT 1080
);

-- Team chat
CREATE TABLE IF NOT EXISTS cora_chat (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anchor_id TEXT NOT NULL DEFAULT 'anchor',
    sender TEXT NOT NULL,
    message TEXT NOT NULL,
    msg_type TEXT DEFAULT 'text',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Brain/knowledge base
CREATE TABLE IF NOT EXISTS cora_brain (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anchor_id TEXT NOT NULL DEFAULT 'anchor',
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT
);

-- Projects
CREATE TABLE IF NOT EXISTS cora_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anchor_id TEXT NOT NULL DEFAULT 'anchor',
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active',
    tasks JSONB DEFAULT '[]'::JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE cora_screens ENABLE ROW LEVEL SECURITY;
ALTER TABLE cora_chat ENABLE ROW LEVEL SECURITY;
ALTER TABLE cora_brain ENABLE ROW LEVEL SECURITY;
ALTER TABLE cora_projects ENABLE ROW LEVEL SECURITY;

-- Policies (open for now)
CREATE POLICY "screens_all" ON cora_screens FOR ALL USING (true);
CREATE POLICY "chat_all" ON cora_chat FOR ALL USING (true);
CREATE POLICY "brain_all" ON cora_brain FOR ALL USING (true);
CREATE POLICY "projects_all" ON cora_projects FOR ALL USING (true);

-- Index for chat ordering
CREATE INDEX IF NOT EXISTS idx_cora_chat_time ON cora_chat(anchor_id, created_at DESC);

-- RPC: Get recent chat messages
CREATE OR REPLACE FUNCTION get_cora_chat(
    p_anchor_id TEXT DEFAULT 'anchor',
    p_limit INT DEFAULT 50
) RETURNS JSONB AS $fn$
BEGIN
    RETURN (
        SELECT COALESCE(jsonb_agg(row_to_json(c)::JSONB), '[]'::JSONB)
        FROM (
            SELECT * FROM cora_chat
            WHERE anchor_id = p_anchor_id
            ORDER BY created_at DESC
            LIMIT p_limit
        ) c
    );
END;
$fn$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC: Post chat message
CREATE OR REPLACE FUNCTION post_cora_chat(
    p_anchor_id TEXT,
    p_sender TEXT,
    p_message TEXT,
    p_msg_type TEXT DEFAULT 'text'
) RETURNS UUID AS $fn$
DECLARE
    v_id UUID;
BEGIN
    INSERT INTO cora_chat (anchor_id, sender, message, msg_type)
    VALUES (p_anchor_id, p_sender, p_message, p_msg_type)
    RETURNING id INTO v_id;
    RETURN v_id;
END;
$fn$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC: Update screen
CREATE OR REPLACE FUNCTION update_cora_screen(
    p_anchor_id TEXT,
    p_image_data TEXT,
    p_width INT DEFAULT 1920,
    p_height INT DEFAULT 1080
) RETURNS BOOLEAN AS $fn$
BEGIN
    INSERT INTO cora_screens (id, image_data, width, height, updated_at)
    VALUES (p_anchor_id, p_image_data, p_width, p_height, NOW())
    ON CONFLICT (id) DO UPDATE SET
        image_data = EXCLUDED.image_data,
        width = EXCLUDED.width,
        height = EXCLUDED.height,
        updated_at = NOW();
    RETURN true;
END;
$fn$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC: Brain remember
CREATE OR REPLACE FUNCTION brain_remember(
    p_anchor_id TEXT,
    p_key TEXT,
    p_value TEXT,
    p_category TEXT DEFAULT 'general',
    p_updated_by TEXT DEFAULT 'user'
) RETURNS UUID AS $fn$
DECLARE
    v_id UUID;
BEGIN
    INSERT INTO cora_brain (anchor_id, key, value, category, updated_by)
    VALUES (p_anchor_id, p_key, p_value, p_category, p_updated_by)
    RETURNING id INTO v_id;
    RETURN v_id;
END;
$fn$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC: Brain recall
CREATE OR REPLACE FUNCTION brain_recall(
    p_anchor_id TEXT,
    p_key TEXT DEFAULT NULL,
    p_category TEXT DEFAULT NULL
) RETURNS JSONB AS $fn$
BEGIN
    RETURN (
        SELECT COALESCE(jsonb_agg(row_to_json(b)::JSONB), '[]'::JSONB)
        FROM cora_brain b
        WHERE anchor_id = p_anchor_id
        AND (p_key IS NULL OR key ILIKE '%' || p_key || '%')
        AND (p_category IS NULL OR category = p_category)
        ORDER BY created_at DESC
    );
END;
$fn$ LANGUAGE plpgsql SECURITY DEFINER;
