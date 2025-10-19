import asyncio 
import pytest
import os
from sqlmodel import Session, text, select
from typing import Generator

from autogenstudio.database import DatabaseManager

# Ensure tests don't require real OpenAI credentials
os.environ.setdefault("OPENAI_API_KEY", "test")
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.conditions import TextMentionTermination
from autogenstudio.datamodel.db import Team, Session as SessionModel, Run, Message, RunStatus, MessageConfig


@pytest.fixture
def test_db(tmp_path) -> Generator[DatabaseManager, None, None]:
    """Fixture for test database using temporary paths"""
    db_path = tmp_path / "test.db"
    db = DatabaseManager(f"sqlite:///{db_path}", base_dir=tmp_path)
    db.reset_db()
    # Initialize database instead of create_db_and_tables
    db.initialize_database(auto_upgrade=False)
    yield db
    # Clean up
    asyncio.run(db.close())
    db.reset_db()
    # No need to manually remove files - tmp_path is cleaned up automatically


@pytest.fixture
def test_user() -> str:
    return "test_user@example.com"


@pytest.fixture
def sample_team(test_user: str) -> Team:
    """Create a sample team with proper config"""
    agent = AssistantAgent(
        name="weather_agent",
        model_client=OpenAIChatCompletionClient(
            model="gpt-4.1-nano",
        ), 
    )

    agent_team = RoundRobinGroupChat([agent], termination_condition=TextMentionTermination("TERMINATE"))
    team_component = agent_team.dump_component()

    return Team(
        user_id=test_user,
        component=team_component.model_dump(),
    )


