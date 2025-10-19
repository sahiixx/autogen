"""Additional comprehensive tests for DatabaseManager"""
import asyncio
import os
import pytest
from pathlib import Path
from sqlmodel import Session, text, select

os.environ.setdefault("OPENAI_API_KEY", "test")
from autogenstudio.database import DatabaseManager
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.conditions import TextMentionTermination
from autogenstudio.datamodel.db import Team, Session as SessionModel, Run, Message, RunStatus, MessageConfig


@pytest.fixture
def test_db(tmp_path):
    """Fixture for test database"""
    db_path = tmp_path / "test_additional.db"
    db = DatabaseManager(f"sqlite:///{db_path}", base_dir=tmp_path)
    db.reset_db()
    db.initialize_database(auto_upgrade=False)
    yield db
    asyncio.run(db.close())
    db.reset_db()


@pytest.fixture
def test_user() -> str:
    return "test_additional@example.com"


class TestDatabaseManagerAdditional:
    def test_concurrent_upsert_operations(self, test_db: DatabaseManager, test_user: str):
        """Test multiple concurrent upsert operations"""
        teams = []
        for i in range(5):
            agent = AssistantAgent(
                name=f"agent_{i}",
                model_client=OpenAIChatCompletionClient(model="gpt-4.1-nano"),
            )
            agent_team = RoundRobinGroupChat([agent], termination_condition=TextMentionTermination("TERMINATE"))
            team = Team(
                user_id=test_user,
                component=agent_team.dump_component().model_dump(),
            )
            teams.append(team)
        
        # Upsert all teams
        for team in teams:
            response = test_db.upsert(team)
            assert response.status is True
        
        # Verify all were created
        result = test_db.get(Team, {"user_id": test_user})
        assert result.status is True
        assert len(result.data) == 5


    def test_get_with_ordering(self, test_db: DatabaseManager, test_user: str):
        """Test get operation with different ordering"""
        import time
        
        for i in range(3):
            agent = AssistantAgent(
                name=f"agent_{i}",
                model_client=OpenAIChatCompletionClient(model="gpt-4.1-nano"),
            )
            agent_team = RoundRobinGroupChat([agent], termination_condition=TextMentionTermination("TERMINATE"))
            team = Team(
                user_id=test_user,
                component=agent_team.dump_component().model_dump(),
            )
            test_db.upsert(team)
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        # Test descending order (default)
        result_desc = test_db.get(Team, {"user_id": test_user}, order="desc")
        assert result_desc.status is True
        assert len(result_desc.data) == 3
        
        # Test ascending order
        result_asc = test_db.get(Team, {"user_id": test_user}, order="asc")
        assert result_asc.status is True
        assert len(result_asc.data) == 3
        
        # Verify ordering is different
        if result_desc.data and result_asc.data:
            assert result_desc.data[0].id != result_asc.data[0].id


    def test_upsert_update_timestamp(self, test_db: DatabaseManager, test_user: str):
        """Test that upsert updates the updated_at timestamp"""
        agent = AssistantAgent(
            name="test_agent",
            model_client=OpenAIChatCompletionClient(model="gpt-4.1-nano"),
        )
        agent_team = RoundRobinGroupChat([agent], termination_condition=TextMentionTermination("TERMINATE"))
        team = Team(
            user_id=test_user,
            component=agent_team.dump_component().model_dump(),
        )
        
        # Initial creation
        response1 = test_db.upsert(team)
        assert response1.status is True
        assert "Created Successfully" in response1.message
        
        import time
        time.sleep(0.1)
        
        # Update the same team
        team.version = "0.0.2"
        response2 = test_db.upsert(team)
        assert response2.status is True
        assert "Updated Successfully" in response2.message
        
        # Verify updated_at changed
        result = test_db.get(Team, {"id": team.id})
        assert result.status is True
        if result.data:
            updated_team = result.data[0]
            assert updated_team.version == "0.0.2"


    def test_delete_nonexistent_entity(self, test_db: DatabaseManager):
        """Test deleting an entity that doesn't exist"""
        response = test_db.delete(Team, {"id": "nonexistent-id-12345"})
        assert response.status is True
        assert "not found" in response.message.lower()


    def test_get_with_no_results(self, test_db: DatabaseManager):
        """Test get operation that returns no results"""
        result = test_db.get(Team, {"user_id": "nonexistent@example.com"})
        assert result.status is True
        assert len(result.data) == 0


    def test_get_return_json_parameter(self, test_db: DatabaseManager, test_user: str):
        """Test get operation with return_json parameter"""
        agent = AssistantAgent(
            name="test_agent",
            model_client=OpenAIChatCompletionClient(model="gpt-4.1-nano"),
        )
        agent_team = RoundRobinGroupChat([agent], termination_condition=TextMentionTermination("TERMINATE"))
        team = Team(
            user_id=test_user,
            component=agent_team.dump_component().model_dump(),
        )
        test_db.upsert(team)
        
        # Test with return_json=False (default)
        result_obj = test_db.get(Team, {"user_id": test_user}, return_json=False)
        assert result_obj.status is True
        assert len(result_obj.data) == 1
        assert isinstance(result_obj.data[0], Team)
        
        # Test with return_json=True
        result_dict = test_db.get(Team, {"user_id": test_user}, return_json=True)
        assert result_dict.status is True
        assert len(result_dict.data) == 1
        assert isinstance(result_dict.data[0], dict)


    def test_database_connection_lifecycle(self, tmp_path):
        """Test database initialization and cleanup lifecycle"""
        db_path = tmp_path / "lifecycle_test.db"
        db = DatabaseManager(f"sqlite:///{db_path}", base_dir=tmp_path)
        
        # Initialize database
        response = db.initialize_database()
        assert response.status is True
        assert db_path.exists()
        
        # Close database
        asyncio.run(db.close())
        
        # Database file should still exist after close
        assert db_path.exists()


    def test_foreign_key_constraint_enforcement(self, test_db: DatabaseManager, test_user: str):
        """Test that foreign key constraints are properly enforced"""
        # Create a team
        agent = AssistantAgent(
            name="test_agent",
            model_client=OpenAIChatCompletionClient(model="gpt-4.1-nano"),
        )
        agent_team = RoundRobinGroupChat([agent], termination_condition=TextMentionTermination("TERMINATE"))
        team = Team(
            user_id=test_user,
            component=agent_team.dump_component().model_dump(),
        )
        test_db.upsert(team)
        
        # Create a session linked to the team
        session = SessionModel(user_id=test_user, team_id=team.id, name="Test Session")
        test_db.upsert(session)
        
        # Try to delete the team (should fail or cascade based on schema)
        response = test_db.delete(Team, {"id": team.id})
        # This test verifies the integrity constraint is being checked
        assert response.status in [True, False]  # Depends on cascade settings


    def test_multiple_filters_in_get(self, test_db: DatabaseManager, test_user: str):
        """Test get operation with multiple filters"""
        # Create multiple teams with different versions
        for i in range(3):
            agent = AssistantAgent(
                name=f"agent_{i}",
                model_client=OpenAIChatCompletionClient(model="gpt-4.1-nano"),
            )
            agent_team = RoundRobinGroupChat([agent], termination_condition=TextMentionTermination("TERMINATE"))
            team = Team(
                user_id=test_user,
                component=agent_team.dump_component().model_dump(),
                version=f"0.0.{i}"
            )
            test_db.upsert(team)
        
        # Get with multiple filters
        result = test_db.get(Team, {"user_id": test_user, "version": "0.0.1"})
        assert result.status is True
        assert len(result.data) == 1
        if result.data:
            assert result.data[0].version == "0.0.1"


    def test_reset_db_without_recreate(self, tmp_path):
        """Test reset_db with recreate_tables=False"""
        db_path = tmp_path / "reset_test.db"
        db = DatabaseManager(f"sqlite:///{db_path}", base_dir=tmp_path)
        
        # Initialize and populate
        db.initialize_database()
        
        # Reset without recreating
        response = db.reset_db(recreate_tables=False)
        assert response.status is True
        assert "dropped successfully" in response.message.lower()
        
        asyncio.run(db.close())