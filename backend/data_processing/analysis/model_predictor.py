import os
import pandas as pd
import numpy as np
import joblib
from typing import Dict, Any, List, Tuple
from sklearn.base import BaseEstimator
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer


class ModelPredictor:
    def __init__(self, models_dir: str = "data/ml_models"):
        self.models_dir = models_dir
        self.model: Pipeline = None
        self.model_info: Dict[str, Any] = {}
        self.original_features: List[str] = []
        self.preprocessor: ColumnTransformer = None

    def load_model(self, model_filename: str) -> None:
        model_path = os.path.join(self.models_dir, model_filename)
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件 {model_path} 不存在。")

        loaded_model = joblib.load(model_path)
        if not isinstance(loaded_model, Pipeline):
            raise ValueError("加载的模型不是 Pipeline 类型。")

        self.model = loaded_model
        self.preprocessor = self.model.named_steps["preprocessor"]
        self.original_features = self.get_original_feature_names()
        self.model_info = {
            "filename": model_filename,
            "type": type(self.model.named_steps["classifier"]).__name__,
            "features": self.original_features,
        }

    def get_original_feature_names(self) -> List[str]:
        if not isinstance(self.preprocessor, ColumnTransformer):
            raise ValueError("预处理器不是 ColumnTransformer 类型。")

        original_features = []
        for name, transformer, columns in self.preprocessor.transformers_:
            if name != "remainder":
                if isinstance(columns, str):
                    original_features.append(columns)
                else:
                    original_features.extend(columns)
        return original_features

    def preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        expected_features = set(self.original_features)
        input_features = set(data.columns)

        if not expected_features.issubset(input_features):
            missing_features = expected_features - input_features
            raise ValueError(f"输入数据缺少以下特征：{missing_features}")

        return data[self.original_features]

    def predict(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        if self.model is None:
            raise ValueError("模型未加载，请先调用 load_model 方法。")

        preprocessed_data = self.preprocess_data(data)
        predictions = self.model.predict(preprocessed_data)
        probabilities = self.model.predict_proba(preprocessed_data)

        return predictions, probabilities

    def get_model_info(self) -> Dict[str, Any]:
        return self.model_info


def list_available_models(models_dir: str = "data/ml_models") -> List[str]:
    return [f for f in os.listdir(models_dir) if f.endswith(".joblib")]
