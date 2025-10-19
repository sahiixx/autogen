"""Additional comprehensive tests for ChatCompletionClientRecorder and session files"""
import asyncio
import aiofiles
import json
import os
import tempfile
from pathlib import Path

import pytest
from autogen_core.models import (
    CreateResult,
    UserMessage,
    RequestUsage,
)
from autogen_ext.experimental.task_centric_memory.utils import PageLogger
from autogen_ext.experimental.task_centric_memory.utils.chat_completion_client_recorder import (
    ChatCompletionClientRecorder,
)
from autogen_ext.models.replay import ReplayChatCompletionClient


@pytest.mark.asyncio
async def test_session_file_structure():
    """Test that session_1.json has the correct structure"""
    session_file = Path("python/packages/autogen-ext/session_1.json")
    
    assert session_file.exists(), "session_1.json should exist"
    
    async with aiofiles.open(session_file, "r") as f:
        data = json.loads(await f.read())
    
    assert isinstance(data, list), "Session file should contain a list"
    assert len(data) > 0, "Session file should not be empty"
    
    # Check first record structure
    record = data[0]
    assert "mode" in record, "Record should have mode field"
    assert "messages" in record, "Record should have messages field"
    assert "response" in record, "Record should have response field"
    assert "stream" in record, "Record should have stream field"
    
    # Verify mode
    assert record["mode"] in ["create", "create_stream"], "Mode should be create or create_stream"
    
    # Verify messages structure
    assert isinstance(record["messages"], list), "Messages should be a list"
    if len(record["messages"]) > 0:
        msg = record["messages"][0]
        assert "content" in msg, "Message should have content"
        assert "source" in msg, "Message should have source"
        assert "type" in msg, "Message should have type"
    
    # Verify response structure
    response = record["response"]
    assert "finish_reason" in response, "Response should have finish_reason"
    assert "content" in response, "Response should have content"
    assert "usage" in response, "Response should have usage"
    assert "cached" in response, "Response should have cached flag"


@pytest.mark.asyncio
async def test_record_mode_creates_session_file():
    """Test that recording mode creates a session file"""
    logger = PageLogger()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        session_file = os.path.join(tmp_dir, "test_session.json")
        
        mock_client = ReplayChatCompletionClient([
            "Response 1",
            "Response 2",
        ])
        
        recorder = ChatCompletionClientRecorder(
            mock_client,
            mode="record",
            session_file_path=session_file,
            logger=logger
        )
        
        # Execute multiple calls
        messages1 = [UserMessage(content="Message 1", source="User")]
        response1 = await recorder.create(messages1)
        assert response1.content == "Response 1"
        
        messages2 = [UserMessage(content="Message 2", source="User")]
        response2 = await recorder.create(messages2)
        assert response2.content == "Response 2"
        
        # Finalize to write to disk
        recorder.finalize()
        
        # Verify file was created
        assert os.path.exists(session_file), "Session file should be created"
        
        # Verify file contents
        async with aiofiles.open(session_file, "r") as f:
            data = json.loads(await f.read())
        
        assert len(data) == 2, "Should have 2 records"
        assert data[0]["response"]["content"] == "Response 1"
        assert data[1]["response"]["content"] == "Response 2"


@pytest.mark.asyncio
async def test_replay_mode_validates_messages():
    """Test that replay mode validates message matching"""
    logger = PageLogger()
    
    # Use the actual session_1.json file
    session_file = "./session_1.json"
    
    mock_client = ReplayChatCompletionClient(["Should not be used"])
    
    recorder = ChatCompletionClientRecorder(
        mock_client,
        mode="replay",
        session_file_path=session_file,
        logger=logger
    )
    
    # Send matching message
    messages = [UserMessage(content="Message 1", source="User")]
    response = await recorder.create(messages)
    
    assert isinstance(response, CreateResult)
    assert response.content == "Response to message 1"
    assert response.cached is True
    
    recorder.finalize()


@pytest.mark.asyncio
async def test_replay_mode_fails_on_message_mismatch():
    """Test that replay mode raises error on message mismatch"""
    logger = PageLogger()
    session_file = "./session_1.json"
    
    mock_client = ReplayChatCompletionClient(["Should not be used"])
    
    recorder = ChatCompletionClientRecorder(
        mock_client,
        mode="replay",
        session_file_path=session_file,
        logger=logger
    )
    
    # Send non-matching message
    messages = [UserMessage(content="Wrong message", source="User")]
    
    with pytest.raises(ValueError, match="doesn't match"):
        await recorder.create(messages)


