"""
基于LangGraph框架构建的SQL查询助手。
此助手可以将自然语言查询需求转换为SQL查询，并提供结果反馈。

主要功能：
1. 理解和分析用户查询意图
2. 提取和标准化查询关键信息
3. 匹配合适的数据源和结构
4. 生成和优化SQL查询
5. 执行查询并提供结果分析
"""

import os
import logging
import pandas as pd
from typing import Annotated, Dict, Optional, List, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, MetaData, inspect, text
from sqlalchemy.engine import Engine

from langfuse.callback import CallbackHandler

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage

from utils.llm_tools import (
    init_language_model,
    LanguageModelChain,
    CustomEmbeddings
)
from utils.vector_db_utils import (
    connect_to_milvus,
    initialize_vector_store,
    search_in_milvus
)

logger = logging.getLogger(__name__)

# 状态类型定义


class SQLAssistantState(TypedDict):
    """SQL助手的状态类型定义"""
    # 消息历史记录
    messages: Annotated[List[BaseMessage], add_messages]
    # 查询意图分析结果
    query_intent: Optional[Dict]
    # 意图是否明确的标志
    is_intent_clear: bool
    # 提取的关键词列表
    keywords: List[str]
    # 业务术语及其描述
    domain_term_mappings: Dict[str, str]
    # 改写后的规范化查询
    normalized_query: Optional[str]
    # 匹配的数据表信息
    matched_tables: List[Dict[str, Any]]
    # 数据表结构信息
    table_structures: List[Dict[str, Any]]
    # 生成的SQL信息
    generated_sql: Optional[Dict[str, Any]]
    # SQL执行结果
    execution_result: Optional[Dict[str, Any]]
    # SQL错误分析结果
    error_analysis_result: Optional[Dict[str, Any]]
    # SQL执行重试计数
    retry_count: int
    # 查询结果反馈
    result_feedback: Optional[str]


class QueryIntentAnalysis(BaseModel):
    """查询意图分析结果模型"""
    is_intent_clear: bool = Field(
        ...,
        description="查询意图是否明确。True表示意图清晰，可以继续处理；False表示需要澄清"
    )
    clarification_question: Optional[str] = Field(
        None,
        description="当意图不明确时，需要向用户提出的澄清问题"
    )


INTENT_CLARITY_ANALYSIS_PROMPT = """你是一个专业的数据分析师，负责判断用户数据查询请求的完整性和明确性。
请仔细分析用户的查询请求，判断是否包含了执行数据库查询所需的必要信息。

角色定位：
- 你应该像一个经验丰富的数据分析师一样思考
- 站在数据库查询的技术角度评估查询需求
- 保持专业、客观的分析态度

判断标准:
1. 查询目标明确：清楚用户想要查询什么数据
2. 查询条件完整：如果需要筛选，条件是否明确
3. 时间范围明确：如果查询涉及时间，时间范围是否明确
4. 业务术语清晰：使用的业务术语和指标是否明确

输出要求:
1. 如果意图明确，设置is_intent_clear为true
2. 如果意图不明确，设置is_intent_clear为false，并生成一个明确的问题来获取缺失信息
3. 问题要具体指出缺失的信息点，便于用户理解和回答"""

INTENT_ANALYSIS_USER_PROMPT = """请分析以下用户的数据查询请求，判断其完整性和明确性：

用户查询：
{query}

请分析这个查询请求是否包含足够的信息来执行数据库查询，并按照指定的JSON格式输出分析结果。"""


def create_intent_clarity_analyzer(temperature: float = 0.0) -> LanguageModelChain:
    """创建意图清晰度分析器

    构建用于评估查询意图清晰度的LLM链

    Args:
        temperature: 模型温度参数，控制输出的随机性

    Returns:
        LanguageModelChain: 配置好的意图清晰度分析链
    """
    llm = init_language_model(temperature=temperature)
    return LanguageModelChain(
        model_cls=QueryIntentAnalysis,
        sys_msg=INTENT_CLARITY_ANALYSIS_PROMPT,
        user_msg=INTENT_ANALYSIS_USER_PROMPT,
        model=llm,
    )()


def format_conversation_history(messages: List[BaseMessage]) -> str:
    """将对话历史格式化为提示词格式

    将消息列表转换为结构化的对话历史文本，用于LLM输入

    Args:
        messages: 消息历史列表

    Returns:
        str: 格式化后的对话历史
    """
    formatted = []
    for msg in messages:
        role = "用户" if isinstance(msg, HumanMessage) else "助手"
        formatted.append(f"{role}: {msg.content}")
    return "\n".join(formatted)


def intent_analysis_node(state: SQLAssistantState) -> dict:
    """分析用户查询意图的节点函数

    分析用户的查询请求，判断是否包含足够的信息来执行查询。
    如果意图不明确，会生成澄清问题。

    Args:
        state: 当前状态对象

    Returns:
        dict: 包含意图分析结果的状态更新
    """
    # 获取所有对话历史
    messages = state.get("messages", [])
    if not messages:
        raise ValueError("状态中未找到消息历史")

    # 格式化对话历史
    dialogue_history = format_conversation_history(messages)

    # 创建分析链
    analysis_chain = create_intent_clarity_analyzer()

    # 执行分析
    result = analysis_chain.invoke({"query": dialogue_history})

    # 如果意图不明确，添加一个助手消息询问澄清
    response = {}
    if not result["is_intent_clear"] and result.get("clarification_question"):
        response["messages"] = [
            AIMessage(content=result["clarification_question"])]

    # 更新状态
    response.update({
        "query_intent": {
            "is_clear": result["is_intent_clear"],
            "clarification_needed": not result["is_intent_clear"],
            "clarification_question": result["clarification_question"] if not result["is_intent_clear"] else None
        },
        "is_intent_clear": result["is_intent_clear"]
    })

    return response

