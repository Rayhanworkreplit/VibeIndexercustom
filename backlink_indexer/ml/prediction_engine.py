"""
Machine Learning optimization for backlink indexing
Predicts optimal method combinations and resource allocation
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
import joblib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from ..models import IndexingMethod, IndexingResult, MLPrediction, MethodPerformance
from ..monitoring.success_tracker import SuccessTracker


class IndexingPredictor:
    """
    ML-powered prediction engine for optimal indexing method selection
    Uses historical data to predict success probability and resource allocation
    """
    
    def __init__(self, success_tracker: SuccessTracker):
        self.success_tracker = success_tracker
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_columns = []
        self.logger = logging.getLogger(__name__)
        
        # Model configuration
        self.model_config = {
            'n_estimators': 100,
            'max_depth': 10,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'random_state': 42
        }
        
    def extract_features(self, url: str, historical_data: pd.DataFrame = None) -> Dict[str, Any]:
        """Extract features from URL for ML prediction"""
        from urllib.parse import urlparse
        import tldextract
        
        parsed_url = urlparse(url)
        extracted = tldextract.extract(url)
        
        features = {
            # URL characteristics
            'url_length': len(url),
            'path_length': len(parsed_url.path),
            'subdomain_count': len(extracted.subdomain.split('.')) if extracted.subdomain else 0,
            'path_depth': len([p for p in parsed_url.path.split('/') if p]),
            'has_query_params': 1 if parsed_url.query else 0,
            'has_fragment': 1 if parsed_url.fragment else 0,
            'is_https': 1 if parsed_url.scheme == 'https' else 0,
            
            # Domain characteristics
            'domain_length': len(extracted.domain) if extracted.domain else 0,
            'tld_length': len(extracted.suffix) if extracted.suffix else 0,
            'is_com_tld': 1 if extracted.suffix == 'com' else 0,
            'is_org_tld': 1 if extracted.suffix == 'org' else 0,
            'has_numbers_in_domain': 1 if any(c.isdigit() for c in extracted.domain) else 0,
            'has_hyphens_in_domain': 1 if '-' in extracted.domain else 0,
            
            # Content-based features (if available)
            'estimated_content_length': self._estimate_content_length(url),
            'likely_content_type': self._predict_content_type(url),
            
            # Time-based features
            'hour_of_day': datetime.now().hour,
            'day_of_week': datetime.now().weekday(),
            'is_weekend': 1 if datetime.now().weekday() >= 5 else 0,
        }
        
        # Historical performance features
        if historical_data is not None:
            domain_history = historical_data[
                historical_data['url'].str.contains(extracted.domain, na=False)
            ]
            
            if not domain_history.empty:
                features.update({
                    'domain_success_rate': domain_history['success'].mean(),
                    'domain_avg_response_time': domain_history['response_time'].mean(),
                    'domain_total_attempts': len(domain_history),
                })
            else:
                features.update({
                    'domain_success_rate': 0.5,  # Neutral default
                    'domain_avg_response_time': 5.0,  # Average default
                    'domain_total_attempts': 0,
                })
        
        return features
    
    def _estimate_content_length(self, url: str) -> int:
        """Estimate content length based on URL patterns"""
        # Simple heuristics - in production, you might cache actual measurements
        if '/blog/' in url or '/article/' in url:
            return 2000  # Blog posts tend to be longer
        elif '/product/' in url:
            return 1000  # Product pages are medium
        elif '/category/' in url:
            return 500   # Category pages are shorter
        else:
            return 1500  # Default estimate
    
    def _predict_content_type(self, url: str) -> str:
        """Predict content type from URL patterns"""
        url_lower = url.lower()
        
        if any(keyword in url_lower for keyword in ['blog', 'article', 'post', 'news']):
            return 'article'
        elif any(keyword in url_lower for keyword in ['product', 'item', 'shop']):
            return 'product'
        elif any(keyword in url_lower for keyword in ['category', 'tag', 'archive']):
            return 'listing'
        elif any(keyword in url_lower for keyword in ['about', 'contact', 'help']):
            return 'page'
        else:
            return 'other'
    
    def prepare_training_data(self, days_back: int = 90) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare training data from historical indexing results"""
        
        # Get historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        historical_results = self.success_tracker.get_historical_data(start_date, end_date)
        
        if not historical_results:
            raise ValueError("No historical data available for training")
        
        # Convert to DataFrame
        df = pd.DataFrame([
            {
                'url': result.url,
                'method': result.method.value,
                'success': result.success,
                'response_time': result.response_time,
                'timestamp': result.timestamp,
                'status_code': result.status_code or 200,
            }
            for result in historical_results
        ])
        
        # Extract features for each URL
        feature_rows = []
        for _, row in df.iterrows():
            features = self.extract_features(row['url'], df)
            features['method'] = row['method']
            features['success'] = row['success']
            features['response_time'] = row['response_time']
            feature_rows.append(features)
        
        feature_df = pd.DataFrame(feature_rows)
        
        # Prepare features and targets
        X = feature_df.drop(['success', 'response_time'], axis=1)
        y = feature_df['success']
        
        # Handle categorical variables
        categorical_columns = ['likely_content_type', 'method']
        for col in categorical_columns:
            if col in X.columns:
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                X[col] = self.label_encoders[col].fit_transform(X[col].astype(str))
        
        # Store feature columns for later use
        self.feature_columns = X.columns.tolist()
        
        return X, y
    
    def train_model(self, days_back: int = 90) -> Dict[str, Any]:
        """Train the ML model on historical data"""
        
        self.logger.info(f"Training model on {days_back} days of historical data...")
        
        try:
            # Prepare data
            X, y = self.prepare_training_data(days_back)
            
            if len(X) < 50:  # Minimum required samples
                self.logger.warning(f"Limited training data ({len(X)} samples). Model may not be reliable.")
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y if y.sum() > 0 else None
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model = RandomForestClassifier(**self.model_config)
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = self.model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Cross-validation
            cv_scores = cross_val_score(self.model, X_train_scaled, y_train, cv=5)
            
            # Feature importance
            feature_importance = dict(zip(
                self.feature_columns,
                self.model.feature_importances_
            ))
            
            # Sort features by importance
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            
            training_results = {
                'accuracy': accuracy,
                'cv_mean_score': cv_scores.mean(),
                'cv_std_score': cv_scores.std(),
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'feature_importance': sorted_features[:10],  # Top 10 features
                'model_version': datetime.now().strftime("%Y%m%d_%H%M%S")
            }
            
            self.logger.info(f"Model trained successfully. Accuracy: {accuracy:.3f}")
            
            # Save model
            self._save_model()
            
            return training_results
            
        except Exception as e:
            self.logger.error(f"Error training model: {str(e)}")
            raise
    
    def predict_method_success(self, url: str, method: IndexingMethod) -> Tuple[float, Dict[str, Any]]:
        """Predict success probability for a specific URL and method combination"""
        
        if not self.model:
            self.logger.warning("Model not trained. Using heuristic predictions.")
            return self._heuristic_prediction(url, method)
        
        try:
            # Extract features
            features = self.extract_features(url)
            features['method'] = method.value
            
            # Convert to DataFrame
            feature_df = pd.DataFrame([features])
            
            # Handle categorical variables
            for col, encoder in self.label_encoders.items():
                if col in feature_df.columns:
                    try:
                        feature_df[col] = encoder.transform(feature_df[col].astype(str))
                    except ValueError:
                        # Handle unseen categories
                        feature_df[col] = 0
            
            # Ensure all required columns are present
            for col in self.feature_columns:
                if col not in feature_df.columns:
                    feature_df[col] = 0
            
            # Reorder columns to match training data
            feature_df = feature_df[self.feature_columns]
            
            # Scale features
            features_scaled = self.scaler.transform(feature_df)
            
            # Predict probability
            probability = self.model.predict_proba(features_scaled)[0][1]  # Probability of success
            
            # Get feature contributions (approximation)
            feature_contributions = {}
            if hasattr(self.model, 'feature_importances_'):
                for i, col in enumerate(self.feature_columns):
                    contribution = self.model.feature_importances_[i] * features_scaled[0][i]
                    feature_contributions[col] = contribution
            
            prediction_info = {
                'probability': probability,
                'confidence': min(1.0, probability * 2) if probability > 0.5 else min(1.0, (1 - probability) * 2),
                'feature_contributions': feature_contributions,
                'model_version': getattr(self, 'model_version', 'unknown')
            }
            
            return probability, prediction_info
            
        except Exception as e:
            self.logger.error(f"Error predicting success for {url} with {method}: {str(e)}")
            return self._heuristic_prediction(url, method)
    
    def _heuristic_prediction(self, url: str, method: IndexingMethod) -> Tuple[float, Dict[str, Any]]:
        """Fallback heuristic prediction when ML model is not available"""
        
        # Base success rates by method (from industry knowledge)
        base_rates = {
            IndexingMethod.SOCIAL_BOOKMARKING: 0.85,
            IndexingMethod.RSS_DISTRIBUTION: 0.90,
            IndexingMethod.WEB2_POSTING: 0.75,
            IndexingMethod.FORUM_COMMENTING: 0.65,
            IndexingMethod.DIRECTORY_SUBMISSION: 0.70,
            IndexingMethod.SOCIAL_SIGNALS: 0.80
        }
        
        base_probability = base_rates.get(method, 0.75)
        
        # Adjust based on URL characteristics
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        
        # HTTPS boost
        if parsed_url.scheme == 'https':
            base_probability += 0.05
        
        # Domain quality indicators
        if any(term in url.lower() for term in ['blog', 'article', 'news']):
            base_probability += 0.03  # Content-rich pages index better
        
        # Path complexity penalty
        if len(parsed_url.path.split('/')) > 6:
            base_probability -= 0.02  # Very deep paths are harder to index
        
        # Ensure probability is within bounds
        probability = max(0.1, min(0.95, base_probability))
        
        prediction_info = {
            'probability': probability,
            'confidence': 0.6,  # Lower confidence for heuristic
            'method': 'heuristic',
            'base_rate': base_rates.get(method, 0.75)
        }
        
        return probability, prediction_info
    
    def optimize_method_combination(self, url: str, available_methods: List[IndexingMethod] = None,
                                  budget_constraint: float = None) -> List[Tuple[IndexingMethod, float]]:
        """Optimize method combination for maximum success probability"""
        
        if available_methods is None:
            available_methods = list(IndexingMethod)
        
        method_predictions = []
        
        # Get predictions for each method
        for method in available_methods:
            probability, info = self.predict_method_success(url, method)
            
            # Calculate cost-effectiveness (if budget constraint is provided)
            cost = self._get_method_cost(method)
            effectiveness = probability / cost if budget_constraint and cost > 0 else probability
            
            method_predictions.append((method, probability, effectiveness))
        
        # Sort by effectiveness (or probability if no budget constraint)
        sort_key = lambda x: x[2] if budget_constraint else x[1]
        method_predictions.sort(key=sort_key, reverse=True)
        
        # Select methods within budget or top N methods
        selected_methods = []
        total_cost = 0
        
        for method, probability, effectiveness in method_predictions:
            cost = self._get_method_cost(method)
            
            if budget_constraint:
                if total_cost + cost <= budget_constraint:
                    selected_methods.append((method, probability))
                    total_cost += cost
            else:
                # Select top 3 methods by default
                if len(selected_methods) < 3:
                    selected_methods.append((method, probability))
        
        return selected_methods
    
    def _get_method_cost(self, method: IndexingMethod) -> float:
        """Get estimated resource cost for each method"""
        # Relative costs (time/resource units)
        costs = {
            IndexingMethod.RSS_DISTRIBUTION: 1.0,      # Fastest
            IndexingMethod.SOCIAL_BOOKMARKING: 2.0,    # Moderate
            IndexingMethod.SOCIAL_SIGNALS: 2.5,        # Moderate
            IndexingMethod.WEB2_POSTING: 4.0,          # Slower
            IndexingMethod.DIRECTORY_SUBMISSION: 3.0,   # Moderate
            IndexingMethod.FORUM_COMMENTING: 5.0       # Slowest (requires content analysis)
        }
        
        return costs.get(method, 3.0)
    
    def create_ml_prediction(self, url: str, methods: List[IndexingMethod] = None) -> MLPrediction:
        """Create a complete ML prediction object"""
        
        if methods is None:
            methods = list(IndexingMethod)
        
        confidence_scores = {}
        predicted_methods = []
        
        for method in methods:
            probability, info = self.predict_method_success(url, method)
            confidence_scores[method] = probability
            
            # Include methods with >70% predicted success
            if probability > 0.7:
                predicted_methods.append(method)
        
        # If no methods meet threshold, include top 2
        if not predicted_methods:
            sorted_methods = sorted(confidence_scores.items(), key=lambda x: x[1], reverse=True)
            predicted_methods = [method for method, _ in sorted_methods[:2]]
        
        model_version = getattr(self, 'model_version', 'unknown')
        
        return MLPrediction(
            url=url,
            predicted_methods=predicted_methods,
            confidence_scores=confidence_scores,
            model_version=model_version
        )
    
    def _save_model(self):
        """Save the trained model and preprocessing objects"""
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'feature_columns': self.feature_columns,
            'model_version': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'config': self.model_config
        }
        
        joblib.dump(model_data, 'backlink_indexer_model.pkl')
        self.logger.info("Model saved successfully")
    
    def load_model(self, model_path: str = 'backlink_indexer_model.pkl') -> bool:
        """Load a previously trained model"""
        try:
            model_data = joblib.load(model_path)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.label_encoders = model_data['label_encoders']
            self.feature_columns = model_data['feature_columns']
            self.model_version = model_data.get('model_version', 'unknown')
            
            self.logger.info(f"Model loaded successfully (version: {self.model_version})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading model: {str(e)}")
            return False
    
    def get_model_performance_summary(self) -> Dict[str, Any]:
        """Get summary of model performance and statistics"""
        
        if not self.model:
            return {'status': 'not_trained'}
        
        # Get recent performance data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        recent_results = self.success_tracker.get_historical_data(start_date, end_date)
        
        summary = {
            'model_version': getattr(self, 'model_version', 'unknown'),
            'feature_count': len(self.feature_columns),
            'recent_predictions': len(recent_results),
            'status': 'active'
        }
        
        if hasattr(self.model, 'feature_importances_'):
            # Top feature importances
            feature_importance = dict(zip(self.feature_columns, self.model.feature_importances_))
            top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
            summary['top_features'] = top_features
        
        return summary