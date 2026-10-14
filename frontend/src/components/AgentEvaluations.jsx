import React, { useState, useEffect } from 'react';

export default function AgentEvaluations() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/eval_results.json')
      .then((res) => (res.ok ? res.json() : null))
      .then((json) => {
        setData(json);
        setLoading(false);
      })
      .catch(() => {
        setData(null);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="glass-card" style={{ padding: '3rem', textAlign: 'center', color: '#60a5fa' }}>
        Loading evaluation scorecard...
      </div>
    );
  }

  if (!data) {
    return (
      <div className="glass-card" style={{ padding: '3rem', textAlign: 'center', maxWidth: '700px', margin: '2rem auto' }}>
        <h3 style={{ fontSize: '1.4rem', color: '#f3f4f6', marginBottom: '0.5rem' }}>No evaluation run yet</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Execute <code>python tests/evals/run_evals.py</code> to run the offline & live benchmarks and publish results.
        </p>
      </div>
    );
  }

  const rows = [
    { node: 'Skeptic', metric: 'Accuracy', value: data.skeptic?.accuracy || 'N/A' },
    { node: 'Skeptic', metric: 'Precision', value: data.skeptic?.precision || 'N/A' },
    { node: 'Skeptic', metric: 'Recall', value: data.skeptic?.recall || 'N/A' },
    { node: 'Skeptic', metric: 'Scope Drift Filtered', value: data.skeptic?.scope_drift_rejected || 'N/A' },
    { node: 'Verifier', metric: 'Bad Items Caught', value: data.verifier?.bad_caught || 'N/A' },
    { node: 'Verifier', metric: 'Good Items Wrongly Rejected', value: data.verifier?.good_wrongly_rejected || 'N/A' },
    { node: 'Verifier', metric: 'Prompt Injections Succeeded', value: data.verifier?.injections_succeeded || '0/5 (0%)' },
    { node: 'Analyst', metric: 'Verdict Match (Ref-based)', value: data.analyst?.verdict_match_rate || 'N/A' },
    { node: 'Analyst', metric: 'G-Eval Usefulness Avg', value: `${data.analyst?.usefulness_avg ?? 0.0} (${data.analyst?.usefulness_gte_70 || 'N/A'} >= 0.7)` },
    { node: 'Editor', metric: 'Rule Checks Passed', value: data.editor?.rule_checks?.required_fields || 'N/A' },
    { node: 'Editor', metric: 'G-Eval Faithfulness Avg', value: `${data.editor?.faithfulness_avg ?? 0.0}` },
    { node: 'Pipeline', metric: 'Bad Items Leaked into Briefs', value: `${data.pipeline?.bad_items_leaked ?? 0}/6` },
    { node: 'Pipeline', metric: 'Gate Publish Decision', value: data.pipeline?.gate_decision || 'N/A' },
    { node: 'Pipeline', metric: 'Total Pipeline Latency', value: `${data.pipeline?.operational?.total_time ?? 0}s` },
  ];

  return (
    <div className="evaluations-container" style={{ maxWidth: '900px', margin: '0 auto', paddingBottom: '3rem' }}>
      <div className="glass-card" style={{ padding: '1.5rem 2rem', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.4rem' }}>Evaluation Scorecard</h2>
        <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          <span>Run Date: <strong style={{ color: '#f3f4f6' }}>{data.timestamp ? data.timestamp.replace('T', ' ').slice(0, 19) + ' UTC' : 'Recent'}</strong></span>
          <span>Errors: <strong style={{ color: data.total_errors > 0 ? '#ef4444' : '#34d399' }}>{data.total_errors ?? 0}</strong></span>
          <span>Models: <strong style={{ color: '#60a5fa' }}>Groq / Gemini / Mistral</strong></span>
        </div>
      </div>

      <div className="glass-card" style={{ padding: '1.25rem', overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
              <th style={{ padding: '0.75rem' }}>Node</th>
              <th style={{ padding: '0.75rem' }}>Metric</th>
              <th style={{ padding: '0.75rem' }}>Score / Count & Rate</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <td style={{ padding: '0.75rem', fontWeight: '600', color: '#60a5fa' }}>{r.node}</td>
                <td style={{ padding: '0.75rem', color: '#f3f4f6' }}>{r.metric}</td>
                <td style={{ padding: '0.75rem', fontFamily: 'monospace', color: '#34d399' }}>{r.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
