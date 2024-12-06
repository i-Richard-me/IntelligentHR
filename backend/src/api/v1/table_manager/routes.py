from fastapi import APIRouter, Depends, Path, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from modules.table_manager.services.table_service import TableService
from modules.table_manager.models.schemas import (
    TableSchema,
    TableRecord,
    TableRecordCreate,
    TableRecordUpdate,
    QueryResult,
    BatchOperationResult,
    PaginationParams,
    SortCondition,
    SortOrder,
    OperationResponse
)
from modules.table_manager.exceptions.table_exceptions import (
    TableManagerError,
    handle_table_manager_error
)
from api.dependencies.auth import get_user_id
import logging

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/table-manager",
    tags=["表格管理"],
    responses={404: {"description": "未找到"},
               400: {"description": "请求无效"},
               500: {"description": "服务器错误"}}
)

@router.get(
    "/tables/{database}/{table_name}/schema",
    response_model=TableSchema,
    summary="获取表结构",
    description="获取指定数据库表的结构信息，包含字段定义、主键等信息"
)
async def get_table_schema(
    database: str = Path(..., description="数据库名称"),
    table_name: str = Path(..., description="表格名称"),
    user_id: str = Depends(get_user_id)
) -> TableSchema:
    """获取表结构"""
    try:
        service = TableService(database)
        return service.get_schema(table_name)
    except TableManagerError as e:
        logger.error(f"获取表结构失败: database={database}, table={table_name}, error={str(e)}")
        raise handle_table_manager_error(e)

@router.get(
    "/tables/{database}/{table_name}/records",
    response_model=QueryResult,
    summary="获取记录列表",
    description="获取表格中的记录列表，支持分页和排序"
)
async def list_records(
    database: str = Path(..., description="数据库名称"),
    table_name: str = Path(..., description="表格名称"),
    user_id: str = Depends(get_user_id),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页记录数"),
    sort_field: Optional[str] = Query(None, description="排序字段"),
    sort_order: Optional[SortOrder] = Query(None, description="排序方向")
) -> QueryResult:
    """获取记录列表"""
    try:
        service = TableService(database)
        
        # 构建分页参数
        pagination = PaginationParams(page=page, page_size=page_size)
        
        # 构建排序参数
        sorts = None
        if sort_field:
            sorts = [SortCondition(field=sort_field, order=sort_order or SortOrder.ASC)]
            
        return service.list_records(
            table_name=table_name,
            pagination=pagination,
            sorts=sorts
        )
    except TableManagerError as e:
        logger.error(f"获取记录列表失败: database={database}, table={table_name}, error={str(e)}")
        raise handle_table_manager_error(e)

@router.get(
    "/tables/{database}/{table_name}/records/{record_id}",
    response_model=TableRecord,
    summary="获取记录详情",
    description="获取指定记录的详细信息"
)
async def get_record(
    database: str = Path(..., description="数据库名称"),
    table_name: str = Path(..., description="表格名称"),
    record_id: str = Path(..., description="记录ID"),
    user_id: str = Depends(get_user_id)
) -> TableRecord:
    """获取记录详情"""
    try:
        service = TableService(database)
        return service.get_record(table_name, record_id)
    except TableManagerError as e:
        logger.error(f"获取记录详情失败: database={database}, table={table_name}, id={record_id}, error={str(e)}")
        raise handle_table_manager_error(e)

@router.post(
    "/tables/{database}/{table_name}/records",
    response_model=BatchOperationResult,
    summary="创建记录",
    description="创建一条或多条记录",
    status_code=201
)
async def create_records(
    request: TableRecordCreate,
    database: str = Path(..., description="数据库名称"),
    table_name: str = Path(..., description="表格名称"),
    user_id: str = Depends(get_user_id)
) -> BatchOperationResult:
    """创建记录"""
    try:
        service = TableService(database)
        return service.create_records(table_name, request.records)
    except TableManagerError as e:
        logger.error(f"创建记录失败: database={database}, table={table_name}, error={str(e)}")
        raise handle_table_manager_error(e)

@router.put(
    "/tables/{database}/{table_name}/records/{record_id}",
    response_model=TableRecord,
    summary="更新记录",
    description="更新指定记录的信息"
)
async def update_record(
    request: TableRecordUpdate,
    database: str = Path(..., description="数据库名称"),
    table_name: str = Path(..., description="表格名称"),
    record_id: str = Path(..., description="记录ID"),
    user_id: str = Depends(get_user_id)
) -> TableRecord:
    """更新记录"""
    try:
        service = TableService(database)
        return service.update_record(table_name, record_id, request.data)
    except TableManagerError as e:
        logger.error(f"更新记录失败: database={database}, table={table_name}, id={record_id}, error={str(e)}")
        raise handle_table_manager_error(e)

@router.delete(
    "/tables/{database}/{table_name}/records/{record_id}",
    response_model=OperationResponse,
    summary="删除记录",
    description="删除指定的记录"
)
async def delete_record(
    database: str = Path(..., description="数据库名称"),
    table_name: str = Path(..., description="表格名称"),
    record_id: str = Path(..., description="记录ID"),
    user_id: str = Depends(get_user_id)
) -> OperationResponse:
    """删除记录"""
    try:
        service = TableService(database)
        success = service.delete_record(table_name, record_id)
        return OperationResponse(
            success=success,
            message="记录删除成功" if success else "记录删除失败"
        )
    except TableManagerError as e:
        logger.error(f"删除记录失败: database={database}, table={table_name}, id={record_id}, error={str(e)}")
        raise handle_table_manager_error(e)