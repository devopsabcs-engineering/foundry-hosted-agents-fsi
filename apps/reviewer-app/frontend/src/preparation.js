import { caseDetail, currentPreparation, prepareRequest, unavailableDetail } from './request.js';

/** Never retry a POST automatically: even a lost response may have persisted. */
export async function prepareCase(api, detail, values, newKey = () => crypto.randomUUID()) {
  const path = `/api/cases/${encodeURIComponent(detail.case.caseId)}`;
  try {
    const result = caseDetail(await api(`${path}/prepare`, {
      method: 'POST',
      body: JSON.stringify(prepareRequest(detail.case.revision, values)),
      headers: { 'Idempotency-Key': newKey() },
    }));
    if (result.case.state !== 'PENDING_REVIEW' || currentPreparation(result.case)?.status !== 'COMPLETED') {
      throw new Error('PREPARATION_NOT_CONFIRMED');
    }
    return { detail: result, confirmed: true };
  } catch (error) {
    try {
      return { detail: caseDetail(await api(path)), confirmed: false, error };
    } catch {
      return { detail: unavailableDetail(detail), confirmed: false, error };
    }
  }
}