# 关键词提取相关定义和实现


class QueryKeywordExtraction(BaseModel):
    """关键词提取结果模型"""
    keywords: List[str] = Field(
        default_factory=list,
        description="从查询中提取的关键实体列表"
    )


DOMAIN_ENTITY_EXTRACTION_PROMPT = """你是一个专业的数据分析师，负责从用户查询中提取需要进行准确匹配的具体业务实体名称。

提取原则：
1. 只提取那些在数据库中需要进行精确匹配的具体实体名称
2. 这些实体通常具有唯一性和特定性，替换成其他名称会导致完全不同的查询结果

不要提取的内容：
1. 泛化的概念词（如：培训、数据、人员、内容等）
2. 时间相关表述（如：2023年、上个月等）
3. 模糊的描述词（如：最近的、所有的等）
4. 常见度量单位（如：数量、金额、比例等）

判断标准：
- 这个词是否需要与数据库中的具体值进行精确匹配？
- 如果用其他词替代，查询结果是否会完全不同？
- 这个词是否代表了一个独特的业务实体？

输出要求：
1. 只输出真正需要进行精确匹配的实体名称
2. 如果没有找到需要精确匹配的实体，返回空列表
3. 去除重复项
4. 保持实体的原始表述形式"""

KEYWORD_EXTRACTION_USER_PROMPT = """请从以下对话中提取需要进行精确匹配的具体业务实体名称：

对话记录：
{dialogue_history}

请按照系统消息中的规则提取关键实体，并以指定的JSON格式输出结果。
注意：只提取那些需要与数据库中的具体值进行精确匹配的实体名称。"""


def create_keyword_extraction_chain(temperature: float = 0.0) -> LanguageModelChain:
    """创建关键词提取任务链

    Args:
        temperature: 模型温度参数，控制输出的随机性

    Returns:
        LanguageModelChain: 配置好的关键词提取任务链
    """
    llm = init_language_model(temperature=temperature)
    return LanguageModelChain(
        model_cls=QueryKeywordExtraction,
        sys_msg=DOMAIN_ENTITY_EXTRACTION_PROMPT,
        user_msg=KEYWORD_EXTRACTION_USER_PROMPT,
        model=llm,
    )()


def keyword_extraction_node(state: SQLAssistantState) -> dict:
    """关键词提取节点函数

    从用户查询和对话历史中提取关键的业务实体和术语。
    包括业务对象、指标和维度等关键信息。

    Args:
        state: 当前状态对象

    Returns:
        dict: 包含提取的关键词的状态更新
    """
    # 获取对话历史
    messages = state.get("messages", [])
    if not messages:
        raise ValueError("状态中未找到消息历史")

    # 格式化对话历史
    dialogue_history = format_conversation_history(messages)

    # 创建提取链
    extraction_chain = create_keyword_extraction_chain()

    # 执行提取
    result = extraction_chain.invoke(
        {"dialogue_history": dialogue_history}
    )

    # 更新状态
    return {
        "keywords": result["keywords"]
    }

# 业务术语规范化相关实现


class DomainTermMapper:
    """业务领域术语映射器

    负责将用户输入的非标准术语映射到标准的领域术语定义。
    使用向量数据库进行语义相似度匹配，支持模糊匹配和同义词处理。
    """

    def __init__(self):
        """初始化术语映射器"""
        # 连接到Milvus向量数据库
        connect_to_milvus("examples")
        # 初始化术语描述集合
        self.collection = initialize_vector_store("term_descriptions")
        # 初始化embedding模型
        self.embeddings = CustomEmbeddings(
            api_key=os.getenv("EMBEDDING_API_KEY", ""),
            api_url=os.getenv("EMBEDDING_API_BASE", ""),
            model=os.getenv("EMBEDDING_MODEL", "")
        )

    def find_standard_terms(
        self,
        keywords: List[str],
        similarity_threshold: float = 0.6
    ) -> Dict[str, str]:
        """查找关键词对应的标准术语及其解释

        Args:
            keywords: 需要标准化的关键词列表
            similarity_threshold: 相似度匹配阈值，控制匹配的严格程度

        Returns:
            Dict[str, str]: 标准术语到解释的映射字典

        Raises:
            ValueError: 向量搜索失败时抛出
        """
        # 如果关键词列表为空，直接返回空字典
        if not keywords:
            return {}

        term_descriptions = {}

        for keyword in keywords:
            try:
                # 生成关键词的向量表示
                query_vector = self.embeddings.embed_query(keyword)

                # 在向量库中搜索相似术语
                results = search_in_milvus(
                    collection=self.collection,
                    query_vector=query_vector,
                    vector_field="term",
                    top_k=1  # 只取最相似的一个结果
                )

                # 如果找到且相似度超过阈值，添加到结果中
                if results and results[0]["distance"] > similarity_threshold:
                    term_descriptions[results[0]["term"]
                                      ] = results[0]["description"]

            except Exception as e:
                logger.error(f"处理关键词 '{keyword}' 时发生错误: {str(e)}")
                continue

        return term_descriptions


