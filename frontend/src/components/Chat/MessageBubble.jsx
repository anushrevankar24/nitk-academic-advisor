import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function MessageBubble({ message, onOpenPdf }) {
  const isBot = message.role === 'bot';

  if (!isBot) {
    return (
      <div className="chat-pair">
        <div className="user-message">{message.content}</div>
      </div>
    );
  }

  // Handle loading state
  if (message.loading) {
    return (
      <div className="chat-pair">
        {/* We can re-render the user message here if desired, but usually they are paired. Since our state has them flat or paired, let's assume flat list of messages for easier React management */}
        <div className="bot-message">
          <div className="typing-indicator">
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
          </div>
        </div>
      </div>
    );
  }

  const { data } = message;
  const confPercent = Math.round(data.confidence * 100);
  const confClass = confPercent >= 80 ? 'high' : confPercent >= 60 ? 'mid' : 'low';
  const confLabel = confPercent >= 80 ? 'High' : confPercent >= 60 ? 'Medium' : 'Low';

  const copyAnswer = () => {
    navigator.clipboard.writeText(data.answer_markdown);
  };

  const getConfidenceColor = (score) => {
    if (score >= 0.8) return '#22c55e';
    if (score >= 0.6) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="bot-message">
      <div className="bot-message-header">
        <span className="bot-label">
          <span className="bot-label-icon">🎓</span> Academic Advisor
        </span>
        <div className="bot-actions">
          <span className={`confidence-badge ${confClass}`} title={`Confidence: ${confPercent}%`}>
            {confLabel} {confPercent}%
          </span>
          {data.time_ms && <span className="response-time">{data.time_ms.toFixed(0)} ms</span>}
          <button className="copy-btn" onClick={copyAnswer} title="Copy answer">📋 Copy</button>
        </div>
      </div>

      <div className="answer-content">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {data.answer_markdown}
        </ReactMarkdown>
      </div>

      {data.sources && data.sources.length > 0 && (
        <SourcesSection sources={data.sources} onOpenPdf={onOpenPdf} getConfidenceColor={getConfidenceColor} />
      )}
    </div>
  );
}

function SourcesSection({ sources, onOpenPdf, getConfidenceColor }) {
  const [isOpen, setIsOpen] = React.useState(true);

  return (
    <div className="sources-section">
      <button className={`sources-toggle ${isOpen ? 'open' : ''}`} onClick={() => setIsOpen(!isOpen)}>
        <span className="sources-toggle-left">
          📚 Sources <span className="sources-count">{sources.length}</span>
        </span>
        <span className="sources-chevron">▼</span>
      </button>

      {isOpen && (
        <div className="sources-list">
          {sources.map((source, idx) => {
            const displayPage = (source.page_start || 0) + 1;
            const displayPageEnd = (source.page_end || source.page_start || 0) + 1;
            const scorePercent = Math.round(source.score * 100);
            const barColor = getConfidenceColor(source.score);
            const pages = displayPage === displayPageEnd ? `p. ${displayPage}` : `pp. ${displayPage}–${displayPageEnd}`;

            return (
              <div 
                key={idx} 
                className="source-card clickable" 
                role="button" 
                tabIndex="0"
                title={`Open ${source.pdf_name} at ${pages}`}
                onClick={() => onOpenPdf(source.pdf_name, source.page_start, source.text)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpenPdf(source.pdf_name, source.page_start, source.text); } }}
              >
                <div className="source-info">
                  <span className="source-name">{source.pdf_name}</span>
                  <span className="source-pages">{pages}</span>
                  <span className="source-open-hint">🔍 Click to view in PDF</span>
                </div>
                <div className="relevance-bar-container">
                  <div className="relevance-bar">
                    <div className="relevance-bar-fill" style={{ width: `${scorePercent}%`, background: barColor }}></div>
                  </div>
                  <span className="relevance-percent" style={{ color: barColor }}>{scorePercent}%</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default MessageBubble;
