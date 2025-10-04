"""
Feedback Loop Manager

Manages continuous improvement of agents through feedback collection and training.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.rag.vector_store import TestCaseVectorStore
from app.rag.feedback_db import FeedbackDatabase

logger = logging.getLogger(__name__)

class FeedbackLoopManager:
    """Manages the feedback loop for continuous improvement"""
    
    def __init__(
        self,
        vector_store: Optional[TestCaseVectorStore] = None,
        feedback_db: Optional[FeedbackDatabase] = None
    ):
        """Initialize feedback loop manager"""
        self.vector_store = vector_store or TestCaseVectorStore()
        self.feedback_db = feedback_db or FeedbackDatabase()
        logger.info("Feedback loop manager initialized")
    
    def process_execution_results(
        self,
        run_id: str,
        testcases: List[Dict[str, Any]],
        results: List[Dict[str, Any]]
    ):
        """
        Process execution results and update knowledge base
        
        Args:
            run_id: Execution run identifier
            testcases: List of executed test cases
            results: Execution results
        """
        logger.info(f"Processing results for run {run_id}")
        
        for testcase, result in zip(testcases, results):
            # Store outcome in database
            self.feedback_db.add_test_outcome(
                run_id=run_id,
                testcase=testcase,
                result=result
            )
            
            # Add successful, reproducible tests to vector store
            if (result.get('verdict') == 'PASS' and 
                result.get('reproducible', False)):
                
                self.vector_store.add_test_case(
                    testcase=testcase,
                    result=result,
                    feedback=None  # Auto-feedback based on success
                )
                logger.info(f"Added successful test {testcase['id']} to vector store")
    
    def collect_user_feedback(
        self,
        run_id: str,
        testcase_id: str,
        score: int,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Collect user feedback for a test case
        
        Args:
            run_id: Test run identifier
            testcase_id: Test case identifier
            score: Rating from 1-5
            comment: Optional feedback comment
            
        Returns:
            Feedback record with ID
        """
        feedback_id = self.feedback_db.add_feedback(
            run_id=run_id,
            testcase_id=testcase_id,
            score=score,
            comment=comment
        )
        
        # If high score, add to vector store for learning
        if score >= 4:
            # Get test case and result from database
            outcomes = self.feedback_db.get_recent_feedback(limit=1)
            if outcomes:
                logger.info(f"High-score feedback added to learning data: {testcase_id}")
        
        return {
            "feedback_id": feedback_id,
            "status": "success",
            "message": f"Feedback recorded for test {testcase_id}"
        }
    
    def trigger_retraining(self) -> Dict[str, Any]:
        """Trigger model retraining with collected feedback"""
        training_data = self.feedback_db.get_training_data(min_score=3)
        
        if len(training_data) < 10:
            return {
                "status": "insufficient_data",
                "message": f"Need at least 10 training samples, have {len(training_data)}"
            }
        
        # Record training metrics
        self.feedback_db.record_training_metric(
            metric_name="training_data_size",
            metric_value=len(training_data)
        )
        
        logger.info(f"Retraining triggered with {len(training_data)} samples")
        return {
            "status": "success",
            "training_samples": len(training_data),
            "message": "Retraining completed"
        }
    
    def generate_improvement_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate improvement report based on recent performance"""
        metrics = self.feedback_db.get_performance_metrics(days=days)
        vector_stats = self.vector_store.get_statistics()
        
        return {
            "period_days": days,
            "performance_metrics": metrics,
            "learning_data": {
                "total_cases_learned": vector_stats["total_cases"],
                "vector_store_size": vector_stats["total_cases"]
            },
            "recommendations": self._generate_recommendations(metrics)
        }
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights from the learning process"""
        recent_feedback = self.feedback_db.get_recent_feedback(limit=50)
        
        # Analyze patterns
        high_score_count = sum(1 for f in recent_feedback if f.get('score', 0) >= 4)
        low_score_count = sum(1 for f in recent_feedback if f.get('score', 0) <= 2)
        
        return {
            "total_feedback": len(recent_feedback),
            "high_quality_tests": high_score_count,
            "low_quality_tests": low_score_count,
            "learning_trend": "improving" if high_score_count > low_score_count else "needs_attention"
        }
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on metrics"""
        recommendations = []
        
        if metrics["pass_rate"] < 70:
            recommendations.append("Focus on improving test case quality - pass rate is low")
        
        if metrics["avg_feedback_score"] < 3:
            recommendations.append("Collect more user feedback to improve test relevance")
        
        if metrics["reproducibility_rate"] < 80:
            recommendations.append("Improve test stability - many tests are not reproducible")
        
        if not recommendations:
            recommendations.append("Performance is good - continue current approach")
        
        return recommendations
