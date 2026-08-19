import React, { useState } from 'react';
import { api } from '../utils/api';

export default function CharacterLookup({ sessionToken }) {
  const [name, setName] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!name.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await api.lookupCharacter(sessionToken, name.trim());
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <h2>Character Lookup</h2>
      <p style={{ marginBottom: '1rem', color: 'var(--color-text-muted)' }}>
        Search for a character to see who they are and their role in the story.
      </p>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="label">Character Name</label>
          <input
            type="text"
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter character name..."
          />
        </div>

        <button 
          type="submit" 
          className="btn btn-primary"
          disabled={loading || !name.trim()}
        >
          {loading ? 'Searching...' : 'Look Up Character'}
        </button>
      </form>

      {error && (
        <div className="error-box">
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div className="character-result">
          {result.status === 'found' ? (
            <>
              <h3 style={{ marginBottom: '0.5rem' }}>{result.character}</h3>
              <p className="mentions-count">
                {result.mentions_count} mention{result.mentions_count !== 1 ? 's' : ''} found
              </p>
              <div className="response-box">
                {result.description.split('\n\n').map((line, i) => (
                  <p key={i} style={{ margin: '0 0 1rem 0' }}>
                    {line.split('\n').map((part, j) => (
                      <React.Fragment key={j}>
                        {j > 0 && <br />}
                        {part}
                      </React.Fragment>
                    ))}
                  </p>
                ))}
              </div>
            </>
          ) : (
            <div className="response-box">
              <p style={{ whiteSpace: 'pre-wrap' }}>{result.message}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
