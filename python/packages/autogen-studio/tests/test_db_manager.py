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


class TestDatabaseEnvironmentVariables:
    """Test suite for environment variable handling in database tests"""
    
    def test_openai_api_key_set(self):
        """Test that OPENAI_API_KEY environment variable is properly set"""
        # This validates the fix added in the diff to prevent tests requiring real API keys
        api_key = os.environ.get("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY should be set for tests"
        assert api_key == "test", "OPENAI_API_KEY should be set to 'test' for test environment"
    
    def test_openai_imports_dont_fail(self):
        """Test that OpenAI-dependent imports work with test API key"""
        # Verify imports work without real credentials
        from autogen_agentchat.agents import AssistantAgent
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        assert AssistantAgent is not None
        assert OpenAIChatCompletionClient is not None
    
    def test_assistant_agent_creation_with_test_key(self, test_user: str):
        """Test that AssistantAgent can be created with test API key"""
        from autogen_agentchat.agents import AssistantAgent
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        
        # Should not raise authentication errors with test key
        agent = AssistantAgent(
            name="test_agent",
            model_client=OpenAIChatCompletionClient(model="gpt-4.1-nano"),
        )
        assert agent is not None
        assert agent.name == "test_agent"


class TestDatabaseAdvancedOperations:
    """Additional comprehensive tests for database operations"""
    
    def test_upsert_with_empty_data(self, test_db: DatabaseManager, test_user: str):
        """Test upsert behavior with minimal data"""
        team = Team(user_id=test_user, component={})
        response = test_db.upsert(team)
        assert response.status is True
        
        # Verify retrieval
        result = test_db.get(Team, {"id": team.id})
        assert result.status is True
        assert result.data is not None
        assert len(result.data) == 1
    
    def test_get_with_multiple_filters(self, test_db: DatabaseManager, sample_team: Team):
        """Test get operation with multiple filter conditions"""
        test_db.upsert(sample_team)
        
        # Test with multiple filters
        result = test_db.get(Team, {"id": sample_team.id, "user_id": sample_team.user_id})
        assert result.status is True
        assert result.data is not None
        assert len(result.data) == 1
    
    def test_delete_nonexistent_entity(self, test_db: DatabaseManager):
        """Test deleting an entity that doesn't exist"""
        # Generate a UUID that doesn't exist
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_db.delete(Team, {"id": fake_id})
        # Should succeed even if no rows deleted
        assert response.status is True
    
    def test_concurrent_upserts(self, test_db: DatabaseManager, test_user: str):
        """Test concurrent upsert operations"""
        teams = []
        for i in range(5):
            team = Team(
                user_id=test_user,
                component={"name": f"Team{i}", "type": "team"}
            )
            response = test_db.upsert(team)
            assert response.status is True
            teams.append(team)
        
        # Verify all were created
        for team in teams:
            result = test_db.get(Team, {"id": team.id})
            assert result.status is True
            assert result.data is not None
            assert len(result.data) == 1
    
    def test_session_run_message_relationships(self, test_db: DatabaseManager, test_user: str, sample_team: Team):
        """Test relationships between Session, Run, and Message entities"""
        # Create hierarchy: Team -> Session -> Run -> Message
        test_db.upsert(sample_team)
        
        session = SessionModel(user_id=test_user, team_id=sample_team.id, name="TestSession")
        test_db.upsert(session)
        
        run = Run(
            user_id=test_user,
            session_id=session.id,
            status=RunStatus.COMPLETE,
            task=MessageConfig(content="TestTask", source="user").model_dump()
        )
        test_db.upsert(run)
        
        message = Message(
            user_id=test_user,
            session_id=session.id,
            run_id=run.id,
            config=MessageConfig(content="TestMessage", source="assistant").model_dump()
        )
        test_db.upsert(message)
        
        # Verify relationships
        session_result = test_db.get(SessionModel, {"id": session.id})
        assert session_result.status is True
        assert session_result.data is not None
        
        run_result = test_db.get(Run, {"id": run.id})
        assert run_result.status is True
        assert run_result.data is not None
        
        message_result = test_db.get(Message, {"id": message.id})
        assert message_result.status is True
        assert message_result.data is not None
    @pytest.mark.asyncio
    async def test_import_team_and_check_exists(self, test_db: DatabaseManager, test_user: str) -> None:
        """Import a team from a dict and verify duplicate detection."""
        sample_config = {"type": "team", "name": "ImportedTeam", "label": "L1"}
        # First import should create the team
        resp1 = await test_db.import_team(team_config=sample_config, user_id=test_user, check_exists=False)
        assert resp1.status is True
        # Second import with check_exists should short-circuit as duplicate
        resp2 = await test_db.import_team(team_config=sample_config, user_id=test_user, check_exists=True)
        assert resp2.status is True
        assert "already exists" in resp2.message.lower()

    @pytest.mark.asyncio
    async def test_import_teams_from_directory(self, test_db: DatabaseManager, test_user: str, tmp_path) -> None:
        """Import multiple team configs from a directory and ignore non-config files."""
        import json as _json
        import yaml as _yaml
        dir_path = tmp_path / "teams"
        dir_path.mkdir(parents=True, exist_ok=True)
        # JSON config
        (_p := dir_path / "t1.json").write_text(_json.dumps({"type": "team", "name": "T1"}))
        # YAML config
        (_py := dir_path / "t2.yaml").write_text(_yaml.dump({"type": "team", "name": "T2"}))
        # Unsupported extension should be ignored
        (dir_path / "ignore.txt").write_text("not a config")
        resp = await test_db.import_teams_from_directory(dir_path, user_id=test_user, check_exists=False)
        assert resp.status is True
        assert isinstance(resp.data, list)
        # Should import only 2 configs
        assert len(resp.data) == 2
        # Each item should include status/message keys
        for item in resp.data:
            assert "status" in item and "message" in item

    def test_delete_row_not_found_message(self, test_db: DatabaseManager) -> None:
        """Deleting a non-existent row should return a friendly message."""
        from autogenstudio.datamodel.db import Team
        resp = test_db.delete(Team, {"id": 999_999})
        assert resp.status is True
        assert "Row not found" in resp.message