# mock executer:
# import asyncio
# import os
# import random
# from typing import Dict, Any

# async def run_testcase(testcase: Dict[str, Any], artifacts_dir: str) -> Dict[int, Dict[str, Any]]:
#     """Mock executor that simulates test execution without Playwright"""
#     os.makedirs(artifacts_dir, exist_ok=True)
    
#     artifacts = {}
    
#     # Simulate test execution with random delays
#     for step in testcase.get('steps', []):
#         sid = step['id']
        
#         # Simulate processing time
#         await asyncio.sleep(random.uniform(0.1, 0.5))
        
#         action = step.get('action', '')
#         selector = step.get('selector', '')
#         value = step.get('value', '')
        
#         # Simulate random test outcomes (mostly pass, some fail)
#         success_rate = 0.8  # 80% success rate
#         is_success = random.random() < success_rate
        
#         if is_success:
#             artifacts[sid] = {
#                 'screenshot_path': f"{artifacts_dir}/{testcase['id']}_step{sid}.png",
#                 'dom_snapshot': f"<html><body>Mock DOM for step {sid}</body></html>",
#                 'console_logs': [f"info: Executed {action} on {selector}"],
#                 'step_result': 'ok'
#             }
#         else:
#             # Simulate failure
#             error_type = 'assertion_failed' if action.startswith('assert') else 'error'
#             artifacts[sid] = {
#                 'step_result': 'error' if action.startswith('assert') else 'assertion_failed',
#                 'error': f"Mock error: Failed to {action} on {selector}",
#                 'console_logs': [f"error: Failed to execute {action}"]
#             }
#             break  # Stop on first failure
    
#     return artifacts


# playwright executer
# ...existing code...
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict
from uuid import uuid4

from app.agents.executor import run_test_case_async

logger = logging.getLogger(__name__)

ARTIFACTS_ROOT = Path(__file__).parents[2].joinpath("artifacts")


async def _run_worker(semaphore: asyncio.Semaphore, run_id: str, tc: Dict, out_root: Path):
    async with semaphore:
        return await run_test_case_async(run_id, tc, out_root)


def start_execution(test_cases: List[Dict], concurrency: int = 3) -> str:
    """
    Start execution of test_cases concurrently (POC). Returns run_id immediately
    and blocks until execution completes (simple POC). Writes report JSON into artifacts/{run_id}/report.json
    """
    run_id = uuid4().hex
    out_root = ARTIFACTS_ROOT / run_id
    out_root.mkdir(parents=True, exist_ok=True)

    async def _execute_all():
        semaphore = asyncio.Semaphore(concurrency)
        tasks = [asyncio.create_task(_run_worker(semaphore, run_id, tc, out_root)) for tc in test_cases]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # normalize results
        normalized = []
        for r in results:
            if isinstance(r, Exception):
                logger.exception("Task failed: %s", r)
                normalized.append({"status": "error", "error": str(r)})
            else:
                normalized.append(r)
        # simple reproducibility: count passes
        passed = sum(1 for r in normalized if r.get("status") == "passed")
        total = len(normalized)
        report = {
            "run_id": run_id,
            "summary": {"total": total, "passed": passed, "failed": total - passed},
            "results": normalized,
        }
        (out_root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        report = loop.run_until_complete(_execute_all())
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        loop.close()

    return run_id
# ...existing code...
