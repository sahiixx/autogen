import os
import json
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from autogenstudio.teammanager import TeamManager

# Ensure tests don't require real OpenAI credentials
os.environ.setdefault("OPENAI_API_KEY", "test")
from autogenstudio.datamodel.types import TeamResult, EnvironmentVariable
from autogen_core import CancellationToken


@pytest.fixture
def sample_config():
    """Create an actual team and dump its configuration"""
    from autogen_agentchat.agents import AssistantAgent
    from autogen_agentchat.teams import RoundRobinGroupChat
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_agentchat.conditions import TextMentionTermination
    
    agent = AssistantAgent(
        name="weather_agent",
        model_client=OpenAIChatCompletionClient(
            model="gpt-4.1-nano",
        ),
    )
    
    agent_team = RoundRobinGroupChat(
        [agent], 
        termination_condition=TextMentionTermination("TERMINATE")
    )
    
    # Dump component and return as dict
    config = agent_team.dump_component()
    return config.model_dump()


@pytest.fixture
def config_file(sample_config, tmp_path):
    """Create a temporary config file"""
    config_path = tmp_path / "test_config.json"
    with open(config_path, "w") as f:
        json.dump(sample_config, f)
    return config_path


@pytest.fixture
def config_dir(sample_config, tmp_path):
    """Create a temporary directory with multiple config files"""
    # Create JSON config
    json_path = tmp_path / "team1.json"
    with open(json_path, "w") as f:
        json.dump(sample_config, f)
    
    # Create YAML config from the same dict
    import yaml
    yaml_path = tmp_path / "team2.yaml"
    # Create a modified copy to verify we can distinguish between them
    yaml_config = sample_config.copy()
    yaml_config["label"] = "YamlTeam"  # Change a field to identify this as the YAML version
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_config, f)
    
    return tmp_path


