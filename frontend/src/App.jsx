// frontend/src/App.jsx
import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      // Points to FastAPI backend
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
    <div style={{ padding: '40px', fontFamily: 'sans-serif', maxWidth: '800px', margin: 'auto' }}>
      <h1>Aegis: Disinformation Dashboard</h1>
      <p>Paste an article or social media post below to verify its authenticity.</p>

      <textarea
        rows="10"
        style={{ width: '100%', padding: '10px', borderRadius: '8px' }}
        placeholder="Enter text here..."
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
      />

      <br />
      <button 
        onClick={handleAnalyze} 
        disabled={loading}
        style={{ marginTop: '20px', padding: '10px 20px', cursor: 'pointer' }}
      >
        {loading ? 'Analyzing...' : 'Generate Trust Report'}
      </button>

      {results && (
        <div style={{ marginTop: '40px', border: '1px solid #ddd', padding: '20px', borderRadius: '8px' }}>
          <h2>Trust Report</h2>
          
          <div style={{ marginBottom: '20px' }}>
            <strong>AI Detection Score:</strong> 
            <span style={{ color: results.ai_score > 0.5 ? 'red' : 'green' }}>
              {' '}{(results.ai_score * 100).toFixed(0)}% AI-Likelihood
            </span>
          </div>

          <div>
            <strong>Fact-Check Hits:</strong>
            <ul>
              {results.claims.map((item, index) => (
                <li key={index} style={{ marginBottom: '10px' }}>
                    "{item.claim}" 
                    <br />
                    <strong>Verdict: {item.rating}</strong> (Source: {item.source})
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