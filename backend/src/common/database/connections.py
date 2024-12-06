"""数据库连接管理模块

提供统一的数据库连接管理，支持多数据库配置和连接
"""
from typing import Dict, Optional, Any
from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
import logging
from pathlib import Path
import urllib.parse

logger = logging.getLogger(__name__)

class DatabaseConnections:
    """数据库连接管理类 - 单例模式"""
    _instance = None
    _engines: Dict[str, Engine] = {}
    _session_makers: Dict[str, sessionmaker] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnections, cls).__new__(cls)
        return cls._instance

    def init_engine(
        self,
        db_name: str,
        db_url: str,
        ensure_path: bool = True,
        **kwargs: Any
    ) -> Engine:
        """初始化数据库引擎

        Args:
            db_name: 数据库标识名
            db_url: 数据库连接URL
            ensure_path: 是否确保SQLite数据库路径存在
            **kwargs: 传递给create_engine的其他参数

        Returns:
            SQLAlchemy引擎实例

        Raises:
            ValueError: 当数据库配置无效时抛出
        """
        try:
            if db_name in self._engines:
                logger.warning(f"数据库引擎 {db_name} 已存在，将被覆盖")

            # 解析数据库URL以确定数据库类型
            parsed_url = urllib.parse.urlparse(db_url)
            db_type = parsed_url.scheme.split('+')[0]

            # 数据库特定的配置
            connect_args = kwargs.pop('connect_args', {})
            if db_type == 'sqlite':
                if ensure_path:
                    db_path = db_url.replace('sqlite:///', '')
                    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                connect_args.setdefault('check_same_thread', False)
            elif db_type == 'mysql':
                # MySQL特定配置
                connect_args.setdefault('charset', 'utf8mb4')
                kwargs.setdefault('pool_recycle', 3600)
                kwargs.setdefault('pool_pre_ping', True)  # 启用连接池预检

            # 创建引擎
            engine = create_engine(
                db_url,
                connect_args=connect_args,
                **kwargs
            )

            # 为MySQL添加事件监听器
            if db_type == 'mysql':
                @event.listens_for(engine, 'engine_connect')
                def receive_engine_connect(connection):
                    if not connection.closed:
                        with connection.begin():
                            connection.execute(text("SET NAMES utf8mb4"))
                            connection.execute(text("SET CHARACTER SET utf8mb4"))
                            connection.execute(text("SET character_set_connection=utf8mb4"))

            self._engines[db_name] = engine
            self._session_makers[db_name] = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine
            )

            logger.info(f"数据库引擎 {db_name} ({db_type}) 初始化成功")
            return engine

        except Exception as e:
            logger.error(f"初始化数据库引擎 {db_name} 失败: {str(e)}")
            raise

    def get_engine(self, db_name: str) -> Optional[Engine]:
        """获取数据库引擎"""
        return self._engines.get(db_name)

    def get_session(self, db_name: str) -> Optional[Session]:
        """获取数据库会话"""
        session_maker = self._session_makers.get(db_name)
        return session_maker() if session_maker else None

    def dispose_engine(self, db_name: str) -> None:
        """释放数据库引擎资源"""
        if db_name in self._engines:
            self._engines[db_name].dispose()
            del self._engines[db_name]
            del self._session_makers[db_name]
            logger.info(f"数据库引擎 {db_name} 已释放")

    def dispose_all(self) -> None:
        """释放所有数据库引擎资源"""
        for db_name in list(self._engines.keys()):
            self.dispose_engine(db_name)

# 全局数据库连接管理器实例
db_connections = DatabaseConnections()