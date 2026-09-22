import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { PublicClientApplication, InteractionRequiredAuthError } from '@azure/msal-browser';
import { AlertTriangle, ArrowLeft, Check, ClipboardCheck, LogIn, LogOut, RefreshCw, RotateCcw, Trash2, X } from 'lucide-react';
import '@fontsource-variable/dm-sans';
import './style.css';
import { ApiError, decisionFailure, formatList, formatTimestamp, premiumView } from './format';
import { decisionRequest } from './request';
import { DEFAULT_LANGUAGE, translate } from './i18n';
import { useLanguage } from './useLanguage';

const REASON_PATTERN = /^[A-Z0-9_]{1,64}$/;

// Not translated: sent verbatim to the backend, which compares it byte-for-byte.
// See the matching constant in `apps/reviewer-app/app.py`.
const CLEAR_QUEUE_PHRASE = 'CLEAR ALL CASES';

function readStoredLanguage() {
  try { return window.localStorage.getItem('fhaf-ui-language') || DEFAULT_LANGUAGE; }
  catch { return DEFAULT_LANGUAGE; }
}

function Notice({ language }) {
  return <div className="notice" role="note"><AlertTriangle size={15} aria-hidden="true" /><span>{translate(language, 'disclaimer.notice')}</span></div>;
}

/** Renders the premium, or the state that explains why there is no figure. */
function Premium({ record, detailed = false, language, t }) {
  const view = premiumView(record, language);
  if (view.kind !== 'amount') {
    return <span className="unpriced">
      <span className="unpriced-label">{view.label}</span>
      <span className="unpriced-reason">{view.reason}</span>
    </span>;
  }
  return <span className="premium">{view.amount}{detailed && view.period ? <span className="period"> {t('detail.perPeriod')} {view.period.replace(/_/g, ' ').toLowerCase()}</span> : null}</span>;
}

function ClearQueueConfirm({ value, onChange, onConfirm, onCancel, busy, t }) {
  const invalid = value !== CLEAR_QUEUE_PHRASE;
  return <form className="reason" role="group" aria-label={t('queue.clearGroupLabel')}
    onSubmit={event => { event.preventDefault(); if (!invalid) onConfirm(); }}>
    <label htmlFor="clear-confirm">{t('queue.clearLabel', { phrase: CLEAR_QUEUE_PHRASE })}</label>
    <input id="clear-confirm" value={value} maxLength={32} autoComplete="off" aria-invalid={invalid}
      onChange={event => onChange(event.target.value)} />
    <span className="reason-help">{t('queue.clearHelp')}</span>
    <div className="reason-actions">
      <button className="danger" type="submit" disabled={busy || invalid}>{t('queue.clearConfirmButton')}</button>
      <button className="secondary" type="button" disabled={busy} onClick={onCancel}>{t('reason.cancel')}</button>
    </div>
  </form>;
}

