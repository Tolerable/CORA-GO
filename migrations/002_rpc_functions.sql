-- CORA-GO RPC Functions
-- Run after 001_initial_schema.sql

-- ============================================
-- NOTES OPERATIONS
-- ============================================

-- Upsert a note (add or update)
CREATE OR REPLACE FUNCTION upsert_note(
    p_key TEXT,
    p_content TEXT,
    p_tags TEXT[] DEFAULT '{}'
)
RETURNS JSON AS $$
DECLARE
    v_note notes;
BEGIN
    INSERT INTO notes (user_id, key, content, tags)
    VALUES (auth.uid(), p_key, p_content, p_tags)
    ON CONFLICT (user_id, key) DO UPDATE SET
        content = EXCLUDED.content,
        tags = EXCLUDED.tags,
        updated_at = NOW()
    RETURNING * INTO v_note;

    RETURN json_build_object(
        'success', true,
        'note', row_to_json(v_note)
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get a note by key
CREATE OR REPLACE FUNCTION get_note(p_key TEXT)
RETURNS JSON AS $$
DECLARE
    v_note notes;
BEGIN
    SELECT * INTO v_note
    FROM notes
    WHERE user_id = auth.uid() AND key = p_key;

    IF v_note IS NULL THEN
        RETURN json_build_object('success', false, 'error', 'Note not found');
    END IF;

    RETURN json_build_object('success', true, 'note', row_to_json(v_note));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Search notes
CREATE OR REPLACE FUNCTION search_notes(
    p_query TEXT DEFAULT NULL,
    p_tag TEXT DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    v_notes JSON;
BEGIN
    SELECT json_agg(row_to_json(n)) INTO v_notes
    FROM notes n
    WHERE n.user_id = auth.uid()
        AND (p_query IS NULL OR
             n.content ILIKE '%' || p_query || '%' OR
             n.key ILIKE '%' || p_query || '%')
        AND (p_tag IS NULL OR p_tag = ANY(n.tags));

    RETURN json_build_object(
        'success', true,
        'notes', COALESCE(v_notes, '[]'::json)
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- INCIDENTS OPERATIONS
-- ============================================

-- Log an incident
CREATE OR REPLACE FUNCTION log_incident(
    p_category TEXT,
    p_transcript TEXT DEFAULT NULL,
    p_duration FLOAT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS JSON AS $$
DECLARE
    v_incident incidents;
BEGIN
    INSERT INTO incidents (user_id, category, transcript, duration_seconds, metadata)
    VALUES (auth.uid(), p_category, p_transcript, p_duration, p_metadata)
    RETURNING * INTO v_incident;

    RETURN json_build_object(
        'success', true,
        'incident', row_to_json(v_incident)
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get recent incidents
CREATE OR REPLACE FUNCTION get_incidents(
    p_category TEXT DEFAULT NULL,
    p_hours INT DEFAULT 24,
    p_limit INT DEFAULT 50
)
RETURNS JSON AS $$
DECLARE
    v_incidents JSON;
BEGIN
    SELECT json_agg(row_to_json(i)) INTO v_incidents
    FROM (
        SELECT * FROM incidents
        WHERE user_id = auth.uid()
            AND created_at > NOW() - (p_hours || ' hours')::INTERVAL
            AND (p_category IS NULL OR category = p_category)
        ORDER BY created_at DESC
        LIMIT p_limit
    ) i;

    RETURN json_build_object(
        'success', true,
        'incidents', COALESCE(v_incidents, '[]'::json)
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- CHAT OPERATIONS
-- ============================================

-- Save chat message
CREATE OR REPLACE FUNCTION save_chat(
    p_session_id UUID,
    p_role TEXT,
    p_content TEXT,
    p_persona TEXT DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    v_msg chat_history;
BEGIN
    INSERT INTO chat_history (user_id, session_id, role, content, persona)
    VALUES (auth.uid(), p_session_id, p_role, p_content, p_persona)
    RETURNING * INTO v_msg;

    RETURN json_build_object('success', true, 'message', row_to_json(v_msg));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get chat session
CREATE OR REPLACE FUNCTION get_chat_session(
    p_session_id UUID,
    p_limit INT DEFAULT 100
)
RETURNS JSON AS $$
DECLARE
    v_messages JSON;
BEGIN
    SELECT json_agg(row_to_json(m)) INTO v_messages
    FROM (
        SELECT * FROM chat_history
        WHERE user_id = auth.uid() AND session_id = p_session_id
        ORDER BY created_at ASC
        LIMIT p_limit
    ) m;

    RETURN json_build_object(
        'success', true,
        'messages', COALESCE(v_messages, '[]'::json)
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- PROFILE OPERATIONS
-- ============================================

-- Update user settings
CREATE OR REPLACE FUNCTION update_settings(p_settings JSONB)
RETURNS JSON AS $$
DECLARE
    v_profile profiles;
BEGIN
    UPDATE profiles
    SET settings = settings || p_settings,
        updated_at = NOW()
    WHERE id = auth.uid()
    RETURNING * INTO v_profile;

    RETURN json_build_object('success', true, 'profile', row_to_json(v_profile));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get user profile with settings
CREATE OR REPLACE FUNCTION get_my_profile()
RETURNS JSON AS $$
DECLARE
    v_profile profiles;
BEGIN
    SELECT * INTO v_profile
    FROM profiles
    WHERE id = auth.uid();

    RETURN json_build_object('success', true, 'profile', row_to_json(v_profile));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- DEVICE SYNC
-- ============================================

-- Register device
CREATE OR REPLACE FUNCTION register_device(
    p_device_name TEXT,
    p_device_type TEXT,
    p_push_token TEXT DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    v_device devices;
BEGIN
    INSERT INTO devices (user_id, device_name, device_type, push_token)
    VALUES (auth.uid(), p_device_name, p_device_type, p_push_token)
    ON CONFLICT (id) DO UPDATE SET
        last_seen = NOW(),
        push_token = COALESCE(EXCLUDED.push_token, devices.push_token)
    RETURNING * INTO v_device;

    RETURN json_build_object('success', true, 'device', row_to_json(v_device));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Heartbeat (update last_seen)
CREATE OR REPLACE FUNCTION device_heartbeat(p_device_id UUID)
RETURNS JSON AS $$
BEGIN
    UPDATE devices
    SET last_seen = NOW()
    WHERE id = p_device_id AND user_id = auth.uid();

    RETURN json_build_object('success', true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