class TestTeamManager:
    
    @pytest.mark.asyncio
    async def test_load_from_file(self, config_file, sample_config):
        """Test loading configuration from a file"""
        config = await TeamManager.load_from_file(config_file)
        assert config == sample_config
        
        # Test file not found
        with pytest.raises(FileNotFoundError):
            await TeamManager.load_from_file("nonexistent_file.json")
        
        # Test unsupported format
        wrong_format = config_file.with_suffix(".txt")
        wrong_format.touch()
        with pytest.raises(ValueError, match="Unsupported file format"):
            await TeamManager.load_from_file(wrong_format)
    
    @pytest.mark.asyncio
    async def test_load_from_directory(self, config_dir):
        """Test loading all configurations from a directory"""
        configs = await TeamManager.load_from_directory(config_dir)
        assert len(configs) == 2 
        
        # Check if at least one team has expected label
        team_labels = [config.get("label") for config in configs]
        assert "RoundRobinGroupChat" in team_labels or "YamlTeam" in team_labels
    
    @pytest.mark.asyncio
    async def test_create_team(self, sample_config):
        """Test creating a team from config"""
        team_manager = TeamManager()
        
        # Mock Team.load_component
        with patch("autogen_agentchat.base.Team.load_component") as mock_load:
            mock_team = MagicMock()
            mock_load.return_value = mock_team
            
            team = await team_manager._create_team(sample_config)
            assert team == mock_team
            mock_load.assert_called_once_with(sample_config)
    

    
    @pytest.mark.asyncio
    async def test_run_stream(self, sample_config):
        """Test streaming team execution results"""
        team_manager = TeamManager()
        
        # Mock _create_team and team.run_stream
        with patch.object(team_manager, "_create_team") as mock_create:
            mock_team = MagicMock()
            
            # Create some mock messages to stream
            mock_messages = [MagicMock(), MagicMock()]
            mock_result = MagicMock()  # TaskResult from run
            mock_messages.append(mock_result)  # Last message is the result
            
            # Set up the async generator for run_stream
            async def mock_run_stream(*args, **kwargs):
                for msg in mock_messages:
                    yield msg
            
            mock_team.run_stream = mock_run_stream
            mock_create.return_value = mock_team
            
            # Call run_stream and collect results
            streamed_messages = []
            async for message in team_manager.run_stream(
                task="Test task",
                team_config=sample_config
            ):
                streamed_messages.append(message)
            
            # Verify the team was created
            mock_create.assert_called_once()
            
            # Check that we got the expected number of messages +1 for the TeamResult
            assert len(streamed_messages) == len(mock_messages)
            
            # Verify the last message is a TeamResult
            assert isinstance(streamed_messages[-1], type(mock_messages[-1]))
 

    @pytest.mark.asyncio
    async def test_create_team_injects_env_vars(self, sample_config, monkeypatch):
        """_create_team should load provided env vars into process environment."""
        team_manager = TeamManager()
        with patch("autogen_agentchat.teams.BaseGroupChat.load_component") as mock_load:
            mock_team = MagicMock()
            # Avoid touching UserProxyAgent path by leaving participants empty
            mock_team._participants = []
            mock_load.return_value = mock_team
            varname = "UNITTEST_FOO"
            if varname in os.environ:
                del os.environ[varname]
            env_vars = [EnvironmentVariable(name=varname, value="BAR")]
            team = await team_manager._create_team(sample_config, env_vars=env_vars)
            assert team is mock_team
            assert os.environ.get(varname) == "BAR"

    @pytest.mark.asyncio
    async def test_run_wraps_result(self, sample_config):
        """run should wrap the underlying team's result in a TeamResult."""
        team_manager = TeamManager()
        with patch.object(team_manager, "_create_team") as mock_create:
            mock_team = MagicMock()
            from autogen_agentchat.base import TaskResult
            async def mock_run(*args, **kwargs):
                return TaskResult(messages=[], stop_reason="test")
            mock_team.run = mock_run
            mock_create.return_value = mock_team
            result = await team_manager.run(task="task", team_config=sample_config)
            from autogenstudio.datamodel.types import TeamResult
            assert isinstance(result, TeamResult)
            assert hasattr(result, "task_result")

    @pytest.mark.asyncio
    async def test_run_stream_respects_cancellation_early(self, sample_config):
        """If cancellation is requested, run_stream should stop early."""
        team_manager = TeamManager()
        with patch.object(team_manager, "_create_team") as mock_create:
            mock_team = MagicMock()
            async def gen(*args, **kwargs):
                # Emit multiple messages; manager should break after first due to cancellation
                yield MagicMock()
                yield MagicMock()
            mock_team.run_stream = gen
            mock_create.return_value = mock_team
            from autogen_core import CancellationToken
            token = CancellationToken()
            token.cancel()
            received = []
            async for msg in team_manager.run_stream(task="t", team_config=sample_config, cancellation_token=token):
                received.append(msg)
            assert len(received) <= 1

    @pytest.mark.asyncio
    async def test_load_from_directory_ignores_non_config_files(self, config_dir):
        """Non JSON/YAML files should be ignored when loading from a directory."""
        stray = Path(config_dir) / "ignore.me"
        stray.write_text("not a config")
        configs = await TeamManager.load_from_directory(config_dir)
        # The fixture creates exactly two valid configs (json + yaml)
        assert len(configs) == 2

