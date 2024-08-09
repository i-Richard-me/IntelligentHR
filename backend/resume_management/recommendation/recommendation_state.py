from typing import List, Dict, Optional, Union, Literal
from pydantic import BaseModel, Field


class ResumeRecommendationState(BaseModel):
    """
    表示简历推荐系统的整体状态，包含了整个推荐过程中的所有关键信息。
    """

    original_query: str = Field(..., description="用户的原始查询")
    status: Literal["ready", "need_more_info"] = Field(..., description="当前状态")
    refined_query: str = Field("", description="优化后的查询")
    query_history: List[str] = Field(default_factory=list, description="查询历史")
    current_question: Optional[str] = Field(None, description="当前问题")
    user_input: Optional[str] = Field(None, description="用户输入")
    collection_relevances: List[Dict[str, Union[str, float]]] = Field(
        default_factory=list, description="集合相关性"
    )
    collection_search_strategies: Dict[str, List[Dict[str, Union[str, float]]]] = Field(
        default_factory=dict, description="集合搜索策略"
    )
    ranked_resume_scores_file: Optional[str] = Field(
        None, description="排序后的简历分数文件"
    )
    resume_details_file: Optional[str] = Field(None, description="简历详情文件")
    recommendation_reasons_file: Optional[str] = Field(None, description="推荐理由文件")
    final_recommendations_file: Optional[str] = Field(None, description="最终推荐文件")


class QueryRefinement(BaseModel):
    """
    表示查询优化的结果，用于存储对用户查询的分析结果，包括查询是否已经足够清晰可以进行搜索，或者是否需要进一步的信息。
    如果需要更多信息，它还包含了下一个要问用户的问题。
    """

    status: Literal["ready", "need_more_info"] = Field(..., description="查询状态")
    content: str = Field(..., description="优化后的查询内容或下一个问题")


class CollectionRelevance(BaseModel):
    """
    表示一个简历数据集合与用户查询的相关性，用于量化不同简历数据集合对于满足用户查询的重要程度。
    """

    collection_name: str = Field(..., description="集合名称")
    relevance_score: float = Field(..., ge=0, le=1, description="相关性分数")


class VectorFieldQuery(BaseModel):
    """
    表示针对单个向量字段的查询策略，用于定义如何查询特定字段以及该查询的重要程度。
    """

    field_name: str = Field(..., description="字段名称")
    query_content: str = Field(..., description="查询内容")
    relevance_score: float = Field(..., ge=0, le=1, description="相关性分数")


class CollectionSearchStrategy(BaseModel):
    """
    表示特定简历数据集合的搜索策略，定义了如何在该集合中搜索匹配的简历，包括要查询的具体字段及其查询策略。
    """

    vector_field_queries: List[VectorFieldQuery] = Field(
        ..., description="向量字段查询列表"
    )


class ResumeSearchStrategy(BaseModel):
    """
    表示整体的简历搜索策略，综合了所有相关简历数据集合的重要性，用于指导整个简历搜索过程。决定了在哪些集合中搜索，以及每个集合的重要程度。
    """

    collection_relevances: List[CollectionRelevance] = Field(
        ..., description="集合相关性列表"
    )


class RecommendationReason(BaseModel):
    """
    表示推荐特定简历的理由，用于说明为什么这份简历适合用户的需求，有助于用户理解推荐的依据和简历的优势。
    """

    reason: str = Field(..., description="推荐理由说明")
