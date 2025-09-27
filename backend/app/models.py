from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class Step(BaseModel):
    id: int
    action: str
    selector: Optional[str] = None
    value: Optional[str] = None
    note: Optional[str] = None

class TestCase(BaseModel):
    id: str
    title: str
    description: str
    steps: List[Step]
    tags: List[str] = []

class StepArtifact(BaseModel):
    screenshot_path: Optional[str] = None
    dom_snapshot: Optional[str] = None
    console_logs: List[str] = []
    network_har_path: Optional[str] = None
    step_result: Optional[str] = None

class TestResult(BaseModel):
    testcase_id: str
    verdict: str
    artifacts: Dict[int, StepArtifact]
    reruns: int
    reproducible: bool
    notes: Optional[str] = None

class RunReport(BaseModel):
    run_id: str
    url: str
    timestamp: str
    summary: Dict[str, int]
    results: List[TestResult]
    triage_notes: Dict[str, str]