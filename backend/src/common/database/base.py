from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 确保data/db目录存在
os.makedirs("data/db", exist_ok=True)

# 数据库URL
SQLALCHEMY_DATABASE_URL = "sqlite:///data/db/tasks.db"

# 创建引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite特定设置
)

# 创建SessionLocal类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建Base类
Base = declarative_base()

# 获取数据库会话的依赖函数
def get_db():
    """获取数据库会话
    
    Yields:
        SQLAlchemy会话对象
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()