def domain_term_mapping_node(state: SQLAssistantState) -> dict:
    """领域术语映射节点函数

    将提取的关键词映射到标准领域术语，并获取其规范定义。
    这个步骤确保后续处理使用统一的业务术语。

    Args:
        state: 当前状态对象

    Returns:
        dict: 包含标准化术语及其解释的状态更新
    """
    # 获取关键词列表
    keywords = state.get("keywords", [])

    try:
        # 创建标准化处理器实例
        standardizer = DomainTermMapper()

        # 执行术语标准化
        term_descriptions = standardizer.find_standard_terms(keywords)

        # 更新状态
        return {
            "domain_term_mappings": term_descriptions
        }

    except Exception as e:
        error_msg = f"业务术语规范化过程出错: {str(e)}"
        logger.error(error_msg)
        return {
            "domain_term_mappings": {},
            "error": error_msg
        }

# 查询需求规范化相关实现


class QueryNormalization(BaseModel):
    """查询需求规范化结果模型"""
    normalized_query: str = Field(
        ...,
        description="规范化后的查询语句"
    )


QUERY_NORMALIZATION_SYSTEM_PROMPT = """你是一个专业的数据分析师，负责将用户的数据查询需求改写为更规范、明确的形式。
请遵循以下规则改写查询：

改写原则：
1. 保持查询的核心意图不变，关注用户表达的查询需求，不要将助手的引导性问题加入改写结果。
2. 使用检索到的标准的业务术语替换同义词(如果存在)
3. 明确指出查询的数据范围（时间、地区等）
4. 明确标注所有查询条件的归属关系
5. 规范化条件表述
6. 移除无关的修饰词和语气词

输出要求：
- 输出一个完整的查询句子
- 使用陈述句形式
- 保持语言简洁明确
- 确保包含所有必要的查询条件"""

QUERY_NORMALIZATION_USER_PROMPT = """请根据以下信息改写用户的查询需求：

1. 对话历史：
{dialogue_history}

2. 检索到的业务术语解释(如果存在)：
{term_descriptions}

请按照系统消息中的规则改写查询，并以指定的JSON格式输出结果。"""


def format_term_descriptions(term_descriptions: dict) -> str:
    """格式化业务术语解释信息

    Args:
        term_descriptions: 业务术语和解释的映射字典

    Returns:
        str: 格式化后的术语解释文本
    """
    if not term_descriptions:
        return "无标准业务术语解释"

    formatted = []
    for term, desc in term_descriptions.items():
        formatted.append(f"- {term}: {desc}")
    return "\n".join(formatted)


def create_query_normalization_chain(temperature: float = 0.0) -> LanguageModelChain:
    """创建查询规范化任务链

    Args:
        temperature: 模型温度参数，控制输出的随机性

    Returns:
        LanguageModelChain: 配置好的查询规范化任务链
    """
    llm = init_language_model(temperature=temperature)

    return LanguageModelChain(
        model_cls=QueryNormalization,
        sys_msg=QUERY_NORMALIZATION_SYSTEM_PROMPT,
        user_msg=QUERY_NORMALIZATION_USER_PROMPT,
        model=llm,
    )()


def query_normalization_node(state: SQLAssistantState) -> dict:
    """查询需求规范化节点函数

    将用户的原始查询改写为规范化的形式，
    使用标准的业务术语，明确查询条件和范围。

    Args:
        state: 当前状态对象

    Returns:
        dict: 包含规范化后查询的状态更新
    """
    # 获取对话历史
    messages = state.get("messages", [])
    if not messages:
        raise ValueError("状态中未找到消息历史")

    # 格式化对话历史
    dialogue_history = format_conversation_history(messages)

    # 格式化术语解释
    term_descriptions = format_term_descriptions(
        state.get("domain_term_mappings", {})
    )

    # 创建规范化链
    normalization_chain = create_query_normalization_chain()

    # 执行规范化
    result = normalization_chain.invoke({
        "dialogue_history": dialogue_history,
        "term_descriptions": term_descriptions
    })

    # 更新状态
    return {
        "normalized_query": result["normalized_query"]
    }

# 数据源识别相关实现


class DataSourceMatcher:
    """数据源匹配器

    负责识别与查询需求最相关的数据表。
    使用向量相似度匹配表的描述信息，支持模糊匹配。
    """

    def __init__(self):
        """初始化数据源匹配器"""
        # 连接到Milvus向量数据库
        connect_to_milvus("examples")
        # 初始化表描述集合
        self.collection = initialize_vector_store("table_descriptions")
        # 初始化embedding模型
        self.embeddings = CustomEmbeddings(
            api_key=os.getenv("EMBEDDING_API_KEY", ""),
            api_url=os.getenv("EMBEDDING_API_BASE", ""),
            model=os.getenv("EMBEDDING_MODEL", "")
        )

    def find_relevant_tables(
        self,
        query: str,
        top_k: int = 1
    ) -> List[Dict[str, Any]]:
        """识别与查询最相关的数据表

        Args:
            query: 规范化后的查询文本
            top_k: 返回的最相关表数量

        Returns:
            List[Dict[str, Any]]: 相关表信息列表，每个表包含名称、描述和相似度分数

        Raises:
            ValueError: 向量搜索失败时抛出
        """
        try:
            # 生成查询文本的向量表示
            query_vector = self.embeddings.embed_query(query)

            # 在向量库中搜索相似表
            results = search_in_milvus(
                collection=self.collection,
                query_vector=query_vector,
                vector_field="description",
                top_k=top_k
            )

            # 转换结果格式
            return [
                {
                    "table_name": result["table_name"],
                    "description": result["description"],
                    "similarity_score": result["distance"]
                }
                for result in results
            ]

        except Exception as e:
            raise ValueError(f"数据表向量搜索失败: {str(e)}")


