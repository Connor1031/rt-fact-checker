// frontend/src/App.jsx
import React, { useState } from 'react';
import axios from 'axios';
import './index.css';

function App() {
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/analyze', {
        text: inputText
      });
      setResults(response.data);
    } catch (error) {
      console.error("Error analyzing text:", error);
      alert("Failed to connect to backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '400px', boxSizing: 'border-box' }}>
      <h1 style={{ marginTop: 0, fontSize: '24px' }}>Aegis Dashboard</h1>
      <p style={{ fontSize: '14px', color: '#a1a1aa' }}>
        Paste an article or social media post below to verify its authenticity.
      </p>

      <textarea
        rows="8"
        style={{ width: '100%', padding: '10px', borderRadius: '8px', boxSizing: 'border-box' }}
        placeholder="Enter text here..."
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
      />

      <button 
        onClick={handleAnalyze} 
        disabled={loading}
        style={{ width: '100%', marginTop: '15px', padding: '12px', borderRadius: '8px', cursor: 'pointer' }}
      >
        {loading ? 'Analyzing...' : 'Generate Trust Report'}
      </button>

      {results && (
        <div style={{ marginTop: '25px', border: '1px solid #333', backgroundColor: '#18181b', padding: '15px', borderRadius: '8px' }}>
          <h2 style={{ marginTop: 0, fontSize: '18px' }}>🛡️ Trust Report</h2>
          
          <div style={{ marginBottom: '15px', paddingBottom: '15px', borderBottom: '1px solid #333' }}>
            <strong>AI Detection Score:</strong> 
            <span style={{ color: results.ai_score > 0.5 ? '#ff6b6b' : '#4ade80', fontWeight: 'bold', marginLeft: '8px' }}>
              {(results.ai_score * 100).toFixed(0)}% AI-Likelihood
            </span>
          </div>

          <div>
            <strong>Fact-Check Hits:</strong>
            <ul style={{ paddingLeft: '20px', margin: '10px 0 0 0', fontSize: '14px' }}>
              {results.claims.map((item, index) => (
                <li key={index} style={{ marginBottom: '12px', color: '#d4d4d8' }}>
                    <em style={{ color: '#a1a1aa' }}>"{item.claim}"</em> 
                    <br />
                    <strong style={{ color: '#fff' }}>Verdict: {item.rating}</strong> 
                    <br />
                    <span style={{ fontSize: '12px', color: '#888' }}>(Source: {item.source})</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;