import React, { useState } from 'react';

export default function App() {
  const [activeTab, setActiveTab] = useState('testing');
  const [report, setReport] = useState(null);
  const [runId, setRunId] = useState('');
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState(null);
  const [feedbackForm, setFeedbackForm] = useState({ testcase_id: '', score: 5, comment: '' });

  const API_BASE = 'http://localhost:8000';

  // Tab Navigation
  const tabs = [
    { id: 'testing', label: 'Testing', icon: '🧪' },
    { id: 'feedback', label: 'Feedback', icon: '📝' },
    { id: 'metrics', label: 'Metrics', icon: '📊' }
  ];

  // Testing Tab Functions
  async function plan() {
    setLoading(true);
    try {
      const planResp = await fetch(`${API_BASE}/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: 'https://play.ezygamers.com/',
          goal: 'find functional and edge case issues in math game',
          use_rag: true
        })
      });
      const planData = await planResp.json();
      
      const rankResp = await fetch(`${API_BASE}/rank`, { method: 'POST' });
      const rankData = await rankResp.json();
      
      setStatus(`✅ RAG Planning: ${planData.count} candidates, Ranked: ${rankData.selected} selected`);
    } catch (error) {
      setStatus(`❌ Error: ${error.message}`);
    }
    setLoading(false);
  }

  async function execute() {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/execute`, { method: 'POST' });
      const data = await resp.json();
      
      if (data.run_id) {
        setRunId(data.run_id);
        setStatus(`🚀 Execution started: ${data.run_id}`);
        pollStatus(data.run_id);
      } else {
        setStatus(`❌ Error: ${data.error || 'Unknown error'}`);
      }
    } catch (error) {
      setStatus(`❌ Error: ${error.message}`);
    }
    setLoading(false);
  }

  async function pollStatus(id) {
    const poll = async () => {
      try {
        const resp = await fetch(`${API_BASE}/status/${id}`);
        const data = await resp.json();
        
        if (data.status === 'completed') {
          setStatus('✅ Execution completed! Fetch report to see results.');
          return;
        } else if (data.status === 'failed') {
          setStatus(`❌ Execution failed: ${data.error || 'Unknown error'}`);
          return;
        }
        
        setStatus(`⏳ Status: ${data.status}`);
        setTimeout(poll, 5000);
      } catch (error) {
        setStatus(`❌ Polling error: ${error.message}`);
      }
    };
    
    setTimeout(poll, 3000);
  }

  async function fetchReport() {
    if (!runId) {
      setStatus('Please enter a run ID');
      return;
    }
    
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/report/${runId}`);
      const data = await resp.json();
      
      if (data.error) {
        setStatus(`❌ Error: ${data.error}`);
      } else {
        setReport(data);
        setStatus('📋 Report loaded successfully');
      }
    } catch (error) {
      setStatus(`❌ Error: ${error.message}`);
    }
    setLoading(false);
  }

  // Feedback Tab Functions
  async function submitFeedback() {
    if (!runId || !feedbackForm.testcase_id) {
      setStatus('Please enter run ID and test case ID');
      return;
    }

    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/rag/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: runId,
          testcase_id: feedbackForm.testcase_id,
          score: parseInt(feedbackForm.score),
          comment: feedbackForm.comment
        })
      });
      const data = await resp.json();
      
      if (data.error) {
        setStatus(`❌ Feedback Error: ${data.error}`);
      } else {
        setStatus('✅ Feedback submitted successfully!');
        setFeedbackForm({ testcase_id: '', score: 5, comment: '' });
      }
    } catch (error) {
      setStatus(`❌ Error: ${error.message}`);
    }
    setLoading(false);
  }

  // Metrics Tab Functions
  async function loadMetrics() {
    setLoading(true);
    try {
      const [metricsResp, statsResp, insightsResp] = await Promise.all([
        fetch(`${API_BASE}/rag/metrics`),
        fetch(`${API_BASE}/rag/stats`),
        fetch(`${API_BASE}/rag/learning-insights`)
      ]);

      const metricsData = await metricsResp.json();
      const statsData = await statsResp.json();
      const insightsData = await insightsResp.json();

      setMetrics({ metrics: metricsData, stats: statsData, insights: insightsData });
      setStatus('📊 Metrics loaded');
    } catch (error) {
      setStatus(`❌ Error loading metrics: ${error.message}`);
    }
    setLoading(false);
  }

  async function triggerRetraining() {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/rag/retrain`, { method: 'POST' });
      const data = await resp.json();
      
      if (data.error) {
        setStatus(`❌ Retraining Error: ${data.error}`);
      } else {
        setStatus(`🎯 Retraining: ${data.message}`);
      }
    } catch (error) {
      setStatus(`❌ Error: ${error.message}`);
    }
    setLoading(false);
  }

  // Render Functions
  const renderTestingTab = () => (
    <div>
      <h2>🧪 AI-Powered Testing</h2>
      <p>Target: <a href="https://play.ezygamers.com/" target="_blank" rel="noopener noreferrer">
        https://play.ezygamers.com/
      </a></p>
      
      <div style={{ marginBottom: '20px' }}>
        <button onClick={plan} disabled={loading} style={{ marginRight: '10px', padding: '10px 20px' }}>
          {loading ? 'Planning...' : '🤖 RAG Plan & Rank'}
        </button>
        
        <button onClick={execute} disabled={loading} style={{ marginRight: '10px', padding: '10px 20px' }}>
          {loading ? 'Executing...' : '🚀 Execute Top 10'}
        </button>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <input
          type="text"
          value={runId}
          onChange={(e) => setRunId(e.target.value)}
          placeholder="Enter run ID"
          style={{ padding: '8px', marginRight: '10px', width: '300px' }}
        />
        <button onClick={fetchReport} disabled={loading} style={{ padding: '8px 16px' }}>
          📋 Fetch Report
        </button>
      </div>

      {report && (
        <div>
          <h3>📊 Test Results</h3>
          <div style={{ backgroundColor: '#f0f8ff', padding: '15px', border: '1px solid #ddd', marginBottom: '20px' }}>
            <p><strong>Run ID:</strong> {report.run_id}</p>
            <p><strong>Results:</strong> {report.summary?.total || 0} total, 
               {report.summary?.passed || 0} passed, {report.summary?.failed || 0} failed</p>
          </div>
          
          <details>
            <summary>📋 Full Report</summary>
            <pre style={{ backgroundColor: '#f8f8f8', padding: '15px', fontSize: '12px', maxHeight: '400px', overflow: 'auto' }}>
              {JSON.stringify(report, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );

  const renderFeedbackTab = () => (
    <div>
      <h2>📝 Feedback & Learning</h2>
      
      <div style={{ backgroundColor: '#f9f9f9', padding: '20px', border: '1px solid #ddd', marginBottom: '20px' }}>
        <h3>Submit Test Case Feedback</h3>
        
        <div style={{ marginBottom: '15px' }}>
          <label>Run ID:</label><br/>
          <input
            type="text"
            value={runId}
            onChange={(e) => setRunId(e.target.value)}
            placeholder="Enter run ID"
            style={{ padding: '8px', width: '300px' }}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label>Test Case ID:</label><br/>
          <input
            type="text"
            value={feedbackForm.testcase_id}
            onChange={(e) => setFeedbackForm({...feedbackForm, testcase_id: e.target.value})}
            placeholder="e.g., tc-001"
            style={{ padding: '8px', width: '300px' }}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label>Score (1-5):</label><br/>
          <select
            value={feedbackForm.score}
            onChange={(e) => setFeedbackForm({...feedbackForm, score: e.target.value})}
            style={{ padding: '8px', width: '100px' }}
          >
            <option value={1}>1 - Poor</option>
            <option value={2}>2 - Fair</option>
            <option value={3}>3 - Good</option>
            <option value={4}>4 - Very Good</option>
            <option value={5}>5 - Excellent</option>
          </select>
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label>Comment:</label><br/>
          <textarea
            value={feedbackForm.comment}
            onChange={(e) => setFeedbackForm({...feedbackForm, comment: e.target.value})}
            placeholder="Optional feedback comment..."
            style={{ padding: '8px', width: '300px', height: '80px' }}
          />
        </div>

        <button onClick={submitFeedback} disabled={loading} style={{ padding: '10px 20px' }}>
          {loading ? 'Submitting...' : '📤 Submit Feedback'}
        </button>
      </div>
    </div>
  );

  const renderMetricsTab = () => (
    <div>
      <h2>📊 RAG Metrics & Insights</h2>
      
      <div style={{ marginBottom: '20px' }}>
        <button onClick={loadMetrics} disabled={loading} style={{ marginRight: '10px', padding: '10px 20px' }}>
          {loading ? 'Loading...' : '🔄 Refresh Metrics'}
        </button>
        
        <button onClick={triggerRetraining} disabled={loading} style={{ padding: '10px 20px' }}>
          {loading ? 'Retraining...' : '🎯 Trigger Retraining'}
        </button>
      </div>

      {metrics && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
            <div style={{ backgroundColor: '#f0f8ff', padding: '15px', border: '1px solid #ddd' }}>
              <h3>🎯 Performance</h3>
              <p><strong>Pass Rate:</strong> {metrics.metrics.performance_metrics?.pass_rate || 0}%</p>
              <p><strong>Avg Feedback:</strong> {metrics.metrics.performance_metrics?.avg_feedback_score || 0}/5</p>
              <p><strong>Reproducibility:</strong> {metrics.metrics.performance_metrics?.reproducibility_rate || 0}%</p>
            </div>
            
            <div style={{ backgroundColor: '#f0fff0', padding: '15px', border: '1px solid #ddd' }}>
              <h3>🧠 Learning Data</h3>
              <p><strong>Cases Learned:</strong> {metrics.stats.vector_store?.total_cases || 0}</p>
              <p><strong>High Quality Tests:</strong> {metrics.insights.high_quality_tests || 0}</p>
              <p><strong>Learning Trend:</strong> {metrics.insights.learning_trend || 'unknown'}</p>
            </div>
          </div>

          <details>
            <summary>📈 Detailed Metrics</summary>
            <pre style={{ backgroundColor: '#f8f8f8', padding: '15px', fontSize: '12px', maxHeight: '300px', overflow: 'auto' }}>
              {JSON.stringify(metrics, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>🤖 Multi-Agent Game Tester with RAG</h1>
      
      {/* Tab Navigation */}
      <div style={{ borderBottom: '2px solid #ddd', marginBottom: '20px' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '10px 20px',
              marginRight: '5px',
              border: 'none',
              backgroundColor: activeTab === tab.id ? '#007bff' : '#f8f9fa',
              color: activeTab === tab.id ? 'white' : '#333',
              cursor: 'pointer',
              borderRadius: '5px 5px 0 0'
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Status Bar */}
      {status && (
        <div style={{ 
          padding: '10px', 
          backgroundColor: '#f0f0f0', 
          border: '1px solid #ccc',
          marginBottom: '20px',
          borderRadius: '5px'
        }}>
          <strong>Status:</strong> {status}
        </div>
      )}

      {/* Tab Content */}
      {activeTab === 'testing' && renderTestingTab()}
      {activeTab === 'feedback' && renderFeedbackTab()}
      {activeTab === 'metrics' && renderMetricsTab()}
    </div>
  );
}
