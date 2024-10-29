# sql_executor.py

import os
from typing import Dict, List, Any, Optional, Tuple
import logging
import re
from dataclasses import dataclass
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime, date
import decimal
import json

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SQLExecutionResult:
    """SQL执行结果"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None
    affected_rows: int = 0
    execution_time: float = 0.0

class SQLValidator:
    """SQL语句验证器"""
    
    @staticmethod
    def is_select_statement(sql: str) -> bool:
        """
        验证是否为SELECT语句
        
        Args:
            sql: SQL语句
            
        Returns:
            bool: 是否为SELECT语句
        """
        # 移除注释和多余的空白
        cleaned_sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        cleaned_sql = re.sub(r'--.*$', '', cleaned_sql, flags=re.MULTILINE)
        cleaned_sql = cleaned_sql.strip()
        
        # 检查是否以SELECT开头
        return cleaned_sql.upper().startswith('SELECT')

    @staticmethod
    def validate_table_name(sql: str, allowed_table: str) -> bool:
        """
        验证SQL语句是否只涉及允许的表
        
        Args:
            sql: SQL语句
            allowed_table: 允许查询的表名
            
        Returns:
            bool: 是否只使用了允许的表
        """
        # 改进的正则表达式，可以匹配更多的表名引用方式
        table_pattern = r'(?:from|join|update|into)\s+(?:`?(\w+)`?|"(\w+)"|\'(\w+)\')'
        tables = re.findall(table_pattern, sql.lower(), re.IGNORECASE)
        
        # 展平并清理表名列表，同时处理引号包裹的情况
        found_tables = {t for tup in tables for t in tup if t}
        
        return len(found_tables) == 1 and allowed_table.lower() in found_tables

class SQLExecutor:
    """SQL执行器"""
    
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        allowed_table: str
    ):
        """
        初始化SQL执行器
        
        Args:
            host: 数据库主机地址
            port: 数据库端口
            user: 数据库用户名
            password: 数据库密码
            database: 数据库名称
            allowed_table: 允许查询的表名
        """
        self.connection_params = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database,
            'cursorclass': DictCursor
        }
        self.allowed_table = allowed_table
        self.validator = SQLValidator()

    def _get_connection(self):
        """获取数据库连接"""
        try:
            connection_params = self.connection_params.copy()
            # 添加连接超时和读取超时设置
            connection_params.update({
                'connect_timeout': 5,
                'read_timeout': 30,
                'write_timeout': 30
            })
            return pymysql.connect(**connection_params)
        except pymysql.Error as e:
            logger.error(f"数据库连接失败: {str(e)}")
            raise

    def _format_value(self, value: Any) -> Any:
        """
        格式化查询结果中的特殊类型值
        
        Args:
            value: 需要格式化的值
            
        Returns:
            格式化后的值
        """
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, decimal.Decimal):
            # 处理精度问题
            return float(str(value))
        elif value is None:
            return None
        return value

    def _format_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        格式化查询结果
        
        Args:
            results: 原始查询结果
            
        Returns:
            格式化后的结果列表
        """
        formatted_results = []
        for row in results:
            formatted_row = {
                key: self._format_value(value)
                for key, value in row.items()
            }
            formatted_results.append(formatted_row)
        return formatted_results

    def execute_sql(self, sql: str) -> SQLExecutionResult:
        """
        执行SQL查询
        
        Args:
            sql: 要执行的SQL语句
            
        Returns:
            SQLExecutionResult: 执行结果
        """
        # 验证SQL类型
        if not self.validator.is_select_statement(sql):
            return SQLExecutionResult(
                success=False,
                error_message="只允许执行SELECT查询"
            )
            
        # 验证表名
        if not self.validator.validate_table_name(sql, self.allowed_table):
            return SQLExecutionResult(
                success=False,
                error_message=f"只允许查询表 {self.allowed_table}"
            )

        start_time = datetime.now()
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # 设置语句超时
                    cursor.execute("SET SESSION MAX_EXECUTION_TIME=5000")  # 5秒超时
                    # 执行查询
                    affected_rows = cursor.execute(sql)
                    results = cursor.fetchall()
                    
                    # 格式化结果
                    formatted_results = self._format_results(results)
                    
                    execution_time = (datetime.now() - start_time).total_seconds()
                    
                    logger.info(
                        f"SQL执行成功, 影响行数: {affected_rows}, "
                        f"执行时间: {execution_time:.3f}秒"
                    )
                    
                    return SQLExecutionResult(
                        success=True,
                        data=formatted_results,
                        affected_rows=affected_rows,
                        execution_time=execution_time
                    )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_message = f"SQL执行错误: {str(e)}"
            logger.error(error_message)
            
            return SQLExecutionResult(
                success=False,
                error_message=error_message,
                execution_time=execution_time
            )

def create_sql_executor(
    allowed_table: str,
    config: Dict[str, Any] = None
) -> SQLExecutor:
    """
    创建SQLExecutor实例的工厂函数。优先使用环境变量中的配置，如果没有则使用传入的config。
    
    Args:
        config: 可选的数据库配置信息
        allowed_table: 允许查询的表名
        
    Returns:
        SQLExecutor: 配置好的SQLExecutor实例
    """
    # 从环境变量获取配置
    env_config = {
        'host': os.getenv('SQLBOT_DB_HOST', 'localhost'),
        'port': int(os.getenv('SQLBOT_DB_PORT', '3306')),
        'user': os.getenv('SQLBOT_DB_USER', 'root'),
        'password': os.getenv('SQLBOT_DB_PASSWORD', ''),
        'database': os.getenv('SQLBOT_DB_NAME', '')
    }
    
    # 如果提供了config参数，使用config覆盖环境变量配置
    if config:
        env_config.update(config)
    
    # 验证必要的配置参数
    required_keys = ['host', 'port', 'user', 'password', 'database']
    if not all(env_config.get(key) for key in required_keys):
        raise ValueError("数据库配置信息不完整，请检查环境变量或配置参数")
        
    return SQLExecutor(
        host=env_config['host'],
        port=env_config['port'],
        user=env_config['user'],
        password=env_config['password'],
        database=env_config['database'],
        allowed_table=allowed_table
    )
