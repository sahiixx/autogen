import json
from pathlib import Path

def test_session_json_schema():
    """Validate basic schema and types for session_1.json."""
    session_path = Path(__file__).resolve().parent.parent / "session_1.json"
    assert session_path.exists(), f"Missing asset: {session_path}"
    data = json.loads(session_path.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) >= 1
    item = data[0]
    # Top-level keys
    for key in ("mode", "messages", "response", "stream"):
        assert key in item
    assert isinstance(item["messages"], list) and len(item["messages"]) >= 1
    msg0 = item["messages"][0]
    assert isinstance(msg0, dict)
    for key in ("content", "source", "type"):
        assert key in msg0
    # Response block
    resp = item["response"]
    assert isinstance(resp, dict)
    assert "usage" in resp and isinstance(resp["usage"], dict)
    usage = resp["usage"]
    # Token counts should be integers
    assert isinstance(usage.get("prompt_tokens"), int)
    assert isinstance(usage.get("completion_tokens"), int)
    # cached flag should be boolean
    assert isinstance(resp.get("cached"), bool)
    # stream should be a list
    assert isinstance(item["stream"], list)