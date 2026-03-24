// frontend/src/App.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './index.css';

function App() {
  const [inputText, setInputText] = useState('');
  const [imageUrl, setImageUrl] = useState(null); // --- NEW: IMAGE STATE ---
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [cooldown, setCooldown] = useState(0);
  
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  // 1. LOAD SAVED DATA WHEN EXTENSION OPENS
  useEffect(() => {
    const savedText = localStorage.getItem('aegis_text');
    const savedImage = localStorage.getItem('aegis_image'); // Load saved image
    const savedResults = localStorage.getItem('aegis_results');
    const savedHistory = localStorage.getItem('aegis_history');
    
    if (savedText) setInputText(savedText);
    if (savedImage) setImageUrl(savedImage);
    if (savedResults) setResults(JSON.parse(savedResults));
    if (savedHistory) setHistory(JSON.parse(savedHistory));
  }, []);

  // 2. SAVE TEXT & IMAGE TO STORAGE
  useEffect(() => {
    localStorage.setItem('aegis_text', inputText);
  }, [inputText]);

  useEffect(() => {
    if (imageUrl) {
      localStorage.setItem('aegis_image', imageUrl);
    } else {
      localStorage.removeItem('aegis_image');
    }
  }, [imageUrl]);

  useEffect(() => {
    if (results) {
      localStorage.setItem('aegis_results', JSON.stringify(results));
    }
  }, [results]);

  // 3. CLEAR BUTTON FUNCTION
  const handleClear = () => {
    setInputText('');
    setImageUrl(null); // Clear image
    setResults(null);
    localStorage.removeItem('aegis_text');
    localStorage.removeItem('aegis_image');
    localStorage.removeItem('aegis_results');
  };

  const handleClearHistory = () => {
    setHistory([]);
    localStorage.removeItem('aegis_history');
  };

  // 4. CATCH TEXT OR IMAGE SENT FROM RIGHT-CLICK MENU
  useEffect(() => {
    if (typeof chrome !== 'undefined' && chrome.storage) {
      chrome.storage.local.get(['aegis_context_text', 'aegis_context_image'], (result) => {
        
        if (result.aegis_context_text) {
          setInputText(result.aegis_context_text);
          setImageUrl(null); // Clear old image if new text is sent
          setShowHistory(false); 
          chrome.storage.local.remove(['aegis_context_text']);
        }
        
        if (result.aegis_context_image) {
          setImageUrl(result.aegis_context_image);
          setInputText(''); // Clear old text if new image is sent
          setShowHistory(false);
          chrome.storage.local.remove(['aegis_context_image']);
        }
      });
      if (chrome.action) {
        chrome.action.setBadgeText({ text: "" });
      }
    }
  }, []);
  
  useEffect(() => {
    if (cooldown > 0) {
      const timer = setTimeout(() => setCooldown(cooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [cooldown]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault(); 
      if (!loading && cooldown === 0 && (inputText.trim().length > 0 || imageUrl)) {
        handleAnalyze();
      }
    }
  };

  const handleAnalyze = async () => {
    if (cooldown > 0) return;
    setLoading(true);
    
    try {
      // Send either text, or image, or both to the backend
      const payload = { text: inputText };
      if (imageUrl) {
        payload.image_url = imageUrl;
      }

      const response = await axios.post('http://localhost:8000/analyze', payload);
      const newResults = response.data;
      setResults(newResults);

      const newHistoryItem = {
        id: Date.now(),
        date: new Date().toLocaleDateString() + ' ' + new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}),
        text: imageUrl ? "Scanned an Image" : inputText,
        imageUrl: imageUrl, // Save thumbnail to history
        results: newResults
      };

      const updatedHistory = [newHistoryItem, ...history].slice(0, 10);
      setHistory(updatedHistory);
      localStorage.setItem('aegis_history', JSON.stringify(updatedHistory));

    } catch (error) {
      console.error("Analysis Error:", error);
      if (error.response && error.response.status === 429) {
        alert("Rate limit exceeded! Please wait before trying again.");
        setCooldown(60); 
      } else {
        alert("Failed to connect to backend. Ensure the Python server is running.");
      }
    } finally {
      setLoading(false);
    }
  };

  const loadHistoryItem = (item) => {
    setInputText(item.text === "Scanned an Image" ? "" : item.text);
    setImageUrl(item.imageUrl || null);
    setResults(item.results);
    setShowHistory(false);
  };

  const getRatingColor = (rating) => {
    if (!rating) return '#a1a1aa';
    const r = rating.toUpperCase();
    if (r === 'TRUE') return '#4ade80';
    if (r === 'FALSE') return '#ff6b6b';
    if (r === 'UNCERTAIN') return '#fbbf24';
    return '#a1a1aa';
  };

  return (
    <div style={{ padding: '20px', maxWidth: '400px', boxSizing: 'border-box' }}>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h1 style={{ margin: 0, fontSize: '24px' }}>Aegis</h1>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            onClick={() => setShowHistory(!showHistory)}
            style={{ padding: '4px 8px', fontSize: '12px', backgroundColor: showHistory ? '#3b82f6' : '#27272a', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            {showHistory ? 'Back to Scanner' : '🕒 History'}
          </button>
          {!showHistory && (results || inputText || imageUrl) && (
            <button 
              onClick={handleClear}
              style={{ padding: '4px 8px', fontSize: '12px', backgroundColor: '#3f3f46', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      <hr style={{ borderColor: '#333', marginBottom: '15px' }} />

      {showHistory ? (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
            <h2 style={{ margin: 0, fontSize: '16px', color: '#e4e4e7' }}>Recent Checks</h2>
            {history.length > 0 && (
              <button onClick={handleClearHistory} style={{ background: 'none', border: 'none', color: '#ef4444', fontSize: '12px', cursor: 'pointer' }}>
                Clear All
              </button>
            )}
          </div>

          {history.length === 0 ? (
            <p style={{ color: '#a1a1aa', fontSize: '14px', textAlign: 'center', marginTop: '40px' }}>No history yet. Run a check!</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {history.map((item) => (
                <div 
                  key={item.id} 
                  onClick={() => loadHistoryItem(item)}
                  style={{ backgroundColor: '#18181b', padding: '12px', borderRadius: '6px', border: '1px solid #3f3f46', cursor: 'pointer' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontSize: '12px', color: '#a1a1aa' }}>{item.date}</span>
                    <span style={{ fontSize: '12px', fontWeight: 'bold', color: item.results.ai_score > 0.5 ? '#ff6b6b' : '#4ade80' }}>
                      {(item.results.ai_score * 100).toFixed(0)}% AI
                    </span>
                  </div>
                  {/* Show tiny image thumbnail in history if it was an image check */}
                  {item.imageUrl && (
                    <img src={item.imageUrl} alt="thumb" style={{ height: '30px', borderRadius: '4px', marginBottom: '4px' }}/>
                  )}
                  <p style={{ margin: 0, fontSize: '13px', color: '#d4d4d8', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    "{item.text}"
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div>
          <p style={{ margin: '0 0 15px 0', fontSize: '14px', color: '#a1a1aa' }}>
            Paste text or right-click an image to verify authenticity.
          </p>

          {/* --- NEW: IMAGE PREVIEW THUMBNAIL --- */}
          {imageUrl && (
            <div style={{ position: 'relative', marginBottom: '10px' }}>
              <img 
                src={imageUrl} 
                alt="Selected to scan" 
                style={{ width: '100%', maxHeight: '200px', objectFit: 'contain', backgroundColor: '#000', borderRadius: '8px', border: '1px solid #3f3f46' }} 
              />
              <button 
                onClick={() => setImageUrl(null)}
                style={{ position: 'absolute', top: '5px', right: '5px', backgroundColor: '#ef4444', color: 'white', border: 'none', borderRadius: '50%', width: '24px', height: '24px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}
              >
                ×
              </button>
            </div>
          )}

          {/* Only show text area if there is no image */}
          {!imageUrl && (
            <textarea
              rows="8"
              style={{ width: '100%', padding: '10px', borderRadius: '8px', boxSizing: 'border-box' }}
              placeholder="Enter text here..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
            />
          )}

          <button 
            onClick={handleAnalyze} 
            disabled={loading || (!inputText && !imageUrl)}
            style={{ width: '100%', marginTop: '15px', padding: '12px', borderRadius: '8px', cursor: (loading || (!inputText && !imageUrl) || cooldown > 0) ? 'not-allowed' :'pointer', backgroundColor: cooldown > 0 ? '#374151' : '#3b82f6', color: 'white', border: 'none', opacity: (!inputText && !imageUrl) ? 0.5 : 1 }}
          >
            {loading ? 'Analyzing...' : cooldown > 0 ? `Wait ${cooldown}s` : 'Generate Trust Report'}
          </button>

          {loading && (
            <div style={{ marginTop: '25px', border: '1px solid #333', backgroundColor: '#18181b', padding: '15px', borderRadius: '8px' }}>
              <div className="skeleton-box" style={{ height: '24px', width: '150px', marginBottom: '15px' }}></div>
              <div className="skeleton-box" style={{ height: '20px', width: '80%', marginBottom: '15px' }}></div>
              <div className="skeleton-box" style={{ height: '60px', width: '100%', borderRadius: '8px' }}></div>
            </div>
          )}

          {!loading && results && (
            <div style={{ marginTop: '25px', border: '1px solid #333', backgroundColor: '#18181b', padding: '15px', borderRadius: '8px' }}>
              <h2 style={{ marginTop: 0, fontSize: '18px' }}>🛡️ Trust Report</h2>
              
              <div style={{ marginBottom: '15px', paddingBottom: '15px', borderBottom: '1px solid #333' }}>
                <strong>AI Detection Score:</strong> 
                <span style={{ color: results.ai_score > 0.5 ? '#ff6b6b' : '#4ade80', fontWeight: 'bold', marginLeft: '8px' }}>
                  {(results.ai_score * 100).toFixed(0)}% AI-Likelihood
                </span>
              </div>

              <div>
                <strong>Fact-Check Analysis:</strong>
                <div style={{ marginTop: '10px' }}>
                  {results.claims.map((item, index) => {
                    const report = item.detailed_report;

                    if (!report) {
                        return (
                          <div key={index} style={{ marginBottom: '12px', color: '#d4d4d8' }}>
                            <strong style={{ color: '#fff' }}>Verdict: </strong> 
                            <span style={{ color: getRatingColor(item.rating), fontWeight: 'bold' }}>{item.rating}</span><br />
                            <em style={{ color: '#a1a1aa' }}>"{item.claim}"</em> 
                          </div>
                        );
                    }

                    return (
                      <div key={index} style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#27272a', borderRadius: '6px' }}>
                        
                        <div style={{ marginBottom: '8px' }}>
                          <strong style={{ fontSize: '14px', color: '#fff' }}>Verdict: </strong>
                          <span style={{ color: getRatingColor(report.rating), fontWeight: 'bold', fontSize: '12px', backgroundColor: '#18181b', padding: '2px 8px', borderRadius: '12px', marginLeft: '4px' }}>
                            {report.rating}
                          </span>
                        </div>
                        
                        <em style={{ color: '#a1a1aa', display: 'block', marginBottom: '8px', fontSize: '13px' }}>"{item.claim}"</em>
                        <p style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#d4d4d8', lineHeight: '1.4' }}>
                          {report.brief_description}
                        </p>
                        
                        {report.sources && report.sources.length > 0 && (
                          <div style={{ marginTop: '10px', borderTop: '1px solid #3f3f46', paddingTop: '10px' }}>
                            <strong style={{ fontSize: '12px', color: '#a1a1aa', textTransform: 'uppercase' }}>Sources & Bias Report</strong>
                            
                            {report.sources.map((src, i) => (
                              <div key={i} style={{ marginTop: '10px', fontSize: '13px', backgroundColor: '#18181b', padding: '10px', borderRadius: '4px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                                  <strong style={{ color: '#60a5fa', fontSize: '14px' }}>{src.source_name}</strong>
                                  <a href={src.link} target="_blank" rel="noopener noreferrer" style={{ color: '#3b82f6', textDecoration: 'none', fontSize: '12px' }}>
                                    View Source ↗
                                  </a>
                                </div>
                                <p style={{ margin: '0 0 6px 0', color: '#d4d4d8' }}>{src.source_summary}</p>
                                
                                <div style={{ fontSize: '12px', color: '#a1a1aa', fontStyle: 'italic', borderLeft: '2px solid #52525b', paddingLeft: '8px' }}>
                                  <span style={{fontWeight: 'bold', color: '#71717a'}}>Bias: </span>{src.bias_report}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;