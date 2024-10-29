# db_schema.py

from typing import List, Dict, Any
import logging
from dataclasses import dataclass
import os
import pymysql
from pymysql.cursors import DictCursor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ColumnInfo:
    """表字段信息"""
    name: str           # 字段名称
    data_type: str      # 数据类型
    comment: str        # 字段注释

class SchemaManager:
    """MySQL表结构信息管理器"""
    
    def __init__(
        self, 
        host: str,
        port: int,
        user: str,
        password: str,
        database: str
    ):
        """
        初始化数据库连接
        
        Args:
            host: 数据库主机地址
            port: 数据库端口
            user: 数据库用户名
            password: 数据库密码
            database: 数据库名称
        """
        self.connection_params = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database,
            'cursorclass': DictCursor
        }

    def get_connection(self):
        """获取数据库连接"""
        try:
            return pymysql.connect(**self.connection_params)
        except pymysql.Error as e:
            logger.error(f"数据库连接失败: {str(e)}")
            raise

    def get_all_tables(self) -> List[Dict[str, str]]:
        """
        获取数据库中所有表的名称和注释
        
        Returns:
            List[Dict[str, str]]: 包含表名和表注释的字典列表
        """
        query = """
        SELECT 
            TABLE_NAME as table_name,  # 修改这里：明确指定别名
            TABLE_COMMENT as table_comment  # 修改这里：明确指定别名
        FROM 
            information_schema.tables
        WHERE 
            table_schema = %s
            AND table_type = 'BASE TABLE'  # 添加这里：只获取基础表，排除视图等
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (self.connection_params['database'],))
                    tables = cursor.fetchall()
                    return [
                        {
                            'name': table['table_name'],
                            'comment': table['table_comment']
                        }
                        for table in tables
                    ]
        except Exception as e:
            logger.error(f"获取表列表失败: {str(e)}")
            raise

    def get_table_schema(self, table_name: str) -> List[ColumnInfo]:
        """
        获取指定表的结构信息
        
        Args:
            table_name: 表名
            
        Returns:
            List[ColumnInfo]: 包含字段信息的列表
        """
        query = """
        SELECT 
            COLUMN_NAME as column_name,
            DATA_TYPE as data_type,
            COLUMN_COMMENT as column_comment
        FROM 
            information_schema.columns
        WHERE 
            table_schema = %s
            AND table_name = %s
        ORDER BY 
            ordinal_position
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (self.connection_params['database'], table_name))
                    columns = cursor.fetchall()
                    return [
                        ColumnInfo(
                            name=column['column_name'],
                            data_type=column['data_type'],
                            comment=column['column_comment'] or ''
                        )
                        for column in columns
                    ]
        except Exception as e:
            logger.error(f"获取表结构失败: {str(e)}")
            raise

    def format_schema_for_llm(self, table_name: str) -> str:
        """
        将表结构信息格式化为适合大模型使用的字符串
        
        Args:
            table_name: 表名
            
        Returns:
            str: 格式化后的表结构信息
        """
        try:
            columns = self.get_table_schema(table_name)
            
            # 构建表结构描述
            schema_desc = [f"表 {table_name} 的结构如下:"]
            schema_desc.append("")
            schema_desc.append("| 字段名称 | 字段类型 | 字段说明 |")
            schema_desc.append("|----------|----------|----------|")
            
            for col in columns:
                comment = col.comment if col.comment else ""
                schema_desc.append(f"| {col.name} | {col.data_type} | {comment} |")
            
            return "\n".join(schema_desc)
            
        except Exception as e:
            logger.error(f"格式化表结构信息失败: {str(e)}")
            raise

def create_schema_manager(config: Dict[str, Any] = None) -> SchemaManager:
    """
    创建SchemaManager实例的工厂函数。优先使用环境变量中的配置，如果没有则使用传入的config。
    
    Args:
        config: 可选的数据库配置信息
        
    Returns:
        SchemaManager: 配置好的SchemaManager实例
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
        
    return SchemaManager(
        host=env_config['host'],
        port=env_config['port'],
        user=env_config['user'],
        password=env_config['password'],
        database=env_config['database']
    )