class TestDatabaseOperations:
    def test_basic_setup(self, test_db: DatabaseManager):
        """Test basic database setup and connection"""
        with Session(test_db.engine) as session:
            result = session.exec(text("SELECT 1")).first() # type: ignore
            assert result[0] == 1
            result = session.exec(select(1)).first()
            assert result == 1

    def test_basic_entity_creation(self, test_db: DatabaseManager, sample_team: Team):
        """Test creating all entity types with proper configs"""
        # Use upsert instead of raw session
        response = test_db.upsert(sample_team)
        assert response.status is True
        
        with Session(test_db.engine) as session:
            saved_team = session.get(Team, sample_team.id)
            assert saved_team is not None

    def test_upsert_operations(self, test_db: DatabaseManager, sample_team: Team):
        """Test upsert for both create and update scenarios"""
        # Test Create
        response = test_db.upsert(sample_team)
        assert response.status is True
        assert "Created Successfully" in response.message

        # Test Update
        team_id = sample_team.id
        sample_team.version = "0.0.2"
        response = test_db.upsert(sample_team)
        assert response.status is True

        # Verify Update
        result = test_db.get(Team, {"id": team_id})
        assert result.status is True
        assert result.data and result.data[0].version == "0.0.2"

    def test_delete_operations(self, test_db: DatabaseManager, sample_team: Team):
        """Test delete with various filters"""
        # First insert the model
        response = test_db.upsert(sample_team)
        assert response.status is True  # Verify insert worked
        
        # Get the ID that was actually saved
        team_id = sample_team.id
        
        # Test deletion by id
        response = test_db.delete(Team, {"id": team_id})
        assert response.status is True
        assert "Deleted Successfully" in response.message

        # Verify deletion
        result = test_db.get(Team, {"id": team_id})
        if result.data:
            assert len(result.data) == 0 
        
    def test_cascade_delete(self, test_db: DatabaseManager, test_user: str):
        """Test all levels of cascade delete"""
        # Enable foreign keys for SQLite (crucial for cascade delete)
        with Session(test_db.engine) as session:
            session.execute(text("PRAGMA foreign_keys=ON"))
            session.commit()

        # Test Run -> Message cascade
        team1 = Team(user_id=test_user, component={"name": "Team1", "type": "team"})
        test_db.upsert(team1)
        session1 = SessionModel(user_id=test_user, team_id=team1.id, name="Session1")
        test_db.upsert(session1)
        run1_id = 1
        test_db.upsert(Run(
            id=run1_id, 
            user_id=test_user, 
            session_id=session1.id or 1,  # Ensure session_id is not None
            status=RunStatus.COMPLETE, 
            task=MessageConfig(content="Task1", source="user").model_dump()
        ))
        test_db.upsert(Message(
            user_id=test_user, 
            session_id=session1.id, 
            run_id=run1_id, 
            config=MessageConfig(content="Message1", source="assistant").model_dump()
        ))
        
        test_db.delete(Run, {"id": run1_id})
        db_message = test_db.get(Message, {"run_id": run1_id})
        if db_message.data:
            assert len(db_message.data) == 0, "Run->Message cascade failed"

        # Test Session -> Run -> Message cascade
        session2 = SessionModel(user_id=test_user, team_id=team1.id, name="Session2")
        test_db.upsert(session2)
        run2_id = 2
        test_db.upsert(Run(
            id=run2_id, 
            user_id=test_user, 
            session_id=session2.id or 2,  # Ensure session_id is not None
            status=RunStatus.COMPLETE, 
            task=MessageConfig(content="Task2", source="user").model_dump()
        ))
        test_db.upsert(Message(
            user_id=test_user, 
            session_id=session2.id, 
            run_id=run2_id, 
            config=MessageConfig(content="Message2", source="assistant").model_dump()
        ))
        
        test_db.delete(SessionModel, {"id": session2.id})
        session = test_db.get(SessionModel, {"id": session2.id})
        run = test_db.get(Run, {"id": run2_id})
        if session.data:
            assert len(session.data) == 0, "Session->Run cascade failed"
        if run.data:
            assert len(run.data) == 0, "Session->Run->Message cascade failed"

        # Clean up
        test_db.delete(Team, {"id": team1.id})

    def test_initialize_database_scenarios(self, tmp_path, monkeypatch):
        """Test different initialize_database parameters"""
        db_path = tmp_path / "test_init.db"
        db = DatabaseManager(f"sqlite:///{db_path}", base_dir=tmp_path)
        
        # Mock the schema manager's check_schema_status to avoid migration issues
        monkeypatch.setattr(db.schema_manager, "check_schema_status", lambda: (False, None))
        monkeypatch.setattr(db.schema_manager, "ensure_schema_up_to_date", lambda: True)

        try:
            # Test basic initialization
            response = db.initialize_database()
            assert response.status is True

            # Test with auto_upgrade
            response = db.initialize_database(auto_upgrade=True)
            assert response.status is True

        finally:
            asyncio.run(db.close())
            db.reset_db() 


