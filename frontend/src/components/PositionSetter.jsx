import React, { useState } from 'react';
import { api } from '../utils/api';

export default function PositionSetter({ book, onPositionSet, onBack }) {
  const [snippet, setSnippet] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await api.setPosition(book.id, snippet);
      setResult(data);
      
      if (data.status === 'position_set') {
        setTimeout(() => onPositionSet(data), 1500);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function getResultMessage() {
    if (!result) return null;

    switch (result.status) {
      case 'no_match':
        return result.message;
      case 'multiple_matches':
        return result.message;
      case 'position_set':
        return `Position set! You're at ${result.chapter_name}. Loading your reading companion...`;
      default:
        return null;
    }
  }

  return (
    <div className="card">
      <h2>Set Your Position</h2>
      <p style={{ marginBottom: '1.5rem', color: 'var(--color-text-muted)' }}>
        <strong>{book.title}</strong>
      </p>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="label">
            Paste a snippet from where you're currently reading
          </label>
          <textarea
            className="input"
            value={snippet}
            onChange={(e) => setSnippet(e.target.value)}
            placeholder="Paste at least 10 words from your current position in the book..."
            rows={6}
          />
          <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
            {snippet.trim().split(/\s+/).filter(Boolean).length} words
            {snippet.trim().split(/\s+/).filter(Boolean).length < 10 && ' (minimum 10 required)'}
          </p>
        </div>

        <button 
          type="submit" 
          className="btn btn-primary"
          disabled={loading || snippet.trim().split(/\s+/).filter(Boolean).length < 10}
        >
          {loading ? 'Finding your position...' : 'Find My Position'}
        </button>
      </form>

      {error && (
        <div className="error-box">
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div className={`response-box ${result.status === 'position_set' ? 'cached' : ''}`}>
          {result.status === 'position_set' && (
            <span className="cached-badge">Position Found</span>
          )}
          <p>{getResultMessage()}</p>
        </div>
      )}

      <button 
        className="btn btn-secondary" 
        style={{ marginTop: '1rem' }}
        onClick={onBack}
      >
        Back to Books
      </button>
    </div>
  );
}
