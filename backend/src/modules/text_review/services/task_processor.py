import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional, Dict
from config.config import config
from common.storage.file_service import FileService
from common.database.dependencies import get_task_db
from modules.text_review.models.task import ReviewTask, TaskStatus
from modules.text_review.workflows.text_review_workflow import TextReviewWorkflow
from modules.text_review.models import TaskQueue

logger = logging.getLogger(__name__)


class TaskProcessor:
    """任务处理器类

    处理文本评估任务的核心服务类
    """

    def __init__(self):
        """初始化任务处理器"""
        self.queue = TaskQueue("review")
        self.file_service = FileService()
        self.reviewer = TextReviewWorkflow()
        self._processing_tasks: Dict[str, asyncio.Task] = {}
        logger.info("评估任务处理器初始化完成")

    async def process_task(self, task_id: str) -> None:
        """处理单个任务

        Args:
            task_id: 任务ID
        """
        db = next(get_task_db())
        try:
            task = await self._get_task(db, task_id)
            if not task:
                logger.error(f"任务未找到: {task_id}")
                return

            if task.status == TaskStatus.CANCELLED:
                logger.info(f"任务已被取消，跳过执行: {task_id}")
                return

            await self._update_task_status(db, task, TaskStatus.PROCESSING)

            process_task = asyncio.create_task(
                self._process_task_content(db, task))
            self._processing_tasks[task_id] = process_task

            try:
                await process_task
            except asyncio.CancelledError:
                logger.info(f"任务被取消: {task_id}")
                # 在新的数据库会话中更新状态
                with next(get_task_db()) as new_db:
                    current_task = new_db.query(ReviewTask).get(task_id)
                    if current_task and current_task.status != TaskStatus.CANCELLED:
                        current_task.status = TaskStatus.CANCELLED
                        current_task.cancelled_at = datetime.now()
                        new_db.commit()
            finally:
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
        with next(get_task_db()) as db:
            try:
                task = db.query(ReviewTask).get(task_id)
                if not task:
                    logger.warning(f"要取消的任务未找到: {task_id}")
                    return False

                if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                    logger.info(f"任务 {task_id} 已经处于终态: {task.status.value}")
                    return False

                task.status = TaskStatus.CANCELLED
                task.cancelled_at = datetime.now()
                db.commit()

                if task_id in self._processing_tasks:
                    process_task = self._processing_tasks[task_id]
                    process_task.cancel()
                    logger.info(f"已取消正在处理的任务: {task_id}")

                logger.info(f"任务已成功取消: {task_id}")
                return True

            except Exception as e:
                logger.error(f"取消任务时发生错误: {task_id}, 错误={str(e)}")
                db.rollback()
                return False

    async def start_processing(self) -> None:
        """启动任务处理循环"""
        logger.info("开始任务处理循环")
        while True:
            try:
                task_id = await self.queue.get_task()
                if task_id:
                    asyncio.create_task(self.process_task(task_id))
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"任务处理循环错误: {str(e)}")
                await asyncio.sleep(1)

    async def _get_task(self, db: Session, task_id: str) -> Optional[ReviewTask]:
        """获取任务信息"""
        return db.query(ReviewTask).filter(ReviewTask.task_id == task_id).first()

    async def _update_task_status(
            self, db: Session, task: ReviewTask, status: TaskStatus
    ) -> None:
        """更新任务状态"""
        task.status = status
        db.commit()
        logger.info(f"任务状态已更新: {task.task_id} -> {status.value}")

    async def _process_task_content(self, db: Session, task: ReviewTask) -> None:
        """处理任务内容"""
        df = self.file_service.read_csv_file(task.source_file_url)
        task.total_records = len(df)
        db.commit()

        texts = df['text'].tolist()
        last_update_count = 0

        def update_progress(completed_count: int):
            """更新任务进度"""
            nonlocal last_update_count
            if completed_count == task.total_records or completed_count - last_update_count >= config.text_review.batch_size:
                try:
                    # 获取新的数据库会话和任务实例
                    with next(get_task_db()) as new_db:
                        current_task = new_db.query(
                            ReviewTask).get(task.task_id)
                        if current_task is None or current_task.status == TaskStatus.CANCELLED:
                            raise asyncio.CancelledError("Task was cancelled")

                        current_task.processed_records = completed_count
                        new_db.commit()
                        last_update_count = completed_count
                        logger.info(f"任务 {task.task_id} 进度更新: {
                                    completed_count}/{task.total_records}")
                except Exception as e:
                    logger.error(f"更新进度失败: {str(e)}")
                    raise

        try:
            results = await self.reviewer.async_batch_review(
                texts=texts,
                context=task.context,
                session_id=task.task_id,
                max_concurrency=config.text_review.max_concurrency,
                progress_callback=update_progress
            )

            # 合并结果
            combined_results = []
            for i, result in enumerate(results):
                if result:  # 添加空值检查
                    combined_row = {
                        **df.iloc[i].to_dict(),
                        'validity': result.validity,
                        'sentiment_class': result.sentiment_class,
                        'sensitive_info': result.sensitive_info
                    }
                    combined_results.append(combined_row)

            # 在新的数据库会话中保存结果
            with next(get_task_db()) as new_db:
                current_task = new_db.query(ReviewTask).get(task.task_id)
                if current_task and current_task.status != TaskStatus.CANCELLED:
                    result_file_path = await self.file_service.save_results_to_csv(
                        combined_results, task.task_id)
                    current_task.status = TaskStatus.COMPLETED
                    current_task.result_file_url = result_file_path
                    current_task.processed_records = task.total_records
                    new_db.commit()

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
        with next(get_task_db()) as new_db:
            task = new_db.query(ReviewTask).get(task_id)
            if task and task.status != TaskStatus.CANCELLED:
                task.status = TaskStatus.FAILED
                task.error_message = error_message
                new_db.commit()
                logger.error(f"任务处理失败: {task_id}, 错误={error_message}")
