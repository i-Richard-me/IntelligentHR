"""
数据清洗模块的路由定义
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import FileResponse
from typing import List
import logging
from modules.data_cleaning.models import (
    TaskCreate,
    TaskResponse,
    TaskQueue,
    EntityConfigResponse,
)
from modules.data_cleaning.models.task import CleaningTask
from modules.data_cleaning.services.entity_config_service import EntityConfigService
from common.storage.file_service import FileService
from api.dependencies.auth import get_user_id
from common.database.dependencies import get_task_db, get_entity_config_db
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

@router.get(
    "/entity-types",
    response_model=List[EntityConfigResponse],
    summary="获取支持的实体类型列表",
    description="获取系统支持的所有实体类型及其配置信息"
)
async def list_entity_types(
    user_id: str = Depends(get_user_id),
    db=Depends(get_entity_config_db)
) -> List[EntityConfigResponse]:
    """获取所有支持的实体类型"""
    try:
        config_service = EntityConfigService(db)
        configs = config_service.list_configs()
        return [EntityConfigResponse.model_validate(config.to_dict()) for config in configs]
    except Exception as e:
        logger.error(f"获取实体类型列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取实体类型列表失败")

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
        search_enabled: bool = Form(True, description="是否启用搜索功能"),
        retrieval_enabled: bool = Form(True, description="是否启用检索功能"),
        user_id: str = Depends(get_user_id),
        task_db=Depends(get_task_db),
        entity_config_db=Depends(get_entity_config_db)
) -> TaskResponse:
    """创建新的数据清洗任务"""
    try:
        # 验证实体类型是否支持
        config_service = EntityConfigService(entity_config_db)
        if not config_service.is_valid_entity_type(entity_type):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的实体类型: {entity_type}"
            )

        # 保存上传的文件
        file_path = await file_service.save_upload_file(file)
        logger.info(f"文件上传成功: {file_path}")

        # 创建任务记录
        task = CleaningTask(
            task_id=str(uuid.uuid4()),
            user_id=user_id,
            entity_type=entity_type,
            search_enabled='enabled' if search_enabled else 'disabled',
            retrieval_enabled='enabled' if retrieval_enabled else 'disabled',
            source_file_url=file_path
        )
        
        task_db.add(task)
        task_db.commit()
        logger.info(f"任务记录创建成功: {task.task_id}")

        # 将任务添加到队列
        await task_queue.add_task(task.task_id)

        # 设置响应状态码为201 Created
        response.status_code = 201
        return TaskResponse.model_validate(task.to_dict())

    except HTTPException:
        raise
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
        db=Depends(get_task_db)
) -> TaskResponse:
    """获取任务状态"""
    task = db.query(CleaningTask).filter(
        CleaningTask.task_id == task_id,
        CleaningTask.user_id == user_id
    ).first()

    if not task:
        logger.warning(f"任务未找到或无权访问: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse.model_validate(task.to_dict())

@router.get(
    "/tasks",
    response_model=List[TaskResponse],
    summary="获取任务列表",
    description="获取当前用户的所有数据清洗任务"
)
async def list_tasks(
        user_id: str = Depends(get_user_id),
        db=Depends(get_task_db)
) -> List[TaskResponse]:
    """获取用户的所有任务"""
    tasks = db.query(CleaningTask).filter(
        CleaningTask.user_id == user_id
    ).order_by(CleaningTask.created_at.desc()).all()

    return [TaskResponse.model_validate(task.to_dict()) for task in tasks]

@router.get(
    "/tasks/{task_id}/download",
    summary="下载清洗结果",
    description="下载指定任务的数据清洗结果文件"
)
async def download_result(
        task_id: str,
        user_id: str = Depends(get_user_id),
        db=Depends(get_task_db)
) -> FileResponse:
    """下载清洗结果"""
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