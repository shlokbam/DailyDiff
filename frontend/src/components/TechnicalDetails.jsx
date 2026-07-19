import React, { useState } from 'react';

const renderAgentIcon = (name) => {
  const strokeColor = "currentColor";
  switch (name) {
    case 'scout':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke={strokeColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="24" height="24" style={{ display: 'block', margin: '0 auto' }}>
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      );
    case 'skeptic':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke={strokeColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="24" height="24" style={{ display: 'block', margin: '0 auto' }}>
          <circle cx="12" cy="12" r="10" />
          <path d="M8 15s1.5-2 4-2 4 2 4 2" strokeWidth="2.5" />
          <line x1="9" y1="9" x2="9.01" y2="9" />
          <line x1="15" y1="9" x2="15.01" y2="9" />
        </svg>
      );
    case 'researcher':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke={strokeColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="24" height="24" style={{ display: 'block', margin: '0 auto' }}>
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        </svg>
      );
    case 'verifier':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke={strokeColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="24" height="24" style={{ display: 'block', margin: '0 auto' }}>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <polyline points="9 11 11 13 15 9" />
        </svg>
      );
    case 'analyst':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke={strokeColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="24" height="24" style={{ display: 'block', margin: '0 auto' }}>
          <line x1="18" y1="20" x2="18" y2="10" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="6" y1="20" x2="6" y2="14" />
        </svg>
      );
    case 'editor':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke={strokeColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="24" height="24" style={{ display: 'block', margin: '0 auto' }}>
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
          <path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
        </svg>
      );
    default:
      return null;
  }
};

export default function TechnicalDetails() {
  const [selectedAgent, setSelectedAgent] = useState('scout');

  const agents = [
    {
      id: 'scout',
      title: 'Scout Agent',
      icon: 'scout',
      role: 'Ecosystem Crawler',
      description: 'Periodically crawls social hubs, trending lists, and code repositories to discover newly published technologies and trending developer utilities.',
      inputs: 'None (Timer-triggered)',
      outputs: 'raw_signals (List of raw title, URL, description pairings)',
      strategy: 'Uses Gemini with tool-calling to query Hacker News top items and GitHub trending lists over the last 24-48 hours. Filters solely for libraries, tools, and databases, ignoring opinion pieces.',
      class: 'agent-scout'
    },
    {
      id: 'skeptic',
      title: 'Skeptic Agent',
      icon: 'skeptic',
      role: 'Hype Filter & Deduplicator',
      description: 'Critically examines raw signals to strip out noise, duplications, pure marketing hype, high-academic math papers, and general political or tech-business gossip.',
      inputs: 'raw_signals',
      outputs: 'candidates, criticisms',
      strategy: 'Applies rigid guidelines: rejects abstract academic papers without working code, products without public repositories, and generic SaaS marketing announcements. Performs string and vector deduplication.',
      class: 'agent-skeptic'
    },
    {
      id: 'researcher',
      title: 'Researcher Agent',
      icon: 'researcher',
      role: 'Documentation Miner',
      description: 'Takes filtered candidates and performs targeted web research. Crawls repo READMEs, official docs, package registry APIs, and open issues to gather granular engineering details.',
      inputs: 'candidates',
      outputs: 'researched_candidates',
      strategy: 'Runs concurrent scraping routines using Jina Reader API or standard HTTP fetches to extract setup commands, architectural decisions, and dependencies from documentation pages.',
      class: 'agent-research'
    },
    {
      id: 'verifier',
      title: 'Verifier Agent',
      icon: 'verifier',
      role: 'Data & Link Integrity Inspector',
      description: 'Checks the validity of gathered information. Verifies links, returns HTTP status checks on homepages, and ensures all structural JSON data matches the typing schemas.',
      inputs: 'researched_candidates',
      outputs: 'vetted_candidates, errors',
      strategy: 'Validates all source URLs via quick HEAD requests. Ensures target packages actually exist on npm/PyPI and enforces structured JSON typing checks on the candidate schema.',
      class: 'agent-verify'
    },
    {
      id: 'analyst',
      title: 'Analyst Agent',
      icon: 'analyst',
      role: 'Developer Utility Scorer',
      description: 'Scores the vetted items based on real-world utility for students, makers, and production developers. Ranks and selects the top 5 updates for the final newsletter.',
      inputs: 'vetted_candidates',
      outputs: 'vetted_candidates (Ranked and tagged)',
      strategy: 'Applies a utility score (0-100) based on accessibility (is it easy to self-host?), uniqueness (does it solve a unique problem?), and project maturity (releases and community traction).',
      class: 'agent-analyze'
    },
    {
      id: 'editor',
      title: 'Editor Agent',
      icon: 'editor',
      role: 'Plain-English Translator',
      description: 'Takes the top 5 scored items and rewrites them into concise, plain-English summaries using intuitive analogies, setting final verdicts and confidence rankings.',
      inputs: 'vetted_candidates (Top 5)',
      outputs: 'final_briefs (Ready for dispatch), history.json',
      strategy: 'Translates jargon (e.g., replaces complex matrix formulas with simpler concepts). Assigns verdicts: INTEGRATE, WATCH, or IGNORE, and formats the output into clean markdown structure.',
      class: 'agent-editor'
    }
  ];

  const currentAgent = agents.find(a => a.id === selectedAgent);

  return (
    <div className="tech-details-container animate-fade-in">
      <header className="tech-header text-center">
        <h2 className="tech-title">System Architecture</h2>
        <p className="tech-subtitle">How DailyDiff Curates and Dispatches Automagically</p>
      </header>

      {/* Intro concept card */}
      <section className="tech-card glass margin-bottom-lg">
        <h3>Autonomous Curation Engine</h3>
        <p style={{ color: 'var(--text-secondary)', lineHeight: '1.6', marginTop: '0.5rem' }}>
          DailyDiff is not written by humans curation-by-curation. Instead, it relies on a coordinated multi-agent state machine built on **LangGraph**. The system runs on a thrice-weekly cron trigger, traversing six specialized AI agent nodes to process hundreds of raw tech updates down to the **5 most valuable things** for developers.
        </p>
      </section>

      {/* Interactive Agent Graph */}
      <section className="tech-section margin-bottom-lg">
        <h3 className="section-title">LangGraph Workflow Explorer</h3>
        <p className="section-subtitle">Click on any node in the agent pipeline to view its prompt strategy and data state transformations:</p>
        
        <div className="agent-graph-visual">
          <div className="graph-nodes-line">
            {agents.map((agent, index) => (
              <React.Fragment key={agent.id}>
                <div 
                  className={`graph-node glass-card ${agent.id === selectedAgent ? 'node-selected' : ''}`}
                  onClick={() => setSelectedAgent(agent.id)}
                >
                  <div className="node-icon">{renderAgentIcon(agent.icon)}</div>
                  <div className="node-name">{agent.title.split(' ')[0]}</div>
                  <div className="node-badge">{agent.role}</div>
                </div>
                {index < agents.length - 1 && (
                  <div className="graph-connector">
                    <span className="connector-arrow">➔</span>
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>

          {/* Interactive Node Drawer */}
          {currentAgent && (
            <div className={`agent-detail-drawer glass ${currentAgent.class}`}>
              <div className="drawer-header">
                <span className="drawer-icon-large">{renderAgentIcon(currentAgent.icon)}</span>
                <div>
                  <h4 className="drawer-title">{currentAgent.title}</h4>
                  <span className="drawer-role-badge">{currentAgent.role}</span>
                </div>
              </div>
              <p className="drawer-desc">{currentAgent.description}</p>
              
              <div className="drawer-grid">
                <div className="drawer-meta-box">
                  <strong>Inputs Mutated:</strong>
                  <code>{currentAgent.inputs}</code>
                </div>
                <div className="drawer-meta-box">
                  <strong>Outputs Written:</strong>
                  <code>{currentAgent.outputs}</code>
                </div>
              </div>
              
              <div className="drawer-strategy-box">
                <h5>Curation Strategy Prompting:</h5>
                <p>{currentAgent.strategy}</p>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Tech Stack Info Grid */}
      <section className="tech-section margin-bottom-lg">
        <h3 className="section-title">The Technology Stack</h3>
        
        <div className="tech-stack-grid">
          <div className="stack-card glass-card">
            <div className="stack-header">
              <span className="stack-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="20" height="20" style={{ display: 'block' }}>
                  <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
                  <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
                  <line x1="6" y1="6" x2="6.01" y2="6" />
                  <line x1="6" y1="18" x2="6.01" y2="18" />
                </svg>
              </span>
              <h4>Backend & API</h4>
            </div>
            <ul>
              <li><strong>FastAPI (Python):</strong> High performance ASGI framework handling endpoint routing and subscribes.</li>
              <li><strong>SQLite:</strong> Local lightweight database engine for subscriber storage and metadata tracking.</li>
              <li><strong>Brevo SMTP API:</strong> Reliable transactional email delivery service dispatching briefs to inboxes.</li>
            </ul>
          </div>

          <div className="stack-card glass-card">
            <div className="stack-header">
              <span className="stack-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="#34d399" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="20" height="20" style={{ display: 'block' }}>
                  <path d="M12 2v4" />
                  <path d="M12 6a6 6 0 0 0-6 6v3h12v-3a6 6 0 0 0-6-6z" />
                  <rect x="4" y="15" width="16" height="5" rx="1" />
                  <circle cx="9" cy="11" r="1" fill="#34d399" />
                  <circle cx="15" cy="11" r="1" fill="#34d399" />
                </svg>
              </span>
              <h4>Agent Orchestration</h4>
            </div>
            <ul>
              <li><strong>LangGraph:</strong> State graph architecture modeling sequential node execution and data validation loops.</li>
              <li><strong>LangChain Community:</strong> Python libraries wrapping HTTP integrations and system prompts.</li>
              <li><strong>Gemini 1.5 & Mistral:</strong> Multimodal and instruction models powering context evaluations.</li>
            </ul>
          </div>

          <div className="stack-card glass-card">
            <div className="stack-header">
              <span className="stack-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="#a78bfa" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="20" height="20" style={{ display: 'block' }}>
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                  <path d="M2 12h20" />
                </svg>
              </span>
              <h4>Frontend Client</h4>
            </div>
            <ul>
              <li><strong>React 19:</strong> Lightweight UI components using modern custom hooks and reactive layouts.</li>
              <li><strong>Vite:</strong> Ultra-fast bundler providing Hot Module Replacement and production optimization.</li>
              <li><strong>Vanilla CSS:</strong> Sleek glassmorphic theme styling, native grid layouts, and custom scroll effects.</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Author/Backstory section */}
      <section className="author-backstory-card glass">
        <div className="author-grid">
          <div className="author-avatar-col">
            <div className="avatar-placeholder">
              <svg viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="36" height="36" style={{ display: 'block' }}>
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>
          </div>
          <div className="author-content-col">
            <h4 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.25rem' }}>About the Project</h4>
            <p style={{ fontSize: '0.8rem', color: '#60a5fa', fontWeight: '500', marginBottom: '0.75rem', letterSpacing: '0.05em', textTransform: 'uppercase' }}>Built by a Developer, for Developers</p>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
              "I built DailyDiff because I grew tired of checking Hacker News, GitHub Trending, and three different subreddits every single morning just to keep up with developer tools. I wanted to bypass the VC fundraising announcements, academic research theory, and marketing jargon."
            </p>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6', marginTop: '0.5rem' }}>
              "By feeding raw scraping outputs into a specialized LangGraph multi-agent pipeline, DailyDiff extracts the core utility of new projects and summarizes them with simple analogies. It is a completely autonomous loop from scouter to inbox."
            </p>
            <div className="author-footer" style={{ marginTop: '1rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>DailyDiff Curation Platform • 2026</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
