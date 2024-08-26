import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from typing import List, Dict, Any, Tuple
import logging

from backend.data_processing.analysis.model_utils import (
    BaseModel,
    create_preprocessor,
    evaluate_model,
    get_feature_importance,
)

class LinearRegressionModel(BaseModel):
    def __init__(self, problem_type):
        super().__init__(problem_type)
        self.logger = logging.getLogger(__name__)

    def optimize(self, X_train, y_train, categorical_cols, numerical_cols, param_ranges, n_trials):
        # 线性回归不需要参数优化，直接返回None
        return None, None, None, None

    def train(self, X_train, y_train, categorical_cols, numerical_cols, param_ranges=None, n_trials=None):
        self.logger.info("Starting Linear Regression training")
        
        preprocessor = create_preprocessor(categorical_cols, numerical_cols)
        model = LinearRegression()
        self.model = Pipeline(steps=[("preprocessor", preprocessor), ("regressor", model)])

        # 在全部训练数据上拟合模型
        self.model.fit(X_train, y_train)

        # 计算训练集 MSE 和 R²
        y_train_pred = self.model.predict(X_train)
        train_mse = np.mean((y_train - y_train_pred)**2)
        train_r2 = self.model.score(X_train, y_train)

        self.logger.info(f"Training MSE: {train_mse}, R²: {train_r2}")

        results = {
            "model": self.model,
            "feature_importance": self.get_feature_importance(),
            "train_mse": train_mse,
            "train_r2": train_r2,
        }

        # 添加系数和截距
        linear_model = self.model.named_steps['regressor']
        results["coefficients"] = pd.Series(
            linear_model.coef_, 
            index=self.model.named_steps['preprocessor'].get_feature_names_out()
        )
        results["intercept"] = linear_model.intercept_

        # 为了保持与其他模型一致的接口，我们将 train_mse 也赋值给 cv_mean_score
        results["cv_mean_score"] = train_mse

        return results

    def evaluate(self, X_test, y_test):
        self.logger.info("Starting model evaluation")
        return evaluate_model(self.model, X_test, y_test, self.problem_type)

    def get_feature_importance(self):
        # 对于线性回归，我们可以使用系数的绝对值作为特征重要性
        linear_model = self.model.named_steps['regressor']
        feature_names = self.model.named_steps['preprocessor'].get_feature_names_out()
        importance = np.abs(linear_model.coef_)
        return pd.Series(importance, index=feature_names).sort_values(ascending=False)