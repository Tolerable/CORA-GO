-- CORA-GO: start_pairing RPC
-- Run this in EZTUNES Supabase SQL Editor

-- 1. First create run_migration helper (for future migrations)
CREATE OR REPLACE FUNCTION run_migration(sql_text TEXT)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSON;
BEGIN
    EXECUTE sql_text;
    RETURN json_build_object('success', true, 'executed_at', NOW());
EXCEPTION WHEN OTHERS THEN
    RETURN json_build_object('success', false, 'error', SQLERRM);
END;
$$;

-- 2. Create the start_pairing RPC for mobile pairing
CREATE OR REPLACE FUNCTION start_pairing(
    p_code text,
    p_email text,
    p_name text
) RETURNS jsonb AS $fn$
DECLARE
    v_user_id uuid;
    v_device_id uuid;
    v_anchor_id text;
    v_anchor_name text;
    v_pairing record;
BEGIN
    -- Get pairing info
    SELECT * INTO v_pairing FROM cora_pairing WHERE code = p_code;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'Invalid pairing code');
    END IF;

    IF v_pairing.expires_at < NOW() THEN
        RETURN jsonb_build_object('error', 'Pairing code expired');
    END IF;

    IF v_pairing.claimed_at IS NOT NULL THEN
        RETURN jsonb_build_object('error', 'Code already claimed');
    END IF;

    -- Generate IDs for response only
    v_user_id := gen_random_uuid();
    v_device_id := gen_random_uuid();
    v_anchor_id := v_pairing.anchor_id;
    v_anchor_name := v_pairing.anchor_name;

    -- Mark as claimed (set claimed_at only, not claimed_by due to FK)
    UPDATE cora_pairing
    SET claimed_at = NOW()
    WHERE code = p_code;

    RETURN jsonb_build_object(
        'success', true,
        'paired', true,
        'user_id', v_user_id,
        'device_id', v_device_id,
        'anchor_id', v_anchor_id,
        'anchor_name', v_anchor_name,
        'email', p_email,
        'name', p_name
    );
END;
$fn$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3. Create get_pairing_info RPC (for code validation)
CREATE OR REPLACE FUNCTION get_pairing_info(p_code text)
RETURNS jsonb AS $fn$
DECLARE
    v_pairing record;
BEGIN
    SELECT * INTO v_pairing FROM cora_pairing WHERE code = p_code;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'Invalid pairing code');
    END IF;

    IF v_pairing.expires_at < NOW() THEN
        RETURN jsonb_build_object('error', 'Pairing code expired');
    END IF;

    RETURN jsonb_build_object(
        'valid', true,
        'anchor_id', v_pairing.anchor_id,
        'anchor_name', v_pairing.anchor_name
    );
END;
$fn$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. Create check_pairing_status RPC
CREATE OR REPLACE FUNCTION check_pairing_status(p_code text)
RETURNS jsonb AS $fn$
DECLARE
    v_pairing record;
BEGIN
    SELECT * INTO v_pairing FROM cora_pairing WHERE code = p_code;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('status', 'expired');
    END IF;

    IF v_pairing.claimed_at IS NOT NULL THEN
        RETURN jsonb_build_object(
            'status', 'claimed',
            'device_name', COALESCE(v_pairing.claimed_by::text, 'Mobile'),
            'anchor_id', v_pairing.anchor_id,
            'anchor_name', v_pairing.anchor_name
        );
    END IF;

    IF v_pairing.expires_at < NOW() THEN
        RETURN jsonb_build_object('status', 'expired');
    END IF;

    RETURN jsonb_build_object('status', 'pending');
END;
$fn$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant access
GRANT EXECUTE ON FUNCTION start_pairing(text, text, text) TO anon;
GRANT EXECUTE ON FUNCTION get_pairing_info(text) TO anon;
GRANT EXECUTE ON FUNCTION check_pairing_status(text) TO anon;
