import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    roc_auc_score,
    classification_report,
    confusion_matrix,
    mean_squared_error,
    r2_score,
)
from sklearn.linear_model import LinearRegression
from typing import List, Dict, Any, Tuple
import joblib
from datetime import datetime
import os
from abc import ABC, abstractmethod

from backend.data_processing.analysis.model_predictor import ModelPredictor


class BaseModel(ABC):
    def __init__(self, problem_type):
        self.problem_type = problem_type
        self.model = None
        self.preprocessor = None

    @abstractmethod
    def optimize(
        self, X_train, y_train, categorical_cols, numerical_cols, param_ranges, n_trials
    ):
        pass

    @abstractmethod
    def train(
        self,
        X_train,
        y_train,
        categorical_cols,
        numerical_cols,
        param_ranges=None,
        n_trials=100,
    ):
        pass

    def evaluate(self, X_test, y_test):
        return evaluate_model(self.model, X_test, y_test, self.problem_type)

    def get_feature_importance(self):
        return get_feature_importance(
            self.model.named_steps["classifier"],
            self.model.named_steps["preprocessor"],
        )


def prepare_data(
    df: pd.DataFrame,
    target_column: str,
    feature_columns: List[str],
    test_size: float = 0.3,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, List[str], List[str]]:
    X = df[feature_columns]
    y = df[target_column]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42
    )

    categorical_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()
    numerical_cols = X.select_dtypes(include=["int64", "float64"]).columns.tolist()

    return X_train, X_test, y_train, y_test, categorical_cols, numerical_cols


def create_preprocessor(
    categorical_cols: List[str], numerical_cols: List[str]
) -> ColumnTransformer:
    numeric_transformer = Pipeline(steps=[("scaler", StandardScaler())])

    categorical_transformer = Pipeline(
        steps=[("onehot", OneHotEncoder(handle_unknown="ignore", drop="if_binary"))]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numerical_cols),
            ("cat", categorical_transformer, categorical_cols),
        ]
    )

    return preprocessor


def evaluate_model(
    model: Any, X_test: pd.DataFrame, y_test: pd.Series, problem_type: str
) -> Dict[str, Any]:
    y_test_pred = model.predict(X_test)

    if problem_type == "classification":
        y_test_pred_proba = model.predict_proba(X_test)[:, 1]
        return {
            "test_roc_auc": roc_auc_score(y_test, y_test_pred_proba),
            "test_confusion_matrix": confusion_matrix(y_test, y_test_pred),
            "test_classification_report": classification_report(y_test, y_test_pred),
        }
    else:  # regression
        mse = mean_squared_error(y_test, y_test_pred)
        r2 = r2_score(y_test, y_test_pred)
        return {
            "test_mse": mse,
            "test_r2": r2,
            "y_test": y_test,
            "y_pred": y_test_pred,
        }


def get_feature_importance(model: Any, preprocessor: ColumnTransformer) -> pd.Series:
    feature_names = preprocessor.get_feature_names_out()
    if hasattr(model, "feature_importances_"):
        feature_importance = pd.Series(
            model.feature_importances_,
            index=feature_names,
        ).sort_values(ascending=False)
    elif hasattr(model, "coef_"):
        feature_importance = pd.Series(
            np.abs(model.coef_),
            index=feature_names,
        ).sort_values(ascending=False)
    else:
        raise ValueError("模型不支持特征重要性计算")
    return feature_importance


def train_model(
    df: pd.DataFrame,
    target_column: str,
    feature_columns: List[str],
    model_type: str,
    problem_type: str,
    test_size: float = 0.3,
    param_ranges: Dict[str, Any] = None,
    n_trials: int = 100,
    use_cv: bool = True,
) -> Dict[str, Any]:
    X_train, X_test, y_train, y_test, categorical_cols, numerical_cols = prepare_data(
        df, target_column, feature_columns, test_size
    )

    model_class = get_model_class(model_type)

    if model_type == "随机森林":
        param_ranges = (
            filter_valid_params(param_ranges, RANDOM_FOREST_PARAMS)
            if param_ranges
            else None
        )
    elif model_type == "决策树":
        param_ranges = (
            filter_valid_params(param_ranges, DECISION_TREE_PARAMS)
            if param_ranges
            else None
        )
    elif model_type == "XGBoost":
        param_ranges = (
            filter_valid_params(param_ranges, XGBOOST_PARAMS) if param_ranges else None
        )
    elif model_type == "线性回归":
        param_ranges = (
            filter_valid_params(param_ranges, LINEAR_REGRESSION_PARAMS)
            if param_ranges
            else None
        )

    model = model_class(problem_type)

    results = model.train(
        X_train, y_train, categorical_cols, numerical_cols, param_ranges, n_trials
    )
    test_metrics = model.evaluate(X_test, y_test)

    results.update(test_metrics)

    return results


def get_model_class(model_type: str):
    from backend.data_processing.analysis.random_forest_trainer import RandomForestModel
    from backend.data_processing.analysis.decision_tree_trainer import DecisionTreeModel
    from backend.data_processing.analysis.xgboost_trainer import XGBoostModel
    from backend.data_processing.analysis.linear_regression_trainer import (
        LinearRegressionModel,
    )

    model_classes = {
        "随机森林": RandomForestModel,
        "决策树": DecisionTreeModel,
        "XGBoost": XGBoostModel,
        "线性回归": LinearRegressionModel,
    }
    return model_classes.get(model_type)


def save_model(
    model: Any,
    model_type: str,
    problem_type: str,
    timestamp: datetime,
    save_path: str = "data/ml_models",
):
    problem_folder = (
        "classification" if problem_type == "classification" else "regression"
    )
    full_save_path = os.path.join(save_path, problem_folder)
    os.makedirs(full_save_path, exist_ok=True)

    file_name = (
        f"{model_type}_{problem_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}.joblib"
    )
    file_path = os.path.join(full_save_path, file_name)
    joblib.dump(model, file_path)
    return file_path


def add_model_record(
    model_records: pd.DataFrame,
    model_type: str,
    problem_type: str,
    model_results: Dict[str, Any],
) -> pd.DataFrame:
    new_record = {
        "模型ID": f"Model_{len(model_records) + 1}",
        "模型类型": model_type,
        "问题类型": "分类" if problem_type == "classification" else "回归",
        "训练时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "交叉验证分数": model_results["cv_mean_score"],
        "测试集分数": (
            model_results["test_roc_auc"]
            if problem_type == "classification"
            else model_results["test_mse"]
        ),
    }

    if "best_params" in model_results:
        new_record["参数"] = str(model_results["best_params"])
    elif model_type == "线性回归":
        new_record["参数"] = "N/A (线性回归无需参数优化)"
    else:
        new_record["参数"] = "未知"

    if "best_trial" in model_results:
        new_record["最佳轮次"] = model_results["best_trial"]
    else:
        new_record["最佳轮次"] = "N/A"

    return pd.concat([model_records, pd.DataFrame([new_record])], ignore_index=True)


def filter_valid_params(params, valid_params):
    return {k: v for k, v in params.items() if k in valid_params}


RANDOM_FOREST_PARAMS = [
    "n_estimators",
    "max_depth",
    "min_samples_split",
    "min_samples_leaf",
    "max_features",
]

DECISION_TREE_PARAMS = [
    "classifier__max_depth",
    "classifier__min_samples_split",
    "classifier__min_samples_leaf",
    "classifier__max_leaf_nodes",
]

XGBOOST_PARAMS = [
    "n_estimators",
    "max_depth",
    "learning_rate",
    "subsample",
    "colsample_bytree",
    "min_child_weight",
    "reg_alpha",
    "reg_lambda",
]

LINEAR_REGRESSION_PARAMS = []


def initialize_session_state():
    default_states = {
        "df": None,
        "model_results": None,
        "target_column": None,
        "feature_columns": None,
        "model_type": "随机森林",
        "problem_type": "classification",
        "rf_param_grid": {
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
                "问题类型",
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
        "do_model_interpretation": False,
    }

    return default_states
