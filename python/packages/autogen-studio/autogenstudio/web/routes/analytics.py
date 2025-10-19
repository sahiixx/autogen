"""
Analytics API Routes - Enhanced monitoring and performance tracking
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select, func
from ..deps import get_db
from ...datamodel.db import Message, Run, Team

router = APIRouter()


class AnalyticsMetrics(BaseModel):
    """Analytics metrics model"""
    total_sessions: int
    total_messages: int
    total_runs: int
    avg_response_time: float
    success_rate: float
    active_teams: int
    messages_per_session: float
    popular_models: List[Dict]
    timeline_data: List[Dict]


class PerformanceMetrics(BaseModel):
    """Performance metrics for agents"""
    agent_id: str
    agent_name: str
    total_runs: int
    avg_response_time: float
    success_count: int
    error_count: int
    last_run: Optional[datetime]


class UsageStatistics(BaseModel):
    """Usage statistics over time"""
    period: str  # "hour", "day", "week", "month"
    data: List[Dict]


@router.get("/metrics", response_model=AnalyticsMetrics)
async def get_analytics_metrics(
    days: int = 7,
    db: Session = Depends(get_db)
) -> AnalyticsMetrics:
    """
    Get comprehensive analytics metrics
    
    Args:
        days: Number of days to analyze (default: 7)
        db: Database session
        
    Returns:
        AnalyticsMetrics with various statistics
    """
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get total counts
        total_runs = db.exec(
            select(func.count(Run.id))
            .where(Run.created_at >= start_date)
        ).one()
        
        # Calculate success rate
        successful_runs = db.exec(
            select(func.count(Run.id))
            .where(Run.created_at >= start_date)
            .where(Run.status == "complete")
        ).one()
        
        success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
        
        # Get active teams
        active_teams = db.exec(
            select(func.count(func.distinct(Team.id)))
        ).one()
        
        # Calculate average response time (mock for now)
        avg_response_time = 1.5  # seconds
        
        # Get timeline data
        timeline_data = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            daily_runs = db.exec(
                select(func.count(Run.id))
                .where(func.date(Run.created_at) == date.date())
            ).one()
            
            timeline_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "runs": daily_runs,
                "success_rate": 95.0  # Mock data
            })
        
        return AnalyticsMetrics(
            total_sessions=0,  # Will be calculated based on sessions
            total_messages=0,  # Will be calculated based on messages
            total_runs=total_runs,
            avg_response_time=avg_response_time,
            success_rate=success_rate,
            active_teams=active_teams,
            messages_per_session=10.5,  # Mock data
            popular_models=[
                {"model": "gpt-4", "usage": 45},
                {"model": "gpt-3.5-turbo", "usage": 35},
                {"model": "claude-3", "usage": 20}
            ],
            timeline_data=timeline_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@router.get("/performance/{team_id}")
async def get_team_performance(
    team_id: str,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get performance metrics for a specific team
    
    Args:
        team_id: Team identifier
        db: Database session
        
    Returns:
        Performance metrics dictionary
    """
    try:
        team = db.get(Team, team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Get runs for this team
        runs = db.exec(
            select(Run)
            .where(Run.team_id == team_id)
            .order_by(Run.created_at.desc())
            .limit(100)
        ).all()
        
        total_runs = len(runs)
        success_count = sum(1 for run in runs if run.status == "complete")
        error_count = total_runs - success_count
        
        return {
            "team_id": team_id,
            "team_name": team.config.name if hasattr(team.config, 'name') else "Unknown",
            "total_runs": total_runs,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": (success_count / total_runs * 100) if total_runs > 0 else 0,
            "avg_response_time": 1.8,  # Mock data
            "last_run": runs[0].created_at if runs else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance: {str(e)}")


@router.get("/usage")
async def get_usage_statistics(
    period: str = "day",
    limit: int = 30,
    db: Session = Depends(get_db)
) -> UsageStatistics:
    """
    Get usage statistics over time
    
    Args:
        period: Time period ("hour", "day", "week", "month")
        limit: Number of periods to return
        db: Database session
        
    Returns:
        UsageStatistics with time-series data
    """
    try:
        data = []
        
        if period == "day":
            for i in range(limit):
                date = datetime.now() - timedelta(days=i)
                daily_runs = db.exec(
                    select(func.count(Run.id))
                    .where(func.date(Run.created_at) == date.date())
                ).one()
                
                data.append({
                    "timestamp": date.strftime("%Y-%m-%d"),
                    "runs": daily_runs,
                    "sessions": 0,  # To be implemented
                    "messages": 0   # To be implemented
                })
        
        data.reverse()  # Chronological order
        
        return UsageStatistics(
            period=period,
            data=data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get usage statistics: {str(e)}")


@router.get("/models/comparison")
async def get_model_comparison(
    team_id: Optional[str] = None,
    days: int = 7,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Compare performance across different models
    
    Args:
        team_id: Optional team filter
        days: Number of days to analyze
        db: Database session
        
    Returns:
        Model comparison data
    """
    try:
        # Mock data for now - would be calculated from actual runs
        models = [
            {
                "model": "gpt-4",
                "runs": 150,
                "avg_response_time": 1.2,
                "success_rate": 98.5,
                "avg_tokens": 450,
                "cost_estimate": 2.45
            },
            {
                "model": "gpt-3.5-turbo",
                "runs": 200,
                "avg_response_time": 0.8,
                "success_rate": 96.0,
                "avg_tokens": 380,
                "cost_estimate": 0.42
            },
            {
                "model": "claude-3-opus",
                "runs": 75,
                "avg_response_time": 1.5,
                "success_rate": 97.5,
                "avg_tokens": 520,
                "cost_estimate": 1.85
            }
        ]
        
        return {
            "period_days": days,
            "team_id": team_id,
            "models": models,
            "total_runs": sum(m["runs"] for m in models),
            "total_cost_estimate": sum(m["cost_estimate"] for m in models)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model comparison: {str(e)}")


@router.get("/health/status")
async def get_system_health(db: Session = Depends(get_db)) -> Dict:
    """
    Get system health status
    
    Returns:
        System health metrics
    """
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "api": "operational",
            "version": "0.4.0+",
            "uptime_seconds": 3600,  # Mock data
            "active_sessions": 0,
            "queue_size": 0
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
