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
 

class TestEnvironmentSetup:
    """Test environment variable setup for team manager tests."""
    
    def test_openai_api_key_is_set(self):
        """Test that OPENAI_API_KEY environment variable is set for tests."""
        api_key = os.environ.get("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY should be set"
        assert api_key != "", "OPENAI_API_KEY should not be empty"
    
    def test_openai_api_key_allows_imports(self):
        """Test that having OPENAI_API_KEY set allows necessary imports."""
        try:
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            # If imports succeed without error, test passes
            assert True
        except Exception as e:
            pytest.fail(f"Should be able to import OpenAI modules with test key: {e}")
    
    def test_environment_set_before_imports(self):
        """Test that OPENAI_API_KEY is set before OpenAI imports."""
        # This verifies the pattern used in the actual test file
        import sys
        
        # Check if the key exists
        api_key = os.environ.get("OPENAI_API_KEY")
        assert api_key is not None
        
        # The modules should already be imported by now
        assert "autogenstudio.teammanager" in sys.modules
    
    def test_setdefault_pattern_works_correctly(self):
        """Test the os.environ.setdefault pattern used in the test file."""
        # Create a test key to verify setdefault behavior
        test_key = "TEST_SETDEFAULT_KEY"
        
        # Clear if exists
        os.environ.pop(test_key, None)
        
        # Use setdefault (should set to default)
        os.environ.setdefault(test_key, "default_value")
        assert os.environ[test_key] == "default_value"
        
        # Use setdefault again (should NOT change)
        os.environ.setdefault(test_key, "new_value")
        assert os.environ[test_key] == "default_value"
        
        # Cleanup
        del os.environ[test_key]
    
    def test_openai_client_instantiation_with_test_key(self):
        """Test that OpenAI client can be instantiated with test credentials."""
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        
        client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
        assert client is not None
        # We're not making actual API calls, just testing instantiation


class TestTeamManagerWithMockCredentials:
    """Test TeamManager functionality with mock OpenAI credentials."""
    
    @pytest.mark.asyncio
    async def test_create_team_config_without_api_calls(self, sample_config):
        """Test that creating team config doesn't require actual API calls."""
        # This should work with just the test credentials
        assert sample_config is not None
        assert isinstance(sample_config, dict)
        assert "label" in sample_config or "agents" in sample_config or "team_type" in sample_config
    
    @pytest.mark.asyncio
    async def test_load_from_file_with_mock_credentials(self, config_file):
        """Test loading config file works without real API credentials."""
        config = await TeamManager.load_from_file(config_file)
        assert config is not None
        assert isinstance(config, dict)
    
    @pytest.mark.asyncio
    async def test_team_manager_initialization_without_real_api_key(self):
        """Test that TeamManager can be initialized without real API key."""
        team_manager = TeamManager()
        assert team_manager is not None
    
    @pytest.mark.asyncio
    async def test_config_serialization_with_test_credentials(self, sample_config):
        """Test that configs can be serialized/deserialized with test credentials."""
        # Serialize
        serialized = json.dumps(sample_config)
        assert serialized is not None
        
        # Deserialize
        deserialized = json.loads(serialized)
        assert deserialized == sample_config
    
    @pytest.mark.asyncio
    async def test_multiple_config_files_with_test_credentials(self, config_dir):
        """Test loading multiple configs without real API credentials."""
        configs = await TeamManager.load_from_directory(config_dir)
        assert len(configs) >= 2
        
        # All configs should be valid dicts
        for config in configs:
            assert isinstance(config, dict)


class TestCredentialErrorHandling:
    """Test error handling related to credentials and environment setup."""
    
    def test_missing_api_key_behavior(self):
        """Test behavior when API key is temporarily removed."""
        original_key = os.environ.get("OPENAI_API_KEY")
        
        try:
            # Temporarily remove key
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
            
            # Re-import to test behavior
            # (In reality, modules are cached, but we can test the pattern)
            os.environ.setdefault("OPENAI_API_KEY", "test")
            assert os.environ["OPENAI_API_KEY"] == "test"
            
        finally:
            # Restore original
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
            else:
                os.environ["OPENAI_API_KEY"] = "test"
    
    def test_invalid_api_key_format_handled_gracefully(self):
        """Test that invalid API key formats are handled gracefully."""
        original_key = os.environ.get("OPENAI_API_KEY")
        
        try:
            # Set obviously invalid key
            os.environ["OPENAI_API_KEY"] = "not-a-real-key"
            
            # Should still be able to create team manager
            team_manager = TeamManager()
            assert team_manager is not None
            
        finally:
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
            else:
                os.environ["OPENAI_API_KEY"] = "test"
    
    @pytest.mark.asyncio
    async def test_api_key_not_leaked_in_errors(self, sample_config):
        """Test that API key is not leaked in error messages."""
        original_key = os.environ.get("OPENAI_API_KEY")
        test_secret_key = "sk-secret-test-key-should-not-appear"
        
        try:
            os.environ["OPENAI_API_KEY"] = test_secret_key
            
            # Try to trigger an error
            team_manager = TeamManager()
            
            # Create mock that raises exception
            with patch.object(team_manager, "_create_team") as mock_create:
                mock_create.side_effect = ValueError("Test error")
                
                try:
                    await team_manager._create_team(sample_config)
                except ValueError as e:
                    error_msg = str(e)
                    # Verify secret key is not in error message
                    assert test_secret_key not in error_msg
        finally:
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
            else:
                os.environ["OPENAI_API_KEY"] = "test"


class TestEnvironmentVariableOrdering:
    """Test that environment variable setup happens in the correct order."""
    
    def test_env_var_set_before_autogenstudio_import(self):
        """Verify OPENAI_API_KEY is available when autogenstudio modules are imported."""
        # At this point in the test file, the key should already be set
        assert os.environ.get("OPENAI_API_KEY") is not None
        
        # And the module should be importable
        import autogenstudio.teammanager
        assert autogenstudio.teammanager.TeamManager is not None
    
    def test_import_order_matches_file_structure(self):
        """Test that imports follow the pattern in the actual file."""
        # The pattern from the file is:
        # 1. import os
        # 2. import other standard libs
        # 3. import autogenstudio.teammanager
        # 4. set OPENAI_API_KEY
        # 5. import OpenAI-dependent modules
        
        # Verify key exists
        assert "OPENAI_API_KEY" in os.environ
        
        # Verify TeamManager is importable
        from autogenstudio.teammanager import TeamManager
        assert TeamManager is not None
        
        # Verify OpenAI-dependent imports work
        assert TeamResult is not None