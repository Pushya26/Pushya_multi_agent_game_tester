# direct api call
# def rank_candidates(candidates):
#     scored = []
    
#     for c in candidates:
#         score = 0
        
#         # Score by number of steps
#         score += len(c.get('steps', []))
        
#         # Bonus for edge case tags
#         tags = c.get('tags', [])
#         if any('edge' in t.lower() for t in tags):
#             score += 10
        
#         # Bonus for assertion steps
#         steps = c.get('steps', [])
#         assertion_count = sum(1 for s in steps if s.get('action', '').startswith('assert'))
#         score += assertion_count * 3
        
#         # Bonus for input/type actions (more interactive)
#         type_count = sum(1 for s in steps if s.get('action') == 'type')
#         score += type_count * 2
        
#         # Bonus for unique selectors
#         selectors = set(s.get('selector', '') for s in steps if s.get('selector'))
#         score += len(selectors)
        
#         scored.append((score, c))
    
#     # Sort by score descending and return top 10
#     scored.sort(reverse=True, key=lambda x: x[0])
#     top10 = [c for _, c in scored[:10]]
    
#     return top10

# using langchain
# ranker.py (LangChain)
# ...existing code...
import math
from typing import List, Dict


def score_candidate(candidate: Dict) -> float:
    """
    Simple heuristic scorer:
    - more steps -> higher coverage
    - penalize very short titles
    - small random-ish deterministic factor based on id
    """
    steps = candidate.get("steps", [])
    title = candidate.get("title", "")
    base = len(steps) * 1.0
    title_bonus = max(0, (len(title) - 8) / 20)
    # deterministic tie-breaker
    tie = sum(ord(c) for c in candidate.get("id", "")) % 10 / 100.0
    return base + title_bonus + tie


def rank_candidates(candidates: List[Dict], top_n: int = 10) -> List[Dict]:
    """
    Score and return the top_n candidates (highest score first).
    """
    scored = []
    for c in candidates:
        s = score_candidate(c)
        scored.append((s, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [c for _, c in scored[:top_n]]
    return top
# ...existing code...