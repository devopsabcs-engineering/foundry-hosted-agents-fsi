/**
 * Body for an approve/reject/revise POST, kept pure so the revision it carries
 * can be asserted without a DOM.
 *
 * The revision is the one the page is displaying, so a reviewer acting on a
 * stale page loses the server's compare-and-swap instead of silently
 * overwriting a decision they never saw. Approve rejects `reasonCode` with a
 * 422 (`extra="forbid"`), so it is dropped rather than sent.
 */
export function decisionRequest(revision, command, reasonCode) {
  const body = { revision };
  if (command !== 'approve' && reasonCode) body.reasonCode = reasonCode;
  return body;
}
