from typing import Any, Dict, List, Optional

import numpy as np
import shap
from lime.lime_tabular import LimeTabularExplainer
from sklearn.preprocessing import LabelEncoder

from config import settings


class ExplanationService:
    """Service for generating model explanations using SHAP and LIME."""

    def __init__(self):
        self.shap_explainer = None
        self.lime_explainer = None
        self.model = None
        self.label_encoder = None
        self.feature_names = None

    def initialize(
        self,
        model: Any,
        label_encoder: LabelEncoder,
        X_train: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ):
        """Initialize explainers with model and training data."""
        self.model = model
        self.label_encoder = label_encoder
        
        # Feature names (e.g., symptom IDs)
        if feature_names:
            self.feature_names = feature_names
        else:
            self.feature_names = [f"feature_{i}" for i in range(X_train.shape[1])]
        
        # Initialize LIME explainer for tabular data
        try:
            self.lime_explainer = LimeTabularExplainer(
                training_data=X_train,
                feature_names=self.feature_names,
                class_names=self.label_encoder.classes_,
                mode="classification",
                random_state=42,
                verbose=False,
            )
        except Exception as e:
            print(f"LIME initialization failed: {e}")
        
        # Initialize SHAP explainer for tree models
        try:
            if hasattr(model, "predict_proba"):
                # For sklearn models with TreeExplainer
                if hasattr(model, "estimators_"):
                    self.shap_explainer = shap.TreeExplainer(model)
            elif hasattr(model, "predict"):
                # For other models with KernelExplainer
                self.shap_explainer = shap.KernelExplainer(
                    model.predict_proba if hasattr(model, "predict_proba") else model.predict,
                    X_train[:min(100, len(X_train))],
                )
        except Exception as e:
            print(f"SHAP initialization failed: {e}")

    def explain_prediction(
        self,
        x_instance: np.ndarray,
        predicted_class: str,
        top_features: int = 5,
    ) -> Dict[str, Any]:
        """
        Generate explanations for a single prediction.
        
        Uses both LIME (local) and SHAP (global context).
        """
        explanation = {
            "predicted_class": predicted_class,
            "lime_explanation": None,
            "shap_explanation": None,
        }
        
        # LIME explanation
        if self.lime_explainer and settings.LIME_ENABLED:
            try:
                lime_exp = self.lime_explainer.explain_instance(
                    x_instance,
                    self.model.predict_proba if hasattr(self.model, "predict_proba") else self.model.predict,
                    num_features=top_features,
                    num_samples=settings.LIME_NUM_SAMPLES,
                )
                
                # Extract feature contributions
                lime_features = lime_exp.as_list()
                explanation["lime_explanation"] = {
                    "features": [
                        {
                            "name": name,
                            "contribution": float(weight),
                        }
                        for name, weight in lime_features
                    ],
                    "predicted_proba": float(lime_exp.predict_proba[
                        list(self.label_encoder.classes_).index(predicted_class)
                    ]),
                }
            except Exception as e:
                print(f"LIME explanation error: {e}")
        
        # SHAP explanation
        if self.shap_explainer:
            try:
                shap_values = self.shap_explainer.shap_values(x_instance.reshape(1, -1))
                
                # Handle different SHAP output formats
                if isinstance(shap_values, list):
                    # Multi-class: get values for predicted class
                    class_idx = list(self.label_encoder.classes_).index(predicted_class)
                    class_shap = shap_values[class_idx]
                else:
                    class_shap = shap_values
                
                # Get top contributing features
                feature_importance = np.abs(class_shap[0])
                top_indices = np.argsort(feature_importance)[-top_features:][::-1]
                
                explanation["shap_explanation"] = {
                    "features": [
                        {
                            "name": self.feature_names[idx],
                            "shap_value": float(class_shap[0, idx]),
                            "importance": float(feature_importance[idx]),
                        }
                        for idx in top_indices
                    ],
                }
            except Exception as e:
                print(f"SHAP explanation error: {e}")
        
        return explanation

    def get_feature_importance(self, top_features: int = 10) -> Dict[str, float]:
        """Get global feature importance from SHAP."""
        if not self.shap_explainer or not self.model:
            return {}
        
        try:
            # Use model's built-in feature importance if available
            if hasattr(self.model, "feature_importances_"):
                importances = self.model.feature_importances_
                indices = np.argsort(importances)[-top_features:][::-1]
                return {
                    self.feature_names[i]: float(importances[i])
                    for i in indices
                }
        except Exception as e:
            print(f"Feature importance error: {e}")
        
        return {}

    def compare_predictions(
        self,
        predictions: List[Dict],
    ) -> Dict[str, Any]:
        """
        Compare multiple predictions and their explanations.
        Useful for understanding model behavior across different inputs.
        """
        return {
            "count": len(predictions),
            "predictions": predictions,
        }


# Global explanation service instance
explanation_service = ExplanationService()
