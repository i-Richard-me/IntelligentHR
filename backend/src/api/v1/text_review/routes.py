from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import FileResponse
from typing import List
import logging
from modules.text_review.models import (
    TaskCreate,
    TaskResponse,
    TaskQueue,
)
from common.database.dependencies import get_task_db
from modules.text_review.models.task import ReviewTask, TaskStatus
from common.storage.file_service import FileService
from api.dependencies.auth import get_user_id
import uuid
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/text-review",
    tags=["文本评估"],
    responses={404: {"description": "未找到"}}
)

# 初始化服务
file_service = FileService()
task_queue = TaskQueue("analysis")


# 新增: 任务取消请求模型
class TaskCancelRequest(BaseModel):
    reason: str | None = None


@router.post(
    "/tasks",
    response_model=TaskResponse,
    summary="创建文本评估任务",
    description="上传文件并创建新的文本评估任务"
)
async def create_task(
        response: Response,
        file: UploadFile = File(..., description="待分析的CSV文件"),
        context: str = Form(..., description="分析上下文"),
        user_id: str = Depends(get_user_id),
        db=Depends(get_task_db)
) -> TaskResponse:
    """创建新的文本评估任务"""
    try:
        # 保存上传的文件
        file_path = await file_service.save_upload_file(file)
        logger.info(f"文件上传成功: {file_path}")

        # 创建任务记录
        task = ReviewTask(
            task_id=str(uuid.uuid4()),
            user_id=user_id,
            context=context,
            source_file_url=file_path
        )
        db.add(task)
        db.commit()
        logger.info(f"任务记录创建成功: {task.task_id}")

        # 将任务添加到队列
        await task_queue.add_task(task.task_id)

        # 设置响应状态码为201 Created
        response.status_code = 201
        return TaskResponse(**task.to_dict())

    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建任务失败")


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="获取任务状态",
    description="通过任务ID获取评估任务的当前状态"
)
async def get_task_status(
        task_id: str,
        user_id: str = Depends(get_user_id),
        db=Depends(get_task_db)
) -> TaskResponse:
    """获取任务状态"""
    task = db.query(ReviewTask).filter(
        ReviewTask.task_id == task_id,
        ReviewTask.user_id == user_id
    ).first()

    if not task:
        logger.warning(f"任务未找到或无权访问: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(**task.to_dict())


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=TaskResponse,
    summary="取消任务",
    description="取消指定的文本评估任务"
)
async def cancel_task(
    task_id: str,
    user_id: str = Depends(get_user_id),
    db = Depends(get_task_db)
) -> TaskResponse:
    """取消指定的任务

    Args:
        task_id: 要取消的任务ID
        user_id: 用户ID
        db: 数据库会话

    Returns:
        TaskResponse: 更新后的任务信息

    Raises:
        HTTPException: 当任务不存在、无权访问或无法取消时抛出
    """
    # 检查任务是否存在且属于当前用户
    task = db.query(ReviewTask).filter(
        ReviewTask.task_id == task_id,
        ReviewTask.user_id == user_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 检查任务是否可以被取消
    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"Task cannot be cancelled in current status: {task.status.value}"
        )

    # 从TaskProcessor获取实例并取消任务
    from modules.text_review.services import TaskProcessor
    processor = TaskProcessor()  # 这里利用了单例模式
    success = await processor.cancel_task(task_id)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to cancel task")

    # 返回更新后的任务信息
    db.refresh(task)
    return TaskResponse(**task.to_dict())


@router.get(
    "/tasks",
    response_model=List[TaskResponse],
    summary="获取任务列表",
    description="获取当前用户的所有文本评估任务"
)
async def list_tasks(
        user_id: str = Depends(get_user_id),
        db=Depends(get_task_db)
) -> List[TaskResponse]:
    """获取用户的所有任务"""
    tasks = db.query(ReviewTask).filter(
        ReviewTask.user_id == user_id
    ).order_by(ReviewTask.created_at.desc()).all()

    return [TaskResponse(**task.to_dict()) for task in tasks]


@router.get("/tasks/{task_id}/download")
async def download_result(
        task_id: str,
        user_id: str = Depends(get_user_id),
        db=Depends(get_task_db)
):
    """下载分析结果"""
    task = db.query(ReviewTask).filter(
        ReviewTask.task_id == task_id,
        ReviewTask.user_id == user_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.result_file_url:
        raise HTTPException(status_code=400, detail="Result file not available")

    return FileResponse(
        task.result_file_url,
        filename=f"review_result_{task.task_id}.csv",
        media_type='text/csv'
    )