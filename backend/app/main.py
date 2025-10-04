from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uuid
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio
import inspect

# Fix for Python 3.13 + Windows compatibility
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from app.agents.planner import generate_candidates
from app.agents.ranker import rank_candidates
from app.agents.orchestrator import orchestrate
from app.agents.analyzer import generate_triage_notes
from app.models import RunReport
from app.config import ARTIFACTS_DIR
from app.agents.planner_rag import RAGPlanner
from app.rag.feedback_loop import FeedbackLoopManager



app = FastAPI(title="Multi-Agent Game Tester", version="1.0.0")

# Enable CORS for frontend - MUST be here
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for POC
in_memory_store: Dict[str, Any] = {}

# Add missing helper functions
async def _maybe_call(func, *args, **kwargs):
    """Call func whether it's sync or async; return result."""
    if func is None:
        raise RuntimeError("Requested function not available")
    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    return await asyncio.to_thread(func, *args, **kwargs)

orchestrate_fn = orchestrate


# Initialize RAG components (add after app initialization)
rag_planner = RAGPlanner()
feedback_manager = FeedbackLoopManager()

# Update the /plan endpoint to use RAG
@app.post("/plan")
async def plan(payload: dict):
    """Generate and store test case candidates using RAG"""
    url = payload.get('url', 'https://play.ezygamers.com/')
    goal = payload.get('goal', 'find bugs and edge cases')
    use_rag = payload.get('use_rag', True)

    try:
        # Use RAG-enhanced planner
        candidates = rag_planner.generate_candidates(
            url=url, 
            goal=goal, 
            use_rag=use_rag,
            count=20
        )
    except Exception as e:
        return {'error': f'Planner failed: {e}'}

    in_memory_store['candidates'] = candidates
    in_memory_store['url'] = url

    return {
        'status': 'success',
        'count': len(candidates),
        'use_rag': use_rag,
        'message': f'Generated {len(candidates)} test cases{"with RAG enhancement" if use_rag else ""}'
    }

@app.post("/rank")
async def rank():
    """Rank candidates and select top 10"""
    candidates = in_memory_store.get('candidates', [])
    if not candidates:
        return {'error': 'No candidates found. Run /plan first.'}
    
    top10 = rank_candidates(candidates)
    in_memory_store['top10'] = top10
    
    return {
        'status': 'success',
        'selected': len(top10),
        'message': f'Selected top {len(top10)} test cases'
    }

# NEW ENDPOINT: Submit feedback
@app.post("/feedback")
async def submit_feedback(payload: dict):
    """
    Submit user feedback for a test case
    
    Body:
    {
        "run_id": "uuid",
        "testcase_id": "tc-001",
        "score": 4,
        "comment": "Great test case!"
    }
    """
    run_id = payload.get('run_id')
    testcase_id = payload.get('testcase_id')
    score = payload.get('score')
    comment = payload.get('comment')
    
    if not all([run_id, testcase_id, score]):
        return {'error': 'Missing required fields: run_id, testcase_id, score'}
    
    try:
        result = feedback_manager.collect_user_feedback(
            run_id=run_id,
            testcase_id=testcase_id,
            score=score,
            comment=comment
        )
        return result
    except ValueError as e:
        return {'error': str(e)}
    except Exception as e:
        return {'error': f'Failed to submit feedback: {e}'}

# NEW ENDPOINT: Get improvement metrics
@app.get("/metrics/improvement")
async def get_improvement_metrics(days: int = 30):
    """Get agent improvement metrics over time"""
    try:
        report = feedback_manager.generate_improvement_report(days=days)
        return report
    except Exception as e:
        return {'error': f'Failed to generate report: {e}'}

# NEW ENDPOINT: Get learning insights
@app.get("/metrics/learning")
async def get_learning_insights():
    """Get insights about what the agent has learned"""
    try:
        insights = feedback_manager.get_learning_insights()
        return insights
    except Exception as e:
        return {'error': f'Failed to get insights: {e}'}

# NEW ENDPOINT: Trigger retraining
@app.post("/retrain")
async def trigger_retraining(payload: dict):
    """
    Trigger agent retraining with high-quality examples
    
    Body:
    {
        "min_feedback_score": 4
    }
    """
    min_score = payload.get('min_feedback_score', 4)
    
    try:
        result = feedback_manager.trigger_retraining(min_feedback_score=min_score)
        return result
    except Exception as e:
        return {'error': f'Retraining failed: {e}'}

# NEW ENDPOINT: Get vector store statistics
@app.get("/rag/stats")
async def get_rag_stats():
    """Get RAG system statistics"""
    try:
        vector_stats = rag_planner.vector_store.get_statistics()
        db_metrics = rag_planner.feedback_db.get_performance_metrics(days=30)
        
        return {
            "vector_store": vector_stats,
            "performance": db_metrics,
            "status": "operational"
        }
    except Exception as e:
        return {'error': f'Failed to get stats: {e}'}

