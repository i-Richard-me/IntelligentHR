"""
权限控制节点模块。
负责进行SQL权限验证和权限条件注入。
"""

import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy import create_engine, text
import os
from pydantic import BaseModel, Field
import re

from backend.sql_assistant.states.assistant_state import SQLAssistantState

logger = logging.getLogger(__name__)


class TablePermissionConfig(BaseModel):
    """表权限配置模型"""

    table_name: str = Field(..., description="表名")
    need_dept_control: bool = Field(..., description="是否需要部门权限控制")
    dept_path_field: Optional[str] = Field(None, description="部门路径字段名")


class PermissionValidator:
    """权限验证器

    负责验证用户的表访问权限,并注入部门权限条件。
    """

    def __init__(self):
        """初始化数据库连接"""
        db_url = (
            f"mysql+pymysql://"
            f"{os.getenv('SQLBOT_DB_USER', 'root')}:"
            f"{os.getenv('SQLBOT_DB_PASSWORD', '')}@"
            f"{os.getenv('SQLBOT_DB_HOST', 'localhost')}:"
            f"{os.getenv('SQLBOT_DB_PORT', '3306')}/"
            f"{os.getenv('SQLBOT_DB_NAME', '')}"
        )
        self.engine = create_engine(db_url)

    def _find_table_alias(self, sql: str, table_name: str) -> Optional[str]:
        """查找表的别名

        Args:
            sql: SQL语句
            table_name: 表名

        Returns:
            Optional[str]: 表别名，如果没有别名则返回None
        """
        # 使用正则表达式查找表名及其可能的别名
        pattern = rf"\b{table_name}\b\s+(?:as\s+)?([a-zA-Z][a-zA-Z0-9_]*)\b"
        match = re.search(pattern, sql, re.IGNORECASE)
        return match.group(1) if match else None

    def _build_auth_subquery(
        self, table_name: str, dept_path_field: str, dept_paths: List[str]
    ) -> str:
        """构建权限验证子查询

        Args:
            table_name: 表名
            dept_path_field: 部门路径字段
            dept_paths: 用户的部门路径列表

        Returns:
            str: 构建的子查询SQL
        """
        patterns = [f"(^|>){dept_id}(>|$)" for dept_id in dept_paths]
        regexp_pattern = "|".join(patterns)
        return f"(SELECT * FROM {table_name} WHERE {dept_path_field} REGEXP '{regexp_pattern}')"

    def get_all_table_names(self) -> List[str]:
        """获取数据库中所有已配置的表名

        Returns:
            List[str]: 表名列表
        """
        query = text(
            """
            SELECT table_name 
            FROM table_permission_config 
            WHERE status = 1
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(query)
            return [row[0] for row in result]

    def extract_table_names(self, sql: str) -> List[str]:
        """从SQL语句中提取表名

        使用配置的表名列表进行匹配，避免误识别SQL关键字或别名。

        Args:
            sql: SQL语句

        Returns:
            List[str]: 提取到的表名列表
        """
        try:
            # 获取所有已配置的表名
            all_tables = self.get_all_table_names()

            # 将SQL语句转换为小写以进行不区分大小写的匹配
            sql_lower = sql.lower()

            # 存储匹配到的表名
            matched_tables = set()

            for table in all_tables:
                # 构建匹配模式：表名前后是空白字符、点、括号等分隔符
                pattern = (
                    r"(?:from|join|update|into)\s+(?:\w+\.)?("
                    + re.escape(table.lower())
                    + r")(?:\s+|$|\))"
                )
                if re.search(pattern, sql_lower):
                    matched_tables.add(table)

            return list(matched_tables)

        except Exception as e:
            logger.error(f"提取表名出错: {str(e)}")
            raise ValueError(f"提取表名失败: {str(e)}")

    def get_user_accessible_tables(self, user_id: int) -> List[str]:
        """获取用户可访问的所有表名"""
        query = text(
            """
            SELECT DISTINCT tpc.table_name 
            FROM user_role ur
            JOIN role_table_permission rtp ON ur.role_id = rtp.role_id
            JOIN table_permission_config tpc ON rtp.table_permission_id = tpc.table_permission_id
            WHERE ur.user_id = :user_id
            AND tpc.status = 1
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(query, {"user_id": user_id})
            return [row[0] for row in result]

    def get_user_dept_paths(self, user_id: int) -> List[str]:
        """获取用户的部门路径列表

        Args:
            user_id: 用户ID

        Returns:
            List[str]: 部门路径列表
        """
        query = text(
            """
            SELECT dept_id 
            FROM user_department 
            WHERE user_id = :user_id
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(query, {"user_id": user_id})
            return [row[0] for row in result]

    def get_table_permission_configs(
        self, table_names: List[str]
    ) -> Dict[str, TablePermissionConfig]:
        """获取表的权限配置信息"""
        query = text(
            """
            SELECT table_name, need_dept_control, dept_path_field
            FROM table_permission_config
            WHERE table_name IN :table_names
            AND status = 1
        """
        )

        configs = {}
        with self.engine.connect() as conn:
            result = conn.execute(query, {"table_names": tuple(table_names)})
            for row in result:
                configs[row[0]] = TablePermissionConfig(
                    table_name=row[0],
                    need_dept_control=bool(row[1]),
                    dept_path_field=row[2],
                )
        return configs

    def verify_and_inject_permissions(
        self, user_id: int, sql: str
    ) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        """验证权限并注入权限条件"""
        try:
            # 提取SQL中的所有表名
            query_tables = self.extract_table_names(sql)
            logger.info(f"从SQL中提取到的表: {query_tables}")

            # 获取用户可访问的表
            accessible_tables = self.get_user_accessible_tables(user_id)

            # 验证表权限
            unauthorized_tables = [
                table for table in query_tables if table not in accessible_tables
            ]
            if unauthorized_tables:
                return False, None, unauthorized_tables

            # 获取表的权限配置信息
            table_configs = self.get_table_permission_configs(query_tables)

            # 获取需要部门权限控制的表
            dept_control_tables = [
                table
                for table in query_tables
                if table_configs.get(table) and table_configs[table].need_dept_control
            ]

            if not dept_control_tables:
                return True, sql, None

            # 获取用户的部门路径
            dept_paths = self.get_user_dept_paths(user_id)
            if not dept_paths:
                return True, sql, None

            # 处理每个需要权限控制的表
            modified_sql = sql
            for table in dept_control_tables:
                field = table_configs[table].dept_path_field
                if not field:
                    continue

                # 获取表的别名
                alias = self._find_table_alias(sql, table)
                logger.info(f"表 {table} 的别名: {alias}")

                # 构建带权限控制的子查询
                auth_subquery = self._build_auth_subquery(table, field, dept_paths)

                # 替换SQL中的原表引用
                # 如果有别名，保留原有的别名
                if alias:
                    auth_subquery = f"{auth_subquery} AS {alias}"
                    # 使用正则表达式替换原表及其别名
                    pattern = rf"{table}\s+(?:as\s+)?{alias}\b"
                    modified_sql = re.sub(
                        pattern, auth_subquery, modified_sql, flags=re.IGNORECASE
                    )
                else:
                    # 直接替换表名
                    pattern = rf"\b{table}\b"
                    modified_sql = re.sub(pattern, auth_subquery, modified_sql)

            # 记录修改后的SQL，方便调试
            logger.info(f"注入权限后的SQL: {modified_sql}")
            return True, modified_sql, None

        except Exception as e:
            logger.error(f"权限验证过程出错: {str(e)}")
            return False, None, None


def permission_control_node(state: SQLAssistantState) -> dict:
    """权限控制节点函数

    验证用户对SQL中涉及表的访问权限,
    并在必要时注入部门权限控制条件。

    Args:
        state: 当前状态对象

    Returns:
        dict: 包含权限验证结果的状态更新
    """
    # 获取用户ID和生成的SQL
    user_id = state.get("user_id")
    generated_sql = state.get("generated_sql", {})

    if not generated_sql or not generated_sql.get("sql_query"):
        return {
            "execution_result": {"success": False, "error": "状态中未找到生成的SQL"}
        }

    # 检查权限控制是否启用
    if os.getenv("USER_AUTH_ENABLED", "false").lower() != "true":
        # 权限控制未启用时，不修改SQL
        return {"generated_sql": generated_sql, "execution_result": {"success": True}}

    if not user_id:
        return {"execution_result": {"success": False, "error": "未找到用户ID信息"}}

    try:
        # 创建权限验证器
        validator = PermissionValidator()

        # 执行权限验证和注入
        is_valid, modified_sql, unauthorized_tables = (
            validator.verify_and_inject_permissions(
                user_id=user_id, sql=generated_sql["sql_query"]
            )
        )

        if not is_valid:
            error_msg = f"权限验证失败: 无权访问表 {', '.join(unauthorized_tables or ['未知表'])}"
            return {
                "execution_result": {
                    "success": False,
                    "error": error_msg,
                    "sql_source": "permission_control",
                }
            }

        # 验证通过，更新SQL
        return {
            "generated_sql": {"sql_query": modified_sql},
            "execution_result": {"success": True},
        }

    except Exception as e:
        error_msg = f"权限控制过程出错: {str(e)}"
        logger.error(error_msg)
        return {
            "execution_result": {
                "success": False,
                "error": error_msg,
                "sql_source": "permission_control",
            }
        }
