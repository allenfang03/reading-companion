import React, { useState, useEffect } from 'react';
import { api, ApiError } from './utils/api';
import BookPicker from './components/BookPicker';
import PositionSetter from './components/PositionSetter';
import RecapView from './components/RecapView';
import CharacterLookup from './components/CharacterLookup';

function App() {
  const [view, setView] = useState('loading');
  const [session, setSession] = useState(null);
  const [selectedBook, setSelectedBook] = useState(null);
  const [books, setBooks] = useState([]);
  const [error, setError] = useState(null);

  // Check for existing session on load
  useEffect(() => {
    const savedToken = localStorage.getItem('session_token');
    if (savedToken) {
      loadSession(savedToken);
    } else {
      loadBooks();
    }
  }, []);

  async function loadBooks() {
    try {
      const data = await api.listBooks();
      setBooks(data.books);
      setView('book-picker');
    } catch (err) {
      setError(err.message);
      setView('error');
    }
  }

  async function loadSession(token) {
    try {
      const data = await api.getSession(token);
      setSession(data);
      setView('session-active');
    } catch (err) {
      if (err.status === 404) {
        localStorage.removeItem('session_token');
        loadBooks();
      } else {
        setError(err.message);
        setView('error');
      }
    }
  }

  function handleBookSelected(book) {
    setSelectedBook(book);
    setView('position-setter');
  }

  async function handlePositionSet(data) {
    if (data.session_token) {
      localStorage.setItem('session_token', data.session_token);
      await loadSession(data.session_token);
    }
  }

  function handleBackToBooks() {
    setSession(null);
    setSelectedBook(null);
    setView('loading');
    loadBooks();
  }

  function handleChangeBook() {
    setSession(null);
    localStorage.removeItem('session_token');
    setView('loading');
    loadBooks();
  }

  if (view === 'loading') {
    return (
      <div className="app">
        <header>
          <h1>Reading Companion</h1>
        </header>
        <main>
          <div className="loading">
            <div className="spinner"></div>
            Loading...
          </div>
        </main>
      </div>
    );
  }

  if (view === 'error') {
    return (
      <div className="app">
        <header>
          <h1>Reading Companion</h1>
        </header>
        <main>
          <div className="card">
            <div className="error-box">
              <strong>Error:</strong> {error}
            </div>
            <button 
              className="btn btn-secondary" 
              style={{ marginTop: '1rem' }}
              onClick={loadBooks}
            >
              Try Again
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="app">
      <header>
        <h1>Reading Companion</h1>
      </header>
      <main>
        {view === 'book-picker' && (
          <BookPicker 
            books={books} 
            onBookSelected={handleBookSelected}
          />
        )}
        
        {view === 'position-setter' && (
          <PositionSetter
            book={selectedBook}
            onPositionSet={handlePositionSet}
            onBack={() => setView('book-picker')}
          />
        )}
        
        {view === 'session-active' && (
          <SessionView 
            session={session}
            onChangeBook={handleChangeBook}
          />
        )}
      </main>
    </div>
  );
}

function SessionView({ session, onChangeBook }) {
  const [activeTab, setActiveTab] = useState('recap');

  if (!session) {
    return (
      <div className="card">
        <div className="loading">
          <div className="spinner"></div>
          Loading session...
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="position-display">
        <div>
          <div className="book-title">{session.title}</div>
          <div className="chapter">Chapter {session.current_chapter_index + 1}</div>
        </div>
        {!session.is_indexed && (
          <span className="status indexing">Indexing...</span>
        )}
      </div>

      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'recap' ? 'active' : ''}`}
          onClick={() => setActiveTab('recap')}
        >
          Recap
        </button>
        <button 
          className={`tab ${activeTab === 'character' ? 'active' : ''}`}
          onClick={() => setActiveTab('character')}
          disabled={!session.is_indexed}
        >
          Character Lookup
        </button>
      </div>

      {activeTab === 'recap' && (
        <RecapView sessionToken={session.session_token} />
      )}
      
      {activeTab === 'character' && (
        <CharacterLookup sessionToken={session.session_token} />
      )}

      <button 
        className="btn btn-secondary" 
        style={{ marginTop: '1.5rem' }}
        onClick={onChangeBook}
      >
        Change Book
      </button>
    </div>
  );
}

export default App;