# NEW ENDPOINT: Search similar test cases
@app.post("/rag/search")
async def search_similar_cases(payload: dict):
    """
    Search for similar test cases
    
    Body:
    {
        "query": "test zero division",
        "k": 5
    }
    """
    query = payload.get('query', '')
    k = payload.get('k', 5)
    
    if not query:
        return {'error': 'Query is required'}
    
    try:
        results = rag_planner.vector_store.search_similar_cases(
            query=query,
            k=k,
            filter_successful=True
        )
        return {
            "query": query,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        return {'error': f'Search failed: {e}'}

# NEW ENDPOINT: Get feedback history
@app.get("/feedback/history")
async def get_feedback_history(testcase_id: Optional[str] = None, limit: int = 100):
    """Get feedback history, optionally filtered by test case"""
    try:
        if testcase_id:
            feedback = rag_planner.feedback_db.get_feedback_for_testcase(testcase_id)
        else:
            feedback = rag_planner.feedback_db.get_recent_feedback(limit=limit)
        
        return {
            "count": len(feedback),
            "feedback": feedback
        }
    except Exception as e:
        return {'error': f'Failed to get feedback: {e}'}

# RAG ENDPOINTS

@app.post("/rag/feedback")
async def submit_feedback(payload: dict):
    """Submit user feedback for a test case"""
    run_id = payload.get('run_id')
    testcase_id = payload.get('testcase_id') 
    score = payload.get('score')
    comment = payload.get('comment')
    
    if not all([run_id, testcase_id, score]):
        return {'error': 'Missing required fields: run_id, testcase_id, score'}
    
    try:
        result = feedback_manager.collect_user_feedback(run_id, testcase_id, score, comment)
        return result
    except Exception as e:
        return {'error': f'Failed to submit feedback: {e}'}

@app.get("/rag/metrics")
async def get_performance_metrics(days: int = 30):
    """Get performance metrics"""
    try:
        return feedback_manager.generate_improvement_report(days=days)
    except Exception as e:
        return {'error': f'Failed to get metrics: {e}'}

@app.post("/rag/retrain")
async def trigger_retraining():
    """Trigger retraining"""
    try:
        return feedback_manager.trigger_retraining()
    except Exception as e:
        return {'error': f'Retraining failed: {e}'}

@app.post("/rag/similar")
async def find_similar_cases(payload: dict):
    """Find similar test cases"""
    query = payload.get('query', '')
    k = payload.get('k', 5)
    
    if not query:
        return {'error': 'Query is required'}
    
    try:
        results = rag_planner.vector_store.search_similar_cases(query=query, k=k)
        return {'query': query, 'count': len(results), 'results': results}
    except Exception as e:
        return {'error': f'Search failed: {e}'}

@app.get("/rag/stats")
async def get_rag_stats():
    """Get RAG system statistics"""
    try:
        vector_stats = rag_planner.vector_store.get_statistics()
        db_metrics = rag_planner.feedback_db.get_performance_metrics(days=30)
        return {'vector_store': vector_stats, 'performance': db_metrics, 'status': 'operational'}
    except Exception as e:
        return {'error': f'Failed to get stats: {e}'}

@app.get("/rag/improvement-report")
async def get_improvement_report(days: int = 30):
    """Generate improvement report"""
    try:
        return feedback_manager.generate_improvement_report(days=days)
    except Exception as e:
        return {'error': f'Failed to generate report: {e}'}

@app.get("/rag/learning-insights")
async def get_learning_insights():
    """Get learning insights"""
    try:
        return feedback_manager.get_learning_insights()
    except Exception as e:
        return {'error': f'Failed to get insights: {e}'}

@app.delete("/rag/clear-data")
async def clear_training_data():
    """Clear training data (use with caution)"""
    try:
        rag_planner.vector_store.clear_store()
        return {'status': 'success', 'message': 'Training data cleared'}
    except Exception as e:
        return {'error': f'Failed to clear data: {e}'}


# Update execute endpoint to process results with feedback manager
@app.post("/execute")
async def execute(background_tasks: BackgroundTasks):
    """Execute top 10 test cases"""
    top10 = in_memory_store.get('top10', [])
    if not top10:
        return {'error': 'No ranked test cases found. Run /plan and /rank first.'}

    run_id = str(uuid.uuid4())
    url = in_memory_store.get('url', 'https://play.ezygamers.com/')

    in_memory_store[run_id] = {'status': 'running', 'progress': 0}

    async def execute_tests():
        try:
            print(f"Starting execution for run_id: {run_id}")
            artifacts_dir = os.path.join(ARTIFACTS_DIR, run_id)
            os.makedirs(artifacts_dir, exist_ok=True)
        
            if orchestrate_fn is None:
                raise RuntimeError("Orchestrator not available")
            results = await _maybe_call(orchestrate_fn, top10, artifacts_dir)
        
            # NEW: Process results with feedback manager
            feedback_manager.process_execution_results(
                run_id=run_id,
                testcases=top10,
                results=results
            )
        
            triage_notes = {}
            if generate_triage_notes:
                triage_notes = await _maybe_call(generate_triage_notes, results)
        
            summary = {
                'total': len(results),
                'passed': sum(1 for r in results if r['verdict'] == 'PASS'),
                'failed': sum(1 for r in results if r['verdict'] == 'FAIL'),
                'flaky': sum(1 for r in results if r['verdict'] == 'FLAKY')
            }
        
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
    
    background_tasks.add_task(execute_tests)
    
    return {
        'status': 'started',
        'run_id': run_id,
        'message': f'Execution started for {len(top10)} test cases'
    }

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