function Queue({ cases, onOpen, onRefresh, onClear, busy, headingRef, failed, language, t }) {
  const [clearing, setClearing] = useState(false);
  const [clearValue, setClearValue] = useState('');
  return <section className="panel">
    <div className="panel-head">
      <div><span className="overline">{t('topbar.overline')}</span><h1 ref={headingRef} tabIndex={-1}>{t('queue.heading')}</h1></div>
      <div className="panel-actions">
        <button className="secondary" type="button" onClick={onRefresh} disabled={busy}><RefreshCw size={16} aria-hidden="true" />{t('queue.refresh')}</button>
        <button className="danger" type="button" disabled={busy} onClick={() => { setClearValue(''); setClearing(true); }}>
          <Trash2 size={16} aria-hidden="true" />{t('queue.clearButton')}
        </button>
      </div>
    </div>
    <Notice language={language} />
    {clearing && <ClearQueueConfirm value={clearValue} busy={busy} t={t}
      onChange={setClearValue} onCancel={() => setClearing(false)}
      onConfirm={() => { setClearing(false); onClear(); }} />}
    {/* An empty list after a failed load means the queue is unknown, not empty.
        Saying "no cases" there tells a reviewer nothing is waiting when the
        backend could not be reached, which is the one wrong answer to give. */}
    {!cases.length
      ? (failed
        ? <p className="empty-queue">{t('queue.emptyFailed')}</p>
        : <p className="empty-queue">{t('queue.emptyNone')}</p>)
      : <div className="queue-scroll" role="region" aria-label={t('queue.regionLabel')} tabIndex={0}>
        <table className="queue">
          <caption className="visually-hidden">{t('queue.caption')}</caption>
          <thead><tr>
            <th scope="col">{t('queue.headers.case')}</th><th scope="col">{t('queue.headers.state')}</th><th scope="col">{t('queue.headers.rev')}</th>
            <th scope="col">{t('queue.headers.preparer')}</th><th scope="col">{t('queue.headers.submitted')}</th><th scope="col">{t('queue.headers.premium')}</th><th scope="col"><span className="visually-hidden">{t('queue.headers.open')}</span></th>
          </tr></thead>
          <tbody>
            {cases.map(record => <tr key={record.caseId}>
              <th scope="row">{record.caseId}</th>
              <td><span className="state">{record.state}</span></td>
              <td>{record.revision}</td>
              <td className="actor">{record.preparerId}</td>
              <td>{formatTimestamp(record.updatedAt, language)}</td>
              <td><Premium record={record} language={language} t={t} /></td>
              <td><button className="secondary" type="button" disabled={busy}
                aria-label={t('queue.reviewAria', { caseId: record.caseId })}
                onClick={() => onOpen(record.caseId)}>{t('queue.reviewButton')}</button></td>
            </tr>)}
          </tbody>
        </table>
      </div>}
  </section>;
}

function ReasonPrompt({ command, value, onChange, onConfirm, onCancel, busy, t }) {
  const invalid = value !== '' && !REASON_PATTERN.test(value);
  const commandWord = t(`reason.commands.${command}`);
  return <form className="reason" onSubmit={event => { event.preventDefault(); if (!invalid) onConfirm(); }}>
    <label htmlFor="reason-code">{t('reason.label', { command: commandWord })}</label>
    <input id="reason-code" value={value} maxLength={64} autoComplete="off" placeholder={t('reason.placeholder')}
      aria-describedby="reason-help" aria-invalid={invalid}
      onChange={event => onChange(event.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, '_'))} />
    <span id="reason-help" className="reason-help">{invalid ? t('reason.helpInvalid') : t('reason.helpBlank')}</span>
    <div className="reason-actions">
      <button className="primary" type="submit" disabled={busy || invalid}>{t('reason.confirm', { command: commandWord })}</button>
      <button className="secondary" type="button" disabled={busy} onClick={onCancel}>{t('reason.cancel')}</button>
    </div>
  </form>;
}

// Approve carries no reason code, but it is irreversible, so it still confirms.
function ApproveConfirm({ onConfirm, onCancel, busy, t }) {
  return <div className="reason" role="group" aria-label={t('approve.groupLabel')}>
    <p className="reason-help">{t('approve.warning')}</p>
    <div className="reason-actions">
      <button className="primary" type="button" disabled={busy} onClick={onConfirm}>{t('approve.confirmButton')}</button>
      <button className="secondary" type="button" disabled={busy} onClick={onCancel}>{t('reason.cancel')}</button>
    </div>
  </div>;
}

