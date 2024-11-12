"""
表结构分析节点模块。
负责解析数据表的详细结构信息。
"""

import os
import logging
from typing import Dict, List
from sqlalchemy import create_engine, MetaData, inspect, Engine

from backend.sql_assistant.states.assistant_state import SQLAssistantState

logger = logging.getLogger(__name__)


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
