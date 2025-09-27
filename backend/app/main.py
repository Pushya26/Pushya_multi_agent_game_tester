# ...existing code...
import sys
import asyncio

# Windows + Python 3.13 fix for subprocess support in asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uuid
import os
from datetime import datetime
from typing import Dict, Any
import inspect
import logging

logger = logging.getLogger(__name__)

# try to import agents/modules with fallbacks
try:
    from app.agents import planner as planner_mod
except Exception:
    planner_mod = None

try:
    from app.agents import ranker as ranker_mod
except Exception:
    ranker_mod = None

try:
    from app.agents import orchestrator as orchestrator_mod
except Exception:
    orchestrator_mod = None

try:
    from app.agents import analyzer as analyzer_mod
except Exception:
    analyzer_mod = None

try:
    from app.agents import executor as executor_mod
except Exception:
    executor_mod = None

from app.models import RunReport
from app.config import ARTIFACTS_DIR

app = FastAPI(title="Multi-Agent Game Tester", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for POC
in_memory_store: Dict[str, Any] = {}

# resolve functions with common fallback names
def _resolve(fn_candidates, module):
    if not module:
        return None
    for name in fn_candidates:
        if hasattr(module, name):
            return getattr(module, name)
    return None

generate_candidates = _resolve(["generate_candidates", "generate_plans", "generate"], planner_mod)
rank_candidates = _resolve(["rank_candidates", "rank"], ranker_mod)
orchestrate_fn = _resolve(["orchestrate", "start_execution", "start"], orchestrator_mod)
generate_triage_notes = _resolve(["generate_triage_notes", "generate_triage", "triage"], analyzer_mod)

async def _maybe_call(func, *args, **kwargs):
    """Call func whether it's sync or async; return result."""
    if func is None:
        raise RuntimeError("Requested function not available")
    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    # sync function -> run in thread to avoid blocking event loop
    return await asyncio.to_thread(func, *args, **kwargs)

@app.get("/")
async def root():
    return {"message": "Multi-Agent Game Tester API"}

@app.post("/plan")
async def plan(payload: dict):
    """Generate and store test case candidates"""
    url = payload.get('url', 'https://play.ezygamers.com/')
    goal = payload.get('goal', 'find bugs and edge cases')

    if generate_candidates is None:
        return {'error': 'Planner not available. Check backend agents.'}

    # try multiple call signatures
    try:
        # prefer (url, goal)
        candidates = await _maybe_call(generate_candidates, url, goal)
    except TypeError:
        try:
            # maybe function expects only count or nothing
            candidates = await _maybe_call(generate_candidates)
        except Exception as e:
            return {'error': f'Planner invocation failed: {e}'}
    except Exception as e:
        return {'error': f'Planner failed: {e}'}

    in_memory_store['candidates'] = candidates
    in_memory_store['url'] = url

    return {
        'status': 'success',
        'count': len(candidates) if candidates else 0,
        'message': f'Generated {len(candidates) if candidates else 0} test case candidates'
    }

@app.post("/rank")
async def rank():
    """Rank candidates and select top 10"""
    candidates = in_memory_store.get('candidates', [])
    if not candidates:
        return {'error': 'No candidates found. Run /plan first.'}

    if rank_candidates is None:
        return {'error': 'Ranker not available. Check backend agents.'}

    try:
        top10 = await _maybe_call(rank_candidates, candidates, 10)
    except TypeError:
        # ranker may accept only candidates and return top 10 internally
        top10 = await _maybe_call(rank_candidates, candidates)
    except Exception as e:
        return {'error': f'Ranker failed: {e}'}

    in_memory_store['top10'] = top10

    return {
        'status': 'success',
        'selected': len(top10),
        'message': f'Selected top {len(top10)} test cases'
    }

@app.post("/execute")
async def execute(background_tasks: BackgroundTasks):
    """Execute top 10 test cases"""
    top10 = in_memory_store.get('top10', [])
    if not top10:
        return {'error': 'No ranked test cases found. Run /plan and /rank first.'}

    run_id = str(uuid.uuid4())
    url = in_memory_store.get('url', 'https://play.ezygamers.com/')

    # Initialize run status
    in_memory_store[run_id] = {'status': 'running', 'progress': 0}

    async def execute_tests():
        try:
            print(f"Starting execution for run_id: {run_id}")
            artifacts_dir = os.path.join(ARTIFACTS_DIR, run_id)
            os.makedirs(artifacts_dir, exist_ok=True)
        
        # Run orchestration
            if orchestrate_fn is None:
                raise RuntimeError("Orchestrator not available")
            results = await _maybe_call(orchestrate_fn, top10, artifacts_dir)
        
        # Generate triage notes
            triage_notes = {}
            if generate_triage_notes:
                triage_notes = await _maybe_call(generate_triage_notes, results)
        
        # Calculate summary
            summary = {
                'total': len(results),
                'passed': sum(1 for r in results if r['verdict'] == 'PASS'),
                'failed': sum(1 for r in results if r['verdict'] == 'FAIL'),
                'flaky': sum(1 for r in results if r['verdict'] == 'FLAKY')
            }
        
        # Create final report
            report = RunReport(
                run_id=run_id,
                url=url,
                timestamp=datetime.now().isoformat(),
                summary=summary,
                results=results,
                triage_notes=triage_notes
            )
        
            in_memory_store[run_id] = {
                'status': 'completed',
                'report': report.dict()
            }
            print(f"Execution completed successfully for run_id: {run_id}")
        
        except Exception as e:
            print(f"Execution failed for run_id {run_id}: {str(e)}")
            in_memory_store[run_id] = {
                'status': 'failed',
                'error': str(e)
            }

    
    # Start background task
    background_tasks.add_task(execute_tests)
    
    return {
        'status': 'started',
        'run_id': run_id,
        'message': f'Execution started for {len(top10)} test cases'
    }

# Add this debug endpoint to main.py to check orchestrator import
@app.get("/debug-orchestrator")
async def debug_orchestrator():
    """Debug orchestrator import"""
    try:
        from app.agents import orchestrator as orch_mod
        functions = [name for name in dir(orch_mod) if not name.startswith('_')]
        has_orchestrate = hasattr(orch_mod, 'orchestrate')
        return {
            'import_success': True,
            'available_functions': functions,
            'has_orchestrate': has_orchestrate,
            'orchestrate_fn_resolved': orchestrate_fn is not None
        }
    except Exception as e:
        return {'import_success': False, 'error': str(e)}



@app.get("/status/{run_id}")
async def get_status(run_id: str):
    """Get execution status"""
    run_data = in_memory_store.get(run_id)
    if not run_data:
        return {'error': 'Run not found'}

    return {
        'run_id': run_id,
        'status': run_data.get('status', 'unknown'),
        'progress': run_data.get('progress', 0)
    }

@app.get("/report/{run_id}")
async def get_report(run_id: str):
    """Get final execution report"""
    run_data = in_memory_store.get(run_id)
    if not run_data:
        return {'error': 'Run not found'}

    if run_data.get('status') != 'completed':
        return {
            'status': run_data.get('status'),
            'message': 'Execution not completed yet'
        }

    return run_data.get('report', {})

@app.get("/runs")
async def list_runs():
    """List all runs"""
    runs = []
    for key, value in in_memory_store.items():
        if isinstance(value, dict) and 'status' in value:
            runs.append({
                'run_id': key,
                'status': value.get('status'),
                'timestamp': value.get('report', {}).get('timestamp') if value.get('report') else None
            })
    return {'runs': runs}

@app.get("/debug")
async def debug():
    """Debug endpoint to test execution"""
    try:
        # try multiple possible executor function names
        run_fn = None
        if executor_mod:
            for name in ("run_testcase", "run_test_case", "run_test_case_async", "run_test_case_sync", "run_test"):
                if hasattr(executor_mod, name):
                    run_fn = getattr(executor_mod, name)
                    break

        if run_fn is None:
            return {'status': 'error', 'error': 'No executor function found in app.agents.executor'}

        # Simple test case
        test_case = {
            'id': 'debug-001',
            'steps': [
                {'id': 1, 'action': 'navigate', 'value': 'https://example.com'},
                {'id': 2, 'action': 'click', 'selector': 'button'}
            ]
        }

        # call sync or async executor appropriately
        if inspect.iscoroutinefunction(run_fn):
            artifacts = await run_fn(test_case, 'debug_artifacts')
        else:
            artifacts = await asyncio.to_thread(run_fn, test_case, 'debug_artifacts')

        return {'status': 'success', 'artifacts': artifacts}

    except Exception as e:
        import traceback
        return {
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }

@app.get("/store")
async def get_store():
    """Debug: Show in-memory store contents"""
    # limit output size
    safe_store = {k: (v if k in ("candidates", "top10") else {"status": v.get("status"), "report_present": bool(v.get("report"))}) for k, v in in_memory_store.items()}
    return {'store_keys': list(in_memory_store.keys()), 'store': safe_store}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# ...existing code...