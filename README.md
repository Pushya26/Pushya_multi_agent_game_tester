# Multi-Agent Game Tester POC

A proof-of-concept multi-agent system for automated testing of web games using LangChain, FastAPI, and Playwright.

## Architecture

- **PlannerAgent**: Generates 20+ test case candidates using LLM
- **RankerAgent**: Scores and selects top 10 test cases
- **OrchestratorAgent**: Coordinates parallel test execution
- **ExecutorAgents**: Run tests with Playwright, capture artifacts
- **AnalyzerAgent**: Analyzes results and reproducibility

## Quick Start

### Prerequisites
- Python 3.11+ (Required - Python 3.13 has Playwright compatibility issues)
- Node.js 18+
- Git
- OpenRouter API key (optional - has fallback)

### Complete Setup Instructions

1. **Clone repository:**
```bash
git clone https://github.com/yourusername/multi-agent-game-tester.git
cd multi-agent-game-tester
```

2. **Backend setup:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
playwright install chromium
```

3. **Environment configuration (optional):**
```bash
# Create .env file in backend directory
echo OPENROUTER_API_KEY=your_key_here > .env
# Note: System works with fallback test cases if no API key provided
```

4. **Start backend server:**
```bash
# From backend directory with venv activated
uvicorn app.main:app --reload --port 8000
```

5. **Setup frontend (new terminal):**
```bash
cd frontend
npm install
npm start
```

6. **Access application:**
- Frontend UI: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Usage Workflow

1. **Open** http://localhost:3000
2. **Click "Plan & Rank"** → Generates 20 test cases, ranks top 10
3. **Click "Execute Top 10"** → Runs tests with mock executor (POC)
4. **Copy run ID** from response
5. **Use run ID** to fetch detailed reports via API or UI
6. **View artifacts** in `backend/artifacts/{run_id}/` directory

## API Endpoints

### Core Workflow
- `POST /plan` - Generate 20 test case candidates using LLM
- `POST /rank` - Score and select top 10 test cases
- `POST /execute` - Execute selected test cases in parallel
- `GET /status/{run_id}` - Check execution progress
- `GET /report/{run_id}` - Get detailed execution report

### Debug & Utility
- `GET /` - API health check
- `GET /runs` - List all test runs
- `GET /debug-orchestrator` - Check agent import status
- `GET /store` - View in-memory data store
- `GET /docs` - Interactive API documentation

### Example Usage

```bash
# 1. Generate test cases
curl -X POST http://localhost:8000/plan \
  -H "Content-Type: application/json" \
  -d '{"url": "https://play.ezygamers.com/", "goal": "find bugs"}'

# 2. Rank test cases
curl -X POST http://localhost:8000/rank

# 3. Execute tests
curl -X POST http://localhost:8000/execute

# 4. Get report (use run_id from step 3)
curl http://localhost:8000/report/{run_id}
```

## Test Artifacts

Each test execution captures:
- Screenshots per step
- DOM snapshots
- Console logs
- Network activity (HAR)
- Step-by-step results

## Docker Deployment

```bash
cd infra
docker-compose up --build
```

## Demo Features

- **LangChain Integration**: AI-powered test case generation
- **Multi-Agent Coordination**: Planner → Ranker → Orchestrator → Executor → Analyzer
- **Concurrent Execution**: Parallel test execution with semaphore control
- **Reproducibility Testing**: Runs each test twice to check consistency
- **Rich Artifacts**: Screenshots, DOM snapshots, console logs, HAR files
- **Mock Execution**: POC uses mock executor (Playwright code included but commented)
- **JSON Reports**: Structured test results with triage notes
- **React Frontend**: Simple UI for workflow interaction

## Target Application

Tests the math puzzle game at: https://play.ezygamers.com/

## Important Notes

- **POC Status**: Uses mock executor for demonstration (Playwright has subprocess issues on Windows + Python 3.13)
- **Fallback System**: Works without OpenRouter API key using predefined test cases
- **Real Playwright Code**: Available in comments for production implementation
- **Artifacts Generated**: Even mock execution creates realistic test artifacts

## Project Structure

```
multi-agent-game-tester/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── planner.py      # LangChain test case generator
│   │   │   ├── ranker.py       # Test case scoring & selection
│   │   │   ├── orchestrator.py # Parallel execution coordinator
│   │   │   ├── executor.py     # Mock test executor (POC)
│   │   │   └── analyzer.py     # Result analysis & triage
│   │   ├── models.py           # Pydantic data models
│   │   ├── main.py            # FastAPI application
│   │   └── config.py          # Configuration & API keys
│   ├── requirements.txt       # Python dependencies
│   └── artifacts/            # Generated test artifacts
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # React UI components
│   │   └── index.js          # React entry point
│   ├── package.json          # Node.js dependencies
│   └── public/
├── README.md                 # This file
└── .gitignore               # Git ignore patterns
```

## Repository Setup

To make this code available on GitHub:

```bash
# Initialize git repository
git init
git add .
git commit -m "Initial commit: Multi-Agent Game Tester POC"
git branch -M main