class TestTeamManagerTaskResultHandling:
    """Additional tests for proper TaskResult handling in TeamManager."""
    
    @pytest.mark.asyncio
    async def test_run_returns_team_result_with_task_result(self, sample_config):
        """Test that run returns TeamResult containing TaskResult."""
        team_manager = TeamManager()
        with patch.object(team_manager, "_create_team") as mock_create:
            mock_team = MagicMock()
            from autogen_agentchat.base import TaskResult
            from autogen_agentchat.messages import TextMessage
            
            # Create a proper TaskResult with messages
            test_messages = [
                TextMessage(content="Test message 1", source="agent1"),
                TextMessage(content="Test message 2", source="agent2")
            ]
            async def mock_run(*args, **kwargs):
                return TaskResult(messages=test_messages, stop_reason="completed")
            
            mock_team.run = mock_run
            mock_create.return_value = mock_team
            
            result = await team_manager.run(task="test task", team_config=sample_config)
            
            from autogenstudio.datamodel.types import TeamResult
            assert isinstance(result, TeamResult)
            assert hasattr(result, "task_result")
            assert result.task_result is not None
            assert result.task_result.stop_reason == "completed"
            assert len(result.task_result.messages) == 2
    
    @pytest.mark.asyncio
    async def test_run_preserves_task_result_stop_reasons(self, sample_config):
        """Test that different stop reasons are preserved in TaskResult."""
        team_manager = TeamManager()
        
        stop_reasons = ["completed", "max_turns", "timeout", "cancelled", "error"]
        
        for stop_reason in stop_reasons:
            with patch.object(team_manager, "_create_team") as mock_create:
                mock_team = MagicMock()
                from autogen_agentchat.base import TaskResult
                
                async def mock_run(*args, _stop_reason=stop_reason, **kwargs):
                    return TaskResult(messages=[], stop_reason=_stop_reason)
                
                mock_team.run = mock_run
                mock_create.return_value = mock_team
                
                result = await team_manager.run(task="test", team_config=sample_config)
                
                assert result.task_result.stop_reason == stop_reason
    
    @pytest.mark.asyncio
    async def test_run_handles_empty_messages(self, sample_config):
        """Test that run handles TaskResult with empty messages list."""
        team_manager = TeamManager()
        with patch.object(team_manager, "_create_team") as mock_create:
            mock_team = MagicMock()
            from autogen_agentchat.base import TaskResult
            
            async def mock_run(*args, **kwargs):
                return TaskResult(messages=[], stop_reason="no_messages")
            
            mock_team.run = mock_run
            mock_create.return_value = mock_team
            
            result = await team_manager.run(task="test", team_config=sample_config)
            
            assert isinstance(result.task_result, TaskResult)
            assert len(result.task_result.messages) == 0
    
    @pytest.mark.asyncio
    async def test_run_with_multiple_message_types(self, sample_config):
        """Test that run handles TaskResult with various message types."""
        team_manager = TeamManager()
        with patch.object(team_manager, "_create_team") as mock_create:
            mock_team = MagicMock()
            from autogen_agentchat.base import TaskResult
            from autogen_agentchat.messages import TextMessage, StopMessage
            
            # Create messages of different types
            messages = [
                TextMessage(content="Hello", source="user"),
                TextMessage(content="Response", source="assistant"),
                StopMessage(content="Done", source="system")
            ]
            
            async def mock_run(*args, **kwargs):
                return TaskResult(messages=messages, stop_reason="completed")
            
            mock_team.run = mock_run
            mock_create.return_value = mock_team
            
            result = await team_manager.run(task="test", team_config=sample_config)
            
            assert len(result.task_result.messages) == 3
            assert result.task_result.messages[0].content == "Hello"
            assert result.task_result.messages[2].source == "system"
    
    @pytest.mark.asyncio
    async def test_run_with_cancellation_token(self, sample_config):
        """Test that run properly passes cancellation token to underlying team."""
        team_manager = TeamManager()
        with patch.object(team_manager, "_create_team") as mock_create:
            mock_team = MagicMock()
            from autogen_agentchat.base import TaskResult
            from autogen_core import CancellationToken
            
            token = CancellationToken()
            run_called_with_token = None
            
            async def mock_run(*args, **kwargs):
                nonlocal run_called_with_token
                run_called_with_token = kwargs.get('cancellation_token')
                return TaskResult(messages=[], stop_reason="test")
            
            mock_team.run = mock_run
            mock_create.return_value = mock_team
            
            await team_manager.run(
                task="test", 
                team_config=sample_config,
                cancellation_token=token
            )
            
            # Verify the token was passed through
            assert run_called_with_token is not None
    
    @pytest.mark.asyncio
    async def test_task_result_immutability(self, sample_config):
        """Test that TaskResult is properly wrapped and not mutated."""
        team_manager = TeamManager()
        with patch.object(team_manager, "_create_team") as mock_create:
            mock_team = MagicMock()
            from autogen_agentchat.base import TaskResult
            from autogen_agentchat.messages import TextMessage
            
            original_messages = [TextMessage(content="Original", source="test")]
            
            async def mock_run(*args, **kwargs):
                return TaskResult(
                    messages=original_messages.copy(), 
                    stop_reason="original"
                )
            
            mock_team.run = mock_run
            mock_create.return_value = mock_team
            
            result = await team_manager.run(task="test", team_config=sample_config)
            
            # Verify the result contains the task result
            assert result.task_result.messages[0].content == "Original"
            assert result.task_result.stop_reason == "original"