function Detail({ detail, onBack, onDecide, busy, headingRef, language, t }) {
  const [pending, setPending] = useState(null);
  const [reason, setReason] = useState('');
  const record = detail.case;
  const decidable = record.state === 'PENDING_REVIEW';

  function start(command) { setPending(command); setReason(''); }

  return <section className="panel">
    <div className="panel-head">
      <div><span className="overline">{t('topbar.overline')}</span><h1 ref={headingRef} tabIndex={-1}>{record.caseId}</h1></div>
      <button className="secondary" type="button" onClick={onBack} disabled={busy}><ArrowLeft size={16} aria-hidden="true" />{t('detail.queueButton')}</button>
    </div>
    <Notice language={language} />

    <dl className="facts">
      <div><dt>{t('detail.facts.state')}</dt><dd><span className="state">{record.state}</span></dd></div>
      <div><dt>{t('detail.facts.revision')}</dt><dd>{record.revision}</dd></div>
      <div><dt>{t('detail.facts.preparer')}</dt><dd className="actor">{record.preparerId}</dd></div>
      <div><dt>{t('detail.facts.reviewer')}</dt><dd className="actor">{record.reviewerId ?? t('detail.reviewerUnassigned')}</dd></div>
      <div><dt>{t('detail.facts.created')}</dt><dd>{formatTimestamp(record.createdAt, language)}</dd></div>
      <div><dt>{t('detail.facts.submitted')}</dt><dd>{formatTimestamp(record.updatedAt, language)}</dd></div>
    </dl>

    <h2>{t('detail.calculationHeading')}</h2>
    <dl className="facts">
      <div><dt>{t('detail.facts.premium')}</dt><dd><Premium record={record} detailed language={language} t={t} /></dd></div>
      <div><dt>{t('detail.facts.currency')}</dt><dd>{record.currency ?? t('detail.notRecorded')}</dd></div>
      <div><dt>{t('detail.facts.period')}</dt><dd>{record.period ?? t('detail.notRecorded')}</dd></div>
      <div><dt>{t('detail.facts.status')}</dt><dd>{record.calculationStatus ?? t('detail.notCalculated')}</dd></div>
      <div><dt>{t('detail.facts.ruleIds')}</dt><dd>{formatList(record.ruleIds, language)}</dd></div>
      <div><dt>{t('detail.facts.issues')}</dt><dd>{formatList(record.issues, language)}</dd></div>
      <div><dt>{t('detail.facts.rulebookVersion')}</dt><dd>{record.rulebookVersion ?? t('detail.notRecorded')}</dd></div>
    </dl>

    <h2>{t('detail.decisionHeading')}</h2>
    {!decidable
      ? <p className="settled">{t('detail.settled', { state: record.state.toLowerCase() })}</p>
      : pending === 'approve'
        ? <ApproveConfirm busy={busy} t={t} onCancel={() => setPending(null)}
          onConfirm={() => { setPending(null); onDecide('approve'); }} />
        : pending
          ? <ReasonPrompt command={pending} value={reason} busy={busy} t={t}
            onChange={setReason} onCancel={() => setPending(null)}
            onConfirm={() => { const command = pending; setPending(null); onDecide(command, reason); }} />
          : <div className="decisions">
            <button className="primary" type="button" disabled={busy} onClick={() => start('approve')}><Check size={16} aria-hidden="true" />{t('decisions.approve')}</button>
            <button className="danger" type="button" disabled={busy} onClick={() => start('reject')}><X size={16} aria-hidden="true" />{t('decisions.reject')}</button>
            <button className="secondary" type="button" disabled={busy} onClick={() => start('revise')}><RotateCcw size={16} aria-hidden="true" />{t('decisions.revise')}</button>
          </div>}

    <h2>{t('detail.auditHeading')}</h2>
    <ol className="audit">
      {detail.auditTrail.map(event => <li key={event.sequence}>
        <span className="audit-command">{event.command}</span>
        <span className="audit-transition">{t('audit.transition', { from: event.fromState ?? t('audit.newState'), to: event.toState })}</span>
        <span className="audit-meta">{t('audit.meta', { revision: event.revision, actor: event.actorId, at: formatTimestamp(event.at, language) })}</span>
      </li>)}
    </ol>
  </section>;
}

