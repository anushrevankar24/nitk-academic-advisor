import React, { useState } from 'react';
import PdfCanvas from './PdfCanvas';

function PdfPanel({ pdfState, onClose }) {
  const [status, setStatus] = useState({ type: '', msg: '' });
  const [zoom, setZoom] = useState(1.0);

  return (
    <div 
      id="pdfPanel" 
      className={`pdf-panel ${pdfState.isOpen ? 'open' : ''}`}
      aria-hidden={!pdfState.isOpen}
    >
      <div className="pdf-panel-header">
        <div className="pdf-panel-title-group">
          <h2 id="pdfPanelTitle" className="pdf-panel-title">
            {pdfState.filename || 'Source Document'}
          </h2>
          <div className="pdf-panel-meta">
            <span id="pdfPanelPage" className="pdf-panel-page">
              {pdfState.filename ? `Page ${pdfState.targetPage}` : ''}
            </span>
            <span id="pdfHighlightStatus" className={`pdf-status ${status.type}`} style={{ fontSize: '0.72rem' }}>
              {status.msg}
            </span>
          </div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button 
            onClick={() => setZoom(z => Math.max(0.5, z - 0.2))} 
            style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', cursor: 'pointer', fontFamily: 'monospace' }}
            title="Zoom Out"
          >−</button>
          <span style={{ fontSize: '0.85rem', width: '38px', textAlign: 'center', fontWeight: '500' }}>{Math.round(zoom * 100)}%</span>
          <button 
            onClick={() => setZoom(z => Math.min(3.0, z + 0.2))} 
            style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', cursor: 'pointer', fontFamily: 'monospace' }}
            title="Zoom In"
          >+</button>
          
          <div style={{ width: '1px', height: '16px', background: 'var(--border-color)', margin: '0 4px' }}></div>

          <button 
            className="pdf-panel-close" 
            aria-label="Close PDF viewer"
            onClick={onClose}
          >✕</button>
        </div>
      </div>

      <div className="pdf-content">
        {status.type === 'loading' && (
          <div id="pdfLoading" className="pdf-loading visible">
            <div className="spinner"></div>
            Loading document...
          </div>
        )}
        
        {pdfState.isOpen && pdfState.filename && (
          <PdfCanvas 
            filename={pdfState.filename} 
            targetPage={pdfState.targetPage} 
            chunkText={pdfState.chunkText}
            onStatus={setStatus}
            scale={zoom}
          />
        )}
      </div>
    </div>
  );
}

export default PdfPanel;
