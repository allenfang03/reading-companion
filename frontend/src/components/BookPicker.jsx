import React, { useState, useRef } from 'react';
import { api } from '../utils/api';

export default function BookPicker({ books, onBookSelected }) {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);

  async function handleUpload(file) {
    setUploading(true);
    setUploadError(null);
    
    try {
      const data = await api.uploadBook(file);
      // Refresh books list
      const updated = await api.listBooks();
      onBookSelected(updated.books.find(b => b.id === data.book_id));
    } catch (err) {
      setUploadError(err.message);
      setUploading(false);
    }
  }

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (file) {
      handleUpload(file);
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.name.endsWith('.epub')) {
      handleUpload(file);
    } else {
      setUploadError('Please drop an EPUB file');
    }
  }

  function handleDragOver(e) {
    e.preventDefault();
  }

  if (books.length === 0) {
    return (
      <div className="card">
        <h2>Welcome to Reading Companion</h2>
        <p style={{ marginBottom: '1rem' }}>
          Upload an EPUB to get started. Your reading position is always kept private.
        </p>
        
        <div 
          className="card"
          style={{ 
            border: '2px dashed var(--color-border)',
            textAlign: 'center',
            cursor: 'pointer'
          }}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".epub"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          {uploading ? (
            <div className="loading">
              <div className="spinner"></div>
              Uploading and processing...
            </div>
          ) : (
            <>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📚</div>
              <p><strong>Drop your EPUB here</strong></p>
              <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
                or click to browse
              </p>
            </>
          )}
        </div>
        
        {uploadError && (
          <div className="error-box" style={{ marginTop: '1rem' }}>
            {uploadError}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Select a Book</h2>
      
      <div className="book-list">
        {books.map(book => (
          <div 
            key={book.id} 
            className="book-item"
            onClick={() => onBookSelected(book)}
          >
            <span className="title">{book.title}</span>
            <span className={`status ${book.is_indexed ? 'ready' : 'indexing'}`}>
              {book.is_indexed ? 'Ready' : 'Indexing...'}
            </span>
          </div>
        ))}
      </div>

      <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--color-border)', paddingTop: '1.5rem' }}>
        <h3 style={{ marginBottom: '1rem', fontSize: '1rem' }}>Add a new book</h3>
        
        <div 
          className="card"
          style={{ 
            border: '2px dashed var(--color-border)',
            textAlign: 'center',
            cursor: 'pointer',
            padding: '1rem'
          }}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".epub"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          {uploading ? (
            <div className="loading">
              <div className="spinner"></div>
              Uploading and processing...
            </div>
          ) : (
            <p>📤 Upload EPUB</p>
          )}
        </div>
        
        {uploadError && (
          <div className="error-box" style={{ marginTop: '1rem' }}>
            {uploadError}
          </div>
        )}
      </div>
    </div>
  );
}
