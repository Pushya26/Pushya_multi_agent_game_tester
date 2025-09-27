# executor_firefox.py
import os
from typing import Dict, Any
from .executor import run_testcase as base_run_testcase

async def run_testcase(
    testcase: Dict[str, Any],
    artifacts_dir: str
) -> Dict[int, Dict[str, Any]]:
    """
    Wrapper executor for Firefox browser.

    Calls the main executor with browser_type="firefox".
    """
    os.makedirs(artifacts_dir, exist_ok=True)
    return await base_run_testcase(testcase, artifacts_dir, browser_type="firefox")
