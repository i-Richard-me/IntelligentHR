import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier
from typing import List, Dict, Any, Tuple
import joblib
from datetime import datetime
import os

from backend.data_processing.analysis.model_predictor import (
    ModelPredictor
)

def prepare_data(
        df: pd.DataFrame,
        target_column: str,
        feature_columns: List[str],
        test_size: float = 0.3,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, List[str], List[str]]:
    """
    准备模型训练和测试数据。

    Args:
        df: 输入数据框
        target_column: 目标变量的列名
        feature_columns: 特征列名列表
        test_size: 测试集占总数据的比例

    Returns:
        训练特征, 测试特征, 训练目标, 测试目标, 分类特征列表, 数值特征列表
    """
    X = df[feature_columns]
    y = df[target_column]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )

    categorical_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()
    numerical_cols = X.select_dtypes(include=["int64", "float64"]).columns.tolist()

    return X_train, X_test, y_train, y_test, categorical_cols, numerical_cols


def create_preprocessor(
        categorical_cols: List[str], numerical_cols: List[str]
) -> ColumnTransformer:
    """
    创建特征预处理器。

    Args:
        categorical_cols: 分类特征列名列表
        numerical_cols: 数值特征列名列表

    Returns:
        预处理器
    """
    numeric_transformer = Pipeline(steps=[("scaler", StandardScaler())])

    categorical_transformer = Pipeline(
        steps=[("onehot", OneHotEncoder(handle_unknown="ignore"))]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numerical_cols),
            ("cat", categorical_transformer, categorical_cols),
        ]
    )

    return preprocessor


def evaluate_model(
        model: Any, X_test: pd.DataFrame, y_test: pd.Series
) -> Dict[str, Any]:
    """
    评估模型性能。

    Args:
        model: 训练好的模型
        X_test: 测试特征
        y_test: 测试目标

    Returns:
        包含评估指标的字典
    """
    y_test_pred = model.predict(X_test)
    y_test_pred_proba = model.predict_proba(X_test)[:, 1]

    return {
        "test_roc_auc": roc_auc_score(y_test, y_test_pred_proba),
        "test_confusion_matrix": confusion_matrix(y_test, y_test_pred),
        "test_classification_report": classification_report(y_test, y_test_pred),
    }


def get_feature_importance(model: Any, preprocessor: ColumnTransformer) -> pd.Series:
    """
    获取特征重要性。

    Args:
        model: 训练好的模型
        preprocessor: 特征预处理器

    Returns:
        特征重要性系列
    """
    feature_names = preprocessor.get_feature_names_out()
    feature_importance = pd.Series(
        model.feature_importances_,
        index=feature_names,
    ).sort_values(ascending=False)
    return feature_importance


def train_model(
        df: pd.DataFrame,
        target_column: str,
        feature_columns: List[str],
        model_type: str,
        test_size: float = 0.3,
        param_ranges: Dict[str, Any] = None,
        n_trials: int = 100,
) -> Dict[str, Any]:
    """
    训练指定类型的模型并进行评估。

    Args:
        df: 输入数据框
        target_column: 目标变量的列名
        feature_columns: 特征列名列表
        model_type: 模型类型 ("随机森林", "决策树", "XGBoost")
        test_size: 测试集占总数据的比例
        param_ranges: 参数搜索范围，如果为None则使用默认值
        n_trials: Optuna优化的试验次数 (仅用于随机森林和XGBoost)

    Returns:
        包含模型、特征重要性、评估指标、最佳参数和最佳轮次的字典
    """
    X_train, X_test, y_train, y_test, categorical_cols, numerical_cols = prepare_data(
        df, target_column, feature_columns, test_size
    )

    if model_type == "随机森林":
        from backend.data_processing.analysis.random_forest_trainer import train_random_forest
        results = train_random_forest(
            df, target_column, feature_columns, test_size, param_ranges, n_trials
        )
    elif model_type == "决策树":
        from backend.data_processing.analysis.decision_tree_trainer import train_decision_tree
        results = train_decision_tree(
            df, target_column, feature_columns, test_size, param_ranges
        )
    elif model_type == "XGBoost":
        from backend.data_processing.analysis.xgboost_trainer import train_xgboost
        results = train_xgboost(
            df, target_column, feature_columns, test_size, param_ranges, n_trials
        )
    else:
        raise ValueError(f"不支持的模型类型: {model_type}")

    return results


def save_model(model: Any, model_id: str, model_type: str, timestamp: datetime, save_path: str = "data/ml_models"):
    """
    保存训练好的模型。

    Args:
        model: 训练好的模型对象
        model_id: 模型ID
        model_type: 模型类型
        timestamp: 训练时间戳
        save_path: 保存路径
    """
    os.makedirs(save_path, exist_ok=True)
    file_name = f"{model_type}_{model_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.joblib"
    file_path = os.path.join(save_path, file_name)
    joblib.dump(model, file_path)
    return file_path


def add_model_record(model_records: pd.DataFrame, model_type: str, model_results: Dict[str, Any]) -> pd.DataFrame:
    """
    添加新的模型记录。

    Args:
        model_records: 现有的模型记录DataFrame
        model_type: 模型类型
        model_results: 模型训练结果

    Returns:
        更新后的模型记录DataFrame
    """
    new_record = {
        "模型ID": f"Model_{len(model_records) + 1}",
        "模型类型": model_type,
        "训练时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "参数": str(model_results["best_params"]),
        "交叉验证分数": model_results["cv_mean_score"],
        "测试集分数": model_results["test_roc_auc"],
    }

    if "best_trial" in model_results:
        new_record["最佳轮次"] = model_results["best_trial"]

    return pd.concat([model_records, pd.DataFrame([new_record])], ignore_index=True)


def initialize_session_state():
    """
    初始化会话状态。
    """
    default_states = {
        "df": None,
        "model_results": None,
        "target_column": None,
        "feature_columns": None,
        "model_type": "随机森林",
        "param_ranges": {
            "n_estimators": (10, 200),
            "max_depth": (5, 30),
            "min_samples_split": (2, 20),
            "min_samples_leaf": (1, 20),
            "max_features": ["sqrt", "log2"],
        },
        "dt_param_grid": {
            "classifier__max_depth": [2, 4, 5, 6, 7, None],
            "classifier__min_samples_split": [2, 3, 4, 5, 8],
            "classifier__min_samples_leaf": [2, 5, 10, 15, 20, 25],
            "classifier__max_leaf_nodes": [10, 20, 25, 30, 35, 40, 45, None],
        },
        "xgb_param_ranges": {
            "n_estimators": (50, 500),
            "max_depth": (3, 10),
            "learning_rate": (0.01, 1.0),
            "subsample": (0.5, 1.0),
            "colsample_bytree": (0.5, 1.0),
            "min_child_weight": (1, 10),
            "reg_alpha": (0, 10),
            "reg_lambda": (0, 10),
        },
        "custom_param_ranges": None,
        "model_records": pd.DataFrame(
            columns=[
                "模型ID",
                "模型类型",
                "训练时间",
                "参数",
                "交叉验证分数",
                "测试集分数",
                "最佳轮次",
            ]
        ),
        "rf_n_trials": 100,
        "xgb_n_trials": 200,
        "predictor": ModelPredictor(),
        "uploaded_data": None,
        "predictions": None,
        "probabilities": None,
        "data_validated": False,
        "mode": "train",

    }

    return default_states
