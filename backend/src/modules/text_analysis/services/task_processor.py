import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional
from config.config import config
from common.storage.file_service import FileService
from common.database.dependencies import get_task_db
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
        self.queue = TaskQueue("analysis")
        self.file_service = FileService()
        self.analyzer = TextContentAnalysisWorkflow()
        logger.info("分析任务处理器初始化完成")
        # 存储当前正在处理的任务信息
        self._processing_tasks = {}

    async def process_task(self, task_id: str) -> None:
        """处理单个任务

        Args:
            task_id: 任务ID
        """
        # 获取任务数据库会话
        db = next(get_task_db())
        try:
            # 获取任务信息
            task = await self._get_task(db, task_id)
            if not task:
                logger.error(f"任务未找到: {task_id}")
                return

            # 如果任务已被取消，则不执行
            if task.status == TaskStatus.CANCELLED:
                logger.info(f"任务已被取消，跳过执行: {task_id}")
                return

            # 更新任务状态为处理中
            await self._update_task_status(db, task, TaskStatus.PROCESSING)

            # 存储处理任务的Future对象
            process_task = asyncio.create_task(self._process_task_content(db, task))
            self._processing_tasks[task_id] = process_task

            try:
                # 等待任务完成或被取消
                await process_task
            except asyncio.CancelledError:
                logger.info(f"任务被取消: {task_id}")
                # 如果任务被取消，更新数据库状态
                task = await self._get_task(db, task_id)
                if task.status != TaskStatus.CANCELLED:  # 避免重复更新
                    task.status = TaskStatus.CANCELLED
                    task.cancelled_at = datetime.now()
                    db.commit()
            finally:
                # 清理任务记录
                self._processing_tasks.pop(task_id, None)

            logger.info(f"任务处理完成: {task_id}")

        except Exception as e:
            logger.error(f"任务处理失败: {task_id}, 错误={str(e)}")
            await self._handle_task_error(db, task_id, str(e))
        finally:
            self.queue.complete_task(task_id)
            db.close()

    async def cancel_task(self, task_id: str) -> bool:
        """取消指定的任务

        Args:
            task_id: 要取消的任务ID

        Returns:
            bool: 是否成功取消任务
        """
        db = next(get_task_db())
        try:
            task = await self._get_task(db, task_id)
            if not task:
                logger.warning(f"要取消的任务未找到: {task_id}")
                return False

            # 如果任务已经完成或已经取消，则返回False
            if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                logger.info(f"任务 {task_id} 已经处于终态: {task.status.value}")
                return False

            # 更新任务状态为已取消
            task.status = TaskStatus.CANCELLED
            task.cancelled_at = datetime.now()
            db.commit()

            # 如果任务正在处理中，则取消处理
            if task_id in self._processing_tasks:
                process_task = self._processing_tasks[task_id]
                process_task.cancel()
                logger.info(f"已取消正在处理的任务: {task_id}")

            logger.info(f"任务已成功取消: {task_id}")
            return True

        except Exception as e:
            logger.error(f"取消任务时发生错误: {task_id}, 错误={str(e)}")
            return False
        finally:
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
        """获取任务信息"""
        return db.query(AnalysisTask).filter(AnalysisTask.task_id == task_id).first()

    async def _update_task_status(
            self, db: Session, task: AnalysisTask, status: TaskStatus
    ) -> None:
        """更新任务状态"""
        task.status = status
        db.commit()
        logger.info(f"任务状态已更新: {task.task_id} -> {status.value}")

    async def _process_task_content(self, db: Session, task: AnalysisTask) -> None:
        """处理任务内容"""
        # 读取CSV文件
        df = self.file_service.read_csv_file(task.source_file_url)
        task.total_records = len(df)
        db.commit()

        texts = df['text'].tolist()
        last_update_count = 0

        def update_progress(completed_count: int):
            """更新任务进度"""
            nonlocal last_update_count
            if completed_count == task.total_records or completed_count - last_update_count >= config.text_analysis.batch_size:
                # 检查任务是否已被取消
                db.refresh(task)
                if task.status == TaskStatus.CANCELLED:
                    raise asyncio.CancelledError("Task was cancelled")

                task.processed_records = completed_count
                try:
                    db.commit()
                    last_update_count = completed_count
                    logger.info(f"任务 {task.task_id} 进度更新: {completed_count}/{task.total_records}")
                except Exception as e:
                    logger.error(f"更新进度失败: {str(e)}")
                    db.rollback()

        try:
            # 执行批量分析
            results = await self.analyzer.async_batch_analyze(
                texts=texts,
                context=task.context,
                session_id=task.task_id,
                max_concurrency=config.text_analysis.max_concurrency,
                progress_callback=update_progress
            )

            # 合并结果
            combined_results = []
            for i, result in enumerate(results):
                combined_row = {
                    **df.iloc[i].to_dict(),
                    'validity': result.validity,
                    'sentiment_class': result.sentiment_class,
                    'sensitive_info': result.sensitive_info
                }
                combined_results.append(combined_row)

            # 保存最终结果
            result_file_path = self.file_service.save_results_to_csv(
                combined_results, task.task_id)

            # 更新任务状态为完成
            task.status = TaskStatus.COMPLETED
            task.result_file_url = result_file_path
            task.processed_records = task.total_records
            db.commit()

        except asyncio.CancelledError:
            logger.info(f"任务处理被取消: {task.task_id}")
            raise
        except Exception as e:
            logger.error(f"处理任务内容失败: {str(e)}")
            raise

    async def _handle_task_error(
            self, db: Session, task_id: str, error_message: str
    ) -> None:
        """处理任务错误"""
        task = await self._get_task(db, task_id)
        if task and task.status != TaskStatus.CANCELLED:  # 只在非取消状态下更新为失败
            task.status = TaskStatus.FAILED
            task.error_message = error_message
            db.commit()
            logger.error(f"任务处理失败: {task_id}, 错误={error_message}")