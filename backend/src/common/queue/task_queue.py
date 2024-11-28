import asyncio
from typing import Optional, Set
import logging

logger = logging.getLogger(__name__)

class TaskQueue:
    """任务队列管理类
    
    使用单例模式确保全局只有一个任务队列实例
    """
    _instance = None
    _queue: asyncio.Queue
    _running_tasks: Set[str]
    _max_concurrent_tasks: int

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskQueue, cls).__new__(cls)
            cls._instance._queue = asyncio.Queue()
            cls._instance._running_tasks = set()
            cls._instance._max_concurrent_tasks = 2
        return cls._instance

    async def add_task(self, task_id: str) -> None:
        """添加任务到队列
        
        Args:
            task_id: 任务ID
        """
        await self._queue.put(task_id)
        logger.info(f"任务 {task_id} 已添加到队列")

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
            logger.info(f"任务 {task_id} 已从队列中取出")
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
            logger.info(f"任务 {task_id} 已完成")

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
