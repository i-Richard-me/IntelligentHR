from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from typing import List, Dict, Any
import logging
from modules.text_classification.models import (
    TaskCreate,
    TaskResponse,
    TaskQueue,
)
from common.database.dependencies import get_task_db
from modules.text_classification.models.task import ClassificationTask, TaskStatus
from common.storage.file_service import FileService
from api.dependencies.auth import get_user_id
import uuid
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/text-classification",
    tags=["文本分类"],
    responses={404: {"description": "未找到"}}
)

# 初始化服务
file_service = FileService()
task_queue = TaskQueue("classification")


# 新增: 任务创建请求模型
class CreateTaskRequest(BaseModel):
    file_url: str
    context: str
    categories: Dict[str, Any]
    is_multi_label: bool = False


@router.post(
    "/tasks",
    response_model=TaskResponse,
    summary="创建文本分类任务",
    description="创建新的���本分类任务,支持单标签和多标签分类"
)
async def create_task(
        response: Response,
        request: CreateTaskRequest,
        user_id: str = Depends(get_user_id),
        db=Depends(get_task_db)
) -> TaskResponse:
    """创建新的文本分类任务"""
    try:
        # 验证文件是否存在
        if not file_service.file_exists(request.file_url):
            raise HTTPException(status_code=400, detail="File not found")

        # 创建任务记录
        task = ClassificationTask(
            task_id=str(uuid.uuid4()),
            user_id=user_id,
            context=request.context,
            categories=request.categories,
            is_multi_label=request.is_multi_label,
            source_file_url=request.file_url
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
    description="通过任务ID获取分类任务的当前状态"
)
async def get_task_status(
        task_id: str,
        user_id: str = Depends(get_user_id),
        db=Depends(get_task_db)
) -> TaskResponse:
    """获取任务状态"""
    task = db.query(ClassificationTask).filter(
        ClassificationTask.task_id == task_id,
        ClassificationTask.user_id == user_id
    ).first()

    if not task:
        logger.warning(f"任务未找到或无权访问: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(**task.to_dict())


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=TaskResponse,
    summary="取消任务",
    description="取消指定的文本分类任务"
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
    task = db.query(ClassificationTask).filter(
        ClassificationTask.task_id == task_id,
        ClassificationTask.user_id == user_id
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
    from modules.text_classification.services import TaskProcessor
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
    description="获取当前用户的所有文本分类任务"
)
async def list_tasks(
        user_id: str = Depends(get_user_id),
        db=Depends(get_task_db)
) -> List[TaskResponse]:
    """获取用户的所有任务"""
    tasks = db.query(ClassificationTask).filter(
        ClassificationTask.user_id == user_id
    ).order_by(ClassificationTask.created_at.desc()).all()

    return [TaskResponse(**task.to_dict()) for task in tasks]


@router.get(
    "/tasks/{task_id}/download",
    summary="获取分类结果文件的下载链接",
    description="获取指定任务的分类结果文件的预签名下载URL"
)
async def download_result(
        task_id: str,
        user_id: str = Depends(get_user_id),
        db=Depends(get_task_db)
):
    """获取分类结果文件的预签名下载URL"""
    task = db.query(ClassificationTask).filter(
        ClassificationTask.task_id == task_id,
        ClassificationTask.user_id == user_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.result_file_url:
        raise HTTPException(status_code=400, detail="Result file not available")

    try:
        # 生成预签名URL（1小时有效期）
        presigned_url = file_service.get_presigned_url(task.result_file_url)
        return {"download_url": presigned_url}
    except Exception as e:
        logger.error(f"生成下载URL失败: {str(e)}")
        raise HTTPException(status_code=500, detail="生成下载URL失败")