# Create GitHub repository and push
git remote add origin https://github.com/yourusername/multi-agent-game-tester.git
git push -u origin main
```

## Troubleshooting

### Common Issues

1. **"Orchestrator not available" error:**
   - Restart backend server: `uvicorn app.main:app --reload --port 8000`
   - Check orchestrator.py has `orchestrate` function

2. **Python 3.13 + Playwright issues:**
   - Use Python 3.11 or add `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())`
   - Current POC uses mock executor to avoid this

3. **LangChain import errors:**
   - Use `langchain_openai` instead of deprecated `langchain.chat_models`
   - Install: `pip install langchain-openai`

4. **Frontend connection issues:**
   - Ensure backend runs on port 8000
   - Check CORS is enabled in FastAPI

### Debug Endpoints

- `GET /debug-orchestrator` - Check orchestrator import status
- `GET /store` - View in-memory data store
- `GET /runs` - List all test runs

## Development Notes

This is a POC implementation demonstrating:
- **Multi-agent coordination** ✅
- **LLM-driven test generation** ✅
- **Automated browser testing** ✅ (simulated)
- **Artifact collection** ✅
- **Result analysis** ✅

### Output Snapshots

![project page](https://raw.githubusercontent.com/Pushya26/Pushya_multi_agent_game_tester/main/screenshots/Screenshot 2025-09-27 140528.png)

![step 1: Executing Planner and Analyer Agents](https://raw.githubusercontent.com/Pushya26/Pushya_multi_agent_game_tester/main/screenshots/Screenshot 2025-09-27 140754.png)

![Step 1 output](https://raw.githubusercontent.com/Pushya26/Pushya_multi_agent_game_tester/main/screenshots/Screenshot 2025-09-27 140800.png)

![step 2: Executing Executor Agent](https://raw.githubusercontent.com/Pushya26/Pushya_multi_agent_game_tester/main/screenshots/Screenshot 2025-09-27 140828.png)

![Step 2 output](https://raw.githubusercontent.com/Pushya26/Pushya_multi_agent_game_tester/main/screenshots/Screenshot 2025-09-27 140835.png)

![Step 3: Output status and report](https://raw.githubusercontent.com/Pushya26/Pushya_multi_agent_game_tester/main/screenshots/Screenshot 2025-09-27 140917.png)

![Result Output](https://raw.githubusercontent.com/Pushya26/Pushya_multi_agent_game_tester/main/screenshots/Screenshot 2025-09-27 140937.png)

![Detailed Report View](https://raw.githubusercontent.com/Pushya26/Pushya_multi_agent_game_tester/main/screenshots/Screenshot 2025-09-27 141013.png)

![Triage notes View](https://raw.githubusercontent.com/Pushya26/Pushya_multi_agent_game_tester/main/screenshots/Screenshot 2025-09-27 141027.png)
