"""
RAG-Enhanced Planner Agent

Uses historical test data and feedback to generate improved test cases.
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate

from app.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from app.rag.vector_store import TestCaseVectorStore
from app.rag.feedback_db import FeedbackDatabase

logger = logging.getLogger(__name__)

class RAGPlanner:
    """RAG-enhanced test case planner"""
    
    def __init__(
        self, 
        vector_store: Optional[TestCaseVectorStore] = None,
        feedback_db: Optional[FeedbackDatabase] = None
    ):
        """
        Initialize RAG planner
        
        Args:
            vector_store: Vector store for similarity search
            feedback_db: Feedback database for metrics
        """
        self.vector_store = vector_store or TestCaseVectorStore()
        self.feedback_db = feedback_db or FeedbackDatabase()
        
        # Initialize LLM
        if OPENROUTER_API_KEY:
            self.llm = ChatOpenAI(
                api_key=OPENROUTER_API_KEY,
                base_url=OPENROUTER_BASE_URL,
                model="mistralai/mistral-7b-instruct:free",
                temperature=0.3,
                request_timeout=20
            )
        else:
            self.llm = None
            logger.warning("No API key - using fallback generation")
    
    def generate_candidates(
        self, 
        url: str, 
        goal: str,
        use_rag: bool = True,
        count: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Generate test case candidates using RAG
        
        Args:
            url: Target URL
            goal: Testing goal
            use_rag: Whether to use RAG enhancement
            count: Number of candidates to generate
            
        Returns:
            List of test case candidates
        """
        if not self.llm:
            logger.info("No LLM available, using fallback")
            return self._get_fallback_candidates(url, count)
        
        try:
            # Retrieve similar successful test cases
            context = ""
            if use_rag:
                context = self._retrieve_context(goal, url)
            
            # Get performance metrics
            metrics = self.feedback_db.get_performance_metrics(days=30)
            
            # Build enhanced prompt
            prompt = self._build_prompt(url, goal, context, metrics, count)
            
            # Generate candidates
            messages = [
                SystemMessage(content="You are an expert test case designer."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            candidates = self._parse_response(response.content)
            
            logger.info(f"Generated {len(candidates)} candidates using RAG")
            return candidates[:count]
            
        except Exception as e:
            logger.error(f"RAG generation failed: {e}")
            return self._get_fallback_candidates(url, count)
    
    def _retrieve_context(self, goal: str, url: str, k: int = 5) -> str:
        """Retrieve relevant context from vector store"""
        query = f"{goal} for {url}"
        similar_cases = self.vector_store.search_similar_cases(
            query=query,
            k=k,
            filter_successful=True
        )
        
        if not similar_cases:
            return "No historical data available."
        
        context_parts = ["Previously successful test patterns:\n"]
        for i, case in enumerate(similar_cases, 1):
            metadata = case['metadata']
            context_parts.append(
                f"{i}. {metadata.get('title', 'Unknown')} "
                f"(Score: {metadata.get('feedback_score', 0)}/5, "
                f"Steps: {metadata.get('step_count', 0)})"
            )
            # Add snippet of content
            content = case['content'][:200]
            context_parts.append(f"   {content}...\n")
        
        return "\n".join(context_parts)
    
    def _build_prompt(
        self, 
        url: str, 
        goal: str, 
        context: str,
        metrics: Dict[str, Any],
        count: int
    ) -> str:
        """Build enhanced prompt with RAG context"""
        prompt = f"""You are designing test cases for a web game at {url}.

GOAL: {goal}

CURRENT PERFORMANCE METRICS:
- Pass Rate: {metrics['pass_rate']}%
- Avg Feedback Score: {metrics['avg_feedback_score']}/5
- Reproducibility: {metrics['reproducibility_rate']}%

{context}

Based on the above context and metrics, generate {count} diverse test cases as a JSON array.
Each test case MUST have this exact structure:
{{
  "id": "tc-001",
  "title": "Test Title",
  "description": "Detailed description",
  "tags": ["edge-case", "math-operation"],
  "steps": [
    {{"id": 1, "action": "navigate", "value": "{url}"}},
    {{"id": 2, "action": "click", "selector": "button"}},
    {{"id": 3, "action": "type", "selector": "input", "value": "123"}},
    {{"id": 4, "action": "assert_text", "selector": ".result", "value": "123"}}
  ]
}}

Available actions:
- navigate: Go to URL
- click: Click element
- type: Enter text
- wait_for: Wait for element
- assert_text: Verify text content
- assert_element: Verify element exists
- evaluate_js: Run JavaScript

IMPORTANT GUIDELINES:
1. Focus on areas where current metrics show weakness
2. Learn from successful patterns in the context above
3. Include edge cases: zero, negative numbers, very large numbers, special characters
4. Test math operations: addition, subtraction, multiplication, division
5. Test UI interactions: button clicks, input validation, result display
6. Make tests reproducible and specific
7. Each test should have 4-8 steps
8. Include assertions to verify behavior

Return ONLY the JSON array, no other text."""
        
        return prompt
    
    def _parse_response(self, content: str) -> List[Dict[str, Any]]:
        """Parse LLM response to extract test cases"""
        # Try to find JSON array
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            try:
                candidates = json.loads(json_match.group(0))
                # Validate structure
                validated = []
                for c in candidates:
                    if self._validate_candidate(c):
                        validated.append(c)
                return validated
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {e}")
        
        return []
    
    def _validate_candidate(self, candidate: Dict[str, Any]) -> bool:
        """Validate test case structure"""
        required_fields = ['id', 'title', 'steps']
        if not all(field in candidate for field in required_fields):
            return False
        
        if not isinstance(candidate['steps'], list) or len(candidate['steps']) == 0:
            return False
        
        for step in candidate['steps']:
            if 'id' not in step or 'action' not in step:
                return False
        
        return True
    
    def _get_fallback_candidates(self, url: str, count: int = 20) -> List[Dict[str, Any]]:
        """Generate fallback candidates without LLM"""
        logger.info("Generating fallback test candidates")
        
        test_values = [0, 1, -1, 10, 100, 999, -50, 0.5, 1.5]
        operations = ['+', '-', '*', '/']
        
        candidates = []
        for i in range(1, count + 1):
            val1 = test_values[i % len(test_values)]
            val2 = test_values[(i + 1) % len(test_values)]
            op = operations[i % len(operations)]
            
            candidates.append({
                "id": f"tc-{i:03d}",
                "title": f"Math Test: {val1} {op} {val2}",
                "description": f"Test {op} operation with values {val1} and {val2}",
                "tags": ["math-operation", "edge-case" if val1 == 0 or val2 == 0 else "basic"],
                "steps": [
                    {"id": 1, "action": "navigate", "value": url},
                    {"id": 2, "action": "wait_for", "selector": "body"},
                    {"id": 3, "action": "type", "selector": "input[type=number]:first", "value": str(val1)},
                    {"id": 4, "action": "click", "selector": f"button[value='{op}']"},
                    {"id": 5, "action": "type", "selector": "input[type=number]:last", "value": str(val2)},
                    {"id": 6, "action": "click", "selector": "button.calculate"},
                    {"id": 7, "action": "assert_element", "selector": ".result"}
                ]
            })
        
        return candidates