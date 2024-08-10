from typing import List, Dict, Optional, Union, Literal
from pydantic import BaseModel, Field


class QueryRefinement(BaseModel):
    """查询完善结果"""

    status: Literal["ready", "need_more_info"] = Field(
        ..., description="查询是否准备好进行下一步"
    )
    content: str = Field(..., description="向用户提问的内容或完善后的查询")


class CollectionRelevance(BaseModel):
    """表示一个简历数据集合与用户查询的相关性。"""

    collection_name: str = Field(..., description="简历数据集合的名称")
    relevance_score: float = Field(
        ..., ge=0, le=1, description="相关性分数（0到1之间的浮点数）"
    )


class ResumeSearchStrategy(BaseModel):
    """表示基于用户查询的简历搜索策略。"""

    collection_relevances: List[CollectionRelevance] = Field(
        ..., description="简历数据集合相关性列表"
    )


class VectorFieldQuery(BaseModel):
    """表示针对单个向量字段的查询策略。"""

    field_name: str = Field(..., description="向量字段名称")
    query_content: str = Field(..., description="用于查询的内容")
    relevance_score: float = Field(
        ..., ge=0, le=1, description="相关性分数（0到1之间的浮点数）"
    )


class CollectionSearchStrategy(BaseModel):
    """表示特定简历数据集合的搜索策略。"""

    vector_field_queries: List[VectorFieldQuery] = Field(
        ..., description="向量字段查询策略列表"
    )


class RecommendationReason(BaseModel):
    """表示推荐理由。"""

    reason: str = Field(
        ..., description="一段简洁有力的推荐理由，解释为什么这份简历适合用户的需求"
    )
