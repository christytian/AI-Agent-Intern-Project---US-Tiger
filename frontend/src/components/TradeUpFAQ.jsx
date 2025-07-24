import React, { useState, useEffect, useRef } from 'react';
import './TradeUpFAQ.css'; // Import your CSS file

// Helper function to safely extract text from objects or strings
const extractText = (item) => {
  if (typeof item === 'string') {
    return item;
  } else if (typeof item === 'object' && item !== null) {
    return item.question || item.text || item.title || item.name || item.content || JSON.stringify(item);
  } else {
    return String(item || '');
  }
};

// Helper function to safely render array items
const renderArrayItem = (item, index, onClick = null) => {
  const text = extractText(item);
  const key = `item-${index}-${text.substring(0, 10)}`;
  
  if (onClick) {
    return (
      <span key={key} onClick={() => onClick(text)} style={{ cursor: 'pointer' }}>
        {text}
      </span>
    );
  }
  return <span key={key}>{text}</span>;
};

const TradeUpFAQ = () => {
  // State management
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [quickQuestions, setQuickQuestions] = useState([]);
  const [stats, setStats] = useState({
    totalFaqs: 'Loading...',
    totalCategories: 'Loading...',
    systemStatus: 'active'
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [isDarkMode, setIsDarkMode] = useState(() => {
    return localStorage.getItem('darkMode') === 'true';
  });
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [showScrollToTop, setShowScrollToTop] = useState(false);
  const [sessionInfo, setSessionInfo] = useState({ session_id: null, user_id: null });

  // Refs
  const chatMessagesRef = useRef(null);
  const chatInputRef = useRef(null);
  const searchTimeoutRef = useRef(null);

  // Initialize component
  useEffect(() => {
    loadQuickQuestions();
    loadStats();
    getCurrentSessionInfo();
    
    // Apply dark mode on load
    if (isDarkMode) {
      document.body.classList.add('dark-mode');
    }
  }, [isDarkMode]);

  // Session info
  const getCurrentSessionInfo = async () => {
    try {
      const response = await fetch('/api/session-info');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setSessionInfo({
        session_id: data.session_id,
        user_id: data.user_id
      });
    } catch (error) {
      console.warn('Could not get session info:', error);
      setSessionInfo({
        session_id: 'temp_session',
        user_id: 'anonymous'
      });
    }
  };

  // UPDATED loadQuickQuestions function - gets default questions from Flask
  const loadQuickQuestions = async () => {
    try {
      console.log('🔄 Loading default quick questions from Flask backend');
      const response = await fetch('/api/quick-questions'); // No keyword = gets default questions
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      console.log('📊 Default questions response:', data);
      
      let questions = [];
      
      // Handle your Flask response format
      if (data.success && Array.isArray(data.questions)) {
        questions = data.questions;
        console.log(`✅ Loaded ${questions.length} default questions`);
      } else if (Array.isArray(data)) {
        questions = data;
      } else {
        console.warn('⚠️ Unexpected response format:', data);
        questions = [];
      }
      
      // Your Flask returns simple strings for default questions
      setQuickQuestions(questions);
      
    } catch (error) {
      console.error('❌ Error loading default questions:', error);
      // Fallback to hardcoded questions if Flask is unavailable
      const fallbackQuestions = [
        "How do I open a Tiger Securities account?",
        "What documents do I need to verify my identity?",
        "What are the trading fees and commissions?",
        "How do I deposit money into my account?",
        "What are the different account types available?",
        "How long does account approval take?"
      ];
      setQuickQuestions(fallbackQuestions);
    }
  };

  // FIXED - Load system stats  
  const loadStats = async () => {
    try {
      const response = await fetch('/api/stats');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Stats raw response:', data);
      
      setStats({
        totalFaqs: data.total_faqs !== undefined ? String(data.total_faqs) : 'N/A',
        totalCategories: data.total_categories !== undefined ? String(data.total_categories) : 'N/A',
        systemStatus: data.system_status || 'error'
      });
      
    } catch (error) {
      console.error('Error loading stats:', error);
      setStats({
        totalFaqs: 'Error',
        totalCategories: 'Error',
        systemStatus: 'error'
      });
    }
  };

  // Search FAQ database
  const searchFAQDatabase = async (query) => {
    if (!query || query.trim().length < 2) return [];
  
    console.log(`🔍 Searching FAQ database for: "${query}"`);
    
    try {
      const response = await fetch('/api/search-faqs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim(), limit: 8 })
      });
      
      console.log(`📡 FAQ Search response status: ${response.status}`);
      
      if (!response.ok) {
        console.error(`❌ FAQ Search failed: HTTP ${response.status}`);
        return [];
      }
      
      const data = await response.json();
      console.log('📊 FAQ Search response:', data);
      
      if (data.success && Array.isArray(data.results)) {
        console.log(`✅ FAQ Search found ${data.results.length} results`);
        // Convert results to the format expected by your React component
        return data.results.map(result => ({
          question: result.question,
          category: result.category,
          relevance_score: result.relevance_score,
          retrieval_method: 'faq_database',
          source_type: 'hardcoded_faq'
        }));
      } else {
        console.warn('⚠️ No FAQ search results found');
        return [];
      }
    } catch (error) {
      console.error('❌ FAQ Search error:', error);
      return [];
    }
  };

  // Vectorstore Search - matches your Flask /api/quick-questions?keyword= endpoint
  const searchVectorstore = async (keyword) => {
    if (!keyword || keyword.trim().length < 2) return [];
    
    console.log(`🎯 Searching vectorstore for keyword: "${keyword}"`);
    
    try {
      const response = await fetch(`/api/quick-questions?keyword=${encodeURIComponent(keyword)}`);
      
      console.log(`📡 Vectorstore search status: ${response.status}`);
      
      if (!response.ok) {
        console.error(`❌ Vectorstore search failed: HTTP ${response.status}`);
        return [];
      }
      
      const data = await response.json();
      console.log('📊 Vectorstore search response:', data);
      
      if (data.success && Array.isArray(data.questions)) {
        console.log(`✅ Vectorstore found ${data.questions.length} questions`);
        // Your Flask backend returns simple strings from vectorstore
        return data.questions.map(question => ({
          question: question,
          category: 'General', // Your vectorstore search doesn't return category
          relevance_score: 0.9, // High relevance since it's from vectorstore
          retrieval_method: 'vectorstore',
          source_type: 'llm_powered'
        }));
      } else {
        console.warn('⚠️ No vectorstore results found');
        return [];
      }
    } catch (error) {
      console.error('❌ Vectorstore search error:', error);
      return [];
    }
  };

  // Combined search strategy that uses both your Flask endpoints
  const performCombinedSearch = async (term) => {
    console.log(`🚀 Starting combined search for: "${term}"`);
    
    let results = [];
    
    try {
      // Strategy 1: Search your vectorstore first (this is your main FAQ data)
      console.log('🎯 Strategy 1: Vectorstore search (LLM-powered)');
      const vectorResults = await searchVectorstore(term);
      
      if (vectorResults.length > 0) {
        console.log(`✅ Vectorstore found ${vectorResults.length} results`);
        results = [...results, ...vectorResults];
      }
      
      // Strategy 2: Search your hardcoded FAQ database for additional results
      console.log('🔍 Strategy 2: FAQ database search');
      const faqResults = await searchFAQDatabase(term);
      
      if (faqResults.length > 0) {
        console.log(`✅ FAQ database found ${faqResults.length} results`);
        results = [...results, ...faqResults];
      }
      
      // Remove duplicates based on question text
      const uniqueResults = [];
      const seen = new Set();
      
      for (const result of results) {
        const questionLower = result.question.toLowerCase();
        if (!seen.has(questionLower)) {
          seen.add(questionLower);
          uniqueResults.push(result);
        }
      }
      
      // Sort by relevance score (vectorstore results first, then FAQ database)
      uniqueResults.sort((a, b) => {
        if (a.retrieval_method === 'vectorstore' && b.retrieval_method !== 'vectorstore') return -1;
        if (b.retrieval_method === 'vectorstore' && a.retrieval_method !== 'vectorstore') return 1;
        return b.relevance_score - a.relevance_score;
      });
      
      // Limit results to 8
      const limitedResults = uniqueResults.slice(0, 8);
      
      console.log(`✅ Combined search returning ${limitedResults.length} unique results`);
      return limitedResults;
      
    } catch (error) {
      console.error('❌ Combined search failed:', error);
      return [];
    }
  };

  // UPDATED handleSearchChange function - integrates with your Flask backend
  const handleSearchChange = async (e) => {
    const term = e.target.value;
    setSearchTerm(term);

    // Clear previous timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    // If empty, reload original questions
    if (term.length === 0) {
      console.log('🔄 Search cleared, reloading original questions');
      loadQuickQuestions();
      return;
    }

    // For 1 character, filter locally from existing questions
    if (term.length === 1) {
      console.log(`🔍 Local filtering for: "${term}"`);
      const filtered = quickQuestions.filter(item => {
        const questionText = extractText(item);
        return questionText.toLowerCase().includes(term.toLowerCase());
      });
      console.log(`📋 Local filter: ${filtered.length} results`);
      setQuickQuestions(filtered);
      return;
    }

    // For 2+ characters, search your Flask backend with debounce
    searchTimeoutRef.current = setTimeout(async () => {
      console.log(`🚀 Backend search for: "${term}"`);
      
      try {
        // Use the combined search that hits both your Flask endpoints
        const results = await performCombinedSearch(term);
        
        if (results.length > 0) {
          console.log(`✅ Setting ${results.length} search results from Flask backend`);
          setQuickQuestions(results);
        } else {
          console.log(`❌ No results found for: "${term}"`);
          setQuickQuestions([]);
        }
        
      } catch (error) {
        console.error('💥 Backend search failed:', error);
        setQuickQuestions([]);
      }
    }, 300); // 300ms debounce
  };


  // FIXED - Ask question function
  const askQuestion = async (question) => {
    const cleanQuestion = String(question || '').trim();
    if (!cleanQuestion) return;

    setInputValue('');
    
    // Add user message
    const userMessage = { 
      type: 'user', 
      content: cleanQuestion, 
      timestamp: Date.now() 
    };
    setMessages(prev => [...prev, userMessage]);
    
    setIsLoading(true);

    try {
      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: cleanQuestion })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log('Ask question raw response:', data);
      setIsLoading(false);

      if (data.success) {
        const botMessage = {
          type: 'bot',
          content: extractText(data.response),
          sources: Array.isArray(data.sources) ? data.sources : [],
          suggested_questions: Array.isArray(data.suggested_questions) ? data.suggested_questions : [],
          system_info: {
            system_used: data.system_used || data.agent_type || 'faq_system',
            capabilities: data.capabilities || 'FAQ System',
            sources_count: data.sources_count || data.num_sources || 0,
            categories: Array.isArray(data.categories) ? data.categories : 
                       Array.isArray(data.categories_used) ? data.categories_used : []
          },
          timestamp: Date.now()
        };
        setMessages(prev => [...prev, botMessage]);
      } else {
        const errorMessage = {
          type: 'error',
          content: extractText(data.error) || 'Sorry, something went wrong.',
          timestamp: Date.now()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      setIsLoading(false);
      const errorMessage = {
        type: 'error',
        content: 'Sorry, I had trouble connecting. Please try again.',
        timestamp: Date.now()
      };
      setMessages(prev => [...prev, errorMessage]);
      console.error('Error:', error);
    }
  };

  // Debug function to test your Flask endpoints directly
  const debugFlaskEndpoints = async () => {
    console.log('🧪 Testing Flask search endpoints...');
    
    const testKeyword = 'account';
    
    // Test 1: Quick questions with keyword (vectorstore search)
    try {
      console.log(`🧪 Test 1: /api/quick-questions?keyword=${testKeyword}`);
      const response1 = await fetch(`/api/quick-questions?keyword=${testKeyword}`);
      console.log('Status:', response1.status);
      const data1 = await response1.json();
      console.log('Vectorstore Response:', data1);
    } catch (error) {
      console.error('Test 1 failed:', error);
    }
    
    // Test 2: FAQ database search
    try {
      console.log(`🧪 Test 2: /api/search-faqs with "${testKeyword}"`);
      const response2 = await fetch('/api/search-faqs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: testKeyword, limit: 8 })
      });
      console.log('Status:', response2.status);
      const data2 = await response2.json();
      console.log('FAQ Database Response:', data2);
    } catch (error) {
      console.error('Test 2 failed:', error);
    }
    
    // Test 3: Default questions (no keyword)
    try {
      console.log('🧪 Test 3: /api/quick-questions (no keyword)');
      const response3 = await fetch('/api/quick-questions');
      console.log('Status:', response3.status);
      const data3 = await response3.json();
      console.log('Default Questions Response:', data3);
    } catch (error) {
      console.error('Test 3 failed:', error);
    }
  };

  // FIXED - Submit feedback
  const submitFeedback = async (feedbackType, messageIndex) => {
    try {
      const message = messages[messageIndex];
      const prevMessage = messages[messageIndex - 1];
      const question = extractText(prevMessage?.content) || '';
      
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          answer_preview: extractText(message.content).substring(0, 200),
          feedback_type: feedbackType,
          session_id: sessionInfo.session_id,
          user_id: sessionInfo.user_id,
          system_used: message.system_info?.system_used,
          categories: Array.isArray(message.system_info?.categories) ? 
                     message.system_info.categories.map(extractText) : [],
          sources_count: message.system_info?.sources_count || 0,
          timestamp: new Date().toISOString()
        })
      });

      const result = await response.json();
      
      if (result.success) {
        // Update message with feedback status
        setMessages(prev => prev.map((msg, idx) => 
          idx === messageIndex 
            ? { ...msg, feedback: feedbackType, feedbackSubmitted: true }
            : msg
        ));
      }
    } catch (error) {
      console.error('Feedback submission failed:', error);
    }
  };

  // Handle submit
  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (inputValue.trim()) {
      askQuestion(inputValue.trim());
    }
  };

  // Toggle theme
  const toggleTheme = () => {
    const newDarkMode = !isDarkMode;
    setIsDarkMode(newDarkMode);
    localStorage.setItem('darkMode', newDarkMode);
    
    if (newDarkMode) {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
  };

  // Scroll to bottom
  const scrollToBottom = () => {
    if (chatMessagesRef.current) {
      setTimeout(() => {
        chatMessagesRef.current.scrollTo({
          top: chatMessagesRef.current.scrollHeight,
          behavior: 'smooth'
        });
      }, 100);
    }
  };

  // Handle scroll for scroll-to-top button
  const handleScroll = () => {
    if (chatMessagesRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = chatMessagesRef.current;
      setShowScrollToTop(scrollHeight - scrollTop - clientHeight > 300);
    }
  };

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Format response text
  const formatResponse = (text) => {
    const safeText = extractText(text);
    return safeText
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>');
  };

  return (
    <div className={`container ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      {/* Sidebar Toggle Button */}
      <button 
        className="sidebar-toggle"
        onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      >
        ☰
      </button>

      {/* Sidebar */}
      <div className={`sidebar ${isSidebarCollapsed ? 'collapsed' : ''}`}>
        {/* Logo */}
        <div className="logo">
          <a href="https://www.tradeup.com" target="_blank" rel="noopener noreferrer">
            <img src="/static/logo-tradeup.png" alt="TradeUP Logo" />
          </a>
          <p>Smart FAQ Assistant</p>
        </div>
        
        {/* FIXED Quick Questions Section */}
        <div className="section">
          <div className="section-title">Quick Questions</div>
          <input
            type="text"
            className="quick-search"
            placeholder="Search FAQs..."
            value={searchTerm}
            onChange={handleSearchChange}
            autoComplete="off"
          />
          <div className="quick-questions-list">
            {Array.isArray(quickQuestions) && quickQuestions.length > 0 ? (
              quickQuestions.map((item, index) => {
                const questionText = extractText(item);
                return (
                  <div 
                    key={`question-${index}`}
                    className="quick-question tiger-stripes" 
                    onClick={() => askQuestion(questionText)}
                    title={typeof item === 'object' ? `Category: ${item.category || 'General'}` : ''}
                  >
                    {questionText}
                  </div>
                );
              })
            ) : searchTerm ? (
              <div className="no-results">
                No FAQs found for "{searchTerm}"<br />
                <span>Try: account, fees, trading, margin</span>
              </div>
            ) : (
              <div className="loading-questions">
                Loading questions...
              </div>
            )}
          </div>
        </div>
        
        {/* System Stats Section */}
        <div className="section">
          <div className="section-title">System Stats</div>
          <div className="stats-card">
            <div className="stat-row">
              <span className="stat-label">Total FAQs</span>
              <span className={`stat-value ${typeof stats.totalFaqs === 'string' && stats.totalFaqs.includes('Loading') ? 'loading' : ''}`}>
                {stats.totalFaqs}
              </span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Categories</span>
              <span className={`stat-value ${typeof stats.totalCategories === 'string' && stats.totalCategories.includes('Loading') ? 'loading' : ''}`}>
                {stats.totalCategories}
              </span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Status</span>
              <span className="status-indicator">
                <span className={`status-dot ${stats.systemStatus !== 'active' ? 'error' : ''}`}></span>
                <span>{stats.systemStatus === 'active' ? 'Active' : 'Error'}</span>
              </span>
            </div>
          </div>
        </div>

        {/* Contact Us */}
        <div className="contact-us">
          <a href="mailto:service@tradeup.com">Contact Us</a>
        </div>
      </div>

      {/* Chat Container */}
      <div className="chat-container">
        {/* Chat Header */}
        <div className="chat-header">
          <div className="chat-header-content">
            <h1>Smart FAQ Assistant</h1>
            <p>Get instant answers about trading, accounts, and platform features</p>
            <button 
              className="theme-toggle"
              onClick={toggleTheme}
            >
              {isDarkMode ? '☀️' : '🌙'}
            </button>
          </div>
        </div>

        {/* Chat Messages */}
        <div 
          className="chat-messages" 
          ref={chatMessagesRef}
          onScroll={handleScroll}
        >
          {/* Welcome Message */}
          {messages.length === 0 && !isLoading && (
            <div className="welcome-message">
              <h2>Welcome to TradeUP!</h2>
              <p>Your AI FAQ assistant—for instant trading and account support.</p>
              <p>Just type your question below to get started.</p>
            </div>
          )}
          
          {/* FIXED Messages Rendering */}
          {Array.isArray(messages) ? messages.map((message, index) => (
            <div key={message.timestamp || index} className={`message ${message.type}`}>
              <div className="message-bubble">
                {message.type === 'error' ? (
                  <span className="error-text">❌ {extractText(message.content)}</span>
                ) : (
                  <div dangerouslySetInnerHTML={{__html: formatResponse(message.content)}} />
                )}
                
                {/* FIXED Sources */}
                {Array.isArray(message.sources) && message.sources.length > 0 && (
                  <div className="sources">
                    <strong>📚 Sources:</strong>
                    {message.sources.map((source, idx) => (
                      <span key={`source-${idx}`} className="source-item">
                        {extractText(source)}
                      </span>
                    ))}
                  </div>
                )}

                {/* FIXED Suggested Questions */}
                {Array.isArray(message.suggested_questions) && message.suggested_questions.length > 0 && (
                  <div className="suggested-questions">
                    <strong>💡 You might also ask:</strong><br />
                    {message.suggested_questions.map((q, idx) => {
                      const questionText = extractText(q);
                      return (
                        <span 
                          key={`suggested-${idx}`}
                          className="suggested-question" 
                          onClick={() => askQuestion(questionText)}
                        >
                          {questionText}
                        </span>
                      );
                    })}
                  </div>
                )}

                {/* Feedback Buttons */}
                {message.type === 'bot' && (
                  <div className="feedback">
                    <button 
                      className={`feedback-btn ${message.feedback === 'up' ? 'selected' : ''}`}
                      onClick={() => submitFeedback('up', index)}
                      disabled={message.feedbackSubmitted}
                    >
                      {message.feedback === 'up' && message.feedbackSubmitted ? '👍 Thanks!' : '👍'}
                    </button>
                    <button 
                      className={`feedback-btn ${message.feedback === 'down' ? 'selected' : ''}`}
                      onClick={() => submitFeedback('down', index)}
                      disabled={message.feedbackSubmitted}
                    >
                      {message.feedback === 'down' && message.feedbackSubmitted ? '👎 Thanks!' : '👎'}
                    </button>
                  </div>
                )}
              </div>

              {/* FIXED System Info */}
              {message.system_info && (
                <div className="message-info">
                  {message.system_info.system_used === 'enhanced_agent' || message.system_info.system_used === 'faq_market_agent' ? '🚀' : 
                   message.system_info.system_used === 'memory_faq' || message.system_info.system_used === 'faq_system' ? '🧠' : '📖'} 
                  {extractText(message.system_info.capabilities) || 'FAQ System'}
                  {message.system_info.sources_count && ` • 📊 ${message.system_info.sources_count} sources`}
                  {Array.isArray(message.system_info.categories) && message.system_info.categories.length > 0 && 
                    ` • 📂 ${message.system_info.categories.map(extractText).join(', ')}`}
                </div>
              )}
            </div>
          )) : null}

          {/* Loading Message */}
          {isLoading && (
            <div className="message bot loading">
              <div className="message-bubble">
                <div className="loading">
                  🐅 Tiger is thinking
                  <div className="loading-dots">
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Scroll to Top Button */}
          {showScrollToTop && (
            <button 
              className="scroll-to-top"
              onClick={() => chatMessagesRef.current?.scrollTo({top: 0, behavior: 'smooth'})}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="18,15 12,9 6,15"></polyline>
              </svg>
            </button>
          )}
        </div>

        {/* Chat Input */}
        <div className="chat-input-container">
          <div className="chat-input-form">
            <input 
              type="text" 
              className="chat-input"
              ref={chatInputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder="Ask me about trading, accounts, fees, or anything else..."
              autoComplete="off"
              disabled={isLoading}
            />
            <button 
              className="send-button"
              onClick={handleSubmit}
              disabled={isLoading || !inputValue.trim()}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22,2 15,22 11,13 2,9"></polygon>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TradeUpFAQ;