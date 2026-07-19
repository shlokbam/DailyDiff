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
  const [selectedNode, setSelectedNode] = useState('trigger');

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

  const n8nNodes = [
    {
      id: 'trigger',
      name: 'Schedule Trigger',
      subtitle: 'Cron Action',
      iconColor: '#60a5fa',
      status: 'Success',
      time: '1ms',
      parameters: {
        'Interval': 'Monday, Wednesday, Friday',
        'Cron Expression': '30 3 * * 1,3,5',
        'Timezone': 'UTC (03:30) / IST (09:00)',
        'Output State': 'trigger_pulse: true'
      },
      description: 'Automatically boots the orchestration environment. GitHub Actions instantiates the workflow based on the thrice-weekly cron configuration, setting up the runner VM.',
      svg: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      )
    },
    {
      id: 'langgraph',
      name: 'LangGraph Runner',
      subtitle: 'Multi-Agent Execution',
      iconColor: '#f97316',
      status: 'Success',
      time: '14.2s',
      parameters: {
        'Executable': 'python backend/run_agent.py',
        'AI Engines': 'Gemini 1.5 Flash, Mistral 7B',
        'Agent Count': '6 Orchestrated Nodes',
        'Output State': 'final_briefs (JSON payload)'
      },
      description: 'Coordinates the multi-agent decision graph. Scout searches social feeds, Skeptic filters, Researcher reads markdown docs, Verifier runs HEAD requests, Analyst scores value, Editor writes briefing.',
      svg: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
          <path d="M12 2L2 7l10 5 10-5-10-5z" />
          <path d="M2 17l10 5 10-5" />
          <path d="M2 12l10 5 10-5" />
        </svg>
      )
    },
    {
      id: 'git',
      name: 'Git Committer',
      subtitle: 'Archive Commit',
      iconColor: '#06b6d4',
      status: 'Success',
      time: '350ms',
      parameters: {
        'Commit Bot': 'github-actions[bot]',
        'Target Path': 'data/archive/YYYY/MM/DD.md',
        'Action': 'Git Add, Commit, Push main',
        'Output State': 'Decentralized git archive updated'
      },
      description: 'Commits files directly to the code repository. It saves a snapshot of history.json, latest.md, and the custom daily markdown file, and pushes it back to main to maintain database versioning.',
      svg: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
          <circle cx="18" cy="18" r="3" />
          <circle cx="6" cy="6" r="3" />
          <circle cx="6" cy="18" r="3" />
          <path d="M6 9v6" />
          <path d="M9 6h6a3 3 0 0 1 3 3v6" />
        </svg>
      )
    },
    {
      id: 'webhook',
      name: 'POST Webhook',
      subtitle: 'FastAPI Dispatcher',
      iconColor: '#10b981',
      status: 'Success',
      time: '180ms',
      parameters: {
        'HTTP Method': 'POST',
        'URL Endpoint': '/api/notify-subscribers',
        'Auth Header': 'X-Auth-Token secret',
        'Payload': 'DailyBriefGroup object'
      },
      description: 'Invokes the subscriber dispatch listener on the FastAPI backend server. Transmits the payload containing the latest briefs and authorizes using the NOTIFY_SECRET_TOKEN.',
      svg: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
          <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
          <path d="M20 14H4a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-4a2 2 0 0 0-2-2z" />
          <line x1="6" y1="6" x2="6.01" y2="6" />
          <line x1="6" y1="18" x2="6.01" y2="18" />
        </svg>
      )
    },
    {
      id: 'smtp',
      name: 'SMTP Mailer',
      subtitle: 'Brevo Dispatch',
      iconColor: '#a855f7',
      status: 'Success',
      time: '2.5s',
      parameters: {
        'Mailing Engine': 'Brevo SMTP Dispatcher',
        'Query Target': 'subscribers.db SQLite table',
        'Template': 'Dynamic HTML briefing builder',
        'Output State': 'Emails sent to active readers'
      },
      description: 'Coordinates email delivery. FastAPI reads the SQLite subscription directory and triggers SMTP broadcasts containing styled briefings to each active reader.',
      svg: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
          <polyline points="22,6 12,13 2,6" />
        </svg>
      )
    }
  ];

  const currentNode = n8nNodes.find(n => n.id === selectedNode);

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

        <div style={{ margin: '1.5rem 0 1.25rem', height: '1px', background: 'var(--border-color)' }}></div>
        
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

      {/* End-to-End Orchestration Pipeline (n8n-style Canvas) */}
      <section className="tech-section margin-bottom-lg">
        <h3 className="section-title">End-to-End Orchestration Pipeline</h3>
        <p className="section-subtitle">Click on any node in the automated curation canvas to view its configuration, settings, and output states:</p>
        
        {/* Status Indicator */}
        <div className="n8n-canvas-status">
          <div className="status-indicator">
            <span className="status-dot"></span>
            <span>Workflow Status: <strong>Successful</strong></span>
          </div>
          <div className="status-meta">
            <span>5 Active Nodes</span>
            <span className="meta-divider">|</span>
            <span>Total Duration: <strong>17.2s</strong></span>
          </div>
        </div>

        {/* n8n Node Canvas */}
        <div className="n8n-canvas">
          <div className="n8n-nodes-flow">
            {n8nNodes.map((node, index) => (
              <React.Fragment key={node.id}>
                <div 
                  className={`n8n-node ${selectedNode === node.id ? 'n8n-node-selected' : ''}`}
                  onClick={() => setSelectedNode(node.id)}
                  style={{ '--node-color': node.iconColor }}
                >
                  {/* Ports */}
                  {index > 0 && <span className="node-port-in"></span>}
                  {index < n8nNodes.length - 1 && <span className="node-port-out"></span>}
                  
                  {/* Node Header */}
                  <div className="node-header">
                    <div className="node-icon-badge" style={{ backgroundColor: `${node.iconColor}15`, color: node.iconColor }}>
                      {node.svg}
                    </div>
                    <div className="node-status-tick">✓</div>
                  </div>
                  
                  {/* Node Content */}
                  <div className="node-body">
                    <div className="node-title">{node.name}</div>
                    <div className="node-subtitle">{node.subtitle}</div>
                  </div>
                  
                  {/* Node Footer */}
                  <div className="node-footer">
                    <span className="node-execution-time">{node.time}</span>
                  </div>
                </div>
                
                {index < n8nNodes.length - 1 && (
                  <div className="n8n-connector">
                    <svg width="40" height="20" viewBox="0 0 40 20" fill="none" style={{ display: 'block' }}>
                      <path d="M0 10H40" stroke="url(#wire-grad)" strokeWidth="2.5" strokeDasharray="5 5" className="wire-flow" />
                      <defs>
                        <linearGradient id="wire-grad" x1="0" y1="0" x2="40" y2="0" gradientUnits="userSpaceOnUse">
                          <stop stopColor={node.iconColor} />
                          <stop offset="1" stopColor={n8nNodes[index+1].iconColor} />
                        </linearGradient>
                      </defs>
                    </svg>
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Parameter Editor Drawer */}
        {currentNode && (
          <div className="n8n-parameter-editor glass animate-fade-in" style={{ '--editor-color': currentNode.iconColor }}>
            <div className="editor-header">
              <div className="editor-title-group">
                <span className="editor-icon" style={{ color: currentNode.iconColor }}>{currentNode.svg}</span>
                <div>
                  <h4>{currentNode.name} Config Panel</h4>
                  <p className="editor-subtitle">Node Parameters & State variables</p>
                </div>
              </div>
              <span className="editor-status-badge">Active Success</span>
            </div>
            
            <p className="editor-desc">{currentNode.description}</p>
            
            <div className="editor-parameters-list">
              <h5 className="parameters-heading">Node Parameters</h5>
              <div className="parameters-table">
                {Object.entries(currentNode.parameters).map(([key, value]) => (
                  <div key={key} className="parameter-row">
                    <span className="parameter-key">{key}</span>
                    <span className="parameter-value">
                      {value.startsWith('http') || value.startsWith('/') || value.includes('python') || value.includes('json') || value.includes('.db') || value.includes('.md') ? (
                        <code>{value}</code>
                      ) : (
                        value
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
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
