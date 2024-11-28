from pathlib import Path
import pandas as pd
from typing import Any, Dict, List
from fastapi import UploadFile
import uuid
import logging

logger = logging.getLogger(__name__)

class FileService:
    """文件服务类
    
    处理文件的上传、读取和保存操作
    """

    def __init__(self, base_dir: str = "data"):
        """初始化文件服务
        
        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
        self.upload_dir = self.base_dir / "uploads"
        self.results_dir = self.base_dir / "results"
        
        # 确保目录存在
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"文件服务初始化完成: 上传目录={self.upload_dir}, 结果目录={self.results_dir}")

    async def save_upload_file(self, file: UploadFile) -> str:
        """保存上传的文件
        
        Args:
            file: 上传的文件对象

        Returns:
            str: 保存后的文件路径
        """
        file_id = str(uuid.uuid4())
        extension = Path(file.filename).suffix
        file_path = self.upload_dir / f"{file_id}{extension}"
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        logger.info(f"文件已保存: {file_path}")
        return str(file_path)

    def read_csv_file(self, file_path: str) -> pd.DataFrame:
        """读取CSV文件
        
        Args:
            file_path: CSV文件路径

        Returns:
            pd.DataFrame: 读取的数据框
        """
        try:
            df = pd.read_csv(file_path)
            logger.info(f"成功读取CSV文件: {file_path}, 行数={len(df)}")
            return df
        except Exception as e:
            logger.error(f"读取CSV文件失败: {file_path}, 错误={str(e)}")
            raise

    def save_results_to_csv(self, results: List[Dict[str, Any]], task_id: str) -> str:
        """保存分析结果到CSV文件
        
        Args:
            results: 包含原始数据和分析结果的字典列表
            task_id: 任务ID

        Returns:
            str: 结果文件路径
        """
        result_path = self.results_dir / f"{task_id}_results.csv"
        df = pd.DataFrame(results)
        # 确保结果文件使用 UTF-8 编码
        df.to_csv(result_path, index=False, encoding='utf-8')
        logger.info(f"分析结果已保存: {result_path}, 行数={len(df)}")
        return str(result_path)