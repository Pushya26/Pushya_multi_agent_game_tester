#!/usr/bin/env python3
"""
Quick demo script to test the multi-agent game tester locally
"""
import asyncio
import sys
import os
sys.path.append('backend')

from app.agents.planner import generate_candidates
from app.agents.ranker import rank_candidates
from app.agents.orchestrator import orchestrate
from app.agents.analyzer import generate_triage_notes

async def run_demo():
    print("🎮 Multi-Agent Game Tester Demo")
    print("=" * 40)
    
    # Step 1: Planning
    print("\n1. Planning Phase...")
    url = "https://play.ezygamers.com/"
    goal = "find functional and edge case issues"
    
    candidates = generate_candidates(url, goal)
    print(f"   Generated {len(candidates)} test case candidates")
    
    # Step 2: Ranking
    print("\n2. Ranking Phase...")
    top10 = rank_candidates(candidates)
    print(f"   Selected top {len(top10)} test cases")
    
    # Show selected test cases
    print("\n   Selected Test Cases:")
    for i, tc in enumerate(top10[:3], 1):  # Show first 3
        print(f"   {i}. {tc['title']} ({len(tc['steps'])} steps)")
    
    # Step 3: Execution (simplified for demo)
    print("\n3. Execution Phase...")
    print("   [Demo mode - would execute with Playwright]")
    
    # Simulate results
    mock_results = [
        {
            'testcase_id': tc['id'],
            'verdict': 'PASS' if i % 3 != 0 else 'FAIL',
            'artifacts': {},
            'reruns': 1,
            'reproducible': True,
            'notes': f"Mock result for {tc['title']}"
        }
        for i, tc in enumerate(top10)
    ]
    
    # Step 4: Analysis
    print("\n4. Analysis Phase...")
    triage_notes = generate_triage_notes(mock_results)
    
    # Summary
    passed = sum(1 for r in mock_results if r['verdict'] == 'PASS')
    failed = sum(1 for r in mock_results if r['verdict'] == 'FAIL')
    
    print(f"\n📊 Results Summary:")
    print(f"   Total: {len(mock_results)}")
    print(f"   Passed: {passed}")
    print(f"   Failed: {failed}")
    
    if triage_notes:
        print(f"\n🔍 Triage Notes:")
        for tc_id, note in triage_notes.items():
            print(f"   {tc_id}: {note}")
    
    print("\n✅ Demo completed!")
    print("\nTo run full system:")
    print("1. Set OPENAI_API_KEY in .env")
    print("2. Start backend: uvicorn app.main:app --reload")
    print("3. Start frontend: npm start")

if __name__ == "__main__":
    asyncio.run(run_demo())