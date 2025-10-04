"""
Feedback Database Manager

Stores user feedback, test outcomes, and training data for continuous improvement.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class FeedbackDatabase:
    """SQLite database for storing feedback and training data"""
    
    def __init__(self, db_path: str = "rag_data/feedback.db"):
        """Initialize feedback database"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info(f"Feedback database initialized at {self.db_path}")
    
    def _create_tables(self):
        """Create database schema"""
        cursor = self.conn.cursor()
        
        # Feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                testcase_id TEXT NOT NULL,
                score INTEGER CHECK(score >= 1 AND score <= 5),
                comment TEXT,
                feedback_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Test outcomes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                testcase_id TEXT NOT NULL,
                verdict TEXT NOT NULL,
                reproducible BOOLEAN,
                execution_time_ms INTEGER,
                step_count INTEGER,
                testcase_json TEXT,
                result_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Training metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                epoch INTEGER,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Agent performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                pass_rate REAL,
                avg_feedback_score REAL,
                total_tests INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
    
    def add_feedback(
        self, 
        run_id: str, 
        testcase_id: str, 
        score: int,
        comment: Optional[str] = None,
        feedback_type: str = "manual"
    ) -> int:
        """
        Add user feedback for a test case
        
        Args:
            run_id: Test run identifier
            testcase_id: Test case identifier
            score: Rating from 1-5
            comment: Optional feedback comment
            feedback_type: Type of feedback (manual, automated, etc.)
            
        Returns:
            Feedback ID
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO feedback (run_id, testcase_id, score, comment, feedback_type)
            VALUES (?, ?, ?, ?, ?)
        """, (run_id, testcase_id, score, comment, feedback_type))
        self.conn.commit()
        
        feedback_id = cursor.lastrowid
        logger.info(f"Added feedback {feedback_id} for test {testcase_id}")
        return feedback_id
    
    def add_test_outcome(
        self,
        run_id: str,
        testcase: Dict[str, Any],
        result: Dict[str, Any]
    ):
        """Store test execution outcome"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO test_outcomes (
                run_id, testcase_id, verdict, reproducible, 
                step_count, testcase_json, result_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            testcase.get('id', 'unknown'),
            result.get('verdict', 'UNKNOWN'),
            result.get('reproducible', False),
            len(testcase.get('steps', [])),
            json.dumps(testcase),
            json.dumps(result)
        ))
        self.conn.commit()
    
    def get_feedback_for_testcase(self, testcase_id: str) -> List[Dict[str, Any]]:
        """Get all feedback for a specific test case"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM feedback 
            WHERE testcase_id = ? 
            ORDER BY created_at DESC
        """, (testcase_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_feedback(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent feedback entries"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT f.*, t.verdict, t.reproducible
            FROM feedback f
            LEFT JOIN test_outcomes t ON f.testcase_id = t.testcase_id
            ORDER BY f.created_at DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_performance_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get agent performance metrics"""
        cursor = self.conn.cursor()
        
        # Overall pass rate
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN verdict = 'PASS' THEN 1 ELSE 0 END) as passed
            FROM test_outcomes
            WHERE created_at >= datetime('now', '-' || ? || ' days')
        """, (days,))
        row = cursor.fetchone()
        total = row['total']
        passed = row['passed']
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        # Average feedback score
        cursor.execute("""
            SELECT AVG(score) as avg_score, COUNT(*) as feedback_count
            FROM feedback
            WHERE created_at >= datetime('now', '-' || ? || ' days')
        """, (days,))
        row = cursor.fetchone()
        avg_score = row['avg_score'] or 0
        feedback_count = row['feedback_count']
        
        # Reproducibility rate
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN reproducible = 1 THEN 1 ELSE 0 END) as reproducible
            FROM test_outcomes
            WHERE created_at >= datetime('now', '-' || ? || ' days')
        """, (days,))
        row = cursor.fetchone()
        total_tests = row['total']
        reproducible_tests = row['reproducible']
        reproducibility_rate = (reproducible_tests / total_tests * 100) if total_tests > 0 else 0
        
        return {
            "pass_rate": round(pass_rate, 2),
            "avg_feedback_score": round(avg_score, 2),
            "feedback_count": feedback_count,
            "reproducibility_rate": round(reproducibility_rate, 2),
            "total_tests": total,
            "period_days": days
        }
    
    def get_training_data(self, min_score: int = 3) -> List[Dict[str, Any]]:
        """
        Get high-quality test cases for training
        
        Args:
            min_score: Minimum feedback score to include
            
        Returns:
            List of test cases with positive outcomes
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT t.testcase_json, t.result_json, f.score
            FROM test_outcomes t
            INNER JOIN feedback f ON t.testcase_id = f.testcase_id
            WHERE f.score >= ? AND t.verdict = 'PASS'
            ORDER BY f.score DESC, t.created_at DESC
        """, (min_score,))
        
        training_data = []
        for row in cursor.fetchall():
            training_data.append({
                "testcase": json.loads(row['testcase_json']),
                "result": json.loads(row['result_json']),
                "score": row['score']
            })
        
        return training_data
    
    def record_training_metric(
        self, 
        metric_name: str, 
        metric_value: float,
        epoch: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record training metrics"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO training_metrics (metric_name, metric_value, epoch, metadata)
            VALUES (?, ?, ?, ?)
        """, (
            metric_name, 
            metric_value, 
            epoch,
            json.dumps(metadata) if metadata else None
        ))
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        self.conn.close()