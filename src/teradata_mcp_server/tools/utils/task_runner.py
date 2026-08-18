"""Background task execution and tracking for long-running operations.

Enables tools like tdml_* (analytic functions) to return immediately with a task ID,
allowing clients to poll for progress instead of blocking.
"""

import asyncio
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    """Status of a background task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskInfo:
    """Metadata and state for a background task."""

    id: str
    status: TaskStatus
    name: str
    result: Any = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


class TaskManager:
    """In-memory task tracking for long-running operations.

    Approved: Simple in-memory storage for single-instance deployments.
    Task results persist until server restart or cleanup (via expire_old_tasks).

    Cleanup strategy:
    - Expire tasks older than 1 day
    - Keep max 1000 tasks; when exceeded, remove oldest
    """

    def __init__(self):
        """Initialize the task store."""
        self._tasks: dict[str, TaskInfo] = {}

    async def submit_task(
        self,
        task_name: str,
        handler: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """Submit a task for background execution and return its ID.

        Args:
            task_name: Human-readable task name (e.g., "tdml_KMeans")
            handler: Sync function to execute in background
            *args: Positional arguments for the handler
            **kwargs: Keyword arguments for the handler

        Returns:
            Task ID (UUID string) for polling progress and retrieving results
        """
        task_id = str(uuid.uuid4())
        task = TaskInfo(id=task_id, status=TaskStatus.PENDING, name=task_name)
        self._tasks[task_id] = task

        # Schedule background execution
        asyncio.create_task(self._run_task(task_id, handler, args, kwargs))
        return task_id

    async def _run_task(self, task_id: str, handler: Callable, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        """Execute a task in a thread pool and track its status."""
        task = self._tasks[task_id]
        task.status = TaskStatus.RUNNING

        try:
            # Run sync handler in thread pool to avoid blocking
            result = await asyncio.to_thread(handler, *args, **kwargs)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()

    def get_task(self, task_id: str) -> TaskInfo | None:
        """Get task metadata and current state.

        Args:
            task_id: UUID of the task to retrieve

        Returns:
            TaskInfo if found, None otherwise
        """
        return self._tasks.get(task_id)

    def expire_old_tasks(self, age_seconds: float = 86400, max_tasks: int = 1000) -> int:
        """Remove old or excess tasks to prevent unbounded memory growth.

        Args:
            age_seconds: Remove tasks older than this (default: 1 day = 86400s)
            max_tasks: Maximum number of tasks to keep; if exceeded, remove oldest

        Returns:
            Number of tasks removed
        """
        now = time.time()
        removed = 0

        # First, remove old completed/failed tasks
        to_delete = [
            task_id
            for task_id, task in self._tasks.items()
            if task.completed_at and (now - task.completed_at) > age_seconds
        ]
        for task_id in to_delete:
            del self._tasks[task_id]
            removed += 1

        # Then, if still over limit, remove oldest tasks
        if len(self._tasks) > max_tasks:
            by_time = sorted(self._tasks.items(), key=lambda x: x[1].created_at)
            excess = len(self._tasks) - max_tasks
            for task_id, _ in by_time[:excess]:
                del self._tasks[task_id]
                removed += excess

        return removed