def data_source_identification_node(state: SQLAssistantState) -> dict:
    """数据源识别节点函数

    根据规范化后的查询需求，识别最相关的数据表。
    使用向量相似度匹配，支持模糊匹配和相关性排序。

    Args:
        state: 当前状态对象

    Returns:
        dict: 包含相关数据表信息的状态更新
    """
    # 获取规范化后的查询
    normalized_query = state.get("normalized_query")
    if not normalized_query:
        raise ValueError("状态中未找到规范化查询")

    try:
        # 创建匹配器实例
        matcher = DataSourceMatcher()

        # 执行数据表匹配
        matched_tables = matcher.find_relevant_tables(normalized_query)

        # 更新状态
        return {
            "matched_tables": matched_tables
        }

    except Exception as e:
        error_msg = f"数据源识别过程出错: {str(e)}"
        logger.error(error_msg)
        return {
            "matched_tables": [],
            "error": error_msg
        }


class DatabaseSchemaParser:
    """数据库表结构解析器

    负责解析和获取数据表的详细结构信息，
    包括字段名称、类型、注释等。
    """

    def __init__(self):
        """初始化数据库连接"""
        self.engine = self._create_engine()
        self.metadata = MetaData()
        self.inspector = inspect(self.engine)

    def _create_engine(self) -> Engine:
        """创建数据库连接引擎

        Returns:
            Engine: SQLAlchemy引擎实例
        """
        db_url = (
            f"mysql+pymysql://"
            f"{os.getenv('SQLBOT_DB_USER', 'root')}:"
            f"{os.getenv('SQLBOT_DB_PASSWORD', '')}@"
            f"{os.getenv('SQLBOT_DB_HOST', 'localhost')}:"
            f"{os.getenv('SQLBOT_DB_PORT', '3306')}/"
            f"{os.getenv('SQLBOT_DB_NAME', '')}"
        )
        return create_engine(db_url)

    def get_table_structure(self, table_name: str) -> Dict[str, List[Dict[str, str]]]:
        """获取指定表的结构信息

        Args:
            table_name: 表名

        Returns:
            Dict: 包含表名和字段列表的字典

        Raises:
            ValueError: 获取表结构失败时抛出
        """
        try:
            columns = []
            for col in self.inspector.get_columns(table_name):
                column_info = {
                    'name': col['name'],
                    'type': str(col['type']),
                    'comment': col.get('comment', '')
                }
                columns.append(column_info)

            return {
                'table_name': table_name,
                'columns': columns
            }

        except Exception as e:
            raise ValueError(f"获取表 {table_name} 的结构失败: {str(e)}")


def table_structure_analysis_node(state: SQLAssistantState) -> dict:
    """表结构分析节点函数

    解析匹配到的数据表的详细结构信息，
    为后续的SQL生成提供必要的表结构信息。

    Args:
        state: 当前状态对象

    Returns:
        dict: 包含表结构信息的状态更新
    """
    # 获取匹配到的表列表
    matched_tables = state.get("matched_tables", [])
    if not matched_tables:
        return {
            "table_structures": [],
            "error": "未找到待分析的数据表"
        }

    try:
        # 创建结构解析器
        parser = DatabaseSchemaParser()
        table_structures = []

        # 获取每个匹配表的结构
        for table in matched_tables:
            structure = parser.get_table_structure(table["table_name"])
            table_structures.append(structure)

        # 更新状态
        return {
            "table_structures": table_structures
        }

    except Exception as e:
        error_msg = f"表结构分析过程出错: {str(e)}"
        logger.error(error_msg)
        return {
            "table_structures": [],
            "error": error_msg
        }

# SQL生成相关实现


class SQLGenerationResult(BaseModel):
    """SQL生成结果模型"""
    is_feasible: bool = Field(
        ...,
        description="表示查询是否可行，根据现有数据表是否能够满足用户的查询需求"
    )
    infeasible_reason: Optional[str] = Field(
        None,
        description="当查询不可行时，说明不可行的具体原因"
    )
    sql_query: Optional[str] = Field(
        None,
        description="当查询可行时，生成的SQL查询语句"
    )


SQL_GENERATION_SYSTEM_PROMPT = """你是一个专业的数据分析师，负责评估用户查询是否能通过现有数据表完成，并生成相应的SQL语句。
请遵循以下规则进行判断和生成：

1. 可行性判断要点：
   - 充分理解数据表中的字段含义和真实的数据类型
   - 检查用户需求的数据项是否能从现有表中获取
   - 检查查询所需的每个字段是否在表中精确存在
   - 严格验证字段的业务含义是否与查询需求完全匹配
   - 确认表之间的关联字段存在且语义一致
   - 确认数据粒度是否满足查询需求
   - 如有字段缺失或语义不匹配，应判定为不可行

2. 当查询不可行时：
   - 设置 is_feasible 为 false
   - 在 infeasible_reason 中详细说明原因
   - 不生成SQL语句

3. 当查询可行时：
   - 设置 is_feasible 为 true
   - 生成标准的SQL语句
   - 使用正确的表和字段名
   - 确保SQL语法正确

4. SQL生成规范：
   - 使用MYSQL语法
   - 正确处理表连接和条件筛选
   - 正确处理NULL值
   - 使用适当的聚合函数和分组

5. 优化建议：
   - 只选择必要的字段
   - 对于容易存在表述不精准的字段，使用'%%keyword%%'进行模糊匹配
   - 添加适当的WHERE条件
   - 使用合适的索引
   - 避免使用SELECT *
   """

