import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { PublicClientApplication, InteractionRequiredAuthError } from '@azure/msal-browser';
import { AlertTriangle, ArrowLeft, Check, ClipboardCheck, LogIn, LogOut, RefreshCw, RotateCcw, X } from 'lucide-react';
import '@fontsource-variable/dm-sans';
import './style.css';
import { ApiError, decisionFailure, formatList, formatTimestamp, premiumView } from './format';
import { decisionRequest } from './request';

const NOTICE = 'Training simulation. Synthetic data only. Not an insurance quote and not a real underwriting decision.';
const REASON_PATTERN = /^[A-Z0-9_]{1,64}$/;

function Notice() {
  return <div className="notice" role="note"><AlertTriangle size={15} aria-hidden="true" /><span>{NOTICE}</span></div>;
}

/** Renders the premium, or the state that explains why there is no figure. */
function Premium({ record, detailed = false }) {
  const view = premiumView(record);
  if (view.kind !== 'amount') {
    return <span className="unpriced">
      <span className="unpriced-label">{view.label}</span>
      <span className="unpriced-reason">{view.reason}</span>
    </span>;
  }
  return <span className="premium">{view.amount}{detailed && view.period ? <span className="period"> per {view.period.replace(/_/g, ' ').toLowerCase()}</span> : null}</span>;
}

function Queue({ cases, onOpen, onRefresh, busy, headingRef, failed }) {
  return <section className="panel">
    <div className="panel-head">
      <div><span className="overline">DESJARDINS / CASE REVIEW</span><h1 ref={headingRef} tabIndex={-1}>Pending review</h1></div>
      <button className="secondary" type="button" onClick={onRefresh} disabled={busy}><RefreshCw size={16} aria-hidden="true" />Refresh</button>
    </div>
    <Notice />
    {/* An empty list after a failed load means the queue is unknown, not empty.
        Saying "no cases" there tells a reviewer nothing is waiting when the
        backend could not be reached, which is the one wrong answer to give. */}
    {!cases.length
      ? (failed
        ? <p className="empty-queue">The queue could not be loaded, so it is not known whether any cases are waiting. See the message above and use Refresh to try again.</p>
        : <p className="empty-queue">No cases are waiting for review.</p>)
      : <div className="queue-scroll" role="region" aria-label="Case queue" tabIndex={0}>
        <table className="queue">
          <caption className="visually-hidden">Cases awaiting review</caption>
          <thead><tr>
            <th scope="col">Case</th><th scope="col">State</th><th scope="col">Rev</th>
            <th scope="col">Preparer</th><th scope="col">Submitted</th><th scope="col">Premium</th><th scope="col"><span className="visually-hidden">Open</span></th>
          </tr></thead>
          <tbody>
            {cases.map(record => <tr key={record.caseId}>
              <th scope="row">{record.caseId}</th>
              <td><span className="state">{record.state}</span></td>
              <td>{record.revision}</td>
              <td className="actor">{record.preparerId}</td>
              <td>{formatTimestamp(record.updatedAt)}</td>
              <td><Premium record={record} /></td>
              <td><button className="secondary" type="button" disabled={busy}
                aria-label={`Review case ${record.caseId}`}
                onClick={() => onOpen(record.caseId)}>Review</button></td>
            </tr>)}
          </tbody>
        </table>
      </div>}
  </section>;
}

function ReasonPrompt({ command, value, onChange, onConfirm, onCancel, busy }) {
  const invalid = value !== '' && !REASON_PATTERN.test(value);
  return <form className="reason" onSubmit={event => { event.preventDefault(); if (!invalid) onConfirm(); }}>
    <label htmlFor="reason-code">Reason code for {command} (optional)</label>
    <input id="reason-code" value={value} maxLength={64} autoComplete="off" placeholder="MISSING_PLAN"
      aria-describedby="reason-help" aria-invalid={invalid}
      onChange={event => onChange(event.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, '_'))} />
    <span id="reason-help" className="reason-help">{invalid ? 'Use up to 64 characters: A-Z, 0-9, underscore.' : 'Leave blank to record no reason.'}</span>
    <div className="reason-actions">
      <button className="primary" type="submit" disabled={busy || invalid}>Confirm {command}</button>
      <button className="secondary" type="button" disabled={busy} onClick={onCancel}>Cancel</button>
    </div>
  </form>;
}

