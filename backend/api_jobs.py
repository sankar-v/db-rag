"""
API endpoints for async job management and monitoring
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from celery.result import AsyncResult
import logging

from celeryconfig import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, started, success, failure, retry
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None


class JobResponse(BaseModel):
    job_id: str
    message: str


@router.get("/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """
    Get the status of an async job
    
    Args:
        job_id: Celery task ID
        
    Returns:
        Job status with result if completed
    """
    try:
        task_result = AsyncResult(job_id, app=celery_app)
        
        status_response = {
            "job_id": job_id,
            "status": task_result.status.lower(),
            "result": None,
            "error": None,
            "progress": None
        }
        
        if task_result.ready():
            if task_result.successful():
                status_response["result"] = task_result.result
                status_response["status"] = "success"
            else:
                status_response["error"] = str(task_result.result)
                status_response["status"] = "failure"
        elif task_result.state == "PROGRESS":
            status_response["progress"] = task_result.info
            status_response["status"] = "started"
        
        return JobStatus(**status_response)
        
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel a running job
    
    Args:
        job_id: Celery task ID
        
    Returns:
        Cancellation confirmation
    """
    try:
        task_result = AsyncResult(job_id, app=celery_app)
        task_result.revoke(terminate=True)
        
        return {"message": f"Job {job_id} cancelled", "job_id": job_id}
        
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=Dict[str, Any])
async def list_active_jobs():
    """
    List all active jobs in the queue
    
    Returns:
        Dictionary with active, scheduled, and reserved jobs
    """
    try:
        # Get active tasks from workers
        inspect = celery_app.control.inspect()
        
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        reserved_tasks = inspect.reserved()
        
        return {
            "active": active_tasks or {},
            "scheduled": scheduled_tasks or {},
            "reserved": reserved_tasks or {}
        }
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/workers")
async def get_worker_stats():
    """
    Get statistics about Celery workers
    
    Returns:
        Worker statistics including status and queue depths
    """
    try:
        inspect = celery_app.control.inspect()
        
        stats = inspect.stats()
        active_queues = inspect.active_queues()
        registered_tasks = inspect.registered()
        
        return {
            "workers": stats or {},
            "queues": active_queues or {},
            "registered_tasks": registered_tasks or {}
        }
        
    except Exception as e:
        logger.error(f"Failed to get worker stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_worker():
    """
    Test that workers are responding (health check)
    
    Returns:
        Health check result
    """
    try:
        from tasks import health_check
        
        result = health_check.delay()
        task_result = result.get(timeout=10)
        
        return {
            "worker_status": "healthy",
            "test_result": task_result
        }
        
    except Exception as e:
        logger.error(f"Worker health check failed: {e}")
        return {
            "worker_status": "unhealthy",
            "error": str(e)
        }
