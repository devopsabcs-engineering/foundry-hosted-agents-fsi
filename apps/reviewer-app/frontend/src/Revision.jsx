import React, { useState } from 'react';
import { CORRECTION_VALUES, currentPreparation, preparationRetry, prepareRequest } from './request.js';
import { formatList, formatTimestamp } from './format.js';

export function Corrections({ values, t }) {
  const entries = Object.keys(CORRECTION_VALUES).filter(field => values?.[field]);
  return entries.length ? <dl className="facts correction-values">
    {entries.map(field => <div key={field}><dt>{t(`revision.${field}`)}</dt><dd>{values[field]}</dd></div>)}
  </dl> : <p className="reason-help">{t('revision.noCorrections')}</p>;
}

export function Revision({ record, busy, unavailable, onPrepare, onRefresh, language, t }) {
  const [values, setValues] = useState(() => {
    const saved = preparationRetry(record) ? record.preparation.corrections : {};
    return Object.fromEntries(Object.entries(CORRECTION_VALUES).map(([field, choices]) =>
      [field, choices.includes(saved?.[field]) ? saved[field] : '']));
  });
  const preparation = record.preparation;
  const current = currentPreparation(record);
  const retry = preparationRetry(record);
  let valid = true;
  try { prepareRequest(record.revision, values); } catch { valid = false; }
  return <section className="revision" aria-labelledby="revision-heading">
    <h2 id="revision-heading">{t('revision.heading')}</h2>
    <p className="reason-help">{t('revision.ownPreparer')}</p>
    {preparation && <>
      <h3>{t('revision.persisted')}</h3>
      <p>{t(current ? 'revision.current' : 'revision.previous', { revision: preparation.revision })}
        {' · '}{t(`revision.statuses.${preparation.status}`)}
        {' · '}{formatTimestamp(preparation.requestedAt, language)}</p>
      <Corrections values={preparation.corrections} t={t} />
      {preparation.responseId && <p className="provenance">{t('revision.responseId')}: {preparation.responseId}</p>}
    </>}
    {current?.status === 'REQUESTED' && <p role="status">{t('revision.pending')}</p>}
    {record.state === 'DRAFT' && <form onSubmit={event => {
      event.preventDefault();
      if (valid && !busy && !unavailable) onPrepare(values);
    }}>
      <p className="reason-help" id="correction-help">{t('revision.help')}</p>
      <div className="correction-fields">
        {Object.entries(CORRECTION_VALUES).map(([field, choices]) => <div key={field}>
          <label htmlFor={`correction-${field}`}>{t(`revision.${field}`)}</label>
          <select id={`correction-${field}`} value={values[field]} disabled={busy || unavailable}
            aria-describedby="correction-help" onChange={event => setValues(previous => ({ ...previous, [field]: event.target.value }))}>
            <option value="">{t('revision.keepOriginal')}</option>
            {choices.map(value => <option key={value} value={value}>{value}</option>)}
          </select>
        </div>)}
      </div>
      {retry && <p className="notice" role="note">{t('revision.retryNotice')}</p>}
      <div className="decisions">
        <button className="primary" type="submit" disabled={busy || unavailable || !valid}>
          {t(retry ? 'revision.retry' : 'revision.prepare')}
        </button>
        <button className="secondary" type="button" disabled={busy} onClick={onRefresh}>{t('revision.refresh')}</button>
      </div>
    </form>}
  </section>;
}

export function AuditDetails({ event, t, language }) {
  const details = event.details;
  return <>
    {event.reasonCode && <span className="audit-meta">{t('revision.reasonCode')}: {event.reasonCode}</span>}
    {details && <div className="audit-details">
      {details.corrections && <Corrections values={details.corrections} t={t} />}
      {details.preparationId && <p className="provenance">{t('revision.preparationId')}: {details.preparationId}</p>}
      {details.responseId && <p className="provenance">{t('revision.responseId')}: {details.responseId}</p>}
      {details.calculation && <dl className="facts">
        <div><dt>{t('detail.facts.status')}</dt><dd>{details.calculation.status}</dd></div>
        <div><dt>{t('revision.amountCents')}</dt><dd>{details.calculation.amountCents ?? t('detail.notRecorded')}</dd></div>
        <div><dt>{t('detail.facts.rulebookVersion')}</dt><dd>{details.calculation.rulebookVersion ?? t('detail.notRecorded')}</dd></div>
        <div><dt>{t('detail.facts.ruleIds')}</dt><dd>{formatList(details.calculation.ruleIds, language)}</dd></div>
        <div><dt>{t('detail.facts.issues')}</dt><dd>{formatList(details.calculation.issues, language)}</dd></div>
      </dl>}
    </div>}
  </>;
}
