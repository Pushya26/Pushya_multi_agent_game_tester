import requests
import json
import re
from app.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

def generate_candidates(url: str, goal: str):
    if not OPENROUTER_API_KEY:
        print("No OpenRouter API key found, using fallback")
        return _get_fallback_candidates(url)
    
    try:
        prompt = f"""You are a test designer for web games. Given URL: {url} and goals: {goal}, 
generate exactly 20 test cases as JSON array. Each test case should have:
{{'id':'tc-001','title':'Test Title','description':'Description','tags':['edge-case'],'steps':[{{'id':1,'action':'navigate','value':'{url}'}},{{'id':2,'action':'click','selector':'button'}}]}}

Actions: navigate, click, type, wait_for, assert_text, assert_element, evaluate_js
Focus on math operations, edge cases (zero, negative, large numbers), UI interactions.
Return ONLY valid JSON array, no other text."""
        
        # Use LangChain wrapper (ChatOpenAI works with OpenRouter by pointing base_url)
        llm = ChatOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,  # crucial for OpenRouter
            model="mistralai/mistral-7b-instruct:free",
            temperature=0.2,
            request_timeout=15,
        )

        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content

        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            candidates = json.loads(json_match.group(0))
            print(f"Generated {len(candidates)} AI test cases via LangChain")
            return candidates[:20]

        print("LangChain generation failed, using fallback")
        return _get_fallback_candidates(url)

    except Exception as e:
        print(f"LangChain error: {e}, using fallback")
        return _get_fallback_candidates(url)

def _get_fallback_candidates(url: str):
    return [
        {
            "id": f"tc-{i:03d}",
            "title": f"Math Game Test {i}",
            "description": f"Test case {i} for math operations",
            "tags": ["basic" if i <= 10 else "edge-case"],
            "steps": [
                {"id": 1, "action": "navigate", "value": url},
                {"id": 2, "action": "wait_for", "selector": "body"},
                {"id": 3, "action": "click", "selector": "button, input[type=button], .btn"},
                {"id": 4, "action": "type", "selector": "input[type=number], input[type=text]", "value": str(i * 10)},
                {"id": 5, "action": "assert_element", "selector": "body"}
            ]
        }
        for i in range(1, 21)
    ]