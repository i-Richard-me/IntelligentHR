from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from modules.collection_manager.services.collection_service import CollectionService
from modules.collection_manager.models.schemas import (
    CollectionInfo,
    DataQuery,
    BatchDataInput,
    BatchDataDelete,
    QueryResult,
    BatchOperationResult,
)
from modules.collection_manager.exceptions.collection_exceptions import (
    CollectionManagerError,
    handle_collection_manager_error
)
from api.dependencies.auth import get_user_id
from common.database.dependencies import get_app_config_db
import logging

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/collection-manager",
    tags=["向量数据库管理"],
    responses={404: {"description": "未找到"},
               400: {"description": "请求无效"},
               500: {"description": "服务器错误"}}
)

# 初始化服务实例
collection_service = CollectionService()

@router.get(
    "/collections/{db_name}",
    response_model=List[CollectionInfo],
    summary="获取Collection列表",
    description="获取指定数据库中可用的Collection列表"
)
async def list_collections(
    db_name: str = Path(..., description="数据库名称"),
    feature_module: str | None = Query(None, description="功能模块名称，用于过滤collection"),
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_app_config_db)
) -> List[CollectionInfo]:
    """获取Collection列表"""
    try:
        collections = await collection_service.get_collections(db, db_name, feature_module)
        return [CollectionInfo(**collection) for collection in collections]
    except CollectionManagerError as e:
        logger.error(f"获取Collection列表失败: database={db_name}, error={str(e)}")
        raise handle_collection_manager_error(e)
    except Exception as e:
        logger.error(f"获取Collection列表时发生未知错误: {str(e)}")
        raise

@router.get(
    "/collections/{db_name}/{collection_name}/data",
    response_model=QueryResult,
    summary="查询Collection数据",
    description="查询指定Collection中的数据，支持向量相似度搜索"
)
async def query_collection_data(
    db_name: str = Path(..., description="数据库名称"),
    collection_name: str = Path(..., description="Collection名称"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页记录数"),
    search_field: str | None = Query(None, description="搜索字段"),
    search_text: str | None = Query(None, description="搜索文本"),
    top_k: int = Query(10, ge=1, le=100, description="返回最相似的记录数"),
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_app_config_db)
) -> QueryResult:
    """查询Collection数据"""
    try:
        query_params = DataQuery(
            page=page,
            page_size=page_size,
            search_field=search_field,
            search_text=search_text,
            top_k=top_k
        )
        
        result = await collection_service.query_collection_data(
            db,
            db_name,
            collection_name,
            query_params
        )
        return result
    except CollectionManagerError as e:
        logger.error(
            f"查询Collection数据失败: database={db_name}, "
            f"collection={collection_name}, error={str(e)}"
        )
        raise handle_collection_manager_error(e)
    except Exception as e:
        logger.error(f"查询Collection数据时发生未知错误: {str(e)}")
        raise

@router.post(
    "/collections/{db_name}/{collection_name}/data",
    response_model=BatchOperationResult,
    summary="批量插入数据",
    description="向指定Collection批量插入或更新数据",
    status_code=201
)
async def batch_insert_data(
    request: BatchDataInput,
    db_name: str = Path(..., description="数据库名称"),
    collection_name: str = Path(..., description="Collection名称"),
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_app_config_db)
) -> BatchOperationResult:
    """批量插入数据"""
    try:
        result = await collection_service.batch_insert_data(
            db,
            db_name,
            collection_name,
            request
        )
        return result
    except CollectionManagerError as e:
        logger.error(
            f"批量插入数据失败: database={db_name}, "
            f"collection={collection_name}, error={str(e)}"
        )
        raise handle_collection_manager_error(e)
    except Exception as e:
        logger.error(f"批量插入数据时发生未知错误: {str(e)}")
        raise

@router.delete(
    "/collections/{db_name}/{collection_name}/data",
    response_model=BatchOperationResult,
    summary="批量删除数据",
    description="从指定Collection批量删除数据"
)
async def batch_delete_data(
    request: BatchDataDelete,
    db_name: str = Path(..., description="数据库名称"),
    collection_name: str = Path(..., description="Collection名称"),
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_app_config_db)
) -> BatchOperationResult:
    """批量删除数据"""
    try:
        result = await collection_service.batch_delete_data(
            db,
            db_name,
            collection_name,
            request
        )
        return result
    except CollectionManagerError as e:
        logger.error(
            f"批量删除数据失败: database={db_name}, "
            f"collection={collection_name}, error={str(e)}"
        )
        raise handle_collection_manager_error(e)
    except Exception as e:
        logger.error(f"批量删除数据时发生未知错误: {str(e)}")
        raise