from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime


class CollectionField(BaseModel):
    """Collection字段配置模型"""
    name: str = Field(..., description="字段名称")
    type: str = Field(..., description="字段类型")
    description: str = Field(..., description="字段描述")
    is_vector: bool = Field(default=False, description="是否为向量字段")

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("字段名称不能为空")
        if not v.isalnum() and not '_' in v:
            raise ValueError("字段名称只能包含字母、数字和下划线")
        return v

    @validator('type')
    def validate_type(cls, v):
        allowed_types = {'str', 'int', 'float', 'bool'}
        if v not in allowed_types:
            raise ValueError(f"字段类型必须是以下之一: {', '.join(allowed_types)}")
        return v


class CollectionConfig(BaseModel):
    """Collection配置模型"""
    name: str = Field(..., description="Collection名称")
    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="Collection描述")
    fields: List[CollectionField] = Field(..., description="字段配置列表")
    embedding_fields: List[str] = Field(..., description="需要向量化的字段列表")
    collection_databases: List[str] = Field(..., description="包含该Collection的数据库列表")
    feature_modules: Optional[List[str]] = Field(default=[], description="所属功能模块列表")

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Collection名称不能为空")
        if not v.isalnum() and not '_' in v:
            raise ValueError("Collection名称只能包含字母、数字和下划线")
        return v

    @validator('embedding_fields')
    def validate_embedding_fields(cls, v, values):
        if 'fields' in values:
            field_names = {field.name for field in values['fields']}
            invalid_fields = set(v) - field_names
            if invalid_fields:
                raise ValueError(f"向量化字段 {invalid_fields} 不存在于字段配置中")
        return v


class DataRecord(BaseModel):
    """数据记录模型"""
    id: Optional[str] = Field(None, description="��录ID")
    data: Dict[str, Any] = Field(..., description="记录数据")
    distance: float = Field(default=0.0, description="向量距离")

class QueryResult(BaseModel):
    """查询结果模型"""
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页记录数")
    data: List[DataRecord] = Field(..., description="记录列表")


class DataQuery(BaseModel):
    """数据查询参数模型"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页记录数")
    search_field: Optional[str] = Field(None, description="搜索字段名称")
    search_text: Optional[str] = Field(None, description="搜索文本")
    top_k: Optional[int] = Field(default=10, ge=1, le=100, description="返回最相似的记录数")


class BatchDataInput(BaseModel):
    """批量数据输入模型"""
    records: List[Dict[str, Any]] = Field(..., description="数据记录列表")
    update_strategy: Literal["upsert", "skip", "error"] = Field(
        default="upsert",
        description="更新策略：upsert-更新或插入, skip-跳过已存在, error-报错"
    )


class BatchDataDelete(BaseModel):
    """批量数据删除模型"""
    ids: Optional[List[str]] = Field(None, description="要删除的记录ID列表")
    filter_conditions: Optional[Dict[str, Any]] = Field(None, description="删除条件")

    @validator('filter_conditions')
    def validate_filter_conditions(cls, v, values):
        if v is None and not values.get('ids'):
            raise ValueError("必须提供ids或filter_conditions之一")
        return v

class BatchOperationResult(BaseModel):
    """批量操作结果模型"""
    success_count: int = Field(..., description="成功处理的记录数")
    error_count: int = Field(..., description="失败的记录数")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="错误详情")


class CollectionInfo(BaseModel):
    """Collection信息模型"""
    name: str = Field(..., description="Collection名称")
    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="Collection描述")
    total_records: int = Field(..., description="总记录数")
    feature_modules: List[str] = Field(default=[], description="所属功能模块列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")