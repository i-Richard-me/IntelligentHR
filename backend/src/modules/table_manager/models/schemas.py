from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
from datetime import datetime

class SortOrder(str, Enum):
    """排序方向枚举"""
    ASC = "asc"
    DESC = "desc"

class FilterOperator(str, Enum):
    """过滤操作符枚举"""
    EQ = "eq"          # 等于
    NEQ = "neq"        # 不等于
    GT = "gt"          # 大于
    GTE = "gte"        # 大于等于
    LT = "lt"          # 小于
    LTE = "lte"        # 小于等于
    LIKE = "like"      # 模糊匹配
    IN = "in"          # 在列表中
    BETWEEN = "between"  # 在范围内

class FilterCondition(BaseModel):
    """过滤条件模型"""
    field: str
    operator: FilterOperator
    value: Any

class SortCondition(BaseModel):
    """排序条件模型"""
    field: str
    order: SortOrder = SortOrder.ASC

class PaginationParams(BaseModel):
    """分页参数模型"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)

class TableQueryParams(BaseModel):
    """表格查询参数模型"""
    pagination: Optional[PaginationParams] = None
    filters: Optional[List[FilterCondition]] = None
    sorts: Optional[List[SortCondition]] = None
    fields: Optional[List[str]] = None

class TableRecord(BaseModel):
    """表格记录模型"""
    id: Optional[Union[str, int]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    data: Dict[str, Any]

    @validator('data')
    def validate_data(cls, v):
        """验证数据字段不为空"""
        if not v:
            raise ValueError("data field cannot be empty")
        return v

class TableRecordCreate(BaseModel):
    """创建记录请求模型"""
    records: List[Dict[str, Any]]

    @validator('records')
    def validate_records(cls, v):
        """验证记录列表不为空"""
        if not v:
            raise ValueError("records cannot be empty")
        return v

class TableRecordUpdate(BaseModel):
    """更新记录请求模型"""
    data: Dict[str, Any]

    @validator('data')
    def validate_data(cls, v):
        """验证数据字段不为空"""
        if not v:
            raise ValueError("data field cannot be empty")
        return v

class TableSchemaField(BaseModel):
    """表格字段模型"""
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    default: Optional[Any] = None
    max_length: Optional[int] = None
    description: Optional[str] = None

class TableSchema(BaseModel):
    """表格结构模型"""
    table_name: str
    fields: List[TableSchemaField]
    primary_keys: List[str]
    description: Optional[str] = None

class QueryResult(BaseModel):
    """查询结果模型"""
    total: int
    page: int
    page_size: int
    data: List[TableRecord]

class BatchOperationResult(BaseModel):
    """批量操作结果模型"""
    success_count: int
    error_count: int
    errors: Optional[List[Dict[str, Any]]] = None

class OperationResponse(BaseModel):
    """操作响应模型"""
    success: bool
    message: str
    data: Optional[Any] = None