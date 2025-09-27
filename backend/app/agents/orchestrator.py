import asyncio
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from app.config import MAX_PARALLELISM
from .analyzer import analyze_results

logger = logging.getLogger(__name__)

# Mock executor for POC (since Playwright has subprocess issues on Windows + Python 3.13)
async def run_testcase_mock(testcase: Dict[str, Any], artifacts_dir: str) -> Dict[int, Dict[str, Any]]:
    """Mock executor that simulates test execution"""
    import random
    os.makedirs(artifacts_dir, exist_ok=True)
    
    artifacts = {}
    for step in testcase.get('steps', []):
        sid = step['id']
        await asyncio.sleep(random.uniform(0.1, 0.3))  # Simulate work
        
        # 80% success rate
        if random.random() < 0.8:
            artifacts[sid] = {
                'screenshot_path': f"{artifacts_dir}/step{sid}.png",
                'dom_snapshot': f"<html><body>Mock DOM step {sid}</body></html>",
                'console_logs': [f"info: Executed {step.get('action', 'unknown')}"],
                'step_result': 'ok'
            }
        else:
            artifacts[sid] = {
                'step_result': 'error',
                'error': f"Mock error in step {sid}",
                'console_logs': [f"error: Failed step {sid}"]
            }
            break
    
    return artifacts

async def orchestrate(testcases: List[Dict[str, Any]], base_artifacts_dir: str) -> List[Dict[str, Any]]:
    """Orchestrate multiple testcases with reproducibility checks"""
    semaphore = asyncio.Semaphore(MAX_PARALLELISM)
    results = []

    async def run_with_semaphore(tc: Dict[str, Any]) -> Dict[str, Any]:
        async with semaphore:
            artifacts_dir = os.path.join(base_artifacts_dir, tc['id'])
            
            # Run test twice for reproducibility
            primary_artifacts = await run_testcase_mock(tc, f"{artifacts_dir}/run1")
            rerun_artifacts = await run_testcase_mock(tc, f"{artifacts_dir}/run2")
            
            reproducible, diffs = analyze_results(primary_artifacts, rerun_artifacts)
            
            # Determine verdict
            verdict = "PASS"
            for artifact in primary_artifacts.values():
                if artifact.get("step_result") in ["assertion_failed", "error"]:
                    verdict = "FAIL"
                    break
            
            return {
                "testcase_id": tc["id"],
                "verdict": verdict,
                "artifacts": primary_artifacts,
                "reruns": 2,
                "reproducible": reproducible,
                "notes": f"Test completed with verdict: {verdict}"
            }

    # Run all testcases concurrently
    tasks = [asyncio.create_task(run_with_semaphore(tc)) for tc in testcases]
    for task in asyncio.as_completed(tasks):
        results.append(await task)

    return results
