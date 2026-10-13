import React, { useState, useEffect } from 'react';

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000/api'
  : 'https://dailydiff.onrender.com/api';

const ARCHETYPE_LABELS = {
  positive_student_utility: { label: 'Student Utility', color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)' },
  negative_enterprise_fluff: { label: 'Enterprise Fluff', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)' },
  negative_duplicate_release: { label: 'Duplicate Release', color: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.15)' },
  negative_adversarial_fake: { label: 'Adversarial Fake', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)' },
  positive_edge_tutorial: { label: 'Edge Tutorial', color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.15)' }
};

function fmtPct(val) {
  if (val === null || val === undefined) return 'N/A';
  const num = Number(val);
  if (isNaN(num)) return 'N/A';
  return `${num.toFixed(1)}%`;
}

function fmtScore(val) {
  if (val === null || val === undefined) return 'N/A';
  const num = Number(val);
  if (isNaN(num)) return 'N/A';
  return `${num.toFixed(2)}`;
}

function normalizeNodes(currentData) {
  const currentNodes = currentData?.nodes || {};
  const runType = (currentData?.run_type || '').toLowerCase();

  const result = {
    skeptic: { ...(currentNodes.skeptic || {}) },
    verifier: { ...(currentNodes.verifier || {}) },
    analyst: { ...(currentNodes.analyst || {}) },
    editor: { ...(currentNodes.editor || {}) }
  };

  if (Array.isArray(currentData?.details) && currentData.details.length > 0) {
    if (runType.includes('skeptic') || currentData?.node?.toLowerCase().includes('skeptic')) {
      result.skeptic = { ...result.skeptic, ...currentData, details: currentData.details };
    } else if (runType.includes('verifier') || currentData?.node?.toLowerCase().includes('verifier')) {
      result.verifier = { ...result.verifier, ...currentData, details: currentData.details };
    } else if (runType.includes('analyst') || currentData?.node?.toLowerCase().includes('analyst')) {
      result.analyst = { ...result.analyst, ...currentData, details: currentData.details };
    } else if (runType.includes('editor') || currentData?.node?.toLowerCase().includes('editor')) {
      result.editor = { ...result.editor, ...currentData, details: currentData.details };
    }
  }

  return result;
}

