import React from 'react';

function Sidebar({ scope, setScope }) {
  return (
    <div className="sidebar" style={{ minWidth: '200px', borderRight: '1px solid var(--border-color)', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="scope-selector">
        <div className="scope-label">Curriculum Level</div>
        <div className="scope-pills" role="radiogroup">
          <button 
            className={`scope-pill ${scope === 'ug' ? 'active' : ''}`}
            role="radio" 
            aria-checked={scope === 'ug'}
            onClick={() => setScope('ug')}
          >
            UG (B.Tech)
          </button>
          <button 
            className={`scope-pill ${scope === 'pg' ? 'active' : ''}`}
            role="radio" 
            aria-checked={scope === 'pg'}
            onClick={() => setScope('pg')}
          >
            PG (M.Tech/Ph.D)
          </button>
        </div>
      </div>
      <div className="sidebar-info" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
        <p>This assistant answers questions based on the official NITK curriculum documents.</p>
        <p>Switch between UG and PG levels to get specific answers for your program.</p>
      </div>
    </div>
  );
}

export default Sidebar;