// Approve carries no reason code, but it is irreversible, so it still confirms.
function ApproveConfirm({ onConfirm, onCancel, busy }) {
  return <div className="reason" role="group" aria-label="Confirm approval">
    <p className="reason-help">Approving records the premium decision against this case and cannot be undone.</p>
    <div className="reason-actions">
      <button className="primary" type="button" disabled={busy} onClick={onConfirm}>Confirm approve</button>
      <button className="secondary" type="button" disabled={busy} onClick={onCancel}>Cancel</button>
    </div>
  </div>;
}

function Detail({ detail, onBack, onDecide, busy, headingRef }) {
  const [pending, setPending] = useState(null);
  const [reason, setReason] = useState('');
  const record = detail.case;
  const decidable = record.state === 'PENDING_REVIEW';

  function start(command) { setPending(command); setReason(''); }

  return <section className="panel">
    <div className="panel-head">
      <div><span className="overline">DESJARDINS / CASE REVIEW</span><h1 ref={headingRef} tabIndex={-1}>{record.caseId}</h1></div>
      <button className="secondary" type="button" onClick={onBack} disabled={busy}><ArrowLeft size={16} aria-hidden="true" />Queue</button>
    </div>
    <Notice />

    <dl className="facts">
      <div><dt>State</dt><dd><span className="state">{record.state}</span></dd></div>
      <div><dt>Revision</dt><dd>{record.revision}</dd></div>
      <div><dt>Preparer</dt><dd className="actor">{record.preparerId}</dd></div>
      <div><dt>Reviewer</dt><dd className="actor">{record.reviewerId ?? 'Not assigned'}</dd></div>
      <div><dt>Created</dt><dd>{formatTimestamp(record.createdAt)}</dd></div>
      <div><dt>Submitted</dt><dd>{formatTimestamp(record.updatedAt)}</dd></div>
    </dl>

    <h2>Calculation</h2>
    <dl className="facts">
      <div><dt>Premium</dt><dd><Premium record={record} detailed /></dd></div>
      <div><dt>Currency</dt><dd>{record.currency ?? 'Not recorded'}</dd></div>
      <div><dt>Period</dt><dd>{record.period ?? 'Not recorded'}</dd></div>
      <div><dt>Status</dt><dd>{record.calculationStatus ?? 'Not calculated'}</dd></div>
      <div><dt>Rule ids</dt><dd>{formatList(record.ruleIds)}</dd></div>
      <div><dt>Issues</dt><dd>{formatList(record.issues)}</dd></div>
      <div><dt>Rulebook version</dt><dd>{record.rulebookVersion ?? 'Not recorded'}</dd></div>
    </dl>

    <h2>Decision</h2>
    {!decidable
      ? <p className="settled">This case is {record.state.toLowerCase()} and can no longer be decided.</p>
      : pending === 'approve'
        ? <ApproveConfirm busy={busy} onCancel={() => setPending(null)}
          onConfirm={() => { setPending(null); onDecide('approve'); }} />
        : pending
          ? <ReasonPrompt command={pending} value={reason} busy={busy}
            onChange={setReason} onCancel={() => setPending(null)}
            onConfirm={() => { const command = pending; setPending(null); onDecide(command, reason); }} />
          : <div className="decisions">
            <button className="primary" type="button" disabled={busy} onClick={() => start('approve')}><Check size={16} aria-hidden="true" />Approve</button>
            <button className="danger" type="button" disabled={busy} onClick={() => start('reject')}><X size={16} aria-hidden="true" />Reject</button>
            <button className="secondary" type="button" disabled={busy} onClick={() => start('revise')}><RotateCcw size={16} aria-hidden="true" />Send back for revision</button>
          </div>}

    <h2>Audit trail</h2>
    <ol className="audit">
      {detail.auditTrail.map(event => <li key={event.sequence}>
        <span className="audit-command">{event.command}</span>
        <span className="audit-transition">{event.fromState ?? 'NEW'} to {event.toState}</span>
        <span className="audit-meta">rev {event.revision} · {event.actorId} · {formatTimestamp(event.at)}</span>
      </li>)}
    </ol>
  </section>;
}

