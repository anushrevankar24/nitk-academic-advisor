import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import ChatContainer from './components/Chat/ChatContainer';
import PdfPanel from './components/PDFViewer/PdfPanel';

function AppContent() {
  const [scope, setScope] = useState('ug');
  const [status, setStatus] = useState({ ready: false, total_chunks: 0 });
  const [pdfState, setPdfState] = useState({
    isOpen: false,
    filename: null,
    targetPage: 1,
    chunkText: null
  });
  const navigate = useNavigate();
  const location = useLocation();

  // Reset PDF state when entering the chat
  useEffect(() => {
    if (location.pathname.startsWith('/chat')) {
      setPdfState({
        isOpen: false,
        filename: null,
        targetPage: 1,
        chunkText: null
      });
    }
  }, [location.pathname]);

  // Enforce simple light theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'light');
    localStorage.setItem('theme', 'light');
  }, []);

  // Fetch status on load
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('/status');
        const data = await response.json();
        if (data.status === 'ready') {
          setStatus({ ready: true, total_chunks: data.total_chunks });
        }
      } catch (err) {
        console.error("Failed to fetch server status", err);
      }
    };
    fetchStatus();
  }, []);

  const openPdf = (filename, pageIndex, text) => {
    setPdfState({
      isOpen: true,
      filename,
      targetPage: (pageIndex || 0) + 1,
      chunkText: text
    });
  };

  const closePdf = () => {
    setPdfState(prev => ({ ...prev, isOpen: false }));
  };

  return (
    <Routes>
      <Route path="/" element={
        <div className="homepage-bg">
          <div className="homepage-overlay"></div>
          
          <button 
            className="floating-chat-btn" 
            onClick={() => navigate('/chat/advisor')}
            aria-label="Open Academic Advisor"
          >
            <span className="chat-icon">💬</span>
          </button>
        </div>
      } />
      <Route path="/chat/:id" element={
        <div className="full-screen-chat" style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-primary)' }}>
          <header className="chat-modal-header" style={{ borderBottom: '1px solid var(--border-color)', padding: '12px 24px' }}>
            <div className="header-left" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <button className="chat-back-btn" onClick={() => navigate('/')} style={{ background: 'transparent', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontWeight: '600', fontSize: '0.9rem', padding: 0 }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
                Back
              </button>
              <div style={{ width: '1px', height: '24px', background: 'var(--border-color)' }}></div>
              <div className="header-titles" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="logo-icon" style={{ fontSize: '1.2rem' }}>🎓</span>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>NITK Academic Advisor</h2>
              </div>
            </div>
          </header>

          <div className="app-body" style={{ flex: 1, minHeight: 0 }}>
            <ChatContainer scope={scope} setScope={setScope} onOpenPdf={openPdf} />
            <PdfPanel pdfState={pdfState} onClose={closePdf} />
          </div>
        </div>
      } />
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