SQL_GENERATION_USER_PROMPT = """请根据以下信息评估查询可行性并生成SQL：

1. 规范化后的查询需求：
{normalized_query}

2. 可用的表结构：
{table_structures}

请首先评估查询可行性，并按照指定的JSON格式输出结果。如果可行则生成SQL查询，如果不可行则提供详细的原因。"""


def format_table_structures(schemas: List[Dict]) -> str:
    """格式化表结构信息

    Args:
        schemas: 表结构信息列表

    Returns:
        str: 格式化后的表结构文本
    """
    formatted = []
    for schema in schemas:
        formatted.append(f"表名: {schema['table_name']}")
        formatted.append("字段列表:")
        formatted.append("| 字段名 | 类型 | 说明 |")
        formatted.append("|--------|------|------|")
        for col in schema['columns']:
            formatted.append(
                f"| {col['name']} | {col['type']} | {col['comment']} |"
            )
        formatted.append("")  # 添加空行分隔
    return "\n".join(formatted)


def create_sql_generation_chain(temperature: float = 0.0) -> LanguageModelChain:
    """创建SQL生成任务链

    Args:
        temperature: 模型温度参数，控制输出的随机性

    Returns:
        LanguageModelChain: 配置好的SQL生成任务链
    """
    llm = init_language_model(temperature=temperature)

    return LanguageModelChain(
        model_cls=SQLGenerationResult,
        sys_msg=SQL_GENERATION_SYSTEM_PROMPT,
        user_msg=SQL_GENERATION_USER_PROMPT,
        model=llm,
    )()


def sql_generation_node(state: SQLAssistantState) -> dict:
    """SQL生成节点函数

    基于查询需求和表结构信息，评估查询可行性并生成SQL语句。
    包含查询可行性评估和SQL语句生成两个主要步骤。

    Args:
        state: 当前状态对象

    Returns:
        dict: 包含SQL生成结果的状态更新
    """
    # 验证必要的输入
    if not state.get("normalized_query"):
        return {"error": "状态中未找到规范化查询"}
    if not state.get("table_structures"):
        return {"error": "状态中未找到表结构信息"}

    try:
        # 准备输入数据
        normalized_query = state["normalized_query"]
        table_structures = format_table_structures(state["table_structures"])
        term_descriptions = format_term_descriptions(
            state.get("domain_term_mappings", {})
        )

        # 创建并执行SQL生成链
        generation_chain = create_sql_generation_chain()
        result = generation_chain.invoke({
            "normalized_query": normalized_query,
            "table_structures": table_structures,
            "term_descriptions": term_descriptions
        })

        # 更新状态
        response = {
            "generated_sql": {
                "is_feasible": result["is_feasible"],
                "infeasible_reason": result["infeasible_reason"] if not result["is_feasible"] else None,
                "sql_query": result["sql_query"] if result["is_feasible"] else None
            }
        }

        # 如果查询不可行，将原因添加到消息历史
        if not result["is_feasible"] and result.get("infeasible_reason"):
            response["messages"] = [
                AIMessage(content=result["infeasible_reason"])]

        return response

    except Exception as e:
        error_msg = f"SQL生成过程出错: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


def route_after_sql_generation(state: SQLAssistantState):
    """SQL生成后的路由函数

    根据SQL生成结果决定下一步操作。
    如果生成成功则执行SQL，否则结束处理。

    Args:
        state: 当前状态对象

    Returns:
        str: 下一个节点的标识符
    """
    generated_sql = state.get("generated_sql", {})
    if not generated_sql or not generated_sql.get('is_feasible'):
        return END
    return "sql_execution"

# SQL执行相关实现


class SQLExecutor:
    """SQL执行器

    负责执行SQL查询并处理结果。
    提供查询重试机制，结果分页，错误处理等功能。
    """

    def __init__(self):
        """初始化SQL执行器"""
        self.engine = self._create_engine()

    def _create_engine(self) -> Engine:
        """创建数据库连接引擎

        Returns:
            Engine: SQLAlchemy引擎实例
        """
        db_url = (
            f"mysql+pymysql://"
            f"{os.getenv('SQLBOT_DB_USER', 'root')}:"
            f"{os.getenv('SQLBOT_DB_PASSWORD', '')}@"
            f"{os.getenv('SQLBOT_DB_HOST', 'localhost')}:"
            f"{os.getenv('SQLBOT_DB_PORT', '3306')}/"
            f"{os.getenv('SQLBOT_DB_NAME', '')}"
        )
        return create_engine(db_url)

    def execute_query(self, sql_query: str) -> Dict[str, Any]:
        """执行SQL查询

        Args:
            sql_query: SQL查询语句

        Returns:
            Dict: 包含执行结果或错误信息的字典。
                 成功时包含results、columns、row_count等信息，
                 失败时包含error信息。
        """
        try:
            # 使用pandas读取SQL结果
            df = pd.read_sql_query(text(sql_query), self.engine)

            # 将结果转换为字典列表
            results = df.to_dict('records')

            # 获取列信息
            columns = list(df.columns)

            # 限制返回的记录数量
            max_rows = 100
            if len(results) > max_rows:
                results = results[:max_rows]
                truncated = True
            else:
                truncated = False

            return {
                'success': True,
                'results': results,
                'columns': columns,
                'row_count': len(df),
                'truncated': truncated,
                'error': None
            }

        except Exception as e:
            error_msg = f"SQL执行错误: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'results': None,
                'columns': None,
                'row_count': 0,
                'truncated': False,
                'error': error_msg
            }