@pytest.mark.asyncio
async def test_replay_mode_fails_on_exhausted_records():
    """Test that replay mode raises error when records are exhausted"""
    logger = PageLogger()
    session_file = "./session_1.json"
    
    mock_client = ReplayChatCompletionClient(["Should not be used"])
    
    recorder = ChatCompletionClientRecorder(
        mock_client,
        mode="replay",
        session_file_path=session_file,
        logger=logger
    )
    
    # Consume the recorded turn
    messages = [UserMessage(content="Message 1", source="User")]
    await recorder.create(messages)
    
    # Try to make another call (should fail)
    with pytest.raises(ValueError, match="No more recorded turns"):
        await recorder.create(messages)


@pytest.mark.asyncio
async def test_record_mode_captures_usage():
    """Test that record mode captures token usage"""
    logger = PageLogger()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        session_file = os.path.join(tmp_dir, "usage_test.json")
        
        mock_client = ReplayChatCompletionClient(["Test response"])
        
        recorder = ChatCompletionClientRecorder(
            mock_client,
            mode="record",
            session_file_path=session_file,
            logger=logger
        )
        
        messages = [UserMessage(content="Test message", source="User")]
        await recorder.create(messages)
        
        recorder.finalize()
        
        # Check usage in saved file
        async with aiofiles.open(session_file, "r") as f:
            data = json.loads(await f.read())
        
        assert "usage" in data[0]["response"]
        usage = data[0]["response"]["usage"]
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage


@pytest.mark.asyncio
async def test_recorder_with_missing_session_file():
    """Test that replay mode fails gracefully with missing file"""
    logger = PageLogger()
    
    mock_client = ReplayChatCompletionClient(["Test"])
    
    with pytest.raises(ValueError, match="Failed to load recorded session"):
        ChatCompletionClientRecorder(
            mock_client,
            mode="replay",
            session_file_path="./nonexistent_file.json",
            logger=logger
        )


@pytest.mark.asyncio
async def test_recorder_mode_validation():
    """Test that invalid mode raises error"""
    logger = PageLogger()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        session_file = os.path.join(tmp_dir, "test.json")
        
        # Create empty session file
        async with aiofiles.open(session_file, "w") as f:
            await f.write(json.dumps([]))
        
        mock_client = ReplayChatCompletionClient(["Test"])
        
        recorder = ChatCompletionClientRecorder(
            mock_client,
            mode="replay",  # Use replay to avoid needing actual calls
            session_file_path=session_file,
            logger=logger
        )
        
        # Manually set invalid mode to test error handling
        recorder.mode = "invalid_mode"
        
        messages = [UserMessage(content="Test", source="User")]
        
        with pytest.raises(ValueError, match="Unknown mode"):
            await recorder.create(messages)


@pytest.mark.asyncio
async def test_recorder_finalize_statistics():
    """Test that finalize reports statistics correctly"""
    logger = PageLogger()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        session_file = os.path.join(tmp_dir, "stats_test.json")
        
        mock_client = ReplayChatCompletionClient([
            "Response 1",
            "Response 2",
            "Response 3",
        ])
        
        recorder = ChatCompletionClientRecorder(
            mock_client,
            mode="record",
            session_file_path=session_file,
            logger=logger
        )
        
        # Make multiple calls
        for i in range(3):
            messages = [UserMessage(content=f"Message {i+1}", source="User")]
            await recorder.create(messages)
        
        recorder.finalize()
        
        # Verify all records were saved
        async with aiofiles.open(session_file, "r") as f:
            data = json.loads(await f.read())
        
        assert len(data) == 3
        assert len(recorder.records) == 3


@pytest.mark.asyncio
async def test_recorder_handles_empty_messages():
    """Test recorder behavior with empty message list"""
    logger = PageLogger()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        session_file = os.path.join(tmp_dir, "empty_test.json")
        
        mock_client = ReplayChatCompletionClient(["Response"])
        
        recorder = ChatCompletionClientRecorder(
            mock_client,
            mode="record",
            session_file_path=session_file,
            logger=logger
        )
        
        # Try with empty messages (might be valid in some scenarios)
        messages = []
        response = await recorder.create(messages)
        
        assert isinstance(response, CreateResult)
        
        recorder.finalize()


@pytest.mark.asyncio
async def test_replay_mode_type_mismatch():
    """Test that replay mode detects create vs create_stream mismatch"""
    logger = PageLogger()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        session_file = os.path.join(tmp_dir, "type_test.json")
        
        # Create a session with create_stream record
        session_data = [{
            "mode": "create_stream",
            "messages": [{"content": "Test", "source": "User", "type": "UserMessage"}],
            "response": {},
            "stream": []
        }]
        
        async with aiofiles.open(session_file, "w") as f:
            await f.write(json.dumps(session_data))
        
        mock_client = ReplayChatCompletionClient(["Test"])
        
        recorder = ChatCompletionClientRecorder(
            mock_client,
            mode="replay",
            session_file_path=session_file,
            logger=logger
        )
        
        messages = [UserMessage(content="Test", source="User")]
        
        # Should fail because we're calling create but record is create_stream
        with pytest.raises(ValueError, match="type mismatch"):
            await recorder.create(messages)