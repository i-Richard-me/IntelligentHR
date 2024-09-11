import os
import json
from typing import Dict, Optional, Any
import mysql.connector
from mysql.connector import Error
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库连接配置
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "resume_db"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
}


def get_db_connection():
    """
    获取数据库连接。

    Returns:
        mysql.connector.connection.MySQLConnection: MySQL数据库连接对象。
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        logger.error(f"Error connecting to MySQL Database: {e}")
        return None


def init_resume_upload_table():
    """
    初始化简历上传表。
    """
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS resume_uploads (
            id INT AUTO_INCREMENT PRIMARY KEY,
            resume_hash VARCHAR(32) UNIQUE NOT NULL,
            resume_type ENUM('pdf', 'url') NOT NULL,
            file_name VARCHAR(255),
            url TEXT,
            minio_path VARCHAR(255),
            raw_content LONGTEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        conn.commit()
        logger.info("Resume upload table initialized successfully.")
    except Error as e:
        logger.error(f"Error creating resume upload table: {e}")
    finally:
        cursor.close()
        conn.close()


def store_resume_record(
    resume_hash: str,
    resume_type: str,
    file_name: Optional[str],
    url: Optional[str],
    minio_path: Optional[str],
    raw_content: str,
):
    """
    存储简历记录到数据库。

    Args:
        resume_hash (str): 简历的哈希值。
        resume_type (str): 简历类型（'pdf' 或 'url'）。
        file_name (Optional[str]): PDF文件名（仅对PDF类型有效）。
        url (Optional[str]): 简历URL（仅对URL类型有效）。
        minio_path (Optional[str]): MinIO中的文件路径（仅对PDF类型有效）。
        raw_content (str): 简历的原始内容。
    """
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
        INSERT INTO resume_uploads (resume_hash, resume_type, file_name, url, minio_path, raw_content)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (resume_hash, resume_type, file_name, url, minio_path, raw_content),
        )
        conn.commit()
        logger.info(f"Resume record stored successfully. Hash: {resume_hash}")
    except Error as e:
        logger.error(f"Error storing resume record: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def get_resume_by_hash(resume_hash: str) -> Optional[Dict[str, Any]]:
    """
    根据哈希值检索简历记录。

    Args:
        resume_hash (str): 简历的哈希值。

    Returns:
        Optional[Dict[str, Any]]: 如果找到简历，返回包含简历信息的字典；否则返回 None。
    """
    conn = get_db_connection()
    if conn is None:
        return None

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM resume_uploads WHERE resume_hash = %s", (resume_hash,)
        )
        result = cursor.fetchone()
        return result
    except Error as e:
        logger.error(f"Error retrieving resume data: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


# 初始化数据库表
init_resume_upload_table()