def sql_execution_node(state: SQLAssistantState) -> dict:
    """SQL执行节点函数

    执行生成的SQL查询，处理执行结果，支持查询重试。
    使用事务确保数据一致性，支持结果分页。

    Args:
        state: 当前状态对象

    Returns:
        dict: 包含SQL执行结果的状态更新
    """
    # 获取重试计数
    retry_count = state.get("retry_count", 0)

    # 检查是否达到最大重试次数
    max_retries = 2  # 最多允许2次重试（初始执行 + 2次重试）
    if retry_count >= max_retries:
        return {
            "execution_result": {
                'success': False,
                'error': "达到最大重试次数限制"
            },
            "retry_count": retry_count
        }

    # 获取要执行的SQL
    # 优先使用错误分析节点修复后的SQL
    error_analysis = state.get("error_analysis_result", {})
    sql_source = "error_analysis" if error_analysis and error_analysis.get(
        "fixed_sql") else "generation"

    if sql_source == "error_analysis":
        sql_query = error_analysis["fixed_sql"]
    else:
        generated_sql = state.get("generated_sql", {})
        if not generated_sql or not generated_sql.get('sql_query'):
            return {
                "execution_result": {
                    'success': False,
                    'error': "状态中未找到SQL查询语句"
                },
                "retry_count": retry_count
            }
        sql_query = generated_sql['sql_query']

    try:
        # 创建执行器实例
        executor = SQLExecutor()

        # 执行SQL
        result = executor.execute_query(sql_query)

        # 在执行结果中添加额外信息
        result.update({
            'sql_source': sql_source,  # 记录SQL来源
            'executed_sql': sql_query,  # 记录实际执行的SQL
            'retry_number': retry_count  # 记录这是第几次重试
        })

        # 更新状态
        return {
            "execution_result": result,
            "retry_count": retry_count + 1  # 增加重试计数
        }

    except Exception as e:
        error_msg = f"SQL执行节点出错: {str(e)}"
        logger.error(error_msg)
        return {
            "execution_result": {
                'success': False,
                'error': error_msg,
                'sql_source': sql_source,
                'executed_sql': sql_query,
                'retry_number': retry_count
            },
            "retry_count": retry_count + 1  # 即使失败也增加重试计数
        }


def route_after_execution(state: SQLAssistantState):
    """SQL执行后的路由函数

    根据SQL执行结果决定下一步操作。
    执行成功则进入结果反馈，失败则进入错误分析。

    Args:
        state: 当前状态对象

    Returns:
        str: 下一个节点的标识符
    """
    execution_result = state.get("execution_result", {})
    if execution_result.get('success', False):
        return "result_generation"  # 执行成功，生成结果反馈
    return "error_analysis"  # 执行失败，进入错误分析

# SQL错误分析相关实现


class ErrorAnalysisResult(BaseModel):
    """SQL错误分析结果模型"""
    is_sql_fixable: bool = Field(
        ...,
        description="判断是否是可以通过修改SQL来解决的错误"
    )
    error_analysis: str = Field(
        ...,
        description="错误原因分析"
    )
    fixed_sql: Optional[str] = Field(
        None,
        description="当错误可修复时，提供修正后的SQL语句"
    )


ERROR_ANALYSIS_SYSTEM_PROMPT = """你是一个专业的数据分析师，负责分析SQL执行失败的原因并提供解决方案。
请遵循以下规则进行分析：

1. 错误类型分析：
   - 语法错误：SQL语句本身的语法问题
   - 字段错误：表或字段名称错误、类型不匹配
   - 数据错误：空值处理、数据范围、类型转换等问题
   - 权限错误：数据库访问权限问题
   - 连接错误：数据库连接、网络等问题
   - 其他系统错误：数据库服务器问题等

2. 判断可修复性：
   - 可修复：通过修改SQL语句可以解决的问题（如语法错误、字段错误等）
   - 不可修复：需要系统层面解决的问题（如权限、连接等问题）

3. 修复建议：
   - 如果是可修复的错误，提供具体的修复后的SQL语句
   - 确保修复后的SQL符合原始查询意图
   - 保持SQL的优化原则
   - 确保使用正确的表和字段名

4. 输出要求：
   - 明确指出是否可以通过修改SQL修复
   - 详细解释错误原因
   - 对于可修复错误，提供修正后的SQL
   - 对于不可修复错误，说明需要采取的其他解决方案"""

ERROR_ANALYSIS_USER_PROMPT = """请分析以下SQL执行失败的原因并提供解决方案：

1. 原始查询需求：
{normalized_query}

2. 可用的表结构：
{table_structures}

3. 业务术语说明：
{term_descriptions}

4. 执行失败的SQL：
{failed_sql}

5. 错误信息：
{error_message}

请分析错误原因，判断是否可以通过修改SQL修复，并按照指定的JSON格式输出分析结果。"""


