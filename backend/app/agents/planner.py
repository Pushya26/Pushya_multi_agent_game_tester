# ...existing code...
import json
import logging
from typing import List, Dict
from uuid import uuid4

from app.config import OPENROUTER_API_KEY

logger = logging.getLogger(__name__)


def _fallback_generate(n: int) -> List[Dict]:
    candidates = []
    for i in range(n):
        tc_id = f"tc-{i+1:03}"
        title = f"PUZZLE_FLOW_{i+1:03}"
        steps = [
            "open https://play.ezygamers.com/",
            "wait for game canvas to load",
            "attempt a valid move (choose first visible number/cell)",
            "observe score / next state"
        ]
        # add some diversity
        if i % 3 == 0:
            steps.append("try invalid input or rapid clicks")
        if i % 5 == 0:
            steps.append("resize or change viewport")
        candidates.append({"id": tc_id, "title": title, "steps": steps})
    return candidates


def generate_plans(n: int = 30) -> List[Dict]:
    """
    Generate n candidate test cases. Try to use LangChain if available and configured,
    otherwise fall back to deterministic generation.
    Each candidate: { id, title, steps: [str] }
    """
    # Try to use langchain if present & API key configured
    try:
        from langchain import LLMChain, PromptTemplate
        from langchain.chat_models import ChatOpenAI

        if not OPENROUTER_API_KEY:
            raise RuntimeError("No OPENROUTER_API_KEY set")

        prompt = PromptTemplate(
            input_variables=["count"],
            template=(
                "You are a test planner. Produce exactly {count} compact end-to-end test cases "
                "for the math puzzle web game at https://play.ezygamers.com/. "
                "Return a JSON array where each element is an object with keys: id, title, steps (array of short instructions). "
                "Keep steps simple and actionable for UI automation."
            ),
        )
        llm = ChatOpenAI(temperature=0.7, model="gpt-4o-mini")  # model name may vary; fallbacks exist
        chain = LLMChain(llm=llm, prompt=prompt)
        raw = chain.run({"count": str(n)})
        try:
            candidates = json.loads(raw)
            # basic validation
            if not isinstance(candidates, list) or len(candidates) < n:
                logger.warning("LangChain returned unexpected format or fewer items; falling back")
                return _fallback_generate(n)
            # ensure ids
            for i, c in enumerate(candidates):
                c.setdefault("id", f"tc-{i+1:03}")
            return candidates
        except Exception:
            logger.exception("Failed to parse LLM output as JSON; falling back")
            return _fallback_generate(n)
    except Exception:
        # any failure -> fallback
        logger.exception("LangChain not available or failed; using fallback generator")
        return _fallback_generate(n)
# ...existing code...

def generate_candidates(url: str, goal: str) -> List[Dict]:
    """
    Generate test case candidates for the given URL and goal
    
    Args:
        url: Target URL to test
        goal: Testing goal/objective
        
    Returns:
        List of test case candidates
    """
    # Use the existing generate_plans function
    candidates = generate_plans(n=20)
    
    # Add URL and goal context to each candidate
    for candidate in candidates:
        # Update steps to include the specific URL
        if candidate.get('steps'):
            candidate['steps'] = [step.replace('https://play.ezygamers.com/', url) for step in candidate['steps']]
        
        # Add description based on goal
        candidate['description'] = f"Test case for {goal} on {url}"
        candidate['tags'] = ['automated', 'web-game']
    
    return candidates
