import React, { useState, useEffect } from 'react';
import OnboardingCalendar from './components/OnboardingCalendar';
import TechnicalDetails from './components/TechnicalDetails';

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
  const [view, setView] = useState('dashboard'); // 'dashboard' or 'tech'
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
        <div className="header-top-row">
          <div className="app-logo-group" onClick={() => setView('dashboard')} style={{ cursor: 'pointer' }}>
            <svg className="app-logo-svg" width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="2" y="2" width="20" height="20" rx="5" stroke="url(#logo-grad)" strokeWidth="2.5" />
              <path d="M6 10H10" stroke="#34d399" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M8 8V12" stroke="#34d399" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M14 14H18" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" />
              <defs>
                <linearGradient id="logo-grad" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#60a5fa" />
                  <stop offset="1" stopColor="#a78bfa" />
                </linearGradient>
              </defs>
            </svg>
            <h1 className="app-title">DailyDiff</h1>
          </div>
          <nav className="header-nav">
            <button 
              className={`nav-link-btn ${view === 'dashboard' ? 'active' : ''}`}
              onClick={() => setView('dashboard')}
            >
              Briefing
            </button>
            <button 
              className={`nav-link-btn ${view === 'tech' ? 'active' : ''}`}
              onClick={() => setView('tech')}
            >
              How It's Made
            </button>
          </nav>
        </div>
        <p className="app-subtitle">WE SCAN THE NOISE. FIVE THINGS SURVIVE.</p>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem', letterSpacing: '0.05em' }}>
          THRICE-WEEKLY: MON • WED • FRI
        </span>
      </header>

      {view === 'tech' ? (
        <TechnicalDetails />
      ) : (
        <>
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
                    <span className="topic-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="16" height="16" style={{ display: 'block' }}>
                        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
                      </svg>
                    </span>
                    <span><strong>Developer Tools:</strong> Light databases, extensions, scripts, and editors.</span>
                  </div>
                  <div className="topic-pill">
                    <span className="topic-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="#34d399" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="16" height="16" style={{ display: 'block' }}>
                        <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
                        <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
                        <line x1="6" y1="6" x2="6.01" y2="6" />
                        <line x1="6" y1="18" x2="6.01" y2="18" />
                      </svg>
                    </span>
                    <span><strong>Self-Hosted Apps:</strong> Private cloud setups, home servers, and local web tools.</span>
                  </div>
                  <div className="topic-pill">
                    <span className="topic-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="#eab308" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="16" height="16" style={{ display: 'block' }}>
                        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                      </svg>
                    </span>
                    <span><strong>Framework Updates:</strong> Tag releases and features of React, Next.js, FastAPI, Go, etc.</span>
                  </div>
                  <div className="topic-pill">
                    <span className="topic-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="#a78bfa" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="16" height="16" style={{ display: 'block' }}>
                        <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A5 5 0 0 0 8 8c0 1 .4 2.5 1.5 3.5.7.8 1.3 1.5 1.5 2.5" />
                        <path d="M9 18h6" />
                        <path d="M10 22h4" />
                      </svg>
                    </span>
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

                <div style={{ margin: '1.5rem 0 1rem', height: '1px', background: 'var(--border-color)' }}></div>
                
                <OnboardingCalendar />
              </div>
            </div>
          </section>

          {/* How It Works Section */}
          <section className="how-it-works-section glass">
            <h4 className="how-it-works-title">How It Works</h4>
            <div className="how-it-works-grid">
              <div className="how-step-card">
                <div className="how-step-num">1. AUTOMATED SCOUTING</div>
                <p className="how-step-desc">AI agents search Hacker News & GitHub for new tools and utility releases.</p>
              </div>
              <div className="how-step-card">
                <div className="how-step-num">2. NO-JARGON FILTER</div>
                <p className="how-step-desc">We remove heavy academic papers, explaining everything with simple analogies.</p>
              </div>
              <div className="how-step-card">
                <div className="how-step-num">3. INBOX DISPATCH</div>
                <p className="how-step-desc">A clean 3-minute markdown newsletter hits your inbox every Mon, Wed, and Fri.</p>
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
        </>
      )}
    </div>
  );
}
