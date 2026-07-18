import React, { useState, useEffect } from 'react';

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000/api'
  : 'https://dailydiff.onrender.com/api';

const MOCK_BRIEFS = [
  {
    date: '2026-07-17',
    published_at: '2026-07-17T06:00:00Z',
    briefs: [
      {
        category: 'Worth Knowing',
        title: 'LangGraph Native Parallel Branching Protocols',
        description: 'The LangChain team released a new orchestration backend that enables dynamic, self-correcting parallel routing across multi-agent state machines.',
        why_it_matters: 'This dramatically speeds up execution for deep research agents since multiple web scraper and verifier nodes can run concurrently without waiting for a single main loop thread.',
        who_cares: 'AI Engineers, backend framework builders, platform teams.',
        verdict: 'INTEGRATE',
        confidence: 94,
        source_url: 'https://github.com/langchain-ai/langgraph'
      },
      {
        category: 'Hidden Gem',
        title: 'LiteLLM Auto-Balancing Gateway Router',
        description: 'LiteLLM launched a lightweight HTTP gateway with built-in model load balancing, fallback routing, and automatic rate-limit cooldown recovery across 100+ LLM APIs.',
        why_it_matters: 'Eliminates custom retry loops and key-rotation code in production apps, shifting the reliability logic to a dedicated serverless proxy.',
        who_cares: 'Production developers, DevOps, API infrastructure teams.',
        verdict: 'WATCH',
        confidence: 88,
        source_url: 'https://github.com/BerriAI/litellm'
      },
      {
        category: 'Research Idea',
        title: 'FlashAttention-3: Ultra-Fast Attention for H100 GPUs',
        description: 'Researchers published a new GPU memory layout algorithm that utilizes asynchronous WGMMA instructions to reach 75% utilization on NVIDIA Hopper architectures.',
        why_it_matters: 'Reduces the cost of training long-context LLMs (up to 128k context lengths) by reducing the attention bottleneck on high-performance clusters.',
        who_cares: 'Machine learning engineers, training infra builders.',
        verdict: 'READ',
        confidence: 97,
        source_url: 'https://arxiv.org/abs/2407.00287'
      }
    ]
  },
  {
    date: '2026-07-15',
    published_at: '2026-07-15T06:00:00Z',
    briefs: [
      {
        category: 'Something Changed',
        title: 'FastAPI native integration of Pydantic v2 settings',
        description: 'FastAPI release v0.111 implements full support for Pydantic v2 validation logic, removing deprecation warnings and speeding up serialisation times by up to 4x.',
        why_it_matters: 'Enables faster API request validations and cleaner data modeling schemas without need for custom converters.',
        who_cares: 'Backend web developers, API engineers.',
        verdict: 'INTEGRATE',
        confidence: 91,
        source_url: 'https://github.com/tiangolo/fastapi'
      },
      {
        category: 'Keep an Eye On This',
        title: 'Verifiable Web Proofs using zkTLS protocols',
        description: 'A new developer SDK allows clients to generate zero-knowledge cryptographic proofs of private web data fetched via standard TLS connections.',
        why_it_matters: 'Allows users to prove their private account data (e.g. credit score or bank balance) to other apps without giving up their passwords or credentials.',
        who_cares: 'Security engineers, privacy developers.',
        verdict: 'WATCH',
        confidence: 82,
        source_url: 'https://huggingface.co/papers/2407.01235'
      }
    ]
  }
];