def create_error_analysis_chain(temperature: float = 0.0) -> LanguageModelChain:
    """创建错误分析任务链

    Args:
        temperature: 模型温度参数，控制输出的随机性

    Returns:
        LanguageModelChain: 配置好的错误分析任务链
    """
    llm = init_language_model(temperature=temperature)

    return LanguageModelChain(
        model_cls=ErrorAnalysisResult,
        sys_msg=ERROR_ANALYSIS_SYSTEM_PROMPT,
        user_msg=ERROR_ANALYSIS_USER_PROMPT,
        model=llm,
    )()


def error_analysis_node(state: SQLAssistantState) -> dict:
    """SQL错误分析节点函数

    分析SQL执行失败的原因，判断是否可修复，
    并在可能的情况下提供修复方案。

    Args:
        state: 当前状态对象

    Returns:
        dict: 包含错误分析结果的状态更新
    """
    # 获取执行结果
    execution_result = state.get("execution_result", {})
    if not execution_result or execution_result.get('success', True):
        return {"error": "状态中未找到失败的执行结果"}

    generated_sql = state.get("generated_sql", {})
    if not generated_sql or not generated_sql.get('sql_query'):
        return {"error": "状态中未找到生成的SQL"}

    try:
        # 准备输入数据
        input_data = {
            "normalized_query": state["normalized_query"],
            "table_structures": format_table_structures(state["table_structures"]),
            "term_descriptions": format_term_descriptions(state.get("domain_term_mappings", {})),
            "failed_sql": generated_sql["sql_query"],
            "error_message": execution_result["error"]
        }

        # 创建并执行错误分析链
        analysis_chain = create_error_analysis_chain()
        result = analysis_chain.invoke(input_data)

        # 更新状态
        return {
            "error_analysis_result": {
                "is_sql_fixable": result["is_sql_fixable"],
                "error_analysis": result["error_analysis"],
                "fixed_sql": result["fixed_sql"] if result["is_sql_fixable"] else None
            }
        }

    except Exception as e:
        error_msg = f"错误分析过程出错: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


def route_after_error_analysis(state: SQLAssistantState):
    """错误分析后的路由函数

    根据错误分析结果决定下一步操作。
    如果错误可修复，则使用修复后的SQL重新执行；
    否则结束处理流程。

    Args:
        state: 当前状态对象

    Returns:
        str: 下一个节点的标识符
    """
    error_analysis_result = state.get("error_analysis_result", {})
    if error_analysis_result.get("is_sql_fixable", False):
        # 如果是可修复的SQL错误，更新生成的SQL并重新执行
        state["generated_sql"] = {
            "is_feasible": True,
            "sql_query": error_analysis_result["fixed_sql"]
        }
        return "sql_execution"
    return END  # 如果不是SQL问题，结束流程


def route_after_intent(state: SQLAssistantState):
    """意图分析后的路由函数

    根据意图分析结果决定下一个处理节点。
    如果意图不明确，结束对话要求澄清；否则继续处理。

    Args:
        state: 当前状态对象

    Returns:
        str: 下一个节点的标识符
    """
    if not state["is_intent_clear"]:
        return END
    return "keyword_extraction"

# SQL结果生成相关实现


class ResultGenerationOutput(BaseModel):
    """查询结果生成输出模型"""
    result_description: str = Field(
        ...,
        description="面向用户的查询结果描述"
    )


RESULT_GENERATION_SYSTEM_PROMPT = """你是一个专业的数据分析师，负责将SQL查询结果转化为用户友好的自然语言描述。
请遵循以下规则生成反馈：

1. 反馈内容要求：
   - 清晰描述查询结果的主要发现
   - 突出重要的数据指标和趋势
   - 使用简洁、专业的语言
   - 需要说明数据的时间范围
   - 适当解释异常或特殊数据

2. 格式规范：
   - 使用自然语言描述
   - 先总体概述，再说明细节
   - 适当使用数字和百分比
   - 保持专业性和可读性的平衡

3. 注意事项：
   - 如果结果被截断，需要说明仅展示部分数据
   - 确保使用正确的业务术语
   - 避免过度解读数据
   - 保持客观中立的语气"""

RESULT_GENERATION_USER_PROMPT = """请根据以下信息生成查询结果描述：

1. 用户的原始查询：
{normalized_query}

2. 查询结果：
总行数：{row_count}
是否截断：{truncated}
数据预览：
{results_preview}

3. 业务术语说明：
{term_descriptions}

请生成一段清晰、专业的描述，向用户说明查询结果。"""


def format_results_preview(execution_result: Dict) -> str:
    """格式化查询结果预览

    将查询结果格式化为易读的表格形式。
    限制预览行数，确保输出简洁。

    Args:
        execution_result: SQL执行结果字典

    Returns:
        str: 格式化后的结果预览文本
    """
    if not execution_result.get('results'):
        return "无数据"

    results = execution_result['results']
    columns = execution_result['columns']

    # 构建表格形式的预览
    lines = []
    # 表头
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "|".join(["-" * len(col) for col in columns]) + "|")
    # 数据行（最多显示5行）
    for row in results[:5]:
        lines.append("| " + " | ".join(str(row[col])
                     for col in columns) + " |")
    if len(results) > 5:
        lines.append("... (更多结果省略)")

    return "\n".join(lines)


def create_result_generation_chain(temperature: float = 0.0) -> LanguageModelChain:
    """创建结果生成任务链

    Args:
        temperature: 模型温度参数，控制输出的随机性

    Returns:
        LanguageModelChain: 配置好的结果生成任务链
    """
    llm = init_language_model(temperature=temperature)

    return LanguageModelChain(
        model_cls=ResultGenerationOutput,
        sys_msg=RESULT_GENERATION_SYSTEM_PROMPT,
        user_msg=RESULT_GENERATION_USER_PROMPT,
        model=llm,
    )()


