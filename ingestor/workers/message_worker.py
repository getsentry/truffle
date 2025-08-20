import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import sentry_sdk

from processors.message_processor import MessageProcessor
from services.queue_service import QueueService

logger = logging.getLogger(__name__)


class MessageWorker:
    """Background worker that processes messages from the queue"""

    def __init__(self, worker_id: str, queue_service: QueueService):
        self.worker_id = worker_id
        self.queue_service = queue_service
        self.processor = MessageProcessor()
        self.is_running = False
        self.processed_count = 0
        self.error_count = 0

    async def start(self) -> None:
        """Start the worker to process messages from queue"""
        self.is_running = True
        logger.info(f"Starting message worker {self.worker_id}")

        try:
            while self.is_running:
                try:
                    # Try to get a message from queue
                    task = await self.queue_service.dequeue_message()

                    if task is None:
                        # No messages in queue, wait a bit
                        await asyncio.sleep(0.5)
                        continue

                    with sentry_sdk.start_transaction(
                        name="Process Message",
                    ) as trx:
                        trx.set_data("truffle.task.id", task.task_id)
                        trx.set_data("truffle.worker.id", self.worker_id)
                        await self._process_task(task)

                except Exception as e:
                    logger.error(
                        f"Worker {self.worker_id} encountered error: {e}", exc_info=True
                    )
                    self.error_count += 1
                    await asyncio.sleep(1)  # Back off on errors

        except asyncio.CancelledError:
            logger.info(f"Worker {self.worker_id} cancelled")
            raise
        finally:
            self.is_running = False
            logger.info(
                f"Worker {self.worker_id} stopped. Processed: {self.processed_count}, Errors: {self.error_count}"
            )

    @sentry_sdk.trace(op="queue.process")
    async def _process_task(self, task) -> None:
        """Process a single message task"""
        try:
            sentry_sdk.update_current_span(
                attributes={
                    "messaging.message.id": task.task_id,
                    "messaging.destination.name": "pending_queue",
                    "messaging.message.retry.count": task.retry_count,
                    "messaging.message.receive.latency": int(
                        (datetime.now(UTC) - task.created_at).total_seconds() * 1000
                    ),
                }
            )

            logger.debug(f"Worker {self.worker_id} processing task {task.task_id}")

            # Process the message through the normal pipeline
            await self.processor.process_message(task.message, task.channel, task.users)

            # Mark as completed
            await self.queue_service.mark_completed(task.task_id)
            self.processed_count += 1

            logger.debug(f"Worker {self.worker_id} completed task {task.task_id}")

        except Exception as e:
            # Mark as failed (will handle retries automatically)
            error_msg = f"Worker {self.worker_id} failed to process task: {str(e)}"
            await self.queue_service.mark_failed(task.task_id, error_msg)
            logger.error(f"Worker {self.worker_id} failed task {task.task_id}: {e}")

    async def stop(self) -> None:
        """Stop the worker gracefully"""
        logger.info(f"Stopping worker {self.worker_id}")
        self.is_running = False

    def get_stats(self) -> dict[str, Any]:
        """Get worker statistics"""
        return {
            "worker_id": self.worker_id,
            "is_running": self.is_running,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
        }


class WorkerManager:
    """Manages multiple message workers"""

    def __init__(self, queue_service: QueueService, num_workers: int = 3):
        self.queue_service = queue_service
        self.num_workers = num_workers
        self.workers: list[MessageWorker] = []
        self.worker_tasks: list[asyncio.Task] = []

    async def start_workers(self) -> None:
        """Start all workers"""
        logger.info(f"Starting {self.num_workers} message workers")

        for i in range(self.num_workers):
            worker = MessageWorker(f"worker-{i + 1}", self.queue_service)
            self.workers.append(worker)

            # Start worker as background task
            task = asyncio.create_task(worker.start())
            self.worker_tasks.append(task)

        logger.info(f"Started {len(self.workers)} workers")

    async def stop_workers(self) -> None:
        """Stop all workers gracefully"""
        logger.info("Stopping all workers")

        # Signal all workers to stop
        for worker in self.workers:
            await worker.stop()

        # Cancel worker tasks
        for task in self.worker_tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)

        self.workers.clear()
        self.worker_tasks.clear()
        logger.info("All workers stopped")

    def get_worker_stats(self) -> list[dict[str, Any]]:
        """Get statistics for all workers"""
        return [worker.get_stats() for worker in self.workers]

    def is_running(self) -> bool:
        """Check if any workers are running"""
        return any(worker.is_running for worker in self.workers)


# Global worker manager instance
_worker_manager: WorkerManager | None = None


def get_worker_manager(
    queue_service: QueueService, num_workers: int = 3
) -> WorkerManager:
    """Get the global worker manager instance"""
    global _worker_manager
    if _worker_manager is None:
        _worker_manager = WorkerManager(queue_service, num_workers)
    return _worker_manager
