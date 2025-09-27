import React, { useState } from 'react';

export default function App() {
  const [report, setReport] = useState(null);
  const [runId, setRunId] = useState('');
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);

  const API_BASE = 'http://localhost:8000';

  async function plan() {
    setLoading(true);
    try {
      const planResp = await fetch(`${API_BASE}/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: 'https://play.ezygamers.com/',
          goal: 'find functional and edge case issues in math game'
        })
      });
      const planData = await planResp.json();
      
      const rankResp = await fetch(`${API_BASE}/rank`, { method: 'POST' });
      const rankData = await rankResp.json();
      
      setStatus(`Planned: ${planData.count} candidates, Ranked: ${rankData.selected} selected`);
    } catch (error) {
      setStatus(`Error: ${error.message}`);
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
        setStatus(`Execution started: ${data.run_id}`);
        
        // Poll for completion
        pollStatus(data.run_id);
      } else {
        setStatus(`Error: ${data.error || 'Unknown error'}`);
      }
    } catch (error) {
      setStatus(`Error: ${error.message}`);
    }
    setLoading(false);
  }

  async function pollStatus(id) {
    const maxAttempts = 30; // 5 minutes max
    let attempts = 0;
    
    const poll = async () => {
      try {
        const resp = await fetch(`${API_BASE}/status/${id}`);
        const data = await resp.json();
        
        setStatus(`Status: ${data.status}`);
        
        if (data.status === 'completed') {
          setStatus('Execution completed! Fetch report to see results.');
          return;
        } else if (data.status === 'failed') {
          setStatus(`Execution failed: ${data.error || 'Unknown error'}`);
          return;
        }
        
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 10000); // Poll every 10 seconds
        } else {
          setStatus('Polling timeout - check status manually');
        }
      } catch (error) {
        setStatus(`Polling error: ${error.message}`);
      }
    };
    
    setTimeout(poll, 5000); // Start polling after 5 seconds
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
        setStatus(`Error: ${data.error}`);
      } else {
        setReport(data);
        setStatus('Report loaded successfully');
      }
    } catch (error) {
      setStatus(`Error: ${error.message}`);
    }
    setLoading(false);
  }

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>Multi-Agent Game Tester (POC)</h1>
      <p>Target: <a href="https://play.ezygamers.com/" target="_blank" rel="noopener noreferrer">
        https://play.ezygamers.com/
      </a></p>
      
      <div style={{ marginBottom: '20px' }}>
        <button 
          onClick={plan} 
          disabled={loading}
          style={{ marginRight: '10px', padding: '10px 20px' }}
        >
          {loading ? 'Planning...' : 'Plan & Rank'}
        </button>
        
        <button 
          onClick={execute} 
          disabled={loading}
          style={{ marginRight: '10px', padding: '10px 20px' }}
        >
          {loading ? 'Executing...' : 'Execute Top 10'}
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
        <button 
          onClick={fetchReport}
          disabled={loading}
          style={{ padding: '8px 16px' }}
        >
          Fetch Report
        </button>
      </div>

      {status && (
        <div style={{ 
          padding: '10px', 
          backgroundColor: '#f0f0f0', 
          border: '1px solid #ccc',
          marginBottom: '20px'
        }}>
          <strong>Status:</strong> {status}
        </div>
      )}

      {report && (
        <div>
          <h2>Test Report</h2>
          <div style={{ marginBottom: '20px' }}>
            <h3>Summary</h3>
            <p><strong>Run ID:</strong> {report.run_id}</p>
            <p><strong>URL:</strong> {report.url}</p>
            <p><strong>Timestamp:</strong> {report.timestamp}</p>
            <p><strong>Results:</strong> {report.summary?.total || 0} total, 
               {report.summary?.passed || 0} passed, 
               {report.summary?.failed || 0} failed, 
               {report.summary?.flaky || 0} flaky</p>
          </div>
          
          <h3>Detailed Results</h3>
          <pre style={{ 
            backgroundColor: '#f8f8f8', 
            padding: '15px', 
            border: '1px solid #ddd',
            whiteSpace: 'pre-wrap',
            fontSize: '12px',
            maxHeight: '600px',
            overflow: 'auto'
          }}>
            {JSON.stringify(report, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}