import React, { useState, useEffect } from 'react';

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000/api'
  : 'https://dailydiff.onrender.com/api';

const getFaviconUrl = (url) => {
  if (!url) return '';
  try {
    const hostname = new URL(url).hostname;
    return `https://www.google.com/s2/favicons?sz=32&domain=${hostname}`;
  } catch {
    return '';
  }
};

const MOCK_BRIEFS = [];

export default function App() {
  const [history, setHistory] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDate, setSelectedDate] = useState('');
  const [expandedCards, setExpandedCards] = useState({});
  const [email, setEmail] = useState('');
  const [subStatus, setSubStatus] = useState({ type: '', message: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchBriefs() {
      let fetchedHistory = [];
      try {
        const response = await fetch(`${API_BASE}/briefs/archive?limit=25`);
        if (response.ok) {
          const data = await response.json();
          if (data && data.length > 0) {
            fetchedHistory = data;
          }
        }
      } catch (err) {
        console.warn('FastAPI backend not reachable, trying to load local static data...');
      }
      
      if (fetchedHistory.length === 0) {
        try {
          const response = await fetch('/data/history.json');
          if (response.ok) {
            const data = await response.json();
            if (data && data.length > 0) {
              fetchedHistory = data.reverse();
            }
          }
        } catch (err) {
          console.warn('Local static file not found, using default pre-populated mock briefings.');
        }
      }
      
      // Combine: keep fetched ones, and add mock ones that don't have the same date as a fetched one
      const fetchedDates = new Set(fetchedHistory.map(item => item.date));
      const filteredMocks = MOCK_BRIEFS.filter(item => !fetchedDates.has(item.date));
      
      const combined = [...filteredMocks, ...fetchedHistory];
      // Sort combined history by date descending
      combined.sort((a, b) => b.date.localeCompare(a.date));
      
      if (combined.length > 0) {
        setHistory(combined);
        setSelectedDate(combined[0].date);
      } else {
        setHistory(MOCK_BRIEFS);
        setSelectedDate(MOCK_BRIEFS[0].date);
      }
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

  // Filtering Logic (Show single selected edition, search within it)
  const activeGroup = history.find(group => group.date === selectedDate);
  const filteredBriefs = activeGroup ? activeGroup.briefs.filter(b => {
    return b.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
           b.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
           b.why_it_matters.toLowerCase().includes(searchQuery.toLowerCase());
  }) : [];

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
            
            <div style={{ margin: '1rem 0', height: '1px', background: 'var(--border-color)' }}></div>
            <div className="how-it-works" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <h4 style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>How it works:</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginTop: '0.25rem' }}>
                <div style={{ background: 'rgba(255,255,255,0.01)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontWeight: '600', fontSize: '0.75rem', color: '#60a5fa', marginBottom: '0.25rem', letterSpacing: '0.02em' }}>1. AUTOMATED SCOUTING</div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>AI agents search Hacker News & GitHub for new tools and utility releases.</p>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.01)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontWeight: '600', fontSize: '0.75rem', color: '#34d399', marginBottom: '0.25rem', letterSpacing: '0.02em' }}>2. NO-JARGON FILTER</div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>We remove heavy academic papers, explaining everything with simple analogies.</p>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.01)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontWeight: '600', fontSize: '0.75rem', color: '#a78bfa', marginBottom: '0.25rem', letterSpacing: '0.02em' }}>3. INBOX DISPATCH</div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>A clean 3-minute markdown newsletter hits your inbox every Mon, Wed, and Fri.</p>
                </div>
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
        
        <div className="date-selector-container">
          <label htmlFor="date-select" className="date-select-label">Edition Date:</label>
          <select 
            id="date-select" 
            className="date-select-dropdown glass"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
          >
            {history.map(group => (
              <option key={group.date} value={group.date}>
                {group.date}{group.isDemo ? ' (Demo)' : ''}{group.date === history[0]?.date ? ' (Latest)' : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main timeline of briefings */}
      {loading ? (
        <div style={{ textAlign: 'center', margin: '4rem 0', color: 'var(--text-secondary)' }}>
          <p>Scouting technology updates...</p>
        </div>
      ) : !activeGroup ? (
        <div style={{ textAlign: 'center', margin: '4rem 0', color: 'var(--text-muted)' }}>
          <p>No editions found.</p>
        </div>
      ) : (
        <div className="timeline">
          <div className="timeline-group">
            <div className="timeline-dot"></div>
            <div className="timeline-date">{activeGroup.date}</div>
            
            {filteredBriefs.length === 0 ? (
              <div style={{ textAlign: 'center', margin: '2rem 0', color: 'var(--text-muted)' }}>
                <p>No briefs found matching your search query in this edition.</p>
              </div>
            ) : (
              <div className="briefs-grid">
                {filteredBriefs.map((brief, index) => {
                  const key = `${activeGroup.date}-${index}`;
                  const isExpanded = !!expandedCards[key];
                  
                  return (
                    <div 
                      key={index} 
                      className="brief-card glass-card" 
                      data-category={brief.category}
                      style={{ cursor: 'pointer' }}
                      onClick={() => toggleExpand(activeGroup.date, index)}
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
                              <div className="source-link-container">
                                {getFaviconUrl(brief.source_url) && (
                                  <img 
                                    src={getFaviconUrl(brief.source_url)} 
                                    alt="" 
                                    className="source-favicon"
                                    onError={(e) => { e.target.style.display = 'none'; }}
                                  />
                                )}
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
                            </div>
                          )}
                        </div>
                      )}
                      
                      <div className="card-footer" style={{ borderTop: isExpanded ? 'none' : '1px solid var(--border-color)', paddingTop: isExpanded ? '0' : '0.75rem', display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                        <span>Click card to {isExpanded ? 'collapse' : 'reveal intelligence detail'}</span>
                        <span className={`chevron-indicator ${isExpanded ? 'rotated' : ''}`}>▼</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
