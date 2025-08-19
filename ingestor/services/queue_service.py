import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class MessageTask:
    """A task representing a message to be processed"""
    task_id: str
    message: dict[str, Any]
    channel: dict[str, Any]
    users: dict[str, dict[str, Any]]
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    error_message: str = None
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(UTC)


class QueueService:
    """In-memory queue service for managing message processing tasks"""

    def __init__(self):
        self.pending_queue: deque[MessageTask] = deque()
        self.processing_tasks: dict[str, MessageTask] = {}
        self.completed_tasks: dict[str, MessageTask] = {}
        self.failed_tasks: dict[str, MessageTask] = {}
        self._lock = asyncio.Lock()

    async def enqueue_message(
        self,
        message: dict[str, Any],
        channel: dict[str, Any],
        users: dict[str, dict[str, Any]]
    ) -> str:
        """Add a message to the processing queue"""
        task = MessageTask(
            task_id=str(uuid4()),
            message=message,
            channel=channel,
            users=users
        )

        async with self._lock:
            self.pending_queue.append(task)

        logger.debug(f"Enqueued message task {task.task_id}")
        return task.task_id

    async def dequeue_message(self) -> MessageTask | None:
        """Get the next message to process"""
        async with self._lock:
            if not self.pending_queue:
                return None

            task = self.pending_queue.popleft()
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.now(UTC)
            self.processing_tasks[task.task_id] = task

        logger.debug(f"Dequeued message task {task.task_id}")
        return task

    async def mark_completed(self, task_id: str) -> None:
        """Mark a task as completed"""
        async with self._lock:
            if task_id in self.processing_tasks:
                task = self.processing_tasks.pop(task_id)
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now(UTC)
                self.completed_tasks[task_id] = task
                logger.debug(f"Marked task {task_id} as completed")

    async def mark_failed(self, task_id: str, error_message: str) -> None:
        """Mark a task as failed and potentially retry"""
        async with self._lock:
            if task_id in self.processing_tasks:
                task = self.processing_tasks.pop(task_id)
                task.error_message = error_message
                task.retry_count += 1

                if task.retry_count <= task.max_retries:
                    # Retry the task
                    task.status = TaskStatus.RETRYING
                    self.pending_queue.appendleft(task)  # Add to front for priority
                    logger.warning(f"Retrying task {task_id} (attempt {task.retry_count})")
                else:
                    # Max retries exceeded
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now(UTC)
                    self.failed_tasks[task_id] = task
                    logger.error(f"Task {task_id} failed after {task.retry_count} attempts: {error_message}")

    async def get_queue_stats(self) -> dict[str, Any]:
        """Get current queue statistics"""
        async with self._lock:
            return {
                "pending": len(self.pending_queue),
                "processing": len(self.processing_tasks),
                "completed": len(self.completed_tasks),
                "failed": len(self.failed_tasks),
                "total_processed": len(self.completed_tasks) + len(self.failed_tasks)
            }

    async def get_recent_tasks(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent tasks for monitoring"""
        async with self._lock:
            all_tasks = []

            # Add recent completed tasks
            for task in list(self.completed_tasks.values())[-limit//2:]:
                all_tasks.append({
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "created_at": task.created_at.isoformat(),
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "retry_count": task.retry_count,
                    "message_preview": task.message.get("text", "")[:100]
                })

            # Add recent failed tasks
            for task in list(self.failed_tasks.values())[-limit//4:]:
                all_tasks.append({
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "created_at": task.created_at.isoformat(),
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "retry_count": task.retry_count,
                    "error_message": task.error_message,
                    "message_preview": task.message.get("text", "")[:100]
                })

            # Add currently processing tasks
            for task in list(self.processing_tasks.values()):
                all_tasks.append({
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "created_at": task.created_at.isoformat(),
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "retry_count": task.retry_count,
                    "message_preview": task.message.get("text", "")[:100]
                })

            # Sort by created_at (most recent first)
            all_tasks.sort(key=lambda x: x["created_at"], reverse=True)
            return all_tasks[:limit]

    async def clear_completed_tasks(self) -> int:
        """Clear completed tasks to free memory"""
        async with self._lock:
            count = len(self.completed_tasks)
            self.completed_tasks.clear()
            logger.info(f"Cleared {count} completed tasks")
            return count


# Global queue instance
_queue_service: QueueService | None = None


def get_queue_service() -> QueueService:
    """Get the global queue service instance"""
    global _queue_service
    if _queue_service is None:
        _queue_service = QueueService()
    return _queue_service