class TestEnvironmentSetup:
    """Test environment variable setup for database manager tests."""
    
    def test_openai_api_key_is_set(self):
        """Test that OPENAI_API_KEY environment variable is set for tests."""
        api_key = os.environ.get("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY should be set"
        assert api_key != "", "OPENAI_API_KEY should not be empty"
    
    def test_openai_api_key_default_value(self):
        """Test that OPENAI_API_KEY has the expected test value."""
        # The test file sets it to "test" if not already set
        api_key = os.environ.get("OPENAI_API_KEY")
        # Should either be "test" (default) or a real key if already set
        assert api_key is not None
        assert len(api_key) > 0
    
    def test_openai_imports_work_with_test_key(self):
        """Test that OpenAI-related imports work with test API key."""
        try:
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import RoundRobinGroupChat
            # If imports succeed, test passes
            assert True
        except ImportError as e:
            pytest.fail(f"OpenAI imports should work with test key: {e}")
    
    def test_can_create_openai_client_without_real_credentials(self):
        """Test that OpenAIChatCompletionClient can be instantiated with test credentials."""
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        
        # This should not raise an error during instantiation
        # (actual API calls will fail, but that's expected)
        try:
            client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
            assert client is not None
        except Exception as e:
            # Some initialization errors are expected, but not import/config errors
            error_msg = str(e).lower()
            assert "import" not in error_msg and "module" not in error_msg
    
    def test_assistant_agent_creation_with_test_credentials(self, test_user: str):
        """Test that AssistantAgent can be created with test credentials."""
        from autogen_agentchat.agents import AssistantAgent
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        
        # Should be able to create agent without making actual API calls
        agent = AssistantAgent(
            name="test_agent",
            model_client=OpenAIChatCompletionClient(model="gpt-4.1-nano"),
        )
        assert agent is not None
        assert agent.name == "test_agent"
    
    def test_environment_isolation(self):
        """Test that environment changes don't affect other tests."""
        original_key = os.environ.get("OPENAI_API_KEY")
        
        # Temporarily change the key
        os.environ["OPENAI_API_KEY"] = "temporary_test_key"
        assert os.environ["OPENAI_API_KEY"] == "temporary_test_key"
        
        # Restore original
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key
        else:
            os.environ["OPENAI_API_KEY"] = "test"
        
        # Verify restoration
        assert os.environ["OPENAI_API_KEY"] in [original_key, "test"]
    
    def test_setdefault_does_not_override_existing(self):
        """Test that os.environ.setdefault doesn't override existing values."""
        # Set a specific value
        os.environ["TEST_KEY_DB_MANAGER"] = "existing_value"
        
        # Try to set default
        os.environ.setdefault("TEST_KEY_DB_MANAGER", "default_value")
        
        # Should still have the existing value
        assert os.environ["TEST_KEY_DB_MANAGER"] == "existing_value"
        
        # Cleanup
        del os.environ["TEST_KEY_DB_MANAGER"]
    
    def test_multiple_test_instances_share_environment(self):
        """Test that all test instances share the same environment variables."""
        key1 = os.environ.get("OPENAI_API_KEY")
        
        # Import again (simulating what happens in another test)
        import os as os2
        key2 = os2.environ.get("OPENAI_API_KEY")
        
        assert key1 == key2, "Environment should be consistent across imports"


class TestDatabaseWithMockCredentials:
    """Test database operations work without real OpenAI API calls."""
    
    def test_team_creation_doesnt_require_api_call(self, test_db: DatabaseManager, test_user: str):
        """Test that creating team config doesn't make actual OpenAI API calls."""
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.teams import RoundRobinGroupChat
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_agentchat.conditions import TextMentionTermination
        from autogenstudio.datamodel.db import Team
        
        # Create agent and team (should not make API calls)
        agent = AssistantAgent(
            name="test_agent",
            model_client=OpenAIChatCompletionClient(model="gpt-4.1-nano"),
        )
        agent_team = RoundRobinGroupChat(
            [agent], 
            termination_condition=TextMentionTermination("TERMINATE")
        )
        team_component = agent_team.dump_component()
        
        team = Team(
            user_id=test_user,
            component=team_component.model_dump(),
        )
        
        # Save to database (should work without API calls)
        response = test_db.upsert(team)
        assert response.status is True
        
        # Retrieve from database
        result = test_db.get(Team, {"id": team.id})
        assert result.status is True
        assert result.data is not None
    
    def test_database_operations_independent_of_api_key_validity(self, test_db: DatabaseManager):
        """Test that database operations work regardless of API key validity."""
        # Store original key
        original_key = os.environ.get("OPENAI_API_KEY")
        
        try:
            # Set to obviously fake key
            os.environ["OPENAI_API_KEY"] = "sk-fake-key-for-testing-only"
            
            # Database operations should still work
            with Session(test_db.engine) as session:
                result = session.exec(text("SELECT 1")).first()
                assert result[0] == 1
        finally:
            # Restore original
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
            else:
                os.environ["OPENAI_API_KEY"] = "test"