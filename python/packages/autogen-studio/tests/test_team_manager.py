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
 


class TestTeamManagerEnvironment:
    """Test suite for environment variable handling in team manager tests"""
    
    def test_openai_api_key_environment(self):
        """Test that OPENAI_API_KEY is properly set in test environment"""
        api_key = os.environ.get("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY should be set"
        assert api_key == "test", "OPENAI_API_KEY should use test value"
    
    @pytest.mark.asyncio
    async def test_team_creation_without_real_credentials(self, sample_config):
        """Test that teams can be created without real OpenAI credentials"""
        team_manager = TeamManager()
        
        with patch("autogen_agentchat.base.Team.load_component") as mock_load:
            mock_team = MagicMock()
            mock_load.return_value = mock_team
            
            # Should not fail due to missing real API credentials
            team = await team_manager._create_team(sample_config)
            assert team is not None


class TestTeamManagerAdvanced:
    """Additional comprehensive tests for TeamManager functionality"""
    
    @pytest.mark.asyncio
    async def test_load_from_file_json_format(self, config_file):
        """Test loading JSON configuration file"""
        config = await TeamManager.load_from_file(config_file)
        assert config is not None
        assert isinstance(config, dict)
        assert "component_type" in config or "label" in config
    
    @pytest.mark.asyncio
    async def test_load_from_file_invalid_json(self, tmp_path):
        """Test loading invalid JSON file raises appropriate error"""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{invalid json content")
        
        with pytest.raises((json.JSONDecodeError, ValueError)):
            await TeamManager.load_from_file(invalid_json)
    
    @pytest.mark.asyncio
    async def test_load_from_directory_empty(self, tmp_path):
        """Test loading from empty directory"""
        configs = await TeamManager.load_from_directory(tmp_path)
        assert isinstance(configs, list)
        assert len(configs) == 0
    
    @pytest.mark.asyncio
    async def test_load_from_directory_mixed_formats(self, config_dir):
        """Test loading directory with both JSON and YAML files"""
        configs = await TeamManager.load_from_directory(config_dir)
        assert len(configs) >= 2
        # Verify we got configs from both file types
        assert isinstance(configs, list)
        for config in configs:
            assert isinstance(config, dict)
    
    @pytest.mark.asyncio
    async def test_create_team_from_dict(self, sample_config):
        """Test creating team from dictionary config"""
        team_manager = TeamManager()
        
        with patch("autogen_agentchat.base.Team.load_component") as mock_load:
            mock_team = MagicMock()
            mock_load.return_value = mock_team
            
            team = await team_manager._create_team(sample_config)
            assert team == mock_team
            mock_load.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_team_from_path(self, config_file):
        """Test creating team from file path"""
        team_manager = TeamManager()
        
        with patch("autogen_agentchat.base.Team.load_component") as mock_load:
            mock_team = MagicMock()
            mock_load.return_value = mock_team
            
            team = await team_manager._create_team(config_file)
            assert team == mock_team
    
    @pytest.mark.asyncio
    async def test_create_team_with_env_vars(self, sample_config):
        """Test creating team with environment variables"""
        team_manager = TeamManager()
        
        env_vars = [
            EnvironmentVariable(name="TEST_VAR_1", value="value1"),
            EnvironmentVariable(name="TEST_VAR_2", value="value2")
        ]
        
        with patch("autogen_agentchat.base.Team.load_component") as mock_load:
            mock_team = MagicMock()
            mock_load.return_value = mock_team
            
            await team_manager._create_team(sample_config, env_vars=env_vars)
            
            # Verify environment variables were set
            assert os.environ.get("TEST_VAR_1") == "value1"
            assert os.environ.get("TEST_VAR_2") == "value2"
    
    @pytest.mark.asyncio
    async def test_run_stream_with_cancellation(self, sample_config):
        """Test run_stream with cancellation token"""
        team_manager = TeamManager()
        cancellation_token = CancellationToken()
        
        with patch.object(team_manager, "_create_team") as mock_create:
            mock_team = MagicMock()
            
            async def mock_run_stream(*args, **kwargs):
                yield MagicMock()
                # Check if cancelled
                if kwargs.get("cancellation_token") and kwargs["cancellation_token"].is_cancelled():
                    return
                yield MagicMock()
            
            mock_team.run_stream = mock_run_stream
            mock_create.return_value = mock_team
            
            messages = []
            async for message in team_manager.run_stream(
                task="Test task",
                team_config=sample_config,
                cancellation_token=cancellation_token
            ):
                messages.append(message)
            
            assert len(messages) >= 1
    
    @pytest.mark.asyncio
    async def test_run_stream_empty_task(self, sample_config):
        """Test run_stream with None task"""
        team_manager = TeamManager()
        
        with patch.object(team_manager, "_create_team") as mock_create:
            mock_team = MagicMock()
            
            async def mock_run_stream(*args, **kwargs):
                # Should handle None task gracefully
                yield MagicMock()
            
            mock_team.run_stream = mock_run_stream
            mock_create.return_value = mock_team
            
            messages = []
            async for message in team_manager.run_stream(
                task=None,
                team_config=sample_config
            ):
                messages.append(message)
            
            assert len(messages) >= 1
            mock_create.assert_called_once()
    @pytest.mark.asyncio
    async def test_run_returns_team_result(self, sample_config):
        """TeamManager.run should return a TeamResult when BaseGroupChat.run is successful."""
        from autogenstudio.datamodel.types import TeamResult
        tm = TeamManager()
        # Patch BaseGroupChat.load_component to avoid constructing real teams
        with patch("autogen_agentchat.teams.BaseGroupChat.load_component") as mock_load:
            class DummyTeam:
                _participants = []
                async def run(self, *args, **kwargs):
                    return MagicMock()  # stand-in for TaskResult
            mock_load.return_value = DummyTeam()
            result = await tm.run(task="hello", team_config=sample_config)
            assert isinstance(result, TeamResult)
            assert result.duration >= 0

    @pytest.mark.asyncio
    async def test_load_from_directory_ignores_non_config(self, tmp_path, sample_config):
        """Non-config files should be ignored when loading from directory."""
        # Valid files
        (tmp_path / "a.json").write_text(json.dumps(sample_config))
        import yaml as _yaml
        (tmp_path / "b.yml").write_text(_yaml.dump(sample_config))
        # Invalid file
        (tmp_path / "c.txt").write_text("noop")
        configs = await TeamManager.load_from_directory(tmp_path)
        assert len(configs) == 2