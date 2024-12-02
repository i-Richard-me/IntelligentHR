import asyncio
from typing import Optional, Set, Dict
import logging

logger = logging.getLogger(__name__)


class TaskQueue:
    """任务队列管理类

    使用单例模式确保每种任务类型只有一个队列实例
    """
    _instances: Dict[str, 'TaskQueue'] = {}

    def __new__(cls, queue_type: str = "default"):
        """创建或获取指定类型的队列实例

        Args:
            queue_type: 队列类型标识符
        """
        if queue_type not in cls._instances:
            cls._instances[queue_type] = super(TaskQueue, cls).__new__(cls)
            instance = cls._instances[queue_type]
            instance._queue = asyncio.Queue()
            instance._running_tasks = set()
            instance._max_concurrent_tasks = 2
            instance._queue_type = queue_type
            logger.info(f"Created new task queue for type: {queue_type}")
        return cls._instances[queue_type]

    async def add_task(self, task_id: str) -> None:
        """添加任务到队列

        Args:
            task_id: 任务ID
        """
        await self._queue.put(task_id)
        logger.info(f"任务 {task_id} 已添加到{self._queue_type}队列")

    async def get_task(self) -> Optional[str]:
        """从队列获取任务

        Returns:
            Optional[str]: 任务ID,如果没有可用任务则返回None
        """
        if len(self._running_tasks) >= self._max_concurrent_tasks:
            return None

        try:
            task_id = await self._queue.get()
            self._running_tasks.add(task_id)
            logger.info(f"任务 {task_id} 已从{self._queue_type}队列中取出")
            return task_id
        except asyncio.QueueEmpty:
            return None

    def complete_task(self, task_id: str) -> None:
        """完成任务

        Args:
            task_id: 任务ID
        """
        if task_id in self._running_tasks:
            self._running_tasks.remove(task_id)
            self._queue.task_done()
            logger.info(f"任务 {task_id} 已从{self._queue_type}队列完成")

    @property
    def active_tasks_count(self) -> int:
        """获取当前正在执行的任务数

        Returns:
            int: 正在执行的任务数量
        """
        return len(self._running_tasks)

    @property
    def queue_size(self) -> int:
        """获取队列中等待的任务数

        Returns:
            int: 等待中的任务数量
        """
        return self._queue.qsize()