def result_generation_node(state: SQLAssistantState) -> dict:
    """结果生成节点函数

    将SQL查询结果转化为用户友好的自然语言描述。
    包括数据概述、关键指标和特殊情况说明。

    Args:
        state: 当前状态对象

    Returns:
        dict: 包含结果描述的状态更新
    """
    # 获取必要信息
    execution_result = state.get("execution_result", {})
    if not execution_result or not execution_result.get('success'):
        return {"error": "状态中未找到成功的执行结果"}

    try:
        # 准备输入数据
        input_data = {
            "normalized_query": state["normalized_query"],
            "row_count": execution_result["row_count"],
            "truncated": execution_result["truncated"],
            "results_preview": format_results_preview(execution_result),
            "term_descriptions": format_term_descriptions(
                state.get("domain_term_mappings", {})
            )
        }

        # 创建并执行结果生成链
        generation_chain = create_result_generation_chain()
        result = generation_chain.invoke(input_data)

        # 将结果描述作为助手消息添加到对话历史
        return {
            "result_description": result["result_description"],
            "messages": [AIMessage(content=result["result_description"])]
        }

    except Exception as e:
        error_msg = f"结果生成过程出错: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

# 最终图构建函数


def build_sql_assistant_graph() -> StateGraph:
    """构建SQL助手的完整处理图

    创建并配置所有节点和边，设置路由逻辑。
    包括意图分析、关键词提取、业务术语规范化等全流程。

    Returns:
        StateGraph: 配置好的状态图实例
    """
    # 创建图构建器
    graph_builder = StateGraph(SQLAssistantState)

    # 添加所有节点
    graph_builder.add_node("intent_analysis", intent_analysis_node)
    graph_builder.add_node("keyword_extraction", keyword_extraction_node)
    graph_builder.add_node("domain_term_mapping", domain_term_mapping_node)
    graph_builder.add_node("query_normalization", query_normalization_node)
    graph_builder.add_node("data_source_identification",
                           data_source_identification_node)
    graph_builder.add_node("table_structure_analysis",
                           table_structure_analysis_node)
    graph_builder.add_node("sql_generation", sql_generation_node)
    graph_builder.add_node("sql_execution", sql_execution_node)
    graph_builder.add_node("error_analysis", error_analysis_node)
    graph_builder.add_node("result_generation", result_generation_node)

    # 设置条件边
    # 意图分析后的路由
    graph_builder.add_conditional_edges(
        "intent_analysis",
        route_after_intent,
        {
            "keyword_extraction": "keyword_extraction",
            END: END
        }
    )

    # SQL生成后的路由
    graph_builder.add_conditional_edges(
        "sql_generation",
        route_after_sql_generation,
        {
            "sql_execution": "sql_execution",
            END: END
        }
    )

    # SQL执行后的路由
    graph_builder.add_conditional_edges(
        "sql_execution",
        route_after_execution,
        {
            "result_generation": "result_generation",
            "error_analysis": "error_analysis"
        }
    )

    # 错误分析后的路由
    graph_builder.add_conditional_edges(
        "error_analysis",
        route_after_error_analysis,
        {
            "sql_execution": "sql_execution",
            END: END
        }
    )

    # 添加基本流程边
    graph_builder.add_edge("keyword_extraction", "domain_term_mapping")
    graph_builder.add_edge("domain_term_mapping", "query_normalization")
    graph_builder.add_edge("query_normalization", "data_source_identification")
    graph_builder.add_edge("data_source_identification",
                           "table_structure_analysis")
    graph_builder.add_edge("table_structure_analysis", "sql_generation")
    graph_builder.add_edge("result_generation", END)

    # 设置入口
    graph_builder.add_edge(START, "intent_analysis")

    return graph_builder


def create_langfuse_handler(session_id: str) -> CallbackHandler:
    """
    创建Langfuse回调处理器。

    Args:
        session_id (str): 会话ID。
        step (str): 当前步骤。

    Returns:
        CallbackHandler: Langfuse回调处理器实例。
    """
    return CallbackHandler(
        tags=["sql_assistant"], session_id=session_id
    )


def run_sql_assistant(
    query: str,
    thread_id: Optional[str] = None,
    checkpoint_saver: Optional[Any] = None
) -> Dict[str, Any]:
    """运行SQL助手

    创建并执行SQL助手的完整处理流程，
    支持会话状态保持和断点续传。

    Args:
        query: 用户的查询文本
        thread_id: 会话ID，用于状态保持
        checkpoint_saver: 状态保存器实例

    Returns:
        Dict[str, Any]: 处理结果字典
    """
    # 创建图构建器
    graph_builder = build_sql_assistant_graph()

    # 使用默认的内存存储器
    if checkpoint_saver is None:
        checkpoint_saver = MemorySaver()

    # 编译图
    graph = graph_builder.compile(checkpointer=checkpoint_saver)

    # 生成会话ID（如果未提供）
    if thread_id is None:
        import uuid
        thread_id = str(uuid.uuid4())

    # 配置运行参数
    config = {"configurable": {"thread_id": thread_id},
              "callbacks": [create_langfuse_handler(thread_id)]}

    # 构造输入消息
    state_input = {
        "messages": [HumanMessage(content=query)]
    }

    # 执行图
    try:
        return graph.invoke(state_input, config)
    except Exception as e:
        error_msg = f"SQL助手执行出错: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
