from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import FileResponse
from typing import List
import logging
from modules.data_cleaning.models import (
    TaskCreate,
    TaskResponse,
    TaskQueue,
    get_db
)
from modules.data_cleaning.models.task import CleaningTask
from common.storage.file_service import FileService
from api.dependencies.auth import get_user_id
import uuid

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/data-cleaning",
    tags=["数据清洗"],
    responses={404: {"description": "未找到"}}
)

# 初始化服务
file_service = FileService()
task_queue = TaskQueue("cleaning")


@router.post(
    "/tasks",
    response_model=TaskResponse,
    summary="创建数据清洗任务",
    description="上传文件并创建新的数据清洗任务，支持实体名称标准化、验证和清洗"
)
async def create_task(
        response: Response,
        file: UploadFile = File(..., description="待清洗的CSV文件"),
        entity_type: str = Form(..., description="实体类型"),
        validation_rules: str = Form(None, description="验证规则"),
        search_enabled: bool = Form(True, description="是否启用搜索功能"),
        retrieval_enabled: bool = Form(True, description="是否启用检索功能"),
        user_id: str = Depends(get_user_id),
        db=Depends(get_db)
) -> TaskResponse:
    """创建新的数据清洗任务

    Args:
        response: FastAPI响应对象
        file: 上传的CSV文件
        entity_type: 实体类型
        validation_rules: 可选的验证规则
        search_enabled: 是否启用搜索功能
        retrieval_enabled: 是否启用检索功能
        user_id: 用户ID（从请求头获取）
        db: 数据库会话

    Returns:
        TaskResponse: 创建的任务信息

    Raises:
        HTTPException: 当文件上传或任务创建失败时抛出
    """
    try:
        # 保存上传的文件
        file_path = await file_service.save_upload_file(file)
        logger.info(f"文件上传成功: {file_path}")

        # 创建任务记录
        task = CleaningTask(
            task_id=str(uuid.uuid4()),
            user_id=user_id,
            entity_type=entity_type,
            validation_rules=validation_rules,
            search_enabled='enabled' if search_enabled else 'disabled',
            retrieval_enabled='enabled' if retrieval_enabled else 'disabled',
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
    description="通过任务ID获取数据清洗任务的当前状态"
)
async def get_task_status(
        task_id: str,
        user_id: str = Depends(get_user_id),
        db=Depends(get_db)
) -> TaskResponse:
    """获取任务状态

    Args:
        task_id: 任务ID
        user_id: 用户ID（从请求头获取）
        db: 数据库会话

    Returns:
        TaskResponse: 任务信息

    Raises:
        HTTPException: 当任务不存在或无权访问时抛出
    """
    task = db.query(CleaningTask).filter(
        CleaningTask.task_id == task_id,
        CleaningTask.user_id == user_id
    ).first()

    if not task:
        logger.warning(f"任务未找到或无权访问: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(**task.to_dict())


@router.get(
    "/tasks",
    response_model=List[TaskResponse],
    summary="获取任务列表",
    description="获取当前用户的所有数据清洗任务"
)
async def list_tasks(
        user_id: str = Depends(get_user_id),
        db=Depends(get_db)
) -> List[TaskResponse]:
    """获取用户的所有任务

    Args:
        user_id: 用户ID（从请求头获取）
        db: 数据库会话

    Returns:
        List[TaskResponse]: 任务列表
    """
    tasks = db.query(CleaningTask).filter(
        CleaningTask.user_id == user_id
    ).order_by(CleaningTask.created_at.desc()).all()

    return [TaskResponse(**task.to_dict()) for task in tasks]


@router.get(
    "/tasks/{task_id}/download",
    summary="下载清洗结果",
    description="下载指定任务的数据清洗结果文件"
)
async def download_result(
        task_id: str,
        user_id: str = Depends(get_user_id),
        db=Depends(get_db)
) -> FileResponse:
    """下载清洗结果

    Args:
        task_id: 任务ID
        user_id: 用户ID（从请求头获取）
        db: 数据库会话

    Returns:
        FileResponse: 清洗结果文件

    Raises:
        HTTPException: 当任务不存在、无权访问或结果文件不可用时抛出
    """
    task = db.query(CleaningTask).filter(
        CleaningTask.task_id == task_id,
        CleaningTask.user_id == user_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.result_file_url:
        raise HTTPException(status_code=400, detail="Result file not available")

    return FileResponse(
        task.result_file_url,
        filename=f"cleaned_data_{task.task_id}.csv",
        media_type='text/csv'
    )