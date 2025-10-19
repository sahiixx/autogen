"""Additional comprehensive tests for TeamManager"""
import os
import json
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, Mock

os.environ.setdefault("OPENAI_API_KEY", "test")
from autogenstudio.teammanager import TeamManager
from autogenstudio.datamodel.types import TeamResult, EnvironmentVariable
from autogen_core import CancellationToken
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.conditions import TextMentionTermination


@pytest.fixture
def sample_config():
    """Create an actual team configuration"""
    agent = AssistantAgent(
        name="test_agent",
        model_client=OpenAIChatCompletionClient(model="gpt-4.1-nano"),
    )
    
    agent_team = RoundRobinGroupChat(
        [agent], 
        termination_condition=TextMentionTermination("TERMINATE")
    )
    
    config = agent_team.dump_component()
    return config.model_dump()


@pytest.fixture
def yaml_config_file(sample_config, tmp_path):
    """Create a YAML config file"""
    import yaml
    yaml_path = tmp_path / "test_team.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(sample_config, f)
    return yaml_path


class TestTeamManagerAdditional:
    
    @pytest.mark.asyncio
    async def test_load_from_file_yaml_format(self, yaml_config_file, sample_config):
        """Test loading YAML configuration"""
        config = await TeamManager.load_from_file(yaml_config_file)
        assert isinstance(config, dict)
        assert "provider" in config or "participants" in config or "label" in config
    
    @pytest.mark.asyncio
    async def test_load_from_directory_mixed_formats(self, tmp_path, sample_config):
        """Test loading from directory with multiple file formats"""
        # Create JSON file
        json_path = tmp_path / "team1.json"
        await asyncio.to_thread(lambda: json_path.write_text(json.dumps(sample_config)))
        
        # Create YAML file
        import yaml
        yaml_path = tmp_path / "team2.yml"
        yaml_config = sample_config.copy()
        yaml_config["label"] = "YAMLTeam"
        yaml_content = yaml.dump(yaml_config)
        await asyncio.to_thread(lambda: yaml_path.write_text(yaml_content))
        
        # Create non-config file (should be ignored)
        txt_path = tmp_path / "readme.txt"
        txt_path.write_text("This should be ignored")
        
        configs = await TeamManager.load_from_directory(tmp_path)
        assert len(configs) == 2
    
    @pytest.mark.asyncio
    async def test_load_from_directory_empty(self, tmp_path):
        """Test loading from empty directory"""
        configs = await TeamManager.load_from_directory(tmp_path)
        assert isinstance(configs, list)
        assert len(configs) == 0
    
    @pytest.mark.asyncio
    async def test_load_from_file_invalid_json(self, tmp_path):
        """Test loading invalid JSON file"""
        invalid_path = tmp_path / "invalid.json"
        invalid_path.write_text("{'invalid': json}")
        
        with pytest.raises(json.JSONDecodeError):
            await TeamManager.load_from_file(invalid_path)
    
    @pytest.mark.asyncio
    async def test_create_team_with_env_vars(self, sample_config):
        """Test creating team with environment variables"""
        team_manager = TeamManager()
        
        env_vars = [
            EnvironmentVariable(name="TEST_VAR_1", value="value1"),
            EnvironmentVariable(name="TEST_VAR_2", value="value2"),
        ]
        
        with patch("autogen_agentchat.base.Team.load_component") as mock_load:
            mock_team = MagicMock()
            mock_load.return_value = mock_team
            
            await team_manager._create_team(sample_config, env_vars=env_vars)
            
            # Verify environment variables were set
            assert os.environ.get("TEST_VAR_1") == "value1"
            assert os.environ.get("TEST_VAR_2") == "value2"
            
            # Cleanup
            os.environ.pop("TEST_VAR_1", None)
            os.environ.pop("TEST_VAR_2", None)
    
    @pytest.mark.asyncio
    async def test_run_with_cancellation(self, sample_config):
        """Test run method with cancellation"""
        team_manager = TeamManager()
        
        with patch.object(team_manager, "_create_team") as mock_create:
            mock_team = MagicMock()
            
            # Create a cancellation token that's already cancelled
            cancellation_token = CancellationToken()
            cancellation_token.cancel()
            
            # Mock team.run to check if cancellation token is passed
            async def mock_run(*args, **kwargs):
                token = kwargs.get("cancellation_token")
                if token and token.is_cancelled():
                    raise asyncio.CancelledError()
                return MagicMock()
            
            mock_team.run = mock_run
            mock_create.return_value = mock_team
            
            # Should handle cancellation gracefully
            with pytest.raises(asyncio.CancelledError):
                await team_manager.run(
                    task="Test task",
                    team_config=sample_config,
                    cancellation_token=cancellation_token
                )
    
    @pytest.mark.asyncio
    async def test_run_stream_with_various_message_types(self, sample_config):
        """Test run_stream with different message types"""
        team_manager = TeamManager()
        
        with patch.object(team_manager, "_create_team") as mock_create:
            mock_team = MagicMock()
            
            # Create mock messages of different types
            from autogen_agentchat.base import TaskResult
            from autogen_agentchat.messages import TextMessage
            
            mock_text_message = TextMessage(content="Test message", source="agent")
            mock_task_result = TaskResult(
                messages=[mock_text_message],
                stop_reason="Task completed"
            )
            
            mock_messages = [mock_text_message, mock_task_result]
            
            async def mock_run_stream(*args, **kwargs):
                for msg in mock_messages:
                    yield msg
            
            mock_team.run_stream = mock_run_stream
            mock_create.return_value = mock_team
            
            messages = []
            async for message in team_manager.run_stream(
                task="Test task",
                team_config=sample_config
            ):
                messages.append(message)
            
            # Should have received messages and a TeamResult
            assert len(messages) >= 2
            assert isinstance(messages[-1], TeamResult)
    
    @pytest.mark.asyncio
    async def test_create_team_from_path(self, tmp_path, sample_config):
        """Test creating team from file path"""
        team_manager = TeamManager()
        config_path = tmp_path / "team.json"
        
        await asyncio.to_thread(lambda: config_path.write_text(json.dumps(sample_config)))
        
        with patch("autogen_agentchat.base.Team.load_component") as mock_load:
            mock_team = MagicMock()
            mock_load.return_value = mock_team
            
            team = await team_manager._create_team(str(config_path))
            assert team == mock_team
    
    @pytest.mark.asyncio
    async def test_create_team_from_component_model(self, sample_config):
        """Test creating team from ComponentModel"""
        team_manager = TeamManager()
        
        from autogen_core import ComponentModel
        component_model = ComponentModel(
            provider="test_provider",
            config=sample_config
        )
        
        with patch("autogen_agentchat.base.Team.load_component") as mock_load:
            mock_team = MagicMock()
            mock_load.return_value = mock_team
            
            team = await team_manager._create_team(component_model)
            assert team == mock_team
    
    @pytest.mark.asyncio
    async def test_run_measures_duration(self, sample_config):
        """Test that run method measures duration correctly"""
        team_manager = TeamManager()
        
        with patch.object(team_manager, "_create_team") as mock_create:
            mock_team = MagicMock()
            
            async def mock_run(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate work
                return MagicMock()
            
            mock_team.run = mock_run
            mock_create.return_value = mock_team
            
            result = await team_manager.run(
                task="Test task",
                team_config=sample_config
            )
            
            assert isinstance(result, TeamResult)
            assert result.duration >= 0.1
    
    @pytest.mark.asyncio
    async def test_team_cleanup_on_exception(self, sample_config):
        """Test that team is cleaned up even when exception occurs"""
        team_manager = TeamManager()
        
        with patch.object(team_manager, "_create_team") as mock_create:
            mock_team = MagicMock()
            mock_agent = MagicMock()
            mock_agent.close = AsyncMock()
            mock_team._participants = [mock_agent]
            
            async def mock_run(*args, **kwargs):
                raise ValueError("Test error")
            
            mock_team.run = mock_run
            mock_create.return_value = mock_team
            
            with pytest.raises(ValueError):
                await team_manager.run(
                    task="Test task",
                    team_config=sample_config
                )
            
            # Verify cleanup was called
            mock_agent.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_from_directory_with_invalid_files(self, tmp_path, sample_config):
        """Test loading from directory with some invalid files"""
        # Create valid JSON file
        valid_path = tmp_path / "valid.json"
        await asyncio.to_thread(lambda: valid_path.write_text(json.dumps(sample_config)))
        
        # Create invalid JSON file
        invalid_path = tmp_path / "invalid.json"
        invalid_path.write_text("not valid json")
        
        configs = await TeamManager.load_from_directory(tmp_path)
        
        # Should only load the valid config
        assert len(configs) == 1
    
    @pytest.mark.asyncio
    async def test_create_team_with_unsupported_type(self):
        """Test _create_team with unsupported config type"""
        team_manager = TeamManager()
        
        with pytest.raises(ValueError, match="Unsupported team_config type"):
            await team_manager._create_team(12345)  # Invalid type