# ==================================================
# File: v1/text_classification/routes.py
# ==================================================

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import FileResponse
from typing import List, Dict, Any
import logging
from modules.text_classification.models import (
    TaskCreate,
    TaskResponse,
    TaskQueue,
    get_db
)
from modules.text_classification.models.task import ClassificationTask
from common.storage.file_service import FileService
from api.dependencies.auth import get_user_id
import uuid

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/text-classification",
    tags=["文本分类"],
    responses={404: {"description": "未找到"}}
)

# 初始化服务
file_service = FileService()
task_queue = TaskQueue()


@router.post(
    "/tasks",
    response_model=TaskResponse,
    summary="创建文本分类任务",
    description="上传文件并创建新的文本分类任务"
)
async def create_task(
        response: Response,
        file: UploadFile = File(..., description="待分类的CSV文件"),
        context: str = Form(..., description="分类上下文"),
        categories: Dict[str, Any] = Form(..., description="分类规则"),
        is_multi_label: bool = Form(False, description="是否为多标签分类"),
        user_id: str = Depends(get_user_id),
        db=Depends(get_db)
) -> TaskResponse:
    try:
        # 保存上传的文件
        file_path = await file_service.save_upload_file(file)
        logger.info(f"文件上传成功: {file_path}")

        # 创建任务记录
        task = ClassificationTask(
            task_id=str(uuid.uuid4()),
            user_id=user_id,
            context=context,
            categories=categories,
            is_multi_label=is_multi_label,
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
    description="通过任务ID获取分类任务的当前状态"
)
async def get_task_status(
        task_id: str,
        user_id: str = Depends(get_user_id),
        db=Depends(get_db)
) -> TaskResponse:
    task = db.query(ClassificationTask).filter(
        ClassificationTask.task_id == task_id,
        ClassificationTask.user_id == user_id
    ).first()

    if not task:
        logger.warning(f"任务未找到或无权访问: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(**task.to_dict())


@router.get(
    "/tasks",
    response_model=List[TaskResponse],
    summary="获取任务列表",
    description="获取当前用户的所有文本分类任务"
)
async def list_tasks(
        user_id: str = Depends(get_user_id),
        db=Depends(get_db)
) -> List[TaskResponse]:
    tasks = db.query(ClassificationTask).filter(
        ClassificationTask.user_id == user_id
    ).order_by(ClassificationTask.created_at.desc()).all()

    return [TaskResponse(**task.to_dict()) for task in tasks]


@router.get(
    "/tasks/{task_id}/download",
    summary="下载分类结果",
    description="下载指定任务的分类结果文件"
)
async def download_result(
        task_id: str,
        user_id: str = Depends(get_user_id),
        db=Depends(get_db)
):
    task = db.query(ClassificationTask).filter(
        ClassificationTask.task_id == task_id,
        ClassificationTask.user_id == user_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.result_file_url:
        raise HTTPException(status_code=400, detail="Result file not available")

    return FileResponse(
        task.result_file_url,
        filename=f"classification_result_{task.task_id}.csv",
        media_type='text/csv'
    )