export default function App() {
  const [history, setHistory] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [expandedCards, setExpandedCards] = useState({});
  const [email, setEmail] = useState('');
  const [subStatus, setSubStatus] = useState({ type: '', message: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchBriefs() {
      try {
        const response = await fetch(`${API_BASE}/briefs/archive?limit=25`);
        if (response.ok) {
          const data = await response.json();
          if (data && data.length > 0) {
            setHistory(data);
            setLoading(false);
            return;
          }
        }
      } catch (err) {
        console.warn('FastAPI backend not reachable, trying to load local static data...');
      }
      
      // Fallback: Check if we have public JSON or use beautiful mock data
      try {
        const response = await fetch('/data/history.json');
        if (response.ok) {
          const data = await response.json();
          if (data && data.length > 0) {
            setHistory(data.reverse()); // Newest first
            setLoading(false);
            return;
          }
        }
      } catch (err) {
        console.warn('Local static file not found, using default pre-populated mock briefings.');
      }
      
      // Load pre-built mock records to ensure a stunning visual presentation
      setHistory(MOCK_BRIEFS);
      setLoading(false);
    }
    fetchBriefs();
  }, []);

  const toggleExpand = (date, index) => {
    const key = `${date}-${index}`;
    setExpandedCards((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleSubscribe = async (e) => {
    e.preventDefault();
    if (!email || !email.includes('@')) {
      setSubStatus({ type: 'error', message: 'Please enter a valid email address.' });
      return;
    }
    
    setSubStatus({ type: 'loading', message: 'Subscribing...' });
    try {
      const response = await fetch(`${API_BASE}/subscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      
      if (response.status === 201 || response.status === 200) {
        setSubStatus({ type: 'success', message: 'Awesome! You are subscribed to DailyDiff.' });
        setEmail('');
      } else {
        const data = await response.json();
        setSubStatus({ type: 'error', message: data.detail || 'Subscription failed.' });
      }
    } catch (err) {
      // Offline fallback
      setSubStatus({ 
        type: 'success', 
        message: 'Mock subscription accepted! (FastAPI local server offline, but your address is validated).' 
      });
      setEmail('');
    }
  };

  // Filtering Logic
  const filteredHistory = history.map(group => {
    const matchedBriefs = group.briefs.filter(b => {
      const matchesSearch = 
        b.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
        b.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        b.why_it_matters.toLowerCase().includes(searchQuery.toLowerCase());
        
      const matchesCategory = 
        selectedCategory === 'All' || 
        b.category.toLowerCase() === selectedCategory.toLowerCase();
        
      return matchesSearch && matchesCategory;
    });
    
    return {
      ...group,
      briefs: matchedBriefs
    };
  }).filter(group => group.briefs.length > 0);

  const categories = ['All', 'Worth Knowing', 'Hidden Gem', 'Research Idea', 'Something Changed', 'Keep an Eye On This'];

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <h1 className="app-title">DailyDiff</h1>
        <p className="app-subtitle">WE SCAN THE NOISE. FIVE THINGS SURVIVE.</p>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem', letterSpacing: '0.05em' }}>
          THRICE-WEEKLY: MON • WED • FRI
        </span>
      </header>

      {/* Intro & Landing Details Section */}
      <section className="intro-section glass">
        <div className="intro-grid">
          <div className="intro-content">
            <h2 className="intro-heading">Thrice-Weekly Tech Curation for Students & Developers</h2>
            <p className="intro-text">
              DailyDiff scans the noise of tech forums and codebases using intelligent AI agents. 
              We skip the abstract math equations and academic research papers, converting tech announcements 
              into plain, conversational English focused on real-world utility.
            </p>
            <div className="intro-topics">
              <div className="topic-pill">
                <span className="topic-icon">🛠️</span>
                <span><strong>Developer Tools:</strong> Light databases, extensions, scripts, and editors.</span>
              </div>
              <div className="topic-pill">
                <span className="topic-icon">🏠</span>
                <span><strong>Self-Hosted Apps:</strong> Private cloud setups, home servers, and local web tools.</span>
              </div>
              <div className="topic-pill">
                <span className="topic-icon">⚡</span>
                <span><strong>Framework Updates:</strong> Tag releases and features of React, Next.js, FastAPI, Go, etc.</span>
              </div>
              <div className="topic-pill">
                <span className="topic-icon">💡</span>
                <span><strong>Engineering Guides:</strong> Practical database optimizations, coding tips, and architectures.</span>
              </div>
            </div>
          </div>
          
          <div className="intro-subscribe">
            <h3 className="subscribe-title" style={{ fontSize: '1.25rem', marginBottom: '0.25rem' }}>Join the Briefing</h3>
            <p className="subscribe-text" style={{ fontSize: '0.85rem', marginBottom: '1rem' }}>
              Get a concise 3-minute markdown digest sent directly to your inbox every Mon • Wed • Fri.
            </p>
            <form onSubmit={handleSubscribe} className="subscribe-form-hero">
              <input 
                type="email" 
                placeholder="your.email@example.com" 
                className="subscribe-input-hero"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={subStatus.type === 'loading'}
              />
              <button 
                type="submit" 
                className="subscribe-button-hero"
                disabled={subStatus.type === 'loading'}
              >
                {subStatus.type === 'loading' ? 'Subscribing...' : 'Subscribe'}
              </button>
            </form>
            {subStatus.message && (
              <p className={`subscribe-message ${subStatus.type === 'success' ? 'message-success' : 'message-error'}`} style={{ marginTop: '0.75rem' }}>
                {subStatus.message}
              </p>
            )}
          </div>
        </div>
      </section>

      {/* Control Panel */}
      <div className="controls-panel glass" style={{ padding: '1rem 1.5rem' }}>
        <input 
          type="text" 
          placeholder="Search updates..." 
          className="search-input"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        
        <div className="category-filter">
          {categories.map(cat => (
            <button 
              key={cat} 
              className={`filter-btn ${selectedCategory === cat ? 'active' : ''}`}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Main timeline of briefings */}
      {loading ? (
        <div style={{ textAlign: 'center', margin: '4rem 0', color: 'var(--text-secondary)' }}>
          <p>Scouting technology updates...</p>
        </div>
      ) : filteredHistory.length === 0 ? (
        <div style={{ textAlign: 'center', margin: '4rem 0', color: 'var(--text-muted)' }}>
          <p>No briefs found matching your filter criteria.</p>
        </div>
      ) : (
        <div className="timeline">
          {filteredHistory.map((group) => (
            <div key={group.date} className="timeline-group">
              <div className="timeline-dot"></div>
              <div className="timeline-date">{group.date}</div>
              
              <div className="briefs-grid">
                {group.briefs.map((brief, index) => {
                  const key = `${group.date}-${index}`;
                  const isExpanded = !!expandedCards[key];
                  
                  return (
                    <div 
                      key={index} 
                      className="brief-card glass-card" 
                      data-category={brief.category}
                      style={{ cursor: 'pointer' }}
                      onClick={() => toggleExpand(group.date, index)}
                    >
                      <div className="card-header">
                        <span className="category-tag">{brief.category}</span>
                        <div className="footer-metrics">
                          <span className="metric-pill">Verdict: {brief.verdict}</span>
                          <span className="metric-pill">Confidence: {brief.confidence}%</span>
                        </div>
                      </div>
                      
                      <h3 className="brief-title">{brief.title}</h3>
                      <p className="brief-description">{brief.description}</p>
                      
                      {isExpanded && (
                        <div className="brief-details">
                          <div className="detail-section">
                            <span className="detail-label">Why It Matters</span>
                            <p className="detail-value">{brief.why_it_matters}</p>
                          </div>
                          
                          <div className="detail-section">
                            <span className="detail-label">Who Cares</span>
                            <p className="detail-value">{brief.who_cares}</p>
                          </div>
                          
                          {brief.source_url && (
                            <div className="detail-section" style={{ marginTop: '0.25rem' }}>
                              <a 
                                href={brief.source_url} 
                                target="_blank" 
                                rel="noreferrer" 
                                className="visit-link"
                                onClick={(e) => e.stopPropagation()} // Stop accordion toggling
                              >
                                View Source Reference &rarr;
                              </a>
                            </div>
                          )}
                        </div>
                      )}
                      
                      <div className="card-footer" style={{ borderTop: isExpanded ? 'none' : '1px solid var(--border-color)', paddingTop: isExpanded ? '0' : '0.75rem' }}>
                        <span>Click card to {isExpanded ? 'collapse' : 'reveal intelligence detail'}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Subscription Section */}
      <section className="subscribe-section glass">
        <h2 className="subscribe-title">Continuous Intelligence Delivery</h2>
        <p className="subscribe-text">
          Receive a concise 3-minute tech digest directly in your inbox. Only developments worth knowing, three times a week.
        </p>
        <form onSubmit={handleSubscribe} className="subscribe-form">
          <input 
            type="email" 
            placeholder="your.email@example.com" 
            className="subscribe-input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={subStatus.type === 'loading'}
          />
          <button 
            type="submit" 
            className="subscribe-button"
            disabled={subStatus.type === 'loading'}
          >
            {subStatus.type === 'loading' ? 'Subscribing...' : 'Subscribe'}
          </button>
        </form>
        {subStatus.message && (
          <p className={`subscribe-message ${subStatus.type === 'success' ? 'message-success' : 'message-error'}`}>
            {subStatus.message}
          </p>
        )}
      </section>
    </div>
  );
}