function Workspace({ auth, config, initialAccount }) {
  const [account, setAccount] = useState(initialAccount);
  const [allowed, setAllowed] = useState(false);
  const [checking, setChecking] = useState(Boolean(initialAccount));
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [cases, setCases] = useState([]);
  const [detail, setDetail] = useState(null);
  const [busy, setBusy] = useState(false);
  const [activity, setActivity] = useState('');

  const api = useCallback(async (path, options = {}) => {
    let accessToken;
    try {
      accessToken = (await auth.acquireTokenSilent({ account, scopes: [config.scope] })).accessToken;
    } catch (failure) {
      if (failure instanceof InteractionRequiredAuthError) {
        throw new ApiError(401, 'Your sign-in needs attention. Sign out and sign in again.');
      }
      throw failure;
    }
    const response = await fetch(path, { ...options, headers: {
      ...options.headers,
      'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}`,
    } });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        typeof body.detail === 'string' ? body.detail : `Request failed (${response.status}).`,
        typeof body.code === 'string' ? body.code : null,
      );
    }
    return response.json();
  }, [auth, account, config.scope]);

  const loadQueue = useCallback(async () => {
    const body = await api('/api/cases');
    setCases(body.cases);
    setDetail(null);
  }, [api]);

  const loadCase = useCallback(async caseId => {
    setDetail(await api(`/api/cases/${encodeURIComponent(caseId)}`));
  }, [api]);

  useEffect(() => {
    if (!account) return;
    let cancelled = false;
    api('/api/me')
      .then(() => { if (cancelled) return; setAllowed(true); return loadQueue(); })
      .catch(failure => { if (!cancelled) setError(failure.message); })
      .finally(() => { if (!cancelled) setChecking(false); });
    return () => { cancelled = true; };
  }, [account, api, loadQueue]);

  async function run(work, successMessage = '') {
    setBusy(true); setError(''); setStatus('');
    try {
      await work();
      if (successMessage) setStatus(successMessage);
    } catch (failure) {
      setError(failure.message);
    } finally { setBusy(false); }
  }

  async function decide(command, reasonCode) {
    if (!detail) return;
    const caseId = detail.case.caseId;
    const body = decisionRequest(detail.case.revision, command, reasonCode);
    setBusy(true); setError(''); setStatus(''); setActivity('Recording decision...');
    let recorded = null;
    try {
      const result = await api(`/api/cases/${encodeURIComponent(caseId)}/${command}`, {
        method: 'POST', body: JSON.stringify(body), headers: { 'Idempotency-Key': crypto.randomUUID() },
      });
      recorded = result.case;
    } catch (failure) {
      const status_ = failure instanceof ApiError ? failure.status : 0;
      const code = failure instanceof ApiError ? failure.code : null;
      const outcome = decisionFailure(status_, failure.message, code);
      setError(outcome.message);
      // A conflict means someone acted first; reload rather than retrying.
      if (outcome.refresh === 'case') await loadCase(caseId).catch(() => loadQueue().catch(() => {}));
      if (outcome.refresh === 'queue') await loadQueue().catch(() => {});
      setActivity(''); setBusy(false);
      return;
    }
    // The decision is durable from here on. The follow-up reads sit outside the
    // try above so a failed refresh is never reported as a failed decision --
    // that would prompt a resubmit and earn a 409.
    setDetail(previous => ({ ...previous, case: recorded }));
    setStatus(`Case ${caseId} recorded as ${recorded.state}.`);
    try {
      await loadQueue();
      await loadCase(caseId).catch(() => {});
    } catch {
      setError(`Case ${caseId} was recorded as ${recorded.state}, but the list could not be refreshed. Use Refresh to reload it. Do not decide again.`);
    } finally { setActivity(''); setBusy(false); }
  }

  async function signIn() {
    setError('');
    try { await auth.loginRedirect({ scopes: [config.scope], prompt: 'select_account' }); }
    catch (failure) { setError(failure.message); }
  }

  async function signOut() {
    setCases([]); setDetail(null); setAllowed(false); setAccount(null);
    await auth.logoutRedirect({ account, postLogoutRedirectUri: window.location.origin });
  }

  // Swapping the panel unmounts the button that was activated, dropping focus
  // to <body>. Moving it to the new heading keeps the keyboard position and
  // gives a screen reader something to announce.
  const view = !allowed ? 'gate' : detail ? 'detail' : 'queue';
  const headingRef = useRef(null);
  const shownView = useRef(view);
  useEffect(() => {
    if (shownView.current === view) return;
    shownView.current = view;
    headingRef.current?.focus();
  }, [view]);

  return <div className="shell">
    <header className="topbar">
      <div className="brand"><ClipboardCheck size={24} aria-hidden="true" /><span>Foundry<span className="brand-sub">CASE REVIEW</span></span></div>
      <span className="environment"><span aria-hidden="true" />{config.environment} pilot</span>
      <span className="identity">{account?.name ?? 'Not signed in'}</span>
      {account && <button className="secondary" type="button" onClick={signOut} disabled={busy}><LogOut size={16} aria-hidden="true" />Sign out</button>}
    </header>
    <main>
      {error && <div className="error" role="alert">{error}</div>}
      {status && <div className="status" role="status">{status}</div>}
      {activity && <div className="pending" role="status"><span className="pulse" aria-hidden="true" />{activity}</div>}
      {!allowed
        ? <section className="panel gate">
          <span className="overline">QUOTE REVIEW</span>
          <h1 ref={headingRef} tabIndex={-1}>Reviews start with access.</h1>
          <Notice />
          <p className="status-label">{checking ? 'Verifying reviewer access...' : 'Internal pilot / reviewers only'}</p>
          {!account && <button className="primary" type="button" onClick={signIn}><LogIn size={18} aria-hidden="true" />Sign in with Microsoft</button>}
        </section>
        : detail
          ? <Detail detail={detail} busy={busy} onDecide={decide} headingRef={headingRef}
            onBack={() => run(loadQueue)} />
          : <Queue cases={cases} busy={busy} onRefresh={() => run(loadQueue)} headingRef={headingRef}
            failed={Boolean(error)}
            onOpen={caseId => run(() => loadCase(caseId))} />}
    </main>
    <footer className="disclaimer">{NOTICE}</footer>
  </div>;
}

async function start() {
  const response = await fetch('/api/config');
  if (!response.ok) throw new Error('Configuration is unavailable.');
  const config = await response.json();
  const auth = new PublicClientApplication({
    auth: { clientId: config.clientId, authority: `https://login.microsoftonline.com/${config.tenantId}`, redirectUri: window.location.origin },
    cache: { cacheLocation: 'sessionStorage' },
  });
  await auth.initialize();
  const result = await auth.handleRedirectPromise();
  const account = result?.account ?? auth.getAllAccounts()[0] ?? null;
  if (account) auth.setActiveAccount(account);
  createRoot(document.getElementById('root')).render(<Workspace auth={auth} config={config} initialAccount={account} />);
}

start().catch(() => {
  // The notice belongs on every view, including the one that renders when
  // nothing else could load.
  createRoot(document.getElementById('root')).render(<div className="startup-error">
    <p role="alert">The review workspace could not load. Refresh to try again.</p>
    <Notice />
  </div>);
});
