# cross_validator.py
import os
from typing import Dict, Any
from .executor import run_testcase as run_testcase_chrome
from .executor_firefox import run_testcase as run_testcase_firefox  # you'll need to add this

def compare_cross_agent_results(chrome_artifacts: Dict[int, Dict], firefox_artifacts: Dict[int, Dict]) -> bool:
    """Basic comparison of artifacts between Chrome & Firefox"""
    for step_id, chrome_step in chrome_artifacts.items():
        firefox_step = firefox_artifacts.get(step_id)
        if not firefox_step:
            return False
        if chrome_step.get("step_result") != firefox_step.get("step_result"):
            return False
    return True

async def cross_validate_testcase(tc: Dict[str, Any], artifacts_dir: str) -> Dict[str, Any]:
    chrome_artifacts = await run_testcase_chrome(tc, os.path.join(artifacts_dir, "chrome"))
    firefox_artifacts = await run_testcase_firefox(tc, os.path.join(artifacts_dir, "firefox"))
    
    match = compare_cross_agent_results(chrome_artifacts, firefox_artifacts)
    
from langchain_core.tools import tool

@tool("cross_validate_testcase", return_direct=True)
async def cross_validate_testcase_tool(tc: Dict[str, Any], artifacts_dir: str):
    """Run cross-browser validation (Chrome vs Firefox)."""
    chrome_artifacts = await run_testcase_chrome(tc, os.path.join(artifacts_dir, "chrome"))
    firefox_artifacts = await run_testcase_firefox(tc, os.path.join(artifacts_dir, "firefox"))
    match = compare_cross_agent_results(chrome_artifacts, firefox_artifacts)
    return {
        "primary_artifacts": chrome_artifacts,
        "cross_validation_artifacts": firefox_artifacts,
        "cross_validation_passed": match
    }
