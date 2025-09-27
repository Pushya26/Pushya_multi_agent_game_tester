# langchain
import hashlib
import os
import requests
import json
import re
from typing import Dict, Any, Tuple
from app.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL

def hash_file(path: str) -> str:
    """Generate hash of file content"""
    try:
        with open(path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return ""

def analyze_results(primary: Dict[int, Dict], rerun: Dict[int, Dict]) -> Tuple[bool, Dict]:
    """Compare primary and rerun results for reproducibility"""
    diffs = {}
    reproducible = True

    for step_id, primary_artifact in primary.items():
        rerun_artifact = rerun.get(step_id, {})

        primary_result = primary_artifact.get("step_result")
        rerun_result = rerun_artifact.get("step_result")

        primary_screenshot = primary_artifact.get("screenshot_path")
        rerun_screenshot = rerun_artifact.get("screenshot_path")

        screenshot_match = True
        if primary_screenshot and rerun_screenshot:
            primary_hash = hash_file(primary_screenshot)
            rerun_hash = hash_file(rerun_screenshot)
            screenshot_match = primary_hash == rerun_hash

        step_reproducible = (primary_result == rerun_result) and screenshot_match

        diffs[step_id] = {
            "primary_result": primary_result,
            "rerun_result": rerun_result,
            "screenshot_match": screenshot_match,
            "step_reproducible": step_reproducible
        }

        if not step_reproducible:
            reproducible = False

    return reproducible, diffs

def generate_triage_notes(results: list) -> Dict[str, str]:
    """Generate AI-powered triage notes for failed tests"""
    notes = {}
    failed_results = [r for r in results if r['verdict'] == 'FAIL']
    
    if not failed_results:
        return notes
    
    # Try AI-powered analysis first
    if OPENROUTER_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            from langchain.prompts import ChatPromptTemplate
            
            llm = ChatOpenAI(
                api_key=OPENROUTER_API_KEY,
                base_url=OPENROUTER_BASE_URL,
                model="mistralai/mistral-7b-instruct:free",
                temperature=0.1
            )
            
            failure_summary = "\n".join([
                f"Test {r['testcase_id']}: {r.get('notes', 'No details')}"
                for r in failed_results[:5]
            ])
            
            prompt = ChatPromptTemplate.from_template("""
            Analyze test failures and provide triage notes in JSON format:
            {{"testcase_id": "Root cause and fix suggestion"}}
            
            Failures: {failures}
            """)
            
            chain = prompt | llm
            resp = chain.invoke({"failures": failure_summary})
            
            try:
                # Extract JSON from response
                content = resp.content
                # Try to find JSON in the response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    for k, v in parsed.items():
                        notes[k] = str(v)
                    return notes
            except Exception as e:
                print(f"AI triage parsing failed: {e}")
        except Exception as e:
            print(f"AI triage analysis failed: {e}")
    
    # Fallback to basic analysis
    for result in failed_results:
        testcase_id = result['testcase_id']
        notes[testcase_id] = "Test failed - needs investigation"
    
    return notes

