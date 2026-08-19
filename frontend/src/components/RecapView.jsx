import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

export default function RecapView({ sessionToken }) {
  const [recap, setRecap] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchRecap();
  }, [sessionToken]);

  async function fetchRecap() {
    setLoading(true);
    setError(null);
    
    try {
      const data = await api.getRecap(sessionToken);
      setRecap(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="card">
        <div className="loading">
          <div className="spinner"></div>
          Generating recap...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="error-box">
          <strong>Error:</strong> {error}
        </div>
        <button 
          className="btn btn-secondary" 
          style={{ marginTop: '1rem' }}
          onClick={fetchRecap}
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>What Happened Since I Last Read</h2>
      
      <div className={`response-box ${recap.cached ? 'cached' : ''}`}>
        {recap.cached && (
          <span className="cached-badge">Cached</span>
        )}
        <p>{recap.recap}</p>
      </div>
      
      <button 
        className="btn btn-secondary" 
        style={{ marginTop: '1rem' }}
        onClick={fetchRecap}
      >
        Refresh Recap
      </button>
    </div>
  );
}
