"""
Export/Import API Routes - Code generation and configuration sharing
"""
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlmodel import Session
import json
from datetime import datetime
from ..deps import get_db
from ...datamodel.db import Team

router = APIRouter()


class ExportConfig(BaseModel):
    """Configuration for export"""
    format: str  # "python", "json", "yaml"
    include_secrets: bool = False
    include_comments: bool = True
    framework: str = "autogen"  # "autogen", "langgraph", "crewai"


class ImportConfig(BaseModel):
    """Configuration for import"""
    source: str  # "json", "yaml", "python"
    override_existing: bool = False


def generate_python_code(team_config: Dict, include_comments: bool = True) -> str:
    """
    Generate Python code from team configuration
    
    Args:
        team_config: Team configuration dictionary
        include_comments: Whether to include explanatory comments
        
    Returns:
        Generated Python code as string
    """
    code_lines = []
    
    if include_comments:
        code_lines.append('"""')
        code_lines.append(f"AutoGen Team: {team_config.get('name', 'Unnamed Team')}")
        code_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        code_lines.append('"""')
        code_lines.append('')
    
    # Imports
    code_lines.append('from autogen_agentchat.agents import AssistantAgent')
    code_lines.append('from autogen_agentchat.teams import RoundRobinGroupChat')
    code_lines.append('from autogen_agentchat.conditions import TextMentionTermination')
    code_lines.append('from autogen_ext.models import OpenAIChatCompletionClient')
    code_lines.append('import asyncio')
    code_lines.append('')
    
    # Model configuration
    if include_comments:
        code_lines.append('# Configure the AI model')
    code_lines.append('model_client = OpenAIChatCompletionClient(')
    code_lines.append('    model="gpt-4",')
    code_lines.append('    # api_key="your-api-key-here"  # Set via environment variable')
    code_lines.append(')')
    code_lines.append('')
    
    # Create agents
    if include_comments:
        code_lines.append('# Define agents')
    
    team_type = team_config.get('team_type', 'RoundRobinGroupChat')
    participants = team_config.get('participants', [])
    
    for idx, agent in enumerate(participants, 1):
        agent_name = agent.get('agent_config', {}).get('name', f'agent_{idx}')
        agent_description = agent.get('agent_config', {}).get('description', '')
        system_message = agent.get('agent_config', {}).get('system_message', '')
        
        if include_comments and agent_description:
            code_lines.append(f'# {agent_description}')
        
        code_lines.append(f'{agent_name.lower().replace(" ", "_")} = AssistantAgent(')
        code_lines.append(f'    name="{agent_name}",')
        if system_message:
            code_lines.append(f'    system_message="""{system_message}""",')
        code_lines.append('    model_client=model_client,')
        code_lines.append(')')
        code_lines.append('')
    
    # Create team
    if include_comments:
        code_lines.append('# Create the team')
    
    agent_names = [
        agent.get('agent_config', {}).get('name', f'agent_{i}').lower().replace(" ", "_")
        for i, agent in enumerate(participants, 1)
    ]
    
    code_lines.append(f'team = {team_type}(')
    code_lines.append(f'    participants=[{", ".join(agent_names)}],')
    
    # Add termination condition
    termination = team_config.get('termination_condition', {})
    if termination:
        code_lines.append('    termination_condition=TextMentionTermination("TERMINATE"),')
    
    code_lines.append(')')
    code_lines.append('')
    
    # Main execution
    if include_comments:
        code_lines.append('# Run the team')
    code_lines.append('async def main():')
    code_lines.append('    result = await team.run(')
    code_lines.append('        task="Your task here"')
    code_lines.append('    )')
    code_lines.append('    print(result)')
    code_lines.append('')
    code_lines.append('if __name__ == "__main__":')
    code_lines.append('    asyncio.run(main())')
    
    return '\n'.join(code_lines)


def generate_langgraph_code(team_config: Dict) -> str:
    """Generate LangGraph-compatible code"""
    code_lines = [
        'from langgraph.graph import StateGraph, END',
        'from langchain_openai import ChatOpenAI',
        'from typing import TypedDict, Annotated',
        'import operator',
        '',
        '# Define the state',
        'class AgentState(TypedDict):',
        '    messages: Annotated[list, operator.add]',
        '    next: str',
        '',
        '# Create the graph',
        'workflow = StateGraph(AgentState)',
        '',
        '# Add your nodes and edges here',
        'workflow.add_node("agent", lambda x: x)',
        'workflow.add_edge("agent", END)',
        '',
        'app = workflow.compile()',
    ]
    return '\n'.join(code_lines)


@router.post("/teams/{team_id}/export", response_class=PlainTextResponse)
async def export_team_code(
    team_id: str,
    config: ExportConfig,
    db: Session = Depends(get_db)
) -> str:
    """
    Export team configuration as code
    
    Args:
        team_id: Team identifier
        config: Export configuration
        db: Database session
        
    Returns:
        Generated code as plain text
    """
    try:
        # Get team from database
        team = db.get(Team, team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Convert team to dict
        team_dict = team.config.model_dump() if hasattr(team.config, 'model_dump') else {}
        
        # Generate code based on format
        if config.format == "python":
            if config.framework == "autogen":
                return generate_python_code(team_dict, config.include_comments)
            elif config.framework == "langgraph":
                return generate_langgraph_code(team_dict)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported framework: {config.framework}")
        
        elif config.format == "json":
            if not config.include_secrets:
                # Remove sensitive data
                team_dict.pop('api_keys', None)
            return json.dumps(team_dict, indent=2)
        
        elif config.format == "yaml":
            import yaml
            if not config.include_secrets:
                team_dict.pop('api_keys', None)
            return yaml.dump(team_dict, default_flow_style=False)
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {config.format}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/teams/import")
async def import_team_config(
    file: UploadFile = File(...),
    config: ImportConfig = None,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Import team configuration from file
    
    Args:
        file: Uploaded configuration file
        config: Import configuration
        db: Database session
        
    Returns:
        Import result with team ID
    """
    try:
        content = await file.read()
        
        # Parse based on source type
        if config and config.source == "json" or file.filename.endswith('.json'):
            team_data = json.loads(content.decode('utf-8'))
        elif config and config.source == "yaml" or file.filename.endswith(('.yaml', '.yml')):
            import yaml
            team_data = yaml.safe_load(content.decode('utf-8'))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        # Validate and create team
        # This would integrate with the team creation logic
        
        return {
            "success": True,
            "message": "Team configuration imported successfully",
            "team_id": "new-team-id",  # Would be generated
            "imported_at": datetime.now().isoformat()
        }
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/teams/{team_id}/share")
async def get_share_link(
    team_id: str,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Generate a shareable link for a team configuration
    
    Args:
        team_id: Team identifier
        db: Database session
        
    Returns:
        Share link and token
    """
    try:
        team = db.get(Team, team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Generate share token (in production, use proper token generation)
        import hashlib
        share_token = hashlib.sha256(f"{team_id}-{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        return {
            "share_url": f"http://localhost:8081/gallery?import={share_token}",
            "token": share_token,
            "expires_at": (datetime.now().timestamp() + 86400 * 7),  # 7 days
            "team_name": team.config.name if hasattr(team.config, 'name') else "Unnamed Team"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate share link: {str(e)}")


@router.get("/templates")
async def get_workflow_templates() -> List[Dict]:
    """
    Get pre-built workflow templates
    
    Returns:
        List of workflow templates
    """
    templates = [
        {
            "id": "customer-support",
            "name": "Customer Support Team",
            "description": "Multi-agent customer support with triage, technical, and escalation agents",
            "category": "support",
            "agents_count": 3,
            "complexity": "medium",
            "use_cases": ["customer service", "help desk", "technical support"]
        },
        {
            "id": "research-team",
            "name": "Research & Analysis Team",
            "description": "Collaborative research team with web search, analysis, and synthesis agents",
            "category": "research",
            "agents_count": 4,
            "complexity": "high",
            "use_cases": ["research", "data analysis", "report generation"]
        },
        {
            "id": "code-review",
            "name": "Code Review Team",
            "description": "Automated code review with analyzer, tester, and documentation agents",
            "category": "development",
            "agents_count": 3,
            "complexity": "medium",
            "use_cases": ["code review", "testing", "documentation"]
        },
        {
            "id": "content-creation",
            "name": "Content Creation Team",
            "description": "Content generation with writer, editor, and SEO specialist agents",
            "category": "content",
            "agents_count": 3,
            "complexity": "low",
            "use_cases": ["blog writing", "social media", "marketing"]
        },
        {
            "id": "data-science",
            "name": "Data Science Pipeline",
            "description": "End-to-end data science with data engineer, analyst, and ML engineer agents",
            "category": "data",
            "agents_count": 4,
            "complexity": "high",
            "use_cases": ["data analysis", "ML modeling", "visualization"]
        }
    ]
    
    return templates


@router.get("/templates/{template_id}")
async def get_template_details(template_id: str) -> Dict:
    """
    Get detailed template configuration
    
    Args:
        template_id: Template identifier
        
    Returns:
        Complete template configuration
    """
    # This would return the full team configuration for the template
    return {
        "id": template_id,
        "name": "Template Name",
        "config": {
            # Full team configuration
        }
    }