function Workspace({ auth, config, initialAccount }) {
  const { language, setLanguage, t } = useLanguage();
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
        throw new ApiError(401, t('errors.signInNeedsAttention'));
      }
      throw failure;
    }
    const response = await fetch(path, { ...options, headers: {
      ...options.headers,
      'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}`, 'X-UI-Language': language,
    } });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        typeof body.detail === 'string' ? body.detail : t('errors.requestFailed', { status: response.status }),
        typeof body.code === 'string' ? body.code : null,
      );
    }
    return response.json();
  }, [auth, account, config.scope, language, t]);

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

  async function clearQueue() {
    setBusy(true); setError(''); setStatus('');
    try {
      const result = await api('/api/cases/clear', {
        method: 'POST', body: JSON.stringify({ confirm: CLEAR_QUEUE_PHRASE }),
      });
      await loadQueue();
      setStatus(t('queue.clearStatus', { count: result.deleted }));
    } catch (failure) {
      setError(failure.message);
    } finally { setBusy(false); }
  }

  async function decide(command, reasonCode) {
    if (!detail) return;
    const caseId = detail.case.caseId;
    const body = decisionRequest(detail.case.revision, command, reasonCode);
    setBusy(true); setError(''); setStatus(''); setActivity(t('activity.recordingDecision'));
    let recorded = null;
    try {
      const result = await api(`/api/cases/${encodeURIComponent(caseId)}/${command}`, {
        method: 'POST', body: JSON.stringify(body), headers: { 'Idempotency-Key': crypto.randomUUID() },
      });
      recorded = result.case;
    } catch (failure) {
      const status_ = failure instanceof ApiError ? failure.status : 0;
      const code = failure instanceof ApiError ? failure.code : null;
      const outcome = decisionFailure(status_, failure.message, code, language);
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
    setStatus(t('status.recorded', { caseId, state: recorded.state }));
    try {
      await loadQueue();
      await loadCase(caseId).catch(() => {});
    } catch {
      setError(t('errors.refreshFailedAfterDecision', { caseId, state: recorded.state }));
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
      <div className="brand"><ClipboardCheck size={24} aria-hidden="true" /><span>{t('topbar.brand')}<span className="brand-sub">{t('topbar.brandSub')}</span></span></div>
      <span className="environment"><span aria-hidden="true" />{t('topbar.pilotBadge', { env: config.environment })}</span>
      <span className="version-badge">v{config.version}</span>
      <span className="identity">{account?.name ?? t('topbar.notSignedIn')}</span>
      <button className="secondary" type="button" onClick={() => setLanguage(language === 'en-CA' ? 'fr-CA' : 'en-CA')}
        title={t('topbar.languageToggleAria')} aria-label={t('topbar.languageToggleAria')}>
        {language === 'en-CA' ? 'FR' : 'EN'}
      </button>
      {account && <button className="secondary" type="button" onClick={signOut} disabled={busy}><LogOut size={16} aria-hidden="true" />{t('topbar.signOut')}</button>}
    </header>
    <main>
      {error && <div className="error" role="alert">{error}</div>}
      {status && <div className="status" role="status">{status}</div>}
      {activity && <div className="pending" role="status"><span className="pulse" aria-hidden="true" />{activity}</div>}
      {!allowed
        ? <section className="panel gate">
          <span className="overline">{t('gate.overline')}</span>
          <h1 ref={headingRef} tabIndex={-1}>{t('gate.heading')}</h1>
          <Notice language={language} />
          <p className="status-label">{checking ? t('gate.checking') : t('gate.restricted')}</p>
          {!account && <button className="primary" type="button" onClick={signIn}><LogIn size={18} aria-hidden="true" />{t('gate.signIn')}</button>}
        </section>
        : detail
          ? <Detail detail={detail} busy={busy} onDecide={decide} headingRef={headingRef} language={language} t={t}
            onBack={() => run(loadQueue)} />
          : <Queue cases={cases} busy={busy} onRefresh={() => run(loadQueue)} onClear={clearQueue} headingRef={headingRef} language={language} t={t}
            failed={Boolean(error)}
            onOpen={caseId => run(() => loadCase(caseId))} />}
    </main>
    <footer className="disclaimer">{translate(language, 'disclaimer.notice')}</footer>
  </div>;
}

async function start() {
  const response = await fetch('/api/config');
  if (!response.ok) throw new Error(translate(readStoredLanguage(), 'errors.configUnavailable'));
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
  const language = readStoredLanguage();
  createRoot(document.getElementById('root')).render(<div className="startup-error">
    <p role="alert">{translate(language, 'errors.startupFailed')}</p>
    <Notice language={language} />
  </div>);
});
