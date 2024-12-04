from pathlib import Path
from omegaconf import OmegaConf
from dotenv import load_dotenv
import os

class Config:
    def __init__(self):
        self.env = os.getenv("APP_ENV", "development")
        root_dir = Path("")  # Set root directory to absolute path
        
        # 加载环境变量
        load_dotenv(root_dir / ".env")
        self.env_vars = OmegaConf.create(dict(os.environ))
        
        # 加载配置文件
        config_path = root_dir / "config" / f"{self.env}.yml"
        self.__dict__.update(OmegaConf.load(str(config_path)))

    @classmethod
    def get_config(cls) -> "Config":
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance

config = Config.get_config()