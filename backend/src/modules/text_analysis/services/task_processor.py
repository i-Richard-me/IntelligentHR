import asyncio
import logging
from sqlalchemy.orm import Session
from typing import Optional
from common.storage.file_service import FileService
from common.database.base import SessionLocal
from modules.text_analysis.models.task import AnalysisTask, TaskStatus
from modules.text_analysis.workflows.content_analysis_workflow import TextContentAnalysisWorkflow
from modules.text_analysis.models import TaskQueue

logger = logging.getLogger(__name__)

class TaskProcessor:
    """任务处理器类
    
    处理文本分析任务的核心服务类
    """

    def __init__(self):
        """初始化任务处理器"""
        self.queue = TaskQueue()
        self.file_service = FileService()
        self.analyzer = TextContentAnalysisWorkflow()
        logger.info("任务处理器初始化完成")

    async def process_task(self, task_id: str) -> None:
        """处理单个任务
        
        Args:
            task_id: 任务ID
        """
        db = SessionLocal()
        try:
            # 获取任务信息
            task = await self._get_task(db, task_id)
            if not task:
                logger.error(f"任务未找到: {task_id}")
                return

            # 更新任务状态
            await self._update_task_status(db, task, TaskStatus.PROCESSING)

            # 处理任务
            await self._process_task_content(db, task)

            logger.info(f"任务处理完成: {task_id}")

        except Exception as e:
            logger.error(f"任务处理失败: {task_id}, 错误={str(e)}")
            await self._handle_task_error(db, task_id, str(e))
        finally:
            self.queue.complete_task(task_id)
            db.close()

    async def start_processing(self) -> None:
        """启动任务处理循环"""
        logger.info("开始任务处理循环")
        while True:
            try:
                task_id = await self.queue.get_task()
                if task_id:
                    asyncio.create_task(self.process_task(task_id))
                else:
                    await asyncio.sleep(1)  # 避免过度循环
            except Exception as e:
                logger.error(f"任务处理循环错误: {str(e)}")
                await asyncio.sleep(1)

    async def _get_task(self, db: Session, task_id: str) -> Optional[AnalysisTask]:
        """获取任务信息
        
        Args:
            db: 数据库会话
            task_id: 任务ID

        Returns:
            Optional[AnalysisTask]: 任务对象
        """
        return db.query(AnalysisTask).filter(AnalysisTask.task_id == task_id).first()

    async def _update_task_status(
        self, db: Session, task: AnalysisTask, status: TaskStatus
    ) -> None:
        """更新任务状态
        
        Args:
            db: 数据库会话
            task: 任务对象
            status: 新状态
        """
        task.status = status
        db.commit()
        logger.info(f"任务状态已更新: {task.task_id} -> {status.value}")

    async def _process_task_content(self, db: Session, task: AnalysisTask) -> None:
        """处理任务内容
        
        Args:
            db: 数据库会话
            task: 任务对象
        """
        # 读取CSV文件
        df = self.file_service.read_csv_file(task.source_file_url)
        task.total_records = len(df)
        db.commit()

        # 读取原始文本并进行分析
        texts = df['text'].tolist()
        results = await self.analyzer.async_batch_analyze(
            texts=texts,
            context=task.context,
            session_id=task.task_id
        )

        # 合并结果
        combined_results = []
        for i, result_dict in enumerate(results):
            combined_row = {
                **df.iloc[i].to_dict(),  # 包含原始数据的所有列
                'validity': result_dict.validity,
                'sentiment_class': result_dict.sentiment_class,
                'sensitive_info': result_dict.sensitive_info
            }
            combined_results.append(combined_row)
            
            # 更新处理进度
            task.processed_records = i + 1
            if (i + 1) % 10 == 0:  # 每处理10条记录提交一次
                db.commit()

        # 保存最终结果
        result_file_path = self.file_service.save_results_to_csv(combined_results, task.task_id)
        
        # 更新任务状态
        task.status = TaskStatus.COMPLETED
        task.result_file_url = result_file_path
        task.processed_records = task.total_records
        db.commit()

    async def _handle_task_error(
        self, db: Session, task_id: str, error_message: str
    ) -> None:
        """处理任务错误
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            error_message: 错误信息
        """
        task = await self._get_task(db, task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = error_message
            db.commit()
            logger.error(f"任务处理失败: {task_id}, 错误={error_message}")