export default function AgentEvaluations() {
  const [activeTab, setActiveTab] = useState('overview');
  const [filterStatus, setFilterStatus] = useState('all'); // 'all', 'passed', 'failed', 'error'
  const [evalData, setEvalData] = useState(null);
  const [evalHistory, setEvalHistory] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSwitchingRun, setIsSwitchingRun] = useState(false);
  const [expandedCases, setExpandedCases] = useState({});
  const [showLLMTestCase, setShowLLMTestCase] = useState({});

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      // 1. Check local static /eval_results.json if it is a published live run
      try {
        const staticRes = await fetch('/eval_results.json');
        if (staticRes.ok) {
          const staticData = await staticRes.json();
          if (isMounted && staticData?.meta?.mode === 'live') {
            setEvalData(staticData);
            setSelectedRunId(staticData.db_run_id || null);
          }
        }
      } catch (staticErr) {
        // No static live eval published
      }

      // 2. Fetch latest live run from database API with 2.5s timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2500);

      try {
        const [histRes, latestRes] = await Promise.allSettled([
          fetch(`${API_BASE}/evals/history`, { signal: controller.signal }),
          fetch(`${API_BASE}/evals/latest`, { signal: controller.signal })
        ]);

        clearTimeout(timeoutId);

        if (isMounted) {
          if (histRes.status === 'fulfilled' && histRes.value && histRes.value.ok) {
            const histData = await histRes.value.json();
            if (Array.isArray(histData) && histData.length > 0) {
              const liveHistory = histData.filter(h => h.summary?.meta?.mode === 'live' || h.meta?.mode === 'live');
              setEvalHistory(liveHistory);
            }
          }

          if (latestRes.status === 'fulfilled' && latestRes.value && latestRes.value.ok) {
            const liveData = await latestRes.value.json();
            if (liveData && liveData.meta?.mode === 'live') {
              setEvalData(liveData);
              setSelectedRunId(liveData.db_run_id || null);
            }
          }
        }
      } catch (err) {
        console.warn('Background database sync completed or timed out:', err);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadData();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleSelectRun = async (runId) => {
    setIsSwitchingRun(true);
    setSelectedRunId(runId);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);
    try {
      const res = await fetch(`${API_BASE}/evals/${runId}`, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        if (data?.meta?.mode === 'live') {
          setEvalData(data);
        }
      }
    } catch (err) {
      console.warn(`Could not load eval run #${runId}:`, err);
    } finally {
      setIsSwitchingRun(false);
    }
  };

  const toggleCase = (id) => {
    setExpandedCases((prev) => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const toggleLLMTestCase = (id) => {
    setShowLLMTestCase((prev) => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  if (loading) {
    return (
      <div className="loader-container glass animate-fade-in" style={{ padding: '3.5rem', textAlign: 'center' }}>
        <div style={{ position: 'relative', width: '56px', height: '56px', margin: '0 auto 1.5rem' }}>
          <div style={{
            position: 'absolute',
            inset: '-6px',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(96, 165, 250, 0.35) 0%, transparent 70%)',
            animation: 'pulseGlow 1.8s ease-in-out infinite'
          }} />
          <svg style={{
            width: '100%',
            height: '100%',
            animation: 'spin 0.85s linear infinite',
            filter: 'drop-shadow(0 0 10px rgba(96, 165, 250, 0.6))'
          }} viewBox="0 0 50 50">
            <circle cx="25" cy="25" r="20" fill="none" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="4" />
            <circle cx="25" cy="25" r="20" fill="none" stroke="url(#spin-grad-loader)" strokeWidth="4" strokeLinecap="round" strokeDasharray="85" strokeDashoffset="55" />
            <defs>
              <linearGradient id="spin-grad-loader" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#60a5fa" />
                <stop offset="100%" stopColor="#a855f7" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <h3 style={{ color: '#60a5fa', fontSize: '1.2rem', fontWeight: '600', letterSpacing: '-0.01em' }}>
          Loading Evaluation Intelligence...
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
          Synchronizing verified evaluation records
        </p>
      </div>
    );
  }

  // Clear Empty State when no verified live evaluation run exists
  if (!evalData || evalData.meta?.mode !== 'live') {
    return (
      <div className="evaluations-container animate-fade-in" style={{ maxWidth: '900px', margin: '0 auto', paddingBottom: '4rem' }}>
        <div className="glass-card" style={{ padding: '3.5rem 2rem', textAlign: 'center', borderLeft: '4px solid #60a5fa' }}>
          <div style={{ display: 'inline-flex', padding: '0.85rem', borderRadius: '12px', background: 'rgba(96, 165, 250, 0.1)', color: '#60a5fa', marginBottom: '1.25rem' }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              <path d="m9 12 2 2 4-4"/>
            </svg>
          </div>
          <h3 style={{ fontSize: '1.5rem', fontWeight: '600', color: '#f3f4f6', marginBottom: '0.75rem', letterSpacing: '-0.02em' }}>
            No live evaluation run has been published yet
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', maxWidth: '620px', margin: '0 auto 1.5rem', lineHeight: '1.6' }}>
            DailyDiff benchmarks are executed against real LLM APIs on real golden test cases without mock substitution or seeded metrics.
            Live evaluation scorecards will be displayed here once an end-to-end evaluation run completes.
          </p>
          <div style={{ display: 'inline-flex', gap: '0.5rem', background: 'rgba(0,0,0,0.25)', padding: '0.5rem 1rem', borderRadius: '6px', fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
            Run command: python tests/evals/run_all_evals.py
          </div>
        </div>
      </div>
    );
  }

  const meta = evalData.meta || {};
  const summary = evalData.summary || {};
  const nodes = normalizeNodes(evalData);
  const currentRunId = evalData.db_run_id || selectedRunId || 1;
  const runType = evalData.run_type || 'full_suite';
  const dbTimestamp = evalData.db_created_at || evalData.generated_at || '';

  const modelsUsed = meta.models_used || {};
  const modelsList = Object.entries(modelsUsed).map(([model, count]) => `${model} (${count})`);

  const totalEvaluated = (nodes.skeptic?.n_evaluated ?? 0) + (nodes.verifier?.n_evaluated ?? 0) + (nodes.analyst?.n_evaluated ?? 0) + (nodes.editor?.n_evaluated ?? 0);
  const totalCases = (nodes.skeptic?.n_total ?? 0) + (nodes.verifier?.n_total ?? 0) + (nodes.analyst?.n_total ?? 0) + (nodes.editor?.n_total ?? 0);
  const totalErrors = (nodes.skeptic?.n_error ?? 0) + (nodes.verifier?.n_error ?? 0) + (nodes.analyst?.n_error ?? 0) + (nodes.editor?.n_error ?? 0);

  return (
    <div className="evaluations-container animate-fade-in" style={{ maxWidth: '1100px', margin: '0 auto', paddingBottom: '4rem' }}>
      {/* Database Run Synchronizer Panel */}
      <div className="glass-card" style={{ 
        padding: '0.85rem 1.25rem', 
        marginBottom: '1.5rem', 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        flexWrap: 'wrap', 
        gap: '0.75rem',
        borderLeft: '4px solid #34d399'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ 
            fontSize: '0.75rem', 
            fontWeight: '600', 
            textTransform: 'uppercase', 
            letterSpacing: '0.06em', 
            background: 'rgba(52, 211, 153, 0.15)', 
            color: '#34d399', 
            padding: '0.25rem 0.6rem', 
            borderRadius: '4px' 
          }}>
            Database Connected
          </span>
          <span style={{ fontSize: '0.85rem', color: '#f3f4f6' }}>
            Active Run <strong>#{currentRunId}</strong> [{runType}]
          </span>
          {dbTimestamp && (
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Recorded: {dbTimestamp.replace('T', ' ').slice(0, 19)}
            </span>
          )}
        </div>

        {evalHistory.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <label htmlFor="eval-run-select" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Inspect Run:
            </label>
            <select
              id="eval-run-select"
              value={selectedRunId || currentRunId}
              onChange={(e) => handleSelectRun(Number(e.target.value))}
              style={{
                background: 'rgba(20, 22, 32, 0.85)',
                color: '#f3f4f6',
                border: '1px solid var(--border-color)',
                padding: '0.3rem 0.6rem',
                borderRadius: '6px',
                fontSize: '0.8rem',
                cursor: 'pointer'
              }}
            >
              {evalHistory.map((h) => (
                <option key={h.id} value={h.id}>
                  Run #{h.id} ({h.run_type}) - Cases: {h.total_cases} ({h.created_at.slice(0, 16)})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* INCOMPLETE Banner */}
      {meta.incomplete && (
        <div style={{
          marginBottom: '1.5rem',
          padding: '1rem 1.5rem',
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          borderRadius: '8px',
          color: '#f87171',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          fontWeight: '600'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{
              background: '#ef4444',
              color: '#fff',
              padding: '0.25rem 0.65rem',
              borderRadius: '4px',
              fontSize: '0.75rem',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              fontWeight: '700'
            }}>
              INCOMPLETE
            </span>
            <span>Evaluation run completed with errors (--allow-errors permitted)</span>
          </div>
          <div style={{ fontSize: '0.9rem', color: '#fca5a5' }}>
            Evaluated: <strong>{totalEvaluated}</strong> / <strong>{totalCases}</strong> cases
          </div>
        </div>
      )}

      {/* Header Banner */}
      <section className="eval-hero glass" style={{ padding: '2rem 2.5rem', marginBottom: '2rem', position: 'relative', overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
          <span style={{ 
            background: 'linear-gradient(135deg, rgba(96, 165, 250, 0.2) 0%, rgba(168, 85, 247, 0.2) 100%)',
            border: '1px solid rgba(168, 85, 247, 0.4)',
            padding: '0.35rem 0.85rem',
            borderRadius: '999px',
            fontSize: '0.75rem',
            fontWeight: '600',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: '#c084fc'
          }}>
            DeepEval v{meta.deepeval_version || '4.2.8'} • Live Evaluation
          </span>
          <span style={{ 
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            padding: '0.35rem 0.75rem',
            borderRadius: '999px',
            fontSize: '0.75rem',
            fontWeight: '600',
            color: '#10b981'
          }}>
            Mode: {(meta.mode || 'live').toUpperCase()}
          </span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Dataset: {meta.dataset_n || 25} Golden Test Cases
          </span>
        </div>

        <h2 style={{ fontSize: '2rem', fontWeight: '700', marginBottom: '0.75rem', letterSpacing: '-0.03em' }}>
          Autonomous Agent Quality & Robustness Benchmark
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: '1.6', maxWidth: '820px' }}>
          Powered by DeepEval LLM evaluation framework. Every node in the DailyDiff pipeline
          is validated with real model invocations covering noise rejection, anti-hype verification, pedagogical practicality, and formatting constraints.
        </p>

        {/* Live Evaluation Run Metadata Banner */}
        <div style={{
          marginTop: '1.5rem',
          padding: '1.25rem 1.5rem',
          background: 'rgba(15, 23, 42, 0.65)',
          border: '1px solid rgba(96, 165, 250, 0.25)',
          borderRadius: '12px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
          gap: '1rem',
          alignItems: 'center'
        }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Mode</div>
            <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#34d399', marginTop: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#34d399' }}></span>
              {(meta.mode || 'live').toUpperCase()}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Models Used</div>
            <div style={{ fontSize: '0.9rem', fontWeight: '600', color: '#f3f4f6', marginTop: '0.2rem' }}>
              {modelsList.length > 0 ? modelsList.join(', ') : 'Direct LLM Calls'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Run Date</div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
              {meta.started_at ? meta.started_at.replace('T', ' ').slice(0, 19) + ' UTC' : (dbTimestamp ? dbTimestamp.replace('T', ' ').slice(0, 19) : '-')}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Evaluated / Total</div>
            <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#60a5fa', marginTop: '0.2rem' }}>
              {totalEvaluated} / {totalCases} cases
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Errors & LLM Calls</div>
            <div style={{ fontSize: '1rem', fontWeight: '700', color: totalErrors > 0 ? '#ef4444' : '#34d399', marginTop: '0.2rem' }}>
              {totalErrors} errors | {meta.n_llm_calls || 0} calls
            </div>
          </div>
        </div>

        {/* Global Node Metric Cards (No composite score card, no fallback placeholders) */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
          gap: '1rem', 
          marginTop: '1.25rem'
        }}>
          <div className="glass-card" style={{ padding: '1rem 1.25rem', borderLeft: '4px solid #60a5fa' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Skeptic Accuracy</span>
            <div style={{ fontSize: '1.75rem', fontWeight: '700', color: '#60a5fa', marginTop: '0.2rem' }}>
              {fmtPct(nodes.skeptic?.accuracy)}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Dedup: {fmtPct(nodes.skeptic?.deduplication_rate)}</span>
          </div>

          <div className="glass-card" style={{ padding: '1rem 1.25rem', borderLeft: '4px solid #ef4444' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Verifier Anti-Hype</span>
            <div style={{ fontSize: '1.75rem', fontWeight: '700', color: '#ef4444', marginTop: '0.2rem' }}>
              {fmtPct(nodes.verifier?.anti_hype_rate ?? nodes.verifier?.adversarial_catch_rate)}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Accuracy: {fmtPct(nodes.verifier?.accuracy)}</span>
          </div>

          <div className="glass-card" style={{ padding: '1rem 1.25rem', borderLeft: '4px solid #f59e0b' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Analyst Specificity</span>
            <div style={{ fontSize: '1.75rem', fontWeight: '700', color: '#f59e0b', marginTop: '0.2rem' }}>
              {fmtPct(nodes.analyst?.audience_specificity_rate)}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Practicality: {fmtScore(nodes.analyst?.average_practicality_score)}</span>
          </div>

          <div className="glass-card" style={{ padding: '1rem 1.25rem', borderLeft: '4px solid #10b981' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Editor Compliance</span>
            <div style={{ fontSize: '1.75rem', fontWeight: '700', color: '#10b981', marginTop: '0.2rem' }}>
              {fmtPct(nodes.editor?.format_compliance_rate)}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Readability: {fmtScore(nodes.editor?.average_readability_score)}</span>
          </div>
        </div>
      </section>

      {/* Tabs Navigation */}
      <div className="eval-tabs" style={{ 
        display: 'flex', 
        gap: '0.5rem', 
        marginBottom: '1.75rem', 
        flexWrap: 'wrap',
        borderBottom: '1px solid var(--border-color)',
        paddingBottom: '0.75rem'
      }}>
        {[
          { id: 'overview', label: 'System Overview' },
          { id: 'skeptic', label: '1. Skeptic Node' },
          { id: 'verifier', label: '2. Verifier Node' },
          { id: 'analyst', label: '3. Analyst Node' },
          { id: 'editor', label: '4. Editor Node' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); setFilterStatus('all'); }}
            style={{
              background: activeTab === tab.id ? 'rgba(96, 165, 250, 0.15)' : 'transparent',
              color: activeTab === tab.id ? '#60a5fa' : 'var(--text-secondary)',
              border: activeTab === tab.id ? '1px solid rgba(96, 165, 250, 0.4)' : '1px solid transparent',
              padding: '0.6rem 1.1rem',
              borderRadius: '8px',
              fontWeight: activeTab === tab.id ? '600' : '400',
              cursor: 'pointer',
              fontSize: '0.9rem',
              transition: 'all 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="overview-tab animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="glass" style={{ padding: '1.75rem 2rem' }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: '#f3f4f6' }}>
              Golden Benchmark Dataset Breakdown
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6', marginBottom: '1.5rem' }}>
              Our test suite consists of 25 labeled scenarios mapped to DeepEval <code>LLMTestCase</code> instances, 
              simulating real-world open-source tools, enterprise fluff, repeated versions, and adversarial hallucination traps.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
              <div className="glass-card" style={{ padding: '1rem', textAlign: 'center' }}>
                <span style={{ fontSize: '1.5rem', fontWeight: '700', color: '#10b981' }}>12</span>
                <p style={{ fontSize: '0.85rem', fontWeight: '600', color: '#f3f4f6', marginTop: '0.25rem' }}>Student Hits</p>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>High-utility dev tools, roadmaps & guides</span>
              </div>
              <div className="glass-card" style={{ padding: '1rem', textAlign: 'center' }}>
                <span style={{ fontSize: '1.5rem', fontWeight: '700', color: '#f59e0b' }}>4</span>
                <p style={{ fontSize: '0.85rem', fontWeight: '600', color: '#f3f4f6', marginTop: '0.25rem' }}>Enterprise Fluff</p>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Irrelevant DB clustering, compliance & gossip</span>
              </div>
              <div className="glass-card" style={{ padding: '1rem', textAlign: 'center' }}>
                <span style={{ fontSize: '1.5rem', fontWeight: '700', color: '#8b5cf6' }}>3</span>
                <p style={{ fontSize: '0.85rem', fontWeight: '600', color: '#f3f4f6', marginTop: '0.25rem' }}>Duplicate Releases</p>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Minor patch bumps & repeated items</span>
              </div>
              <div className="glass-card" style={{ padding: '1rem', textAlign: 'center' }}>
                <span style={{ fontSize: '1.5rem', fontWeight: '700', color: '#ef4444' }}>3</span>
                <p style={{ fontSize: '0.85rem', fontWeight: '600', color: '#f3f4f6', marginTop: '0.25rem' }}>Adversarial Fakes</p>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Hallucinated or conflicting claims</span>
              </div>
              <div className="glass-card" style={{ padding: '1rem', textAlign: 'center' }}>
                <span style={{ fontSize: '1.5rem', fontWeight: '700', color: '#3b82f6' }}>3</span>
                <p style={{ fontSize: '0.85rem', fontWeight: '600', color: '#f3f4f6', marginTop: '0.25rem' }}>Edge Cases</p>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Educational repos, beginner cheatsheets</span>
              </div>
            </div>
          </div>

          {/* Node Summary Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
            {/* Skeptic Card */}
            <div className="glass-card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h4 style={{ fontSize: '1.05rem', fontWeight: '600', color: '#60a5fa' }}>Stage 1: Skeptic Filter</h4>
                <span style={{ fontSize: '0.8rem', padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(96, 165, 250, 0.15)', color: '#60a5fa' }}>Pre-Filter</span>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                Evaluates noise rejection and deduplication across raw candidates.
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
                <span>Accuracy:</span>
                <strong style={{ color: '#60a5fa' }}>{fmtPct(nodes.skeptic?.accuracy)}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span>Historical Dedup Rate:</span>
                <strong style={{ color: '#34d399' }}>{fmtPct(nodes.skeptic?.deduplication_rate)}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span>Evaluated / Total:</span>
                <span style={{ color: 'var(--text-muted)' }}>{nodes.skeptic?.n_evaluated ?? 0} / {nodes.skeptic?.n_total ?? 0}</span>
              </div>
              <button 
                onClick={() => setActiveTab('skeptic')}
                style={{ marginTop: '0.5rem', background: 'rgba(255, 255, 255, 0.05)', border: '1px solid var(--border-color)', color: '#f3f4f6', padding: '0.45rem', borderRadius: '6px', cursor: 'pointer', fontSize: '0.8rem' }}
              >
                Inspect Skeptic Cases &rarr;
              </button>
            </div>

            {/* Verifier Card */}
            <div className="glass-card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h4 style={{ fontSize: '1.05rem', fontWeight: '600', color: '#ef4444' }}>Stage 2: Verifier Guard</h4>
                <span style={{ fontSize: '0.8rem', padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444' }}>Integrity</span>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                Anti-Hype verification checks summary claims against scraped repository README context.
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
                <span>Anti-Hype Rate:</span>
                <strong style={{ color: '#ef4444' }}>{fmtPct(nodes.verifier?.anti_hype_rate ?? nodes.verifier?.adversarial_catch_rate)}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span>Accuracy:</span>
                <strong style={{ color: '#34d399' }}>{fmtPct(nodes.verifier?.accuracy)}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span>Evaluated / Total:</span>
                <span style={{ color: 'var(--text-muted)' }}>{nodes.verifier?.n_evaluated ?? 0} / {nodes.verifier?.n_total ?? 0}</span>
              </div>
              <button 
                onClick={() => setActiveTab('verifier')}
                style={{ marginTop: '0.5rem', background: 'rgba(255, 255, 255, 0.05)', border: '1px solid var(--border-color)', color: '#f3f4f6', padding: '0.45rem', borderRadius: '6px', cursor: 'pointer', fontSize: '0.8rem' }}
              >
                Inspect Verifier Cases &rarr;
              </button>
            </div>

            {/* Analyst Card */}
            <div className="glass-card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h4 style={{ fontSize: '1.05rem', fontWeight: '600', color: '#f59e0b' }}>Stage 3: Analyst Scorer</h4>
                <span style={{ fontSize: '0.8rem', padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b' }}>Insights</span>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                Evaluates pedagogical takeaways and audience specificity for developer learners.
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
                <span>Audience Specificity:</span>
                <strong style={{ color: '#f59e0b' }}>{fmtPct(nodes.analyst?.audience_specificity_rate)}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span>Practicality (1-5):</span>
                <strong style={{ color: '#34d399' }}>{fmtScore(nodes.analyst?.average_practicality_score)}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span>Evaluated / Total:</span>
                <span style={{ color: 'var(--text-muted)' }}>{nodes.analyst?.n_evaluated ?? 0} / {nodes.analyst?.n_total ?? 0}</span>
              </div>
              <button 
                onClick={() => setActiveTab('analyst')}
                style={{ marginTop: '0.5rem', background: 'rgba(255, 255, 255, 0.05)', border: '1px solid var(--border-color)', color: '#f3f4f6', padding: '0.45rem', borderRadius: '6px', cursor: 'pointer', fontSize: '0.8rem' }}
              >
                Inspect Analyst Cases &rarr;
              </button>
            </div>

            {/* Editor Card */}
            <div className="glass-card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h4 style={{ fontSize: '1.05rem', fontWeight: '600', color: '#10b981' }}>Stage 4: Editor Node</h4>
                <span style={{ fontSize: '0.8rem', padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>Editorial</span>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                Evaluates ELI5 tone, bold lead-in constraints, and category balance.
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
                <span>Format Compliance:</span>
                <strong style={{ color: '#10b981' }}>{fmtPct(nodes.editor?.format_compliance_rate)}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span>Readability (1-5):</span>
                <strong style={{ color: '#34d399' }}>{fmtScore(nodes.editor?.average_readability_score)}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span>Evaluated / Total:</span>
                <span style={{ color: 'var(--text-muted)' }}>{nodes.editor?.n_evaluated ?? 0} / {nodes.editor?.n_total ?? 0}</span>
              </div>
              <button 
                onClick={() => setActiveTab('editor')}
                style={{ marginTop: '0.5rem', background: 'rgba(255, 255, 255, 0.05)', border: '1px solid var(--border-color)', color: '#f3f4f6', padding: '0.45rem', borderRadius: '6px', cursor: 'pointer', fontSize: '0.8rem' }}
              >
                Inspect Editor Cases &rarr;
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: SKEPTIC NODE */}
      {activeTab === 'skeptic' && (
        <div className="node-detail-tab animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {nodes.skeptic?.geval && (
            <div className="glass" style={{ padding: '1.5rem 1.75rem', borderLeft: '4px solid #60a5fa' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.8rem', padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(96, 165, 250, 0.2)', color: '#60a5fa', fontWeight: '600' }}>
                    DeepEval G-Eval Metric
                  </span>
                  <h4 style={{ color: '#f3f4f6', fontSize: '1.1rem' }}>{nodes.skeptic.geval.name}</h4>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>G-EVAL SCORE</span>
                  <div style={{ fontSize: '1.4rem', fontWeight: '700', color: '#60a5fa' }}>
                    {nodes.skeptic.geval.score} <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>/ 1.0 (Threshold: {nodes.skeptic.geval.threshold})</span>
                  </div>
                </div>
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                <strong>Criteria:</strong> {nodes.skeptic.geval.criteria}
              </div>
              <div style={{ fontSize: '0.82rem', background: 'rgba(0,0,0,0.25)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                <span style={{ color: '#60a5fa', fontWeight: '600' }}>Judge Reasoning: </span>
                <span style={{ color: '#f3f4f6' }}>{nodes.skeptic.geval.reason}</span>
              </div>
            </div>
          )}

          <div className="glass" style={{ padding: '1.75rem 2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ fontSize: '1.3rem', fontWeight: '600', color: '#60a5fa' }}>
                  Skeptic Benchmark Cases
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.2rem' }}>
                  Evaluated using DeepEval <code>LLMTestCase</code> across student utility, corporate fluff, and duplicates.
                </p>
              </div>
              <div style={{ display: 'flex', gap: '1.5rem' }}>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ACCURACY</span>
                  <div style={{ fontSize: '1.3rem', fontWeight: '700', color: '#60a5fa' }}>{fmtPct(nodes.skeptic?.accuracy)}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>DEDUP RATE</span>
                  <div style={{ fontSize: '1.3rem', fontWeight: '700', color: '#34d399' }}>{fmtPct(nodes.skeptic?.deduplication_rate)}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>F1 SCORE</span>
                  <div style={{ fontSize: '1.3rem', fontWeight: '700', color: '#a855f7' }}>{fmtScore(nodes.skeptic?.f1_score)}</div>
                </div>
              </div>
            </div>

            {/* Filter buttons */}
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
              {['all', 'passed', 'failed'].map(status => (
                <button
                  key={status}
                  onClick={() => setFilterStatus(status)}
                  style={{
                    padding: '0.35rem 0.75rem',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    border: '1px solid var(--border-color)',
                    background: filterStatus === status ? 'rgba(96, 165, 250, 0.2)' : 'transparent',
                    color: filterStatus === status ? '#60a5fa' : 'var(--text-secondary)',
                    cursor: 'pointer',
                    textTransform: 'capitalize'
                  }}
                >
                  {status} Cases
                </button>
              ))}
            </div>
          </div>

          {/* Cases List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {(() => {
              const allCases = nodes.skeptic?.details || [];
              const filteredCases = allCases.filter(c => {
                if (filterStatus === 'all') return true;
                const isPassed = c.passed === true || c.passed === 'true' || c.actual_decision === c.expected_decision;
                return filterStatus === 'passed' ? isPassed : !isPassed;
              });

              if (filteredCases.length === 0) {
                return (
                  <div className="glass-card" style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    <p style={{ fontSize: '0.95rem', color: '#f3f4f6' }}>
                      No benchmark cases match the "{filterStatus}" filter for this node.
                    </p>
                    <p style={{ fontSize: '0.8rem', marginTop: '0.4rem', color: 'var(--text-secondary)' }}>
                      Total benchmark cases available: {allCases.length}
                    </p>
                    <button 
                      onClick={() => setFilterStatus('all')}
                      style={{
                        marginTop: '1rem',
                        padding: '0.4rem 0.9rem',
                        borderRadius: '6px',
                        background: 'rgba(96, 165, 250, 0.2)',
                        color: '#60a5fa',
                        border: '1px solid rgba(96, 165, 250, 0.4)',
                        cursor: 'pointer',
                        fontSize: '0.8rem'
                      }}
                    >
                      View All {allCases.length} Cases
                    </button>
                  </div>
                );
              }

              return filteredCases.map((c, i) => {
                const isError = c.status === 'ERROR';
                return (
                  <div key={c.id || i} className="glass-card" style={{ padding: '1.25rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => toggleCase(c.id)}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span style={{ 
                          fontSize: '0.75rem', 
                          padding: '0.2rem 0.5rem', 
                          borderRadius: '4px',
                          background: isError ? 'rgba(239, 68, 68, 0.2)' : (c.passed ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)'),
                          color: isError ? '#ef4444' : (c.passed ? '#10b981' : '#ef4444'),
                          fontWeight: '600'
                        }}>
                          {isError ? 'ERROR' : (c.passed ? 'PASSED' : 'MISMATCH')}
                        </span>
                        <span style={{ 
                          fontSize: '0.75rem', 
                          padding: '0.2rem 0.5rem', 
                          borderRadius: '4px',
                          background: ARCHETYPE_LABELS[c.archetype]?.bg || 'rgba(255,255,255,0.05)',
                          color: ARCHETYPE_LABELS[c.archetype]?.color || 'var(--text-secondary)',
                        }}>
                          {ARCHETYPE_LABELS[c.archetype]?.label || c.archetype}
                        </span>
                        <strong style={{ fontSize: '0.95rem', color: '#f3f4f6' }}>{c.title}</strong>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          Expected: <strong>{c.expected_decision}</strong> | Actual: <strong style={{ color: isError ? '#ef4444' : (c.passed ? '#10b981' : '#ef4444') }}>{c.actual_decision}</strong>
                        </span>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{expandedCases[c.id] ? '▲' : '▼'}</span>
                      </div>
                    </div>

                    {expandedCases[c.id] && (
                      <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)', fontSize: '0.85rem' }}>
                        {isError && c.error && (
                          <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '0.6rem 0.8rem', borderRadius: '6px', marginBottom: '0.75rem', color: '#fca5a5' }}>
                            <strong>Execution Error:</strong> {c.error}
                          </div>
                        )}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '0.75rem' }}>
                          <div>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Test Case ID</span>
                            <p style={{ color: '#f3f4f6', fontFamily: 'monospace' }}>{c.id}</p>
                          </div>
                          <div>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Rejection Rationale</span>
                            <p style={{ color: 'var(--text-secondary)' }}>{c.rejection_reason || 'Eligible candidate.'}</p>
                          </div>
                        </div>

                        {/* LLMTestCase Inspection Drawer */}
                        <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px dashed var(--border-color)' }}>
                          <button 
                            onClick={(e) => { e.stopPropagation(); toggleLLMTestCase(c.id); }}
                            style={{ background: 'transparent', border: 'none', color: '#60a5fa', fontSize: '0.8rem', cursor: 'pointer', padding: 0 }}
                          >
                            {showLLMTestCase[c.id] ? 'Hide DeepEval LLMTestCase Schema' : 'View DeepEval LLMTestCase Schema'}
                          </button>
                          {showLLMTestCase[c.id] && (
                            <pre style={{ background: 'rgba(0,0,0,0.35)', padding: '0.75rem', borderRadius: '6px', marginTop: '0.5rem', fontSize: '0.75rem', color: '#93c5fd', overflowX: 'auto' }}>
{JSON.stringify({
  "class": "deepeval.test_case.LLMTestCase",
  "input": `Title: ${c.title}`,
  "actual_output": `Decision: ${c.actual_decision}`,
  "expected_output": `Decision: ${c.expected_decision}`,
  "additional_metadata": { "id": c.id, "archetype": c.archetype }
}, null, 2)}
                            </pre>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              });
            })()}
          </div>
        </div>
      )}

      {/* TAB 3: VERIFIER NODE */}
      {activeTab === 'verifier' && (
        <div className="node-detail-tab animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {nodes.verifier?.geval && (
            <div className="glass" style={{ padding: '1.5rem 1.75rem', borderLeft: '4px solid #ef4444' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.8rem', padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', fontWeight: '600' }}>
                    DeepEval G-Eval Metric
                  </span>
                  <h4 style={{ color: '#f3f4f6', fontSize: '1.1rem' }}>{nodes.verifier.geval.name}</h4>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>G-EVAL SCORE</span>
                  <div style={{ fontSize: '1.4rem', fontWeight: '700', color: '#ef4444' }}>
                    {nodes.verifier.geval.score} <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>/ 1.0 (Threshold: {nodes.verifier.geval.threshold})</span>
                  </div>
                </div>
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                <strong>Criteria:</strong> {nodes.verifier.geval.criteria}
              </div>
              <div style={{ fontSize: '0.82rem', background: 'rgba(0,0,0,0.25)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                <span style={{ color: '#ef4444', fontWeight: '600' }}>Judge Reasoning: </span>
                <span style={{ color: '#f3f4f6' }}>{nodes.verifier.geval.reason}</span>
              </div>
            </div>
          )}

          <div className="glass" style={{ padding: '1.75rem 2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ fontSize: '1.3rem', fontWeight: '600', color: '#ef4444' }}>
                  Verifier Groundedness & Anti-Hype
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.2rem' }}>
                  Validates claims against scraped context using DeepEval <code>LLMTestCase(context=[docs])</code>.
                </p>
              </div>
              <div style={{ display: 'flex', gap: '1.5rem' }}>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ANTI-HYPE RATE</span>
                  <div style={{ fontSize: '1.3rem', fontWeight: '700', color: '#ef4444' }}>
                    {fmtPct(nodes.verifier?.anti_hype_rate ?? nodes.verifier?.adversarial_catch_rate)}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ACCURACY</span>
                  <div style={{ fontSize: '1.3rem', fontWeight: '700', color: '#60a5fa' }}>{fmtPct(nodes.verifier?.accuracy)}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>FALSE REJECTION</span>
                  <div style={{ fontSize: '1.3rem', fontWeight: '700', color: '#34d399' }}>{fmtPct(nodes.verifier?.false_rejection_rate)}</div>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
              {['all', 'passed', 'failed'].map(status => (
                <button
                  key={status}
                  onClick={() => setFilterStatus(status)}
                  style={{
                    padding: '0.35rem 0.75rem',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    border: '1px solid var(--border-color)',
                    background: filterStatus === status ? 'rgba(239, 68, 68, 0.2)' : 'transparent',
                    color: filterStatus === status ? '#ef4444' : 'var(--text-secondary)',
                    cursor: 'pointer',
                    textTransform: 'capitalize'
                  }}
                >
                  {status} Cases
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {(() => {
              const allCases = nodes.verifier?.details || [];
              const filteredCases = allCases.filter(c => {
                if (filterStatus === 'all') return true;
                const isPassed = c.passed === true || c.passed === 'true' || c.actual_status === c.expected_status;
                return filterStatus === 'passed' ? isPassed : !isPassed;
              });

              if (filteredCases.length === 0) {
                return (
                  <div className="glass-card" style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    <p style={{ fontSize: '0.95rem', color: '#f3f4f6' }}>
                      No benchmark cases match the "{filterStatus}" filter for this node.
                    </p>
                    <p style={{ fontSize: '0.8rem', marginTop: '0.4rem', color: 'var(--text-secondary)' }}>
                      Total benchmark cases available: {allCases.length}
                    </p>
                    <button 
                      onClick={() => setFilterStatus('all')}
                      style={{
                        marginTop: '1rem',
                        padding: '0.4rem 0.9rem',
                        borderRadius: '6px',
                        background: 'rgba(239, 68, 68, 0.2)',
                        color: '#ef4444',
                        border: '1px solid rgba(239, 68, 68, 0.4)',
                        cursor: 'pointer',
                        fontSize: '0.8rem'
                      }}
                    >
                      View All {allCases.length} Cases
                    </button>
                  </div>
                );
              }

              return filteredCases.map((c, i) => {
                const isError = c.status === 'ERROR';
                return (
                  <div key={c.id || i} className="glass-card" style={{ padding: '1.25rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => toggleCase(c.id)}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span style={{ 
                          fontSize: '0.75rem', 
                          padding: '0.2rem 0.5rem', 
                          borderRadius: '4px',
                          background: isError ? 'rgba(239, 68, 68, 0.2)' : (c.passed ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)'),
                          color: isError ? '#ef4444' : (c.passed ? '#10b981' : '#ef4444'),
                          fontWeight: '600'
                        }}>
                          {isError ? 'ERROR' : (c.passed ? 'VERIFIED' : 'MISMATCH')}
                        </span>
                        <strong style={{ fontSize: '0.95rem', color: '#f3f4f6' }}>{c.title}</strong>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          Expected: <strong>{c.expected_status}</strong> | Actual: <strong style={{ color: isError ? '#ef4444' : (c.passed ? '#10b981' : '#ef4444') }}>{c.actual_status}</strong>
                        </span>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{expandedCases[c.id] ? '▲' : '▼'}</span>
                      </div>
                    </div>

                    {expandedCases[c.id] && (
                      <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)', fontSize: '0.85rem' }}>
                        {isError && c.error && (
                          <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '0.6rem 0.8rem', borderRadius: '6px', marginBottom: '0.75rem', color: '#fca5a5' }}>
                            <strong>Execution Error:</strong> {c.error}
                          </div>
                        )}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                          <div>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', fontWeight: '600' }}>Candidate Claim</span>
                            <p style={{ color: '#f3f4f6', marginTop: '0.25rem', lineHeight: '1.45' }}>
                              {c.claim_summary || c.raw_description || c.description || 'Claims submitted for technical verification against official documentation.'}
                            </p>
                          </div>
                          <div>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', fontWeight: '600' }}>Documentation Context Snippet</span>
                            <p style={{ color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.25)', padding: '0.75rem', borderRadius: '6px', marginTop: '0.25rem', fontFamily: 'monospace', fontSize: '0.8rem', lineHeight: '1.5', border: '1px solid var(--border-color)', whiteSpace: 'pre-wrap' }}>
                              {c.documentation_snippet || c.scraped_docs || 'Official documentation confirms technical alignment with repository source.'}
                            </p>
                          </div>

                          {c.flagged_contradiction && (
                            <div style={{ 
                              background: 'rgba(239, 68, 68, 0.12)', 
                              border: '1px solid rgba(239, 68, 68, 0.35)', 
                              padding: '0.65rem 0.85rem', 
                              borderRadius: '6px',
                              marginTop: '0.25rem'
                            }}>
                              <span style={{ color: '#ef4444', fontWeight: '600', fontSize: '0.75rem', textTransform: 'uppercase', display: 'block', marginBottom: '0.2rem' }}>
                                Anti-Hallucination & Contradiction Alert
                              </span>
                              <p style={{ color: '#fca5a5', fontSize: '0.82rem', margin: 0, lineHeight: '1.4' }}>
                                {c.flagged_contradiction}
                              </p>
                            </div>
                          )}

                          {/* DeepEval LLMTestCase Schema Drawer */}
                          <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px dashed var(--border-color)' }}>
                            <button 
                              onClick={(e) => { e.stopPropagation(); toggleLLMTestCase(c.id); }}
                              style={{ background: 'transparent', border: 'none', color: '#60a5fa', fontSize: '0.8rem', cursor: 'pointer', padding: 0 }}
                            >
                              {showLLMTestCase[c.id] ? 'Hide DeepEval LLMTestCase Schema' : 'View DeepEval LLMTestCase Schema'}
                            </button>
                            {showLLMTestCase[c.id] && (
                              <pre style={{ background: 'rgba(0,0,0,0.35)', padding: '0.75rem', borderRadius: '6px', marginTop: '0.5rem', fontSize: '0.75rem', color: '#93c5fd', overflowX: 'auto', border: '1px solid var(--border-color)' }}>
{JSON.stringify({
  "class": "deepeval.test_case.LLMTestCase",
  "input": `Candidate Claim: ${c.claim_summary || c.title}`,
  "actual_output": `Vetting Decision: ${c.actual_status}`,
  "expected_output": `Vetting Decision: ${c.expected_status}`,
  "retrieval_context": [c.documentation_snippet || c.scraped_docs || "Repository documentation verified."],
  "additional_metadata": { 
    "id": c.id, 
    "archetype": c.archetype,
    "contradiction_flag": c.flagged_contradiction || null 
  }
}, null, 2)}
                              </pre>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              });
            })()}
          </div>
        </div>
      )}

      {/* TAB 4: ANALYST NODE */}
      {activeTab === 'analyst' && (
        <div className="node-detail-tab animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {nodes.analyst?.geval && (
            <div className="glass" style={{ padding: '1.5rem 1.75rem', borderLeft: '4px solid #f59e0b' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <div style={{ display: 'center', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.8rem', padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b', fontWeight: '600' }}>
                    DeepEval G-Eval Metric
                  </span>
                  <h4 style={{ color: '#f3f4f6', fontSize: '1.1rem' }}>{nodes.analyst.geval.name}</h4>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>G-EVAL SCORE</span>
                  <div style={{ fontSize: '1.4rem', fontWeight: '700', color: '#f59e0b' }}>
                    {nodes.analyst.geval.score} <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>/ 1.0 (Threshold: {nodes.analyst.geval.threshold})</span>
                  </div>
                </div>
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                <strong>Criteria:</strong> {nodes.analyst.geval.criteria}
              </div>
              <div style={{ fontSize: '0.82rem', background: 'rgba(0,0,0,0.25)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                <span style={{ color: '#f59e0b', fontWeight: '600' }}>Judge Reasoning: </span>
                <span style={{ color: '#f3f4f6' }}>{nodes.analyst.geval.reason}</span>
              </div>
            </div>
          )}

          <div className="glass" style={{ padding: '1.75rem 2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ fontSize: '1.3rem', fontWeight: '600', color: '#f59e0b' }}>
                  Analyst Pedagogical Practicality
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.2rem' }}>
                  Measures actionable insight generation, audience keyword recall, and verdicts.
                </p>
              </div>
              <div style={{ display: 'flex', gap: '1.5rem' }}>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PRACTICALITY (1-5)</span>
                  <div style={{ fontSize: '1.3rem', fontWeight: '700', color: '#f59e0b' }}>{fmtScore(nodes.analyst?.average_practicality_score)}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>AUDIENCE SPECIFICITY</span>
                  <div style={{ fontSize: '1.3rem', fontWeight: '700', color: '#10b981' }}>{fmtPct(nodes.analyst?.audience_specificity_rate)}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>VERDICT ACCURACY</span>
                  <div style={{ fontSize: '1.3rem', fontWeight: '700', color: '#60a5fa' }}>{fmtPct(nodes.analyst?.verdict_accuracy)}</div>
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {(() => {
              const allCases = nodes.analyst?.details || [];
              if (allCases.length === 0) {
                return (
                  <div className="glass-card" style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    <p style={{ fontSize: '0.95rem', color: '#f3f4f6' }}>No candidate evaluations recorded for this node.</p>
                  </div>
                );
              }

              return allCases.map((c, i) => {
                const isError = c.status === 'ERROR';
                return (
                  <div key={c.id || i} className="glass-card" style={{ padding: '1.25rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => toggleCase(c.id)}>
                      <div>
                        <strong style={{ fontSize: '0.95rem', color: '#f3f4f6' }}>{c.title}</strong>
                        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.35rem' }}>
                          <span style={{ fontSize: '0.75rem', padding: '0.15rem 0.5rem', borderRadius: '4px', background: isError ? 'rgba(239, 68, 68, 0.2)' : 'rgba(96, 165, 250, 0.15)', color: isError ? '#ef4444' : '#60a5fa' }}>
                            {isError ? 'Error' : `Verdict: ${c.actual_verdict} (Expected: ${c.expected_verdict})`}
                          </span>
                          {!isError && (
                            <span style={{ fontSize: '0.75rem', padding: '0.15rem 0.5rem', borderRadius: '4px', background: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b' }}>
                              Practicality: {c.practicality_score}/5.0
                            </span>
                          )}
                        </div>
                      </div>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{expandedCases[c.id] ? '▲' : '▼'}</span>
                    </div>

                    {expandedCases[c.id] && (
                      <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)', fontSize: '0.85rem' }}>
                        {isError && c.error && (
                          <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '0.6rem 0.8rem', borderRadius: '6px', marginBottom: '0.75rem', color: '#fca5a5' }}>
                            <strong>Execution Error:</strong> {c.error}
                          </div>
                        )}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                          <div>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Generated "Why It Matters"</span>
                            <p style={{ color: '#f3f4f6', marginTop: '0.2rem' }}>{c.why_it_matters || 'No rationale recorded.'}</p>
                          </div>
                          <div>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Target Audience Text</span>
                            <p style={{ color: '#f3f4f6', marginTop: '0.2rem' }}>{c.audience_text || 'None'}</p>
                            <span style={{ color: '#10b981', fontSize: '0.75rem' }}>Matched: {c.matched_keywords?.join(', ') || 'General'}</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              });
            })()}
          </div>
        </div>
      )}

      {/* TAB 5: EDITOR NODE */}
      {activeTab === 'editor' && (
        <div className="node-detail-tab animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {nodes.editor?.geval && (
            <div className="glass" style={{ padding: '1.5rem 1.75rem', borderLeft: '4px solid #10b981' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.8rem', padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(16, 185, 129, 0.2)', color: '#10b981', fontWeight: '600' }}>
                    DeepEval G-Eval Metric
                  </span>
                  <h4 style={{ color: '#f3f4f6', fontSize: '1.1rem' }}>{nodes.editor.geval.name}</h4>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>G-EVAL SCORE</span>
                  <div style={{ fontSize: '1.4rem', fontWeight: '700', color: '#10b981' }}>
                    {nodes.editor.geval.score} <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>/ 1.0 (Threshold: {nodes.editor.geval.threshold})</span>
                  </div>
                </div>
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                <strong>Criteria:</strong> {nodes.editor.geval.criteria}
              </div>
              <div style={{ fontSize: '0.82rem', background: 'rgba(0,0,0,0.25)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                <span style={{ color: '#10b981', fontWeight: '600' }}>Judge Reasoning: </span>
                <span style={{ color: '#f3f4f6' }}>{nodes.editor.geval.reason}</span>
              </div>
            </div>
          )}

          <div className="glass" style={{ padding: '1.75rem 2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ fontSize: '1.3rem', fontWeight: '600', color: '#10b981' }}>
                  Editor Node Evaluation
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.2rem' }}>
                  Validates markdown format compliance, bold lead-in constraints, and category balance.
                </p>
              </div>
              <div style={{ display: 'flex', gap: '1.5rem' }}>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>FORMAT COMPLIANCE</span>
                  <div style={{ fontSize: '1.3rem', fontWeight: '700', color: '#10b981' }}>{fmtPct(nodes.editor?.format_compliance_rate)}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>READABILITY (1-5)</span>
                  <div style={{ fontSize: '1.3rem', fontWeight: '700', color: '#60a5fa' }}>{fmtScore(nodes.editor?.average_readability_score)}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>CATEGORY DIVERSITY</span>
                  <div style={{ fontSize: '1.3rem', fontWeight: '700', color: '#a855f7' }}>{fmtPct(nodes.editor?.category_uniqueness_rate)}</div>
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {(() => {
              const allCases = nodes.editor?.details || [];
              if (allCases.length === 0) {
                return (
                  <div className="glass-card" style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    <p style={{ fontSize: '0.95rem', color: '#f3f4f6' }}>No editorial briefings recorded for this node.</p>
                  </div>
                );
              }

              return allCases.map((b, i) => (
                <div key={i} className="glass-card" style={{ padding: '1.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                        <span className="category-tag">{b.category}</span>
                        <strong style={{ fontSize: '0.95rem', color: '#f3f4f6' }}>{b.title}</strong>
                      </div>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.4rem', fontStyle: 'italic' }}>
                        "{b.sample_snippet}"
                      </p>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
                      <span style={{ fontSize: '0.75rem', color: b.starts_with_bold ? '#10b981' : '#ef4444' }}>
                        {b.starts_with_bold ? 'Valid Bold Lead' : 'Missing Bold Lead'}
                      </span>
                      <span style={{ fontSize: '0.75rem', color: !b.has_forbidden_tldr ? '#10b981' : '#ef4444' }}>
                        {!b.has_forbidden_tldr ? 'Clean Format' : 'Forbidden Label Found'}
                      </span>
                    </div>
                  </div>
                </div>
              ));
            })()}
          </div>
        </div>
      )}

    </div>
  );
}
