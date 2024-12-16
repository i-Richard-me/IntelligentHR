from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import logging
from modules.sensitive_detection.models import (
    TaskCreate,
    TaskResponse,
    TaskQueue,
    SensitiveDetectionTask,
    TaskStatus,
    TaskCancelRequest,
    SensitiveTypeConfig
)
from common.database.dependencies import get_task_db
from common.storage.file_service import FileService
from api.dependencies.auth import get_user_id
import uuid
import json

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/sensitive-detection",
    tags=["敏感信息检测"],
    responses={404: {"description": "未找到"}}
)

class SensitiveDetectionRequest(BaseModel):
    file_url: str = Field(..., description="文件URL（从文件上传接口获取）")
    context: str = Field(..., description="分析上下文")
    sensitive_types: Dict[str, Dict[str, str]] = Field(..., description="敏感信息类型配置")

# 初始化服务
file_service = FileService()
task_queue = TaskQueue("sensitive")

@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=201,
    summary="创建敏感信息检测任务",
    description="创建新的敏感信息检测任务"
)
async def create_task(
    request: SensitiveDetectionRequest,
    user_id: str = Depends(get_user_id),
    db=Depends(get_task_db)
) -> TaskResponse:
    """创建新的敏感信息检测任务"""
    try:
        # 创建任务记录
        task = SensitiveDetectionTask(
            task_id=str(uuid.uuid4()),
            user_id=user_id,
            context=request.context,
            sensitive_types=request.sensitive_types,
            source_file_url=request.file_url
        )
        db.add(task)
        db.commit()
        logger.info(f"任务记录创建成功: {task.task_id}")

        # 将任务添加到队列
        task_queue = TaskQueue("sensitive")
        await task_queue.add_task(task.task_id)

        return TaskResponse(**task.to_dict())

    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建任务失败")


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="获取任务状态",
    description="通过任务ID获取敏感信息检测任务的当前状态"
)
async def get_task_status(
        task_id: str,
        user_id: str = Depends(get_user_id),
        db=Depends(get_task_db)
) -> TaskResponse:
    """获取任务状态"""
    task = db.query(SensitiveDetectionTask).filter(
        SensitiveDetectionTask.task_id == task_id,
        SensitiveDetectionTask.user_id == user_id
    ).first()

    if not task:
        logger.warning(f"任务未找到或无权访问: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(**task.to_dict())


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=TaskResponse,
    summary="取消任务",
    description="取消指定的敏感信息检测任务"
)
async def cancel_task(
    task_id: str,
    cancel_request: TaskCancelRequest,
    user_id: str = Depends(get_user_id),
    db = Depends(get_task_db)
) -> TaskResponse:
    """取消指定的任务

    Args:
        task_id: 要取消的任务ID
        cancel_request: 取消请求信息
        user_id: 用户ID
        db: 数据库会话

    Returns:
        TaskResponse: 更新后的任务信息

    Raises:
        HTTPException: 当任务不存在、无权访问或无法取消时抛出
    """
    # 检查任务是否存在且属于当前用户
    task = db.query(SensitiveDetectionTask).filter(
        SensitiveDetectionTask.task_id == task_id,
        SensitiveDetectionTask.user_id == user_id
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
    from modules.sensitive_detection.services import TaskProcessor
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
    description="获取当前用户的所有敏感信息检测任务"
)
async def list_tasks(
        user_id: str = Depends(get_user_id),
        db=Depends(get_task_db)
) -> List[TaskResponse]:
    """获取用户的所有任务"""
    tasks = db.query(SensitiveDetectionTask).filter(
        SensitiveDetectionTask.user_id == user_id
    ).order_by(SensitiveDetectionTask.created_at.desc()).all()

    return [TaskResponse(**task.to_dict()) for task in tasks]


@router.get(
    "/tasks/{task_id}/download",
    summary="获取任务结果文件的下载链接",
    description="获取敏感信息检测任务的结果文件的预签名下载URL"
)
async def download_result(
        task_id: str,
        user_id: str = Depends(get_user_id),
        db=Depends(get_task_db)
):
    """获取结果文件的预签名下载URL"""
    task = db.query(SensitiveDetectionTask).filter(
        SensitiveDetectionTask.task_id == task_id,
        SensitiveDetectionTask.user_id == user_id
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