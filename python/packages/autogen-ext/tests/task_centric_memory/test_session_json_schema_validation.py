"""
Comprehensive tests for session JSON file schema validation.
Tests the session_1.json file structure used by ChatCompletionClientRecorder.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import pytest


class TestSessionJsonSchemaValidation:
    """Test suite for validating session JSON file format and structure."""

    @pytest.fixture
    def session_file_path(self) -> Path:
        """Return the path to the session_1.json file."""
        return Path("python/packages/autogen-ext/session_1.json")

    @pytest.fixture
    def session_data(self, session_file_path: Path) -> List[Dict[str, Any]]:
        """Load and return the session data from session_1.json."""
        with open(session_file_path, "r") as f:
            return json.load(f)

    def test_session_file_exists(self, session_file_path: Path) -> None:
        """Test that session_1.json file exists."""
        assert session_file_path.exists(), f"Session file not found: {session_file_path}"
        assert session_file_path.is_file(), f"Session path is not a file: {session_file_path}"

    def test_session_file_is_valid_json(self, session_file_path: Path) -> None:
        """Test that session_1.json contains valid JSON."""
        try:
            with open(session_file_path, "r") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in session file: {e}")

    def test_session_data_is_list(self, session_data: List[Dict[str, Any]]) -> None:
        """Test that session data is a list of records."""
        assert isinstance(session_data, list), "Session data must be a list"
        assert len(session_data) > 0, "Session data should not be empty"

    def test_record_has_required_fields(self, session_data: List[Dict[str, Any]]) -> None:
        """Test that each record has the required fields: mode, messages, response, stream."""
        required_fields = {"mode", "messages", "response", "stream"}
        for idx, record in enumerate(session_data):
            assert isinstance(record, dict), f"Record {idx} must be a dictionary"
            missing_fields = required_fields - set(record.keys())
            assert not missing_fields, f"Record {idx} missing required fields: {missing_fields}"

    def test_mode_field_valid(self, session_data: List[Dict[str, Any]]) -> None:
        """Test that mode field has valid values."""
        valid_modes = {"create", "create_stream"}
        for idx, record in enumerate(session_data):
            mode = record.get("mode")
            assert mode in valid_modes, f"Record {idx} has invalid mode: {mode}. Expected one of {valid_modes}"

    def test_messages_field_structure(self, session_data: List[Dict[str, Any]]) -> None:
        """Test that messages field is a list of message dictionaries."""
        for idx, record in enumerate(session_data):
            messages = record.get("messages")
            assert isinstance(messages, list), f"Record {idx}: messages must be a list"
            for msg_idx, message in enumerate(messages):
                assert isinstance(message, dict), f"Record {idx}, message {msg_idx} must be a dictionary"
                # Check for common message fields
                assert "content" in message, f"Record {idx}, message {msg_idx} missing 'content'"
                assert "source" in message, f"Record {idx}, message {msg_idx} missing 'source'"
                assert "type" in message, f"Record {idx}, message {msg_idx} missing 'type'"

    def test_first_record_structure_matches_expected(self, session_data: List[Dict[str, Any]]) -> None:
        """Test that the first record matches the expected structure from the test."""
        assert len(session_data) >= 1, "Session data should have at least one record"
        first_record = session_data[0]
        
        assert first_record["mode"] == "create"
        assert len(first_record["messages"]) == 1
        assert first_record["messages"][0]["content"] == "Message 1"
        assert first_record["messages"][0]["source"] == "User"
        assert first_record["messages"][0]["type"] == "UserMessage"
        assert first_record["response"]["content"] == "Response to message 1"
        assert first_record["response"]["finish_reason"] == "stop"
        assert isinstance(first_record["stream"], list)