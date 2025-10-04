#!/usr/bin/env python3
"""
RAG System Initialization Script

Sets up vector store, feedback database, and downloads required models.
"""

import os
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.append('backend')

from app.rag.vector_store import TestCaseVectorStore
from app.rag.feedback_db import FeedbackDatabase
from app.agents.planner_rag import RAGPlanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_rag_system():
    """Initialize RAG system components"""
    logger.info("🚀 Initializing RAG system...")
    
    # Create data directories
    os.makedirs("backend/rag_data", exist_ok=True)
    os.makedirs("backend/rag_data/chroma", exist_ok=True)
    
    # Initialize vector store (downloads models)
    logger.info("📚 Initializing vector store...")
    vector_store = TestCaseVectorStore()
    
    # Initialize feedback database
    logger.info("💾 Initializing feedback database...")
    feedback_db = FeedbackDatabase()
    
    # Initialize RAG planner (tests LLM connection)
    logger.info("🤖 Initializing RAG planner...")
    rag_planner = RAGPlanner(vector_store, feedback_db)
    
    # Add sample data for testing
    logger.info("📝 Adding sample test cases...")
    sample_testcase = {
        "id": "tc-sample-001",
        "title": "Sample Math Test",
        "description": "Test basic addition",
        "tags": ["math", "basic"],
        "steps": [
            {"id": 1, "action": "navigate", "value": "https://play.ezygamers.com/"},
            {"id": 2, "action": "type", "selector": "input", "value": "5"},
            {"id": 3, "action": "click", "selector": "button[value='+']"},
            {"id": 4, "action": "type", "selector": "input", "value": "3"},
            {"id": 5, "action": "assert_text", "selector": ".result", "value": "8"}
        ]
    }
    
    sample_result = {
        "verdict": "PASS",
        "reproducible": True,
        "timestamp": "2024-01-01T00:00:00Z",
        "notes": "Sample successful test"
    }
    
    vector_store.add_test_case(sample_testcase, sample_result)
    feedback_db.add_test_outcome("sample-run", sample_testcase, sample_result)
    
    # Get statistics
    stats = vector_store.get_statistics()
    metrics = feedback_db.get_performance_metrics(days=30)
    
    logger.info("✅ RAG system initialized successfully!")
    logger.info(f"📊 Vector store: {stats['total_cases']} cases")
    logger.info(f"📈 Database: {metrics['total_tests']} test records")
    
    return True

if __name__ == "__main__":
    try:
        init_rag_system()
        print("\n🎉 RAG system ready! You can now:")
        print("1. Start backend: uvicorn app.main:app --reload --port 8000")
        print("2. Start frontend: npm start")
        print("3. Open http://localhost:3000")
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        sys.exit(1)
