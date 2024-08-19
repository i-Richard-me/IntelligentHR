import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_validate
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
import optuna
from typing import List, Dict, Tuple, Union


def encode_categorical_variables(
    df: pd.DataFrame, categorical_columns: List[str]
) -> pd.DataFrame:
    """
    对数据框中的分类变量进行编码。

    Args:
        df (pd.DataFrame): 输入的数据框。
        categorical_columns (List[str]): 需要编码的分类变量列名列表。

    Returns:
        pd.DataFrame: 包含编码后分类变量的数据框。
    """
    encoder = LabelEncoder()
    for column in categorical_columns:
        df[f"{column}_encoded"] = encoder.fit_transform(df[column].astype(str))
    return df


def optimize_random_forest(
    X: pd.DataFrame, y: pd.Series, param_ranges: Dict
) -> Tuple[RandomForestClassifier, Dict, float]:
    """
    使用Optuna优化随机森林模型的超参数。

    Args:
        X (pd.DataFrame): 特征数据框。
        y (pd.Series): 目标变量系列。
        param_ranges (Dict): 超参数搜索范围的字典。

    Returns:
        Tuple[RandomForestClassifier, Dict, float]: 优化后的随机森林模型、最佳参数字典和最佳交叉验证分数。
    """
    numerical_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = X.select_dtypes(exclude=[np.number]).columns.tolist()

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numerical_cols),
            ("cat", LabelEncoder(), categorical_cols),
        ]
    )

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int(
                "n_estimators",
                param_ranges["n_estimators"][0],
                param_ranges["n_estimators"][1],
            ),
            "max_depth": trial.suggest_int(
                "max_depth", param_ranges["max_depth"][0], param_ranges["max_depth"][1]
            ),
            "min_samples_split": trial.suggest_int(
                "min_samples_split",
                param_ranges["min_samples_split"][0],
                param_ranges["min_samples_split"][1],
            ),
            "min_samples_leaf": trial.suggest_int(
                "min_samples_leaf",
                param_ranges["min_samples_leaf"][0],
                param_ranges["min_samples_leaf"][1],
            ),
            "max_features": trial.suggest_categorical(
                "max_features", param_ranges["max_features"]
            ),
        }

        rf = RandomForestClassifier(**params, random_state=42)

        pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", rf)])

        scores = cross_validate(pipeline, X, y, cv=5, scoring="roc_auc", n_jobs=-1)
        return np.mean(scores["test_score"])

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=100, n_jobs=-1)

    best_params = study.best_params
    best_model = RandomForestClassifier(**best_params, random_state=42)
    best_score = study.best_value

    return best_model, best_params, best_score


def train_and_evaluate_model(
    df: pd.DataFrame,
    target_column: str,
    feature_columns: List[str],
    test_size: float = 0.3,
    param_ranges: Dict = None,
) -> Dict[str, Union[RandomForestClassifier, pd.Series, float, Dict, str]]:
    """
    训练随机森林模型并进行评估。

    Args:
        df (pd.DataFrame): 输入数据框。
        target_column (str): 目标变量的列名。
        feature_columns (List[str]): 特征列名列表。
        test_size (float): 测试集占总数据的比例，默认为0.3。
        param_ranges (Dict): 参数搜索范围，如果为None则使用默认值。

    Returns:
        Dict: 包含模型、特征重要性、评估指标和最佳参数的字典。
    """
    # 准备数据
    X = df[feature_columns]
    y = df[target_column]

    # 分割数据集
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=test_size, random_state=42
    )

    # 如果没有提供参数范围，使用默认值
    if param_ranges is None:
        param_ranges = {
            "n_estimators": (10, 200),
            "max_depth": (5, 30),
            "min_samples_split": (2, 20),
            "min_samples_leaf": (1, 20),
            "max_features": ["sqrt", "log2"],
        }

    # 优化模型
    best_model, best_params, cv_mean_score = optimize_random_forest(
        X_train, y_train, param_ranges
    )

    # 在验证集上评估模型
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), X.select_dtypes(include=[np.number]).columns),
            ("cat", LabelEncoder(), X.select_dtypes(exclude=[np.number]).columns),
        ]
    )
    pipeline = Pipeline(
        steps=[("preprocessor", preprocessor), ("classifier", best_model)]
    )
    pipeline.fit(X_train, y_train)

    y_val_pred = pipeline.predict(X_val)
    y_val_pred_proba = pipeline.predict_proba(X_val)[:, 1]

    val_roc_auc = roc_auc_score(y_val, y_val_pred_proba)
    val_confusion_matrix = confusion_matrix(y_val, y_val_pred)
    val_classification_report = classification_report(y_val, y_val_pred)

    # 计算特征重要性
    feature_importance = pd.Series(
        best_model.feature_importances_, index=X.columns
    ).sort_values(ascending=False)

    return {
        "model": pipeline,
        "feature_importance": feature_importance,
        "cv_mean_score": cv_mean_score,
        "val_roc_auc": val_roc_auc,
        "val_confusion_matrix": val_confusion_matrix,
        "val_classification_report": val_classification_report,
        "best_params": best_params,
    }
