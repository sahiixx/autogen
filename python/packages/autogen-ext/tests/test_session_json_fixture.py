"""
Comprehensive tests for session_1.json fixture file used by ChatCompletionClientRecorder tests.
This validates the test fixture structure and ensures it conforms to expected schema.
"""
import json
import os
import pytest
from pathlib import Path


@pytest.fixture
def session_fixture_path():
    """Get path to session_1.json fixture"""
    # session_1.json is in the autogen-ext package root
    base_path = Path(__file__).parent.parent
    return base_path / "session_1.json"


class TestSessionJsonFixture:
    """Test suite for validating session_1.json test fixture"""
    
    def test_session_file_exists(self, session_fixture_path):
        """Test that session_1.json fixture file exists"""
        assert session_fixture_path.exists(), f"Session fixture should exist at {session_fixture_path}"
        assert session_fixture_path.is_file(), "Session fixture should be a file"
    
    def test_session_file_valid_json(self, session_fixture_path):
        """Test that session_1.json contains valid JSON"""
        with open(session_fixture_path, 'r') as f:
            data = json.load(f)
        assert data is not None, "Session fixture should contain valid JSON"
        assert isinstance(data, list), "Session fixture should be a JSON array"
    
    def test_session_structure(self, session_fixture_path):
        """Test that session_1.json has expected structure"""
        with open(session_fixture_path, 'r') as f:
            data = json.load(f)
        
        assert len(data) > 0, "Session fixture should contain at least one record"
        
        # Validate first record structure
        record = data[0]
        assert "mode" in record, "Record should have 'mode' field"
        assert "messages" in record, "Record should have 'messages' field"
        assert "response" in record, "Record should have 'response' field"
        assert "stream" in record, "Record should have 'stream' field"
    
    def test_session_mode_field(self, session_fixture_path):
        """Test that mode field has valid value"""
        with open(session_fixture_path, 'r') as f:
            data = json.load(f)
        
        record = data[0]
        assert record["mode"] == "create", "Mode should be 'create' or 'create_stream'"
    
    def test_session_messages_structure(self, session_fixture_path):
        """Test that messages array has correct structure"""
        with open(session_fixture_path, 'r') as f:
            data = json.load(f)
        
        record = data[0]
        messages = record["messages"]
        assert isinstance(messages, list), "Messages should be an array"
        assert len(messages) > 0, "Messages should not be empty"
        
        # Validate message structure
        message = messages[0]
        assert "content" in message, "Message should have 'content'"
        assert "source" in message, "Message should have 'source'"
        assert "type" in message, "Message should have 'type'"
        assert message["type"] == "UserMessage", "First message type should be UserMessage"
        assert message["source"] == "User", "Message source should be 'User'"
        assert message["content"] == "Message 1", "Message content should match"
    
    def test_session_response_structure(self, session_fixture_path):
        """Test that response object has correct structure"""
        with open(session_fixture_path, 'r') as f:
            data = json.load(f)
        
        record = data[0]
        response = record["response"]
        assert isinstance(response, dict), "Response should be an object"
        
        # Validate response fields
        assert "finish_reason" in response, "Response should have 'finish_reason'"
        assert "content" in response, "Response should have 'content'"
        assert "usage" in response, "Response should have 'usage'"
        
        assert response["finish_reason"] == "stop", "Finish reason should be 'stop'"
        assert response["content"] == "Response to message 1", "Content should match"
    
    def test_session_usage_structure(self, session_fixture_path):
        """Test that usage object has correct structure"""
        with open(session_fixture_path, 'r') as f:
            data = json.load(f)
        
        record = data[0]
        usage = record["response"]["usage"]
        assert isinstance(usage, dict), "Usage should be an object"
        
        # Validate usage fields
        assert "prompt_tokens" in usage, "Usage should have 'prompt_tokens'"
        assert "completion_tokens" in usage, "Usage should have 'completion_tokens'"
        
        assert isinstance(usage["prompt_tokens"], int), "Prompt tokens should be integer"
        assert isinstance(usage["completion_tokens"], int), "Completion tokens should be integer"
        assert usage["prompt_tokens"] == 2, "Prompt tokens should match"
        assert usage["completion_tokens"] == 4, "Completion tokens should match"
    
    def test_session_optional_fields(self, session_fixture_path):
        """Test optional fields in response"""
        with open(session_fixture_path, 'r') as f:
            data = json.load(f)
        
        record = data[0]
        response = record["response"]
        
        # These fields are optional but should be present in fixture
        assert "cached" in response, "Response should have 'cached' field"
        assert response["cached"] is True, "Cached should be True"
        
        assert "logprobs" in response, "Response should have 'logprobs' field"
        assert response["logprobs"] is None, "Logprobs should be None"
        
        assert "thought" in response, "Response should have 'thought' field"
        assert response["thought"] is None, "Thought should be None"
    
    def test_session_stream_field(self, session_fixture_path):
        """Test that stream field is present and empty for create mode"""
        with open(session_fixture_path, 'r') as f:
            data = json.load(f)
        
        record = data[0]
        assert "stream" in record, "Record should have 'stream' field"
        assert isinstance(record["stream"], list), "Stream should be an array"
        assert len(record["stream"]) == 0, "Stream should be empty for 'create' mode"
    
    def test_session_file_used_by_recorder_test(self):
        """Test that session_1.json is used by ChatCompletionClientRecorder test"""
        # Verify the test file references session_1.json
        test_file = Path(__file__).parent / "task_centric_memory" / "test_chat_completion_client_recorder.py"
        
        if test_file.exists():
            content = test_file.read_text()
            assert "session_1.json" in content, "Test should reference session_1.json"
            assert "ChatCompletionClientRecorder" in content, "Test should use ChatCompletionClientRecorder"


class TestSessionJsonCompatibility:
    """Test session_1.json compatibility with ChatCompletionClientRecorder"""
    
    def test_fixture_matches_recorder_expectations(self, session_fixture_path):
        """Test that fixture structure matches what ChatCompletionClientRecorder expects"""
        with open(session_fixture_path, 'r') as f:
            data = json.load(f)
        
        # Validate it matches RecordDict TypedDict structure
        for record in data:
            assert record["mode"] in ["create", "create_stream"], "Mode must be valid"
            assert isinstance(record["messages"], list), "Messages must be list"
            assert isinstance(record["response"], dict), "Response must be dict"
            assert isinstance(record["stream"], list), "Stream must be list"
    
    def test_fixture_can_be_loaded_for_replay(self, session_fixture_path):
        """Test that fixture can be loaded in replay mode"""
        # Simulate what ChatCompletionClientRecorder does in replay mode
        try:
            with open(session_fixture_path, 'r') as f:
                records = json.load(f)
            
            assert len(records) > 0, "Should have records to replay"
            
            # Simulate checking a record
            record = records[0]
            assert record["mode"] == "create", "First record should be create mode"
            
            # Simulate extracting response
            response_data = record["response"]
            assert "content" in response_data
            assert "finish_reason" in response_data
            assert "usage" in response_data
            
        except Exception as e:
            pytest.fail(f"Failed to load fixture for replay: {e}")
    
    def test_message_content_matches_response(self, session_fixture_path):
        """Test logical consistency between message and response"""
        with open(session_fixture_path, 'r') as f:
            data = json.load(f)
        
        record = data[0]
        message_content = record["messages"][0]["content"]
        response_content = record["response"]["content"]
        
        # Response should reference the message
        assert message_content == "Message 1", "Message content should be 'Message 1'"
        assert "message 1" in response_content.lower(), "Response should reference the message"