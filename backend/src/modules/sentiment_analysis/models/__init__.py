"""
情感分析模块
提供文本情感倾向的自动分析功能
"""

# src/modules/sentiment_analysis/models/__init__.py
"""
情感分析模块的数据模型
"""
from .task import SentimentTask, TaskStatus, TaskCreate, TaskResponse, TaskCancelRequest
from common.queue.task_queue import TaskQueue

__all__ = [
    'SentimentTask',
    'TaskStatus',
    'TaskCreate',
    'TaskResponse',
    'TaskCancelRequest',
    'TaskQueue'
]