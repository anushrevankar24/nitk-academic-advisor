import React, { useState, useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';

function ChatContainer({ scope, setScope, onOpenPdf }) {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatHistoryRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleInputChange = (e) => {
    setInputValue(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px';
  };

  const askQuestion = async (questionText = inputValue) => {
    const question = questionText.trim();
    if (!question || isLoading) return;

    setInputValue('');
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'; // Reset height
    }

    // Add user message and loading bot message
    setMessages(prev => [
      ...prev,
      { role: 'user', content: question },
      { role: 'bot', loading: true }
    ]);
    setIsLoading(true);

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: question,
          level: scope === 'all' ? undefined : scope
        })
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const responseData = await response.json();

      setMessages(prev => {
        const newMsgs = [...prev];
        newMsgs[newMsgs.length - 1] = { role: 'bot', loading: false, data: responseData };
        return newMsgs;
      });
    } catch (error) {
      setMessages(prev => {
        const newMsgs = [...prev];
        newMsgs[newMsgs.length - 1] = { 
          role: 'bot', 
          loading: false, 
          data: {
            confidence: 0,
            answer_markdown: `**⚠️ Error:** ${error.message}. Please try again.`
          } 
        };
        return newMsgs;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      askQuestion();
    }
  };

  const fillQuestion = (text) => {
    setInputValue(text);
    if (inputRef.current) {
      inputRef.current.focus();
    }
    // We optionally could auto-send, but let's just fill
  };

  return (
    <div className="chat-container">
      <div className="chat-history" ref={chatHistoryRef}>
        <div className="chat-content-constraint">
          {messages.length === 0 ? (
            <div className="welcome-message">
              <h2>Welcome to NITK Academic Advisor</h2>
              <p>Ask me anything about NITK academic policies, regulations, curriculum, grading, attendance, and more.</p>
              <div className="example-queries">
                <p className="example-label">Try asking:</p>
                <button className="example-chip" onClick={() => fillQuestion('What is the minimum attendance required to appear for exams?')}>📋 Minimum attendance for exams?</button>
                <button className="example-chip" onClick={() => fillQuestion('How can I complete my liberal arts credits?')}>🎨 Liberal arts credit requirements?</button>
                <button className="example-chip" onClick={() => fillQuestion('What is the grading system for B.Tech?')}>📊 B.Tech grading system?</button>
                <button className="example-chip" onClick={() => fillQuestion('How do I apply for a course drop?')}>📝 Course drop procedure?</button>
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <MessageBubble key={idx} message={msg} onOpenPdf={onOpenPdf} />
            ))
          )}
        </div>
      </div>

      <div className="input-bar">
        <div className="chat-content-constraint">
          <div className="input-bar-inner">
            <div className="input-row">
            <div className="scope-inline-selector">
              <select 
                value={scope} 
                onChange={(e) => setScope(e.target.value)}
                className="scope-dropdown"
                title="Curriculum Level"
              >
                <option value="ug">UG</option>
                <option value="pg">PG</option>
              </select>
            </div>
            <textarea
              id="questionInput"
              ref={inputRef}
              placeholder="Ask a question... (Ctrl+Enter to send)"
              rows="1"
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            ></textarea>
            <button 
              className="send-btn" 
              onClick={() => askQuestion()} 
              disabled={!inputValue.trim() || isLoading}
              title="Send"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            </button>
          </div>
          <span className="input-hint"><kbd>Ctrl</kbd> + <kbd>Enter</kbd> to send</span>
        </div>
        </div>
      </div>
    </div>
  );
}

export default ChatContainer;
