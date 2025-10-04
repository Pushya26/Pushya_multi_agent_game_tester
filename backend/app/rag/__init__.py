"""
RAG (Retrieval-Augmented Generation) Package

This package provides RAG capabilities for the multi-agent game tester:
- Vector storage for test case learning
- Feedback database for continuous improvement  
- Feedback loop management for agent training
"""

from .vector_store import TestCaseVectorStore
from .feedback_db import FeedbackDatabase
from .feedback_loop import FeedbackLoopManager

__all__ = [
    'TestCaseVectorStore',
    'FeedbackDatabase', 
    'FeedbackLoopManager'
]

__version__ = '1.0.0'
