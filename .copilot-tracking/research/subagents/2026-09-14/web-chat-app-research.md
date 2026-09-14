# Research: `apps/web-chat/` and supporting scripts in sibling repo `devopsabcs-engineering/foundry-hosted-agents`

Sibling repo default branch: `main`. All contents fetched via `gh api -H "Accept: application/vnd.github.raw" repos/devopsabcs-engineering/foundry-hosted-agents/contents/<path>` and `gh api repos/.../git/trees/main?recursive=1`. The sibling repo demos an "Air Canada Threat Assessment" agent (LangGraph supervisor + Defender/anomaly MCP specialists); the local repo (`foundry-hosted-agents-fsi`) demos a Desjardins insurance "quote-preparation-agent". The web-chat app and its scripts are domain-agnostic infrastructure/tooling except for a handful of hardcoded names (agent name, tenant/app IDs, RG/ACR/app names, sample queries) that must be re-parameterized for the new domain.

Status: Complete

---

## 1. Recursive file tree of `apps/web-chat/`

```text
apps/web-chat/.dockerignore
apps/web-chat/Dockerfile
apps/web-chat/app.py
apps/web-chat/auth.py
apps/web-chat/frontend/.gitignore
apps/web-chat/frontend/index.html
apps/web-chat/frontend/package-lock.json
apps/web-chat/frontend/package.json
apps/web-chat/frontend/src/main.jsx
apps/web-chat/frontend/src/request.js
apps/web-chat/frontend/src/samples.js
apps/web-chat/frontend/src/stream.js
apps/web-chat/frontend/src/style.css
apps/web-chat/frontend/tests/request.test.js
apps/web-chat/frontend/tests/samples.test.js
apps/web-chat/frontend/tests/stream.test.js
apps/web-chat/frontend/vite.config.js
apps/web-chat/requirements.txt
apps/web-chat/tests/test_app.py
apps/web-chat/tests/test_auth.py
```

There is **no `README.md` inside `apps/web-chat/`**. Documentation for the app lives in the top-level `README.md` (a short table row) and in the sibling repo's wiki page `Web-Chat-Pilot.md` (very detailed — architecture diagrams, auth flow, deployment commands, verification log). `package-lock.json` exists (large, not reproduced here — standard npm lockfile for the dependencies in `package.json` below).

---

## 2. Key file contents

### `apps/web-chat/requirements.txt`

```text
fastapi==0.135.1
uvicorn==0.41.0
httpx==0.28.1
httpx-sse==0.4.3
PyJWT[crypto]==2.12.1
azure-identity==1.25.3
aiohttp>=3.13.3,<4
```

Note: `aiohttp` was added after a production incident — `azure-identity`'s async `DefaultAzureCredential` needs it as a transport dependency at runtime; its absence was not caught by mocked unit tests and caused a crash-on-startup in the real container (see wiki "Symptom" table in section 4).

### `apps/web-chat/frontend/package.json`

```json
{
  "name": "foundry-threat-assessment-web-chat",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "vite build",
    "test": "node --test tests/*.test.js"
  },
  "dependencies": {
    "@azure/msal-browser": "^4.0.0",
    "@fontsource-variable/dm-sans": "^5.0.0",
    "@fontsource-variable/newsreader": "^5.0.0",
    "@vitejs/plugin-react": "^5.0.0",
    "eventsource-parser": "^3.0.0",
    "lucide-react": "^0.468.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-markdown": "^10.0.0",
    "remark-gfm": "^4.0.0",
    "vite": "^7.0.0"
  }
}
```

`name` is domain-specific ("foundry-threat-assessment-web-chat") — rename for the Desjardins quote domain.

### Backend entrypoint: `apps/web-chat/app.py`

The entrypoint is `app.py` (FastAPI factory `create_app`, run via `uvicorn app:create_app --factory`). Full contents:

```python
import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from azure.identity.aio import DefaultAzureCredential
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from httpx_sse import aconnect_sse
from pydantic import BaseModel, ConfigDict, Field

from auth import Identity, PilotAuth

logger = logging.getLogger("web_chat")


@dataclass(frozen=True)
class Settings:
    tenant_id: str
    client_id: str
    pilot_group_id: str
    agent_endpoint: str
    managed_identity_client_id: str | None = None
    session_ttl: int = 3600
    max_sessions: int = 128
    max_turns: int = 20

    @classmethod
    def from_env(cls):
        endpoint = os.environ["AGENT_ENDPOINT"]
        parsed = httpx.URL(endpoint)
        if parsed.scheme != "https" or not parsed.host.endswith(".services.ai.azure.com"):
            raise ValueError("AGENT_ENDPOINT must be a Foundry HTTPS endpoint")
        return cls(
            tenant_id=str(uuid.UUID(os.environ["ENTRA_TENANT_ID"])),
            client_id=str(uuid.UUID(os.environ["ENTRA_CLIENT_ID"])),
            pilot_group_id=str(uuid.UUID(os.environ["PILOT_GROUP_ID"])),
            agent_endpoint=endpoint,
            managed_identity_client_id=os.environ.get("AZURE_CLIENT_ID"),
        )


@dataclass
class Conversation:
    owner: Identity
    touched: float = field(default_factory=time.monotonic)
    messages: list = field(default_factory=list)
    busy: bool = False
    completed: dict[str, tuple[str, str]] = field(default_factory=dict)


class SessionStore:
    def __init__(self, settings):
        self.settings = settings
        self.sessions: dict[str, Conversation] = {}

    def create(self, owner):
        now = time.monotonic()
        self.sessions = {
            key: value for key, value in self.sessions.items()
            if value.busy or now - value.touched < self.settings.session_ttl
        }
        if len(self.sessions) >= self.settings.max_sessions:
            raise HTTPException(429, "Pilot capacity reached. Try again later.")
        if sum(session.owner == owner for session in self.sessions.values()) >= 5:
            raise HTTPException(429, "Close an existing conversation before starting another.")
        identifier = str(uuid.uuid4())
        self.sessions[identifier] = Conversation(owner)
        return identifier

    def get(self, identifier, owner):
        session = self.sessions.get(identifier)
        if session is None or session.owner != owner:
            raise HTTPException(404, "Conversation not found. Start a new conversation.")
        if not session.busy and time.monotonic() - session.touched >= self.settings.session_ttl:
            del self.sessions[identifier]
            raise HTTPException(404, "Conversation expired. Start a new conversation.")
        session.touched = time.monotonic()
        return session


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=8000)


class FoundryClient:
    def __init__(self, settings):
        self.settings = settings
        self.credential = DefaultAzureCredential(
            managed_identity_client_id=settings.managed_identity_client_id,
        )
        self.http = httpx.AsyncClient(timeout=httpx.Timeout(180, connect=15))

    async def close(self):
        await self.http.aclose()
        await self.credential.close()

    async def events(self, messages):
        token = await self.credential.get_token("https://ai.azure.com/.default")
        completion = None
        byte_count = 0
        async with asyncio.timeout(180):
            async with aconnect_sse(
                self.http, "POST", self.settings.agent_endpoint,
                headers={"Authorization": f"Bearer {token.token}"},
                json={"input": messages, "stream": True, "store": False},
            ) as stream:
                stream.response.raise_for_status()
                async for event in stream.aiter_sse():
                    byte_count += len(event.data)
                    if byte_count > 2_000_000:
                        raise ValueError("Response exceeds limit")
                    if event.data == "[DONE]":
                        continue
                    payload = json.loads(event.data)
                    response = payload.get("response") or {}
                    kind = payload.get("type", "")
                    if payload.get("error") or response.get("error") or kind in {
                        "error", "response.failed", "response.incomplete", "response.error",
                    }:
                        raise ValueError("Agent reported failure")
                    if kind == "response.completed":
                        if completion is not None or response.get("status") != "completed":
                            raise ValueError("Invalid completion")
                        texts = [
                            content["text"] for item in response.get("output", [])
                            if item.get("type") == "message" and item.get("role") == "assistant"
                            for content in item.get("content", [])
                            if content.get("type") == "output_text" and content.get("text", "").strip()
                        ]
                        completion = "\n\n".join(texts)
                        if not completion or len(completion) > 64000:
                            raise ValueError("Missing or oversized assistant response")
        if completion is None:
            raise ValueError("Incomplete response")
        yield {"type": "answer", "text": completion}


def sse(payload):
    return "data: " + json.dumps(payload, ensure_ascii=True) + "\n\n"


def create_app(settings=None, verifier=None, upstream=None):
    settings = settings or Settings.from_env()
    verifier = verifier or PilotAuth(settings.tenant_id, settings.client_id, settings.pilot_group_id)
    store = SessionStore(settings)
    slots = asyncio.Semaphore(4)

    @asynccontextmanager
    async def lifespan(application):
        application.state.upstream = upstream or FoundryClient(settings)
        yield
        if upstream is None:
            await application.state.upstream.close()

    application = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    application.state.store = store

    async def identity(authorization: str | None = Header(default=None)):
        return await verifier.authorize(authorization)

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        if request.headers.get("content-length", "").isdigit():
            if int(request.headers["content-length"]) > 40000:
                return JSONResponse({"detail": "Request too large."}, status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self' https://login.microsoftonline.com; "
            "frame-src https://login.microsoftonline.com; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self' https://login.microsoftonline.com"
        )
        return response

    @application.get("/healthz")
    async def health():
        return {"status": "ok"}

    @application.get("/api/config")
    async def config():
        return {"tenantId": settings.tenant_id, "clientId": settings.client_id,
                "scope": f"api://{settings.client_id}/Chat.Access", "environment": "staging"}

    @application.get("/api/me")
    async def me(owner: Identity = Depends(identity)):
        return {"objectId": owner.object_id}

    @application.post("/api/conversations", status_code=201)
    async def create(owner: Identity = Depends(identity)):
        return {"id": store.create(owner)}

    @application.delete("/api/conversations/{identifier}", status_code=204)
    async def delete(identifier: uuid.UUID, owner: Identity = Depends(identity)):
        session = store.get(str(identifier), owner)
        if session.busy:
            raise HTTPException(409, "Stop the current response first.")
        del store.sessions[str(identifier)]

    @application.post("/api/conversations/{identifier}/messages")
    async def message(identifier: uuid.UUID, body: Message, owner: Identity = Depends(identity),
                      idempotency_key: uuid.UUID | None = Header(default=None)):
        session = store.get(str(identifier), owner)
        request_id = str(idempotency_key or uuid.uuid4())
        if request_id in session.completed:
            original, answer = session.completed[request_id]
            if original != body.text:
                raise HTTPException(409, "This request key was already used for a different message.")
            return StreamingResponse(iter([
                sse({"type": "status", "text": "Complete", "requestId": request_id}),
                sse({"type": "answer", "text": answer, "requestId": request_id}),
                sse({"type": "done"}),
            ]), media_type="text/event-stream",
                headers={"X-Accel-Buffering": "no", "X-Request-ID": request_id})
        if session.busy:
            raise HTTPException(409, "A response is already in progress.")
        if len(session.messages) >= settings.max_turns * 2:
            raise HTTPException(409, "Conversation limit reached. Start a new conversation.")
        if slots.locked():
            raise HTTPException(429, "The pilot is busy. Try again shortly.")
        session.busy = True
        await slots.acquire()

        async def generate():
            started = time.monotonic()
            task = None
            outcome = "cancelled"
            try:
                yield sse({"type": "status", "text": "Assessing", "requestId": request_id})
                user_message = {"role": "user", "content": [{"type": "input_text", "text": body.text}]}
                messages = session.messages + [user_message]

                async def result():
                    answer = None
                    async for event in application.state.upstream.events(messages):
                        if event["type"] == "answer":
                            answer = event["text"]
                    if not answer:
                        raise ValueError("No answer")
                    return answer

                task = asyncio.create_task(result())
                while not task.done():
                    await asyncio.wait({task}, timeout=10)
                    if not task.done():
                        yield ": keepalive\n\n"
                answer = task.result()
                session.messages = messages + [{"role": "assistant", "content": answer}]
                session.completed[request_id] = (body.text, answer)
                yield sse({"type": "answer", "text": answer, "requestId": request_id})
                yield sse({"type": "done"})
                outcome = "success"
            except (httpx.HTTPError, ValueError, TimeoutError) as exc:
                outcome = type(exc).__name__
                yield sse({"type": "error", "text": "The assessment could not complete. Try again.",
                           "requestId": request_id})
            except Exception as exc:
                outcome = type(exc).__name__
                yield sse({"type": "error", "text": "The service is temporarily unavailable.",
                           "requestId": request_id})
            finally:
                if task is not None and not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                session.busy = False
                session.touched = time.monotonic()
                slots.release()
                logger.warning("chat_request id=%s outcome=%s seconds=%.3f",
                               request_id, outcome, time.monotonic() - started)

        return StreamingResponse(generate(), media_type="text/event-stream",
                                 headers={"X-Accel-Buffering": "no", "X-Request-ID": request_id})

    dist = Path(__file__).parent / "frontend" / "dist"
    if dist.exists():
        application.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return application
```

Notable domain-specific-but-generic-shape behaviors: it targets a Foundry **hosted-agent Responses API** (`https://<account>.services.ai.azure.com/api/projects/<project>/agents/<agent-name>/endpoint/protocols/openai/responses?api-version=v1` — same protocol shape the local `quote-preparation-agent` uses), streams SSE, does server-owned conversation history, idempotency-key replay, and per-user/session capacity limits. None of the business logic is threat-assessment-specific — this is fully portable.

### `apps/web-chat/auth.py`

```python
import asyncio
from dataclasses import dataclass

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient


@dataclass(frozen=True)
class Identity:
    tenant_id: str
    object_id: str


class PilotAuth:
    def __init__(self, tenant_id: str, client_id: str, group_id: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.group_id = group_id
        self.issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        self.keys = PyJWKClient(
            f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
            timeout=10,
        )

    def verify(self, token: str) -> Identity:
        try:
            key = self.keys.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "nbf", "iss", "aud", "tid", "oid"]},
                leeway=30,
            )
        except jwt.PyJWKClientConnectionError as exc:
            raise HTTPException(503, "Sign-in verification is temporarily unavailable.") from exc
        except jwt.PyJWTError as exc:
            raise HTTPException(401, "A valid access token is required.") from exc
        if claims.get("tid") != self.tenant_id or claims.get("azp") != self.client_id:
            raise HTTPException(403, "This application is not authorized.")
        if "Chat.Access" not in claims.get("scp", "").split():
            raise HTTPException(403, "Chat permission is required.")
        if self.group_id not in claims.get("groups", []):
            raise HTTPException(403, "Pilot membership is required. Contact the pilot administrator.")
        if not isinstance(claims["oid"], str) or not claims["oid"]:
            raise HTTPException(401, "A user identity is required.")
        return Identity(claims["tid"], claims["oid"])

    async def authorize(self, authorization: str | None) -> Identity:
        if not authorization or not authorization.startswith("Bearer ") or len(authorization) > 32768:
            raise HTTPException(401, "Sign in to continue.")
        return await asyncio.to_thread(self.verify, authorization[7:])
```

Fully generic (tenant/client/group IDs are injected, not hardcoded). Enforces RS256 signature, issuer, audience, `tid`, `azp`, `scp` contains `Chat.Access`, and pilot-group membership claim — fails closed on group-overage tokens (no Graph fallback).

### `apps/web-chat/Dockerfile`

```dockerfile
FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/index.html frontend/vite.config.js ./
COPY frontend/src ./src
COPY frontend/tests/request.test.js frontend/tests/stream.test.js ./tests/
RUN npm test && npm run build

FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home appuser
COPY app.py auth.py ./
COPY --from=frontend /build/dist ./frontend/dist
RUN IDENTITY_ENDPOINT=http://localhost/identity IDENTITY_HEADER=build-check python -c "import asyncio; from app import FoundryClient, Settings; client = FoundryClient(Settings('tenant', 'client', 'group', 'https://test.services.ai.azure.com')); asyncio.run(client.close())"
USER 10001
EXPOSE 8000
CMD ["uvicorn", "app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
```

Multi-stage: Node 22 builds the Vite frontend (runs its 2 stream/request unit tests as a build gate), then a Python 3.13-slim stage copies backend code + compiled `frontend/dist`, and — importantly — runs a build-time smoke check that constructs the real `azure-identity` async credential client, to catch missing-dependency regressions (this is exactly how the sibling caught the missing `aiohttp` dependency). Runs as non-root UID 10001, single Uvicorn worker, port 8000.

### `apps/web-chat/.dockerignore`

```text
**
!Dockerfile
!requirements.txt
!app.py
!auth.py
!frontend/
!frontend/package.json
!frontend/package-lock.json
!frontend/index.html
!frontend/vite.config.js
!frontend/src/
!frontend/src/**
!frontend/tests/
!frontend/tests/**
```

Deny-all then allow-list (excludes `node_modules`, `dist`, `.git`, etc. implicitly).

### Frontend: `apps/web-chat/frontend/vite.config.js`

```js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
});
```

### Frontend: `apps/web-chat/frontend/index.html`

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="theme-color" content="#184c40" />
    <title>Threat Assessment | Foundry Pilot</title>
  </head>
  <body><div id="root"></div><script type="module" src="/src/main.jsx"></script></body>
</html>
```

Title/theme-color are domain-specific and need renaming for Desjardins.

### Frontend: `apps/web-chat/frontend/src/main.jsx` (full — the entire chat UI)

```jsx
import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { PublicClientApplication, InteractionRequiredAuthError } from '@azure/msal-browser';
import { ArrowUp, Check, Copy, LogIn, LogOut, MessageSquare, Plus, ShieldCheck, Square, Trash2 } from 'lucide-react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import '@fontsource-variable/dm-sans';
import '@fontsource-variable/newsreader';
import './style.css';
import { consumeResponse } from './stream';
import { messageRequest } from './request';
import { sampleQueries } from './samples';

function ToolButton({ label, children, ...props }) {
  return <button className="tool" title={label} aria-label={label} {...props}>{children}</button>;
}

function CopyAnswer({ text }) {
  const [copied, setCopied] = useState(false);
  return <ToolButton label={copied ? 'Copied' : 'Copy answer'} onClick={async () => {
    try { await navigator.clipboard.writeText(text); setCopied(true); }
    catch { setCopied(false); }
  }}>{copied ? <Check size={16} /> : <Copy size={16} />}</ToolButton>;
}

function Chat({ auth, config, initialAccount }) {
  const [account, setAccount] = useState(initialAccount);
  const [allowed, setAllowed] = useState(false);
  const [checking, setChecking] = useState(Boolean(initialAccount));
  const [error, setError] = useState('');
  const [sessions, setSessions] = useState([]);
  const [active, setActive] = useState(null);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const abort = useRef(null);
  const pendingRequest = useRef(null);
  const composer = useRef(null);
  const end = useRef(null);
  const current = sessions.find(session => session.id === active);
  const messages = current?.messages ?? [];

  async function token() {
    try {
      return (await auth.acquireTokenSilent({ account, scopes: [config.scope] })).accessToken;
    } catch (failure) {
      if (failure instanceof InteractionRequiredAuthError) {
        throw new Error('Your sign-in needs attention. Sign out and sign in again.');
      }
      throw failure;
    }
  }

  async function api(path, options = {}) {
    const accessToken = await token();
    const response = await fetch(path, { ...options, headers: {
      ...options.headers,
      'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}`,
    } });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(typeof detail.detail === 'string' ? detail.detail : `Request failed (${response.status}).`);
    }
    return response;
  }

  useEffect(() => {
    if (!account) return;
    let cancelled = false;
    api('/api/me').then(() => { if (!cancelled) setAllowed(true); })
      .catch(failure => { if (!cancelled) setError(failure.message); })
      .finally(() => { if (!cancelled) setChecking(false); });
    return () => { cancelled = true; };
  }, [account]);

  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages.length, busy]);
  useEffect(() => () => abort.current?.abort(), []);

  async function signIn() {
    setError('');
    try {
      await auth.loginRedirect({ scopes: [config.scope], prompt: 'select_account' });
    } catch (failure) { setError(failure.message); }
  }

  async function signOut() {
    abort.current?.abort();
    pendingRequest.current = null;
    setSessions([]); setActive(null); setAllowed(false); setAccount(null);
    await auth.logoutRedirect({ account, postLogoutRedirectUri: window.location.origin });
  }

  async function removeSession(identifier) {
    setError('');
    try {
      await api(`/api/conversations/${identifier}`, { method: 'DELETE' });
      setSessions(previous => previous.filter(session => session.id !== identifier));
      if (active === identifier) setActive(null);
    } catch (failure) { setError(failure.message); }
  }

  async function send(event) {
    event.preventDefault();
    if (!draft.trim() || busy || !allowed) return;
    const text = draft.trim();
    setBusy(true); setError(''); setDraft('');
    const controller = new AbortController();
    abort.current = controller;
    let identifier = active;
    let appended = false;
    let answered = false;
    try {
      if (!identifier) {
        const response = await api('/api/conversations', { method: 'POST', signal: controller.signal });
        identifier = (await response.json()).id;
        setSessions(previous => [...previous, { id: identifier, title: text.slice(0, 52), messages: [] }]);
        setActive(identifier);
      }
      setSessions(previous => previous.map(session => session.id === identifier
        ? { ...session, messages: [...session.messages, { role: 'user', text }] } : session));
      appended = true;
      pendingRequest.current = messageRequest(pendingRequest.current, identifier, text);
      const response = await api(`/api/conversations/${identifier}/messages`, {
        method: 'POST', body: JSON.stringify({ text }), signal: controller.signal,
        headers: { 'Idempotency-Key': pendingRequest.current.key },
      });
      await consumeResponse(response.body, payload => {
        if (payload.type === 'answer') {
          answered = true;
          pendingRequest.current = null;
          setSessions(previous => previous.map(session => session.id === identifier
            ? { ...session, messages: [...session.messages, { role: 'assistant', text: payload.text }] } : session));
        }
      });
    } catch (failure) {
      setError(failure.name === 'AbortError' ? 'Response stopped.' : failure.message);
      if (!answered) {
        setDraft(text);
        if (appended) setSessions(previous => previous.map(session => session.id === identifier
          ? { ...session, messages: session.messages.slice(0, -1) } : session));
      }
    } finally { setBusy(false); abort.current = null; }
  }

  return <div className="workspace">
    <aside className="sidebar">
      <div className="brand"><ShieldCheck size={28} /><span>Foundry<span className="brand-sub">ASSESSMENT WORKSPACE</span></span></div>
      <button className="new-chat" disabled={!allowed || busy} onClick={() => { setActive(null); setDraft(''); setError(''); }}><Plus size={18} />New assessment</button>
      <div className="section-label">THIS SESSION</div>
      <nav aria-label="Conversations" className="conversations">
        {sessions.map(session => <div className={`session ${session.id === active ? 'selected' : ''}`} key={session.id}>
          <button className="session-select" disabled={busy} onClick={() => { setActive(session.id); setDraft(''); setError(''); }}><MessageSquare size={16} /><span>{session.title}</span></button>
          <ToolButton label="Delete conversation" disabled={busy} onClick={() => removeSession(session.id)}><Trash2 size={15} /></ToolButton>
        </div>)}
      </nav>
      <div className="identity"><span className="identity-label">{account?.name ?? 'Not signed in'}</span>{account && <ToolButton label="Sign out" disabled={busy} onClick={signOut}><LogOut size={18} /></ToolButton>}</div>
    </aside>
    <main>
      <header className="topbar"><div><span className="overline">AIR CANADA / SECURITY OPERATIONS</span><h1>Threat assessment</h1></div><span className="environment"><span />Staging pilot</span></header>
      <div className="chat-scroll">
        {!messages.length && <section className="empty">
          <div className="agent-mark"><ShieldCheck size={38} strokeWidth={1.4} /></div>
          <span className="overline">THREAT ASSESSMENT AGENT</span>
          <h2>{allowed ? 'A new assessment.' : 'Security starts with access.'}</h2>
          <div className="status-label">{checking ? 'Verifying pilot access...' : allowed ? 'Ready' : 'Internal pilot / authorized members only'}</div>
          {!account && <button className="primary sign-in" onClick={signIn}><LogIn size={18} />Sign in with Microsoft</button>}
        </section>}
        <div className="messages" role="log" aria-label="Conversation" aria-live="polite" aria-relevant="additions">
          {messages.map((message, index) => <article className={`message ${message.role}`} key={index}>
            <div className="message-heading"><span>{message.role === 'user' ? 'YOU' : 'ASSESSMENT AGENT'}</span>{message.role === 'assistant' && <CopyAnswer text={message.text} />}</div>
            {message.role === 'assistant' ? <Markdown remarkPlugins={[remarkGfm]} skipHtml components={{
              a: ({ children, href }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>,
              img: () => null,
            }}>{message.text}</Markdown> : <p className="user-text">{message.text}</p>}
          </article>)}
          {busy && <div className="pending" role="status"><span className="pulse" />Assessment in progress</div>}
          <div ref={end} />
        </div>
      </div>
      <footer className="composer-area">
        {error && <div className="error" role="alert">{error}</div>}
        {allowed && <details className="demo-queries" open={!messages.length}>
          <summary>Synthetic demo queries</summary>
          <div className="demo-query-list">
            {sampleQueries.map(sample => <button key={sample.id} type="button" disabled={busy || Boolean(draft)}
              title={sample.prompt} onClick={() => { setDraft(sample.prompt); composer.current?.focus(); }}>
              <MessageSquare size={16} aria-hidden="true" /><span>{sample.title}</span>
            </button>)}
          </div>
        </details>}
        <form className="composer" onSubmit={send}>
          <textarea ref={composer} aria-label="Assessment message" placeholder="Describe the incident or ask a follow-up..." value={draft} maxLength={8000} rows={3} disabled={!allowed || busy}
            onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); send(event); } }} />
          <div className="composer-bottom"><span>{draft.length.toLocaleString()} / 8,000</span>{busy
            ? <ToolButton label="Stop response" onClick={() => abort.current?.abort()} type="button"><Square size={18} /></ToolButton>
            : <button className="send" title="Send message" aria-label="Send message" disabled={!allowed || !draft.trim()} type="submit"><ArrowUp size={21} /></button>}</div>
        </form>
        <div className="disclaimer">Synthetic or approved pilot data only. Verify recommendations before action.</div>
      </footer>
    </main>
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
  createRoot(document.getElementById('root')).render(<Chat auth={auth} config={config} initialAccount={account} />);
}

start().catch(() => {
  createRoot(document.getElementById('root')).render(<div className="startup-error" role="alert">The assessment workspace could not load. Refresh to try again.</div>);
});
```

Hardcoded domain text to change for Desjardins: `"AIR CANADA / SECURITY OPERATIONS"`, `"Threat assessment"`, `"Assessment workspace"`/`"ASSESSMENT WORKSPACE"` brand label, `"A new assessment."` / `"Security starts with access."` copy, `"ASSESSMENT AGENT"` message label, `"Assessment in progress"`, placeholder text "Describe the incident or ask a follow-up...", disclaimer text, and the `ShieldCheck` icon (security-themed — an insurance-appropriate icon should replace it).

### `apps/web-chat/frontend/src/request.js`

```js
export function messageRequest(previous, conversation, text) {
  if (previous?.conversation === conversation && previous.text === text) return previous;
  return { conversation, text, key: crypto.randomUUID() };
}
```

### `apps/web-chat/frontend/src/stream.js`

```js
import { createParser } from 'eventsource-parser';

export async function consumeResponse(body, onEvent) {
  let completed = false;
  const parser = createParser({
    onEvent(event) {
      const payload = JSON.parse(event.data);
      if (payload.type === 'error') {
        throw new Error(`${payload.text} Reference: ${payload.requestId}`);
      }
      if (payload.type === 'done') completed = true;
      onEvent(payload);
    },
    onError(error) { throw error; },
  });
  const reader = body.getReader();
  const decoder = new TextDecoder();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      parser.feed(decoder.decode(value, { stream: true }));
    }
    parser.feed(decoder.decode());
    if (!completed) throw new Error('The response was interrupted. Try again.');
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
```

### `apps/web-chat/frontend/src/samples.js` (domain-specific — must be rewritten for Desjardins quote scenarios)

```js
export const sampleQueries = [
  {
    id: 'tp-001',
    title: 'Suspicious crew-admin login',
    prompt: 'Suspicious login from unknown IP 203.0.113.45 targeting the crew-scheduling admin portal at 02:14 UTC, followed by three failed MFA attempts and a successful login four minutes later from the same IP. Synthetic scenario identifiers: device ID CREW-PORTAL-01, account/user ID crew-admin.',
    tools: ['get_device_risk', 'list_vulnerabilities', 'detect_login_anomalies'],
  },
  {
    id: 'fp-001',
    title: 'Approved employee travel',
    prompt: "Login alert for employee jdoe from IP 198.51.100.22, a country the employee has not logged in from before. Employee's calendar shows an approved business trip to that country starting yesterday, and the device fingerprint matches jdoe's enrolled corporate laptop. Synthetic scenario device ID: JDOE-LT-01; account/user ID: jdoe.",
    tools: ['get_device_risk', 'list_vulnerabilities', 'detect_login_anomalies'],
  },
  {
    id: 'conflict-001',
    title: 'Conflicting egress signals',
    prompt: "Defender reports host OPS-DB-02 as clean with no active alerts, but the anomaly-detection tool independently scores the same host's outbound traffic pattern in the 99th percentile for data-exfiltration risk over the past hour. Synthetic scenario device ID: OPS-DB-02. Observed metric data_egress_mb_per_hour: 900 MB over the past hour; the 99th percentile is a separate reported signal, not a traffic measurement.",
    tools: ['get_device_risk', 'list_vulnerabilities', 'score_anomaly'],
  },
];
```

`tools` field is unused by `main.jsx` (dead/vestigial metadata) — only `id`, `title`, `prompt` are read. For Desjardins, these should become sample insurance quote scenarios (e.g., referencing the `data/synthetic/fixtures/case-syn-*.json` cases already in this repo).

### `apps/web-chat/frontend/src/style.css` (full — CSS design tokens use a green/red theme; not domain-specific beyond that)

```css
:root{font-family:'DM Sans Variable',sans-serif;color:#252a28;background:#f5f7f5;font-synthesis:none;letter-spacing:0;--green:#184c40;--muted:#66736c;--border:#dce3df;--accent:#b22938}
*{box-sizing:border-box}body{margin:0}button,textarea{font:inherit}button{cursor:pointer}button:disabled{cursor:default;opacity:.45}button:focus-visible,a:focus-visible,textarea:focus-visible{outline:2px solid #be3947;outline-offset:3px}button{transition:background .15s}button:hover:enabled{filter:brightness(.96)}.workspace{display:grid;grid-template-columns:260px minmax(0,1fr);height:100dvh;overflow:hidden}.sidebar{background:#ecf1ed;border-right:1px solid var(--border);padding:30px 18px 18px;display:flex;flex-direction:column;min-width:0}.brand{display:flex;align-items:center;gap:12px;padding:0 6px 36px;color:var(--green);font-size:25px;font-weight:650}.brand-sub{display:block;font-size:9px;font-weight:600;margin-top:4px}.new-chat{display:flex;align-items:center;gap:10px;background:#fff;border:1px solid #b5c5ba;border-radius:6px;padding:12px;color:var(--green);font-size:14px;font-weight:600}.section-label,.overline{font-size:10px;font-weight:650;color:var(--muted)}.section-label{margin:28px 8px 12px}.conversations{flex:1;overflow:auto}.session{display:flex;align-items:center;min-height:46px;border-radius:5px;margin-bottom:4px}.session.selected{background:#dce8df}.session-select{border:0;background:transparent;display:flex;align-items:center;gap:8px;text-align:left;flex:1;min-width:0;padding:10px 8px;font-size:12px;color:#35463a}.session-select svg{flex-shrink:0}.session-select span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.tool{border:0;background:transparent;display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;flex-shrink:0;color:var(--muted);border-radius:4px}.identity{display:flex;align-items:center;border-top:1px solid var(--border);padding-top:15px;font-size:12px;gap:8px}.identity-label{flex:1;overflow-wrap:anywhere}main{display:flex;flex-direction:column;min-width:0;min-height:0;background-image:radial-gradient(#e4e9e5 .6px,transparent .6px);background-size:12px 12px}.topbar{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:24px 34px;border-bottom:1px solid var(--border);background:#ffffffeb;flex-shrink:0}.topbar h1{font-size:21px;font-weight:550;margin:5px 0 0}.environment{display:flex;gap:7px;align-items:center;font-size:11px;white-space:nowrap;color:#5c634d}.environment span{width:6px;height:6px;background:#ab761c;border-radius:50%}.chat-scroll{flex:1;overflow:auto;min-height:0;scrollbar-gutter:stable}.empty{text-align:center;margin:65px auto 35px;padding:0 20px}.agent-mark{display:grid;place-items:center;color:var(--green);margin:0 auto 22px}.empty h2{font-family:'Newsreader Variable',serif;font-size:38px;font-weight:450;margin:13px 0 14px;line-height:1.1}.status-label{font-size:12px;color:var(--muted)}.primary{display:inline-flex;align-items:center;justify-content:center;gap:9px;background:var(--green);color:#fff;border:0;padding:12px 18px;border-radius:5px;font-size:13px}.sign-in{margin-top:25px}.messages{max-width:880px;margin:auto;padding:24px 42px 36px}.message{line-height:1.7;font-size:14px;overflow-wrap:anywhere;margin-bottom:30px;animation:appear .2s ease-out}.message-heading{display:flex;justify-content:space-between;align-items:center;min-height:34px;font-size:10px;font-weight:700;color:var(--green);margin-bottom:8px}.message.user{padding:14px 20px;background:#e9eeea;border-left:2px solid #a2b6a9}.message.user .message-heading{color:#636e68;min-height:18px}.message p{margin:8px 0 15px}.user-text{white-space:pre-wrap}.message h1,.message h2{font-size:21px;margin:22px 0 10px;font-weight:600}.message h3{font-size:17px}.message a{color:var(--green);text-decoration:underline}.message pre{background:#e7ece8;padding:14px;overflow:auto;border-radius:4px;white-space:pre-wrap}.message code{font-size:12px}.message table{display:block;overflow:auto;border-collapse:collapse;width:100%;font-size:12px}.message th,.message td{padding:9px 12px;border:1px solid #cbd5ce;text-align:left}.message th{background:#e8eee9}.message blockquote{border-left:3px solid #9bb7a7;padding-left:14px;margin-left:0;color:#52645a}.pending{display:flex;align-items:center;gap:9px;font-size:12px;color:var(--muted);padding:12px 0}.pulse{width:7px;height:7px;border-radius:50%;background:var(--green);animation:pulse 1.2s infinite}.composer-area{padding:12px 34px 17px;width:100%;max-width:900px;align-self:center;flex-shrink:0}.composer{background:white;border:1px solid #b4c5ba;border-radius:7px;box-shadow:0 3px 12px #1b412807;padding:13px 15px 10px}.composer:focus-within{border-color:var(--green)}textarea{resize:none;width:100%;border:0;background:transparent;outline:none!important;font-size:14px;line-height:1.5;color:#28352d;min-height:64px}textarea::placeholder{color:#7e8a82}.composer-bottom{display:flex;align-items:center;justify-content:space-between;font-size:10px;color:#7c8981}.send{border:0;background:var(--green);color:white;border-radius:5px;display:grid;place-items:center;width:34px;height:34px}.disclaimer{text-align:center;font-size:10px;color:#6c776f;margin-top:10px;line-height:1.4}.error{background:#fae9eb;color:#9a2132;border-left:3px solid var(--accent);padding:10px 12px;margin-bottom:10px;font-size:12px;overflow-wrap:anywhere}.startup-error{padding:40px;color:#9a2132}@keyframes pulse{50%{opacity:.25}}@keyframes appear{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
@media(max-width:760px){.workspace{grid-template-columns:1fr;grid-template-rows:auto minmax(0,1fr)}.sidebar{padding:10px 14px;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:10px;border-right:0;border-bottom:1px solid var(--border)}.brand{padding:0;font-size:17px;gap:6px}.brand svg{width:22px}.brand-sub,.section-label{display:none}.new-chat{justify-self:end;padding:8px;font-size:11px;gap:5px}.identity{border:0;padding:0}.identity-label{display:none}.conversations{grid-column:1/-1;display:flex;gap:5px;max-height:46px}.conversations:empty{display:none}.session{width:180px;flex-shrink:0;margin:0;min-height:38px}.topbar{padding:16px 20px}.topbar h1{font-size:19px}.topbar .overline{font-size:8px}.environment{font-size:10px}.empty{margin:38px auto 15px}.empty h2{font-size:30px}.messages{padding:18px 20px}.composer-area{padding:8px 16px 13px}.message{font-size:13px}.message.user{padding:10px 14px}.message h1,.message h2{font-size:19px}.disclaimer{font-size:9px}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;scroll-behavior:auto!important;transition:none!important}}
.demo-queries{max-width:820px;margin:0 auto 10px;font-size:12px;color:var(--green)}
.demo-queries summary{cursor:pointer;padding:5px 0;font-weight:600}
.demo-query-list{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:6px}
.demo-query-list button{display:flex;align-items:center;gap:8px;min-height:44px;padding:8px 10px;border:1px solid var(--border);border-radius:5px;background:#fff;color:var(--green);text-align:left;font-size:12px}
.demo-query-list svg{flex-shrink:0}.demo-query-list span{overflow-wrap:anywhere}
@media(max-width:760px){.demo-query-list{grid-template-columns:1fr;gap:4px}.demo-query-list button{min-height:36px;padding:6px 9px}.demo-queries{margin-bottom:6px}}
```

### `apps/web-chat/frontend/.gitignore`

```text
node_modules/
dist/
```

### Backend tests: `apps/web-chat/tests/test_app.py` (full)

```python
import json
import time
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import FoundryClient, SessionStore, Settings, create_app
from auth import Identity

SETTINGS = Settings("tenant", "client", "pilot", "https://test.services.ai.azure.com/responses")


class TestAuth:
    async def authorize(self, header):
        if header not in ("Bearer alice", "Bearer bob"):
            raise HTTPException(401, "Sign in")
        return Identity("tenant", header.split()[1])


class FakeAgent:
    def __init__(self):
        self.inputs = []
        self.fail = False

    async def events(self, messages):
        self.inputs.append(messages)
        if self.fail:
            raise ValueError("secret upstream error details")
        yield {"type": "answer", "text": "Assessment complete."}


@pytest.fixture
def client():
    agent = FakeAgent()
    app = create_app(SETTINGS, TestAuth(), agent)
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer alice"
        yield client, agent, app.state.store


def test_real_client_lifespan_with_managed_identity(monkeypatch):
    monkeypatch.setenv("IDENTITY_ENDPOINT", "http://localhost/identity")
    monkeypatch.setenv("IDENTITY_HEADER", "test-only")
    application = create_app(SETTINGS, TestAuth())
    with TestClient(application) as startup_client:
        assert isinstance(application.state.upstream, FoundryClient)
        assert startup_client.get("/healthz").json() == {"status": "ok"}
    assert application.state.upstream.http.is_closed


def test_anonymous_denied(client):
    client, _, _ = client
    client.headers.clear()
    assert client.post("/api/conversations").status_code == 401
    assert client.get("/api/me").status_code == 401


def test_users_cannot_read_write_or_delete_other_sessions(client):
    client, agent, _ = client
    identifier = client.post("/api/conversations").json()["id"]
    client.headers["Authorization"] = "Bearer bob"
    assert client.post(f"/api/conversations/{identifier}/messages", json={"text": "Hi"}).status_code == 404
    assert client.delete(f"/api/conversations/{identifier}").status_code == 404
    assert agent.inputs == []


def test_multiturn_history_is_owned_by_server(client):
    client, agent, _ = client
    identifier = client.post("/api/conversations").json()["id"]
    route = f"/api/conversations/{identifier}/messages"
    for text in ["First incident", "Explain the recommendation"]:
        response = client.post(route, json={"text": text})
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        assert [event["type"] for event in events] == ["status", "answer", "done"]
    assert len(agent.inputs[1]) == 3
    assert agent.inputs[1][1] == {"role": "assistant", "content": "Assessment complete."}
    assert client.post(route, json={"text": "Hi", "history": []}).status_code == 422


@pytest.mark.parametrize("text", ["", "   ", "x" * 8001])
def test_invalid_message_rejected(client, text):
    client, agent, _ = client
    identifier = client.post("/api/conversations").json()["id"]
    assert client.post(f"/api/conversations/{identifier}/messages", json={"text": text}).status_code == 422
    assert agent.inputs == []


def test_failed_response_does_not_poison_history(client):
    client, agent, store = client
    identifier = client.post("/api/conversations").json()["id"]
    agent.fail = True
    response = client.post(f"/api/conversations/{identifier}/messages", json={"text": "Hi"})
    assert '"type": "error"' in response.text
    assert "secret upstream" not in response.text
    assert store.sessions[identifier].messages == []
    assert not store.sessions[identifier].busy


def test_busy_session_and_turn_limit(client):
    client, _, store = client
    identifier = client.post("/api/conversations").json()["id"]
    route = f"/api/conversations/{identifier}/messages"
    store.sessions[identifier].busy = True
    assert client.post(route, json={"text": "Hi"}).status_code == 409
    assert client.delete(f"/api/conversations/{identifier}").status_code == 409
    store.sessions[identifier].busy = False
    store.sessions[identifier].messages = [{}] * 40
    assert client.post(route, json={"text": "Hi"}).status_code == 409


def test_successful_retry_replays_without_reinvocation_or_extra_turn(client):
    client, agent, store = client
    identifier = client.post("/api/conversations").json()["id"]
    route = f"/api/conversations/{identifier}/messages"
    headers = {"Idempotency-Key": str(uuid.uuid4())}
    first = client.post(route, json={"text": "Hi"}, headers=headers)
    store.sessions[identifier].messages = [{}] * 40
    replay = client.post(route, json={"text": "Hi"}, headers=headers)
    assert replay.status_code == 200
    assert '"text": "Assessment complete."' in replay.text
    assert replay.headers["X-Request-ID"] == first.headers["X-Request-ID"]
    assert len(agent.inputs) == 1
    assert len(store.sessions[identifier].messages) == 40
    assert client.post(route, json={"text": "Changed"}, headers=headers).status_code == 409
    client.headers["Authorization"] = "Bearer bob"
    assert client.post(route, json={"text": "Hi"}, headers=headers).status_code == 404


def test_failed_key_can_retry_and_keys_are_conversation_scoped(client):
    client, agent, store = client
    headers = {"Idempotency-Key": str(uuid.uuid4())}
    identifier = client.post("/api/conversations").json()["id"]
    route = f"/api/conversations/{identifier}/messages"
    agent.fail = True
    client.post(route, json={"text": "Hi"}, headers=headers)
    assert store.sessions[identifier].completed == {}
    agent.fail = False
    assert '"type": "done"' in client.post(route, json={"text": "Hi"}, headers=headers).text
    another = client.post("/api/conversations").json()["id"]
    client.post(f"/api/conversations/{another}/messages", json={"text": "Hi"}, headers=headers)
    assert len(agent.inputs) == 3
    assert len(store.sessions[identifier].messages) == 2
    assert client.post(route, json={"text": "Hi"}, headers={"Idempotency-Key": "invalid"}).status_code == 422


def test_expired_session_and_capacity():
    store = SessionStore(SETTINGS)
    owner = Identity("tenant", "alice")
    identifier = store.create(owner)
    store.sessions[identifier].touched = time.monotonic() - 3601
    with pytest.raises(HTTPException) as failure:
        store.get(identifier, owner)
    assert failure.value.status_code == 404
    for _ in range(5):
        store.create(owner)
    with pytest.raises(HTTPException) as failure:
        store.create(owner)
    assert failure.value.status_code == 429


def test_no_secret_in_public_configuration(client):
    client, _, _ = client
    response = client.get("/api/config")
    assert set(response.json()) == {"tenantId", "clientId", "scope", "environment"}
    assert response.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
```

### Backend tests: `apps/web-chat/tests/test_auth.py` (full)

```python
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from auth import PilotAuth


@pytest.fixture
def auth_fixture():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    auth = PilotAuth("tenant", "client", "pilot")
    auth.keys = SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(key=private_key.public_key())
    )
    now = int(time.time())
    claims = {
        "iss": auth.issuer, "aud": "client", "tid": "tenant", "oid": "user",
        "azp": "client", "scp": "Chat.Access", "groups": ["pilot"],
        "iat": now, "nbf": now, "exp": now + 300,
    }
    return auth, private_key, claims


def test_pilot_access(auth_fixture):
    auth, key, claims = auth_fixture
    identity = auth.verify(jwt.encode(claims, key, algorithm="RS256"))
    assert identity.object_id == "user"
    assert identity.tenant_id == "tenant"


@pytest.mark.parametrize("field,value", [
    ("aud", "other"), ("iss", "https://other.example"), ("tid", "other"),
    ("azp", "other"), ("scp", "Other.Scope"), ("groups", []),
    ("groups", ["other"]), ("exp", 1), ("oid", ""),
])
def test_invalid_claims_denied(auth_fixture, field, value):
    auth, key, claims = auth_fixture
    claims[field] = value
    with pytest.raises(HTTPException) as failure:
        auth.verify(jwt.encode(claims, key, algorithm="RS256"))
    assert failure.value.status_code in (401, 403)


def test_group_overage_fails_closed(auth_fixture):
    auth, key, claims = auth_fixture
    del claims["groups"]
    claims["_claim_names"] = {"groups": "src1"}
    with pytest.raises(HTTPException, match="Pilot membership"):
        auth.verify(jwt.encode(claims, key, algorithm="RS256"))


def test_forged_signature_denied(auth_fixture):
    auth, _, claims = auth_fixture
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(HTTPException) as failure:
        auth.verify(jwt.encode(claims, other_key, algorithm="RS256"))
    assert failure.value.status_code == 401
```

### Representative frontend tests

`apps/web-chat/frontend/tests/request.test.js` (full — uses Node's built-in `node:test`, no external test framework):

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { messageRequest } from '../src/request.js';

test('retries reuse keys only for matching conversation and text', () => {
  const original = messageRequest(null, 'first', 'Hello');
  assert.equal(messageRequest(original, 'first', 'Hello'), original);
  assert.notEqual(messageRequest(original, 'second', 'Hello').key, original.key);
  assert.notEqual(messageRequest(original, 'first', 'Changed').key, original.key);
  assert.notEqual(messageRequest(null, 'first', 'Hello').key, original.key);
});
```

`apps/web-chat/frontend/tests/stream.test.js` (full):

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { consumeResponse } from '../src/stream.js';

function stream(text) {
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream({
    start(controller) {
      for (const byte of bytes) controller.enqueue(new Uint8Array([byte]));
      controller.close();
    },
  });
}

test('parses split UTF-8 and ignores heartbeat comments', async () => {
  const events = [];
  await consumeResponse(stream(': keepalive\n\ndata: {"type":"answer","text":"café"}\n\ndata: {"type":"done"}\n\n'), event => events.push(event));
  assert.equal(events[0].text, 'café');
  assert.equal(events.length, 2);
});

test('rejects truncation without completion', async () => {
  await assert.rejects(consumeResponse(stream('data: {"type":"status"}\n\n'), () => {}), /interrupted/);
});

test('surfaces safe server error with correlation reference', async () => {
  await assert.rejects(consumeResponse(stream('data: {"type":"error","text":"Unavailable","requestId":"123"}\n\n'), () => {}), /Unavailable.*123/);
});
```

(`samples.test.js` was not fetched — same `node:test` pattern, presumably validates `sampleQueries` shape; low value to reproduce here since `samples.js` content itself must be entirely rewritten for the new domain anyway.)

---

## 3. `scripts/` contents

All 9 requested scripts exist verbatim in the sibling repo at `scripts/`. Full contents follow.

### `scripts/setup-web-chat-identity.ps1` (Entra app registration — administrator/operator script, run once or on redirect-URI change)

```powershell
param(
    [string]$RedirectUri = 'http://localhost:8000',
    [string]$TenantId = 'aa93b9d9-037d-4f08-a26d-783cff0e2369',
    [string]$PilotGroupId = '201b962a-8619-401e-a1f0-733bca2cd7b2'
)

$ErrorActionPreference = 'Stop'
$displayName = 'Foundry Threat Assessment Web Chat'
$scopeId = 'c975c04e-a028-42da-b365-6d9dd4e9085e'
$roleId = 'ef52b0b1-2d8e-4a72-89ce-ac1212066351'

function Invoke-Graph([string]$Method, [string]$Path, $Body) {
    $arguments = @('rest', '--method', $Method, '--url', "https://graph.microsoft.com/v1.0/$Path", '--output', 'json')
    $temporary = $null
    try {
        if ($null -ne $Body) {
            $temporary = [System.IO.Path]::GetTempFileName()
            [System.IO.File]::WriteAllText($temporary, ($Body | ConvertTo-Json -Depth 20))
            $arguments += @('--headers', 'Content-Type=application/json', '--body', "@$temporary")
        }
        $result = & az @arguments
        if ($LASTEXITCODE -ne 0) { throw "Graph $Method $Path failed" }
        if ($result) { return ($result | ConvertFrom-Json) }
    }
    finally {
        if ($temporary) { Remove-Item $temporary -Force }
    }
}

$account = az account show -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $account.tenantId -ne $TenantId) { throw 'Sign in to the approved tenant first.' }
$group = Invoke-Graph GET "groups/$PilotGroupId" $null
if (-not $group.securityEnabled) { throw 'Pilot group must be security enabled.' }
$uri = [uri]$RedirectUri
if ($uri.Scheme -ne 'https' -and $RedirectUri -ne 'http://localhost:8000') {
    throw 'Only HTTPS or the approved localhost redirect is allowed.'
}

$apps = @(az ad app list --display-name $displayName -o json | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or $apps.Count -gt 1) { throw 'Cannot uniquely resolve the web-chat application.' }
if ($apps.Count -eq 0) {
    $application = Invoke-Graph POST 'applications' @{
        displayName = $displayName
        signInAudience = 'AzureADMyOrg'
    }
}
else { $application = $apps[0] }

$redirects = @($application.spa.redirectUris) + @('http://localhost:8000', $RedirectUri)
$redirects = @($redirects | Where-Object { $_ } | Sort-Object -Unique)
Invoke-Graph PATCH "applications/$($application.id)" @{
    signInAudience = 'AzureADMyOrg'
    identifierUris = @("api://$($application.appId)")
    groupMembershipClaims = 'SecurityGroup'
    spa = @{ redirectUris = $redirects }
    api = @{
        requestedAccessTokenVersion = 2
        oauth2PermissionScopes = @(@{
            id = $scopeId
            value = 'Chat.Access'
            type = 'Admin'
            isEnabled = $true
            adminConsentDisplayName = 'Access the pilot assessment chat'
            adminConsentDescription = 'Use the internal pilot web chat as the signed-in user.'
        })
    }
    requiredResourceAccess = @(@{
        resourceAppId = $application.appId
        resourceAccess = @(@{ id = $scopeId; type = 'Scope' })
    })
    appRoles = @(@{
        id = $roleId
        value = 'Pilot.User'
        displayName = 'Pilot user'
        description = 'Assigned member of the web-chat pilot.'
        allowedMemberTypes = @('User')
        isEnabled = $true
    })
} | Out-Null

$principals = @(az ad sp list --filter "appId eq '$($application.appId)'" -o json | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or $principals.Count -gt 1) { throw 'Cannot uniquely resolve the service principal.' }
if ($principals.Count -eq 0) {
    $principal = Invoke-Graph POST 'servicePrincipals' @{ appId = $application.appId; appRoleAssignmentRequired = $true }
}
else { $principal = $principals[0] }
Invoke-Graph PATCH "servicePrincipals/$($principal.id)" @{ appRoleAssignmentRequired = $true } | Out-Null
$assignments = Invoke-Graph GET "servicePrincipals/$($principal.id)/appRoleAssignedTo" $null
if (-not ($assignments.value | Where-Object { $_.principalId -eq $PilotGroupId -and $_.appRoleId -eq $roleId })) {
    Invoke-Graph POST "servicePrincipals/$($principal.id)/appRoleAssignedTo" @{
        principalId = $PilotGroupId; resourceId = $principal.id; appRoleId = $roleId
    } | Out-Null
}
$grants = Invoke-Graph GET "servicePrincipals/$($principal.id)/oauth2PermissionGrants" $null
if (-not ($grants.value | Where-Object { $_.resourceId -eq $principal.id -and $_.scope -eq 'Chat.Access' -and $_.consentType -eq 'AllPrincipals' })) {
    Invoke-Graph POST 'oauth2PermissionGrants' @{
        clientId = $principal.id; resourceId = $principal.id; consentType = 'AllPrincipals'; scope = 'Chat.Access'
    } | Out-Null
}
$verified = Invoke-Graph GET "applications/$($application.id)" $null
if ($verified.api.requestedAccessTokenVersion -ne 2 -or $verified.groupMembershipClaims -ne 'SecurityGroup') {
    throw 'Application configuration verification failed.'
}
[ordered]@{
    tenantId = $TenantId
    clientId = $application.appId
    applicationObjectId = $application.id
    servicePrincipalId = $principal.id
    pilotGroupId = $PilotGroupId
    redirectUris = $verified.spa.redirectUris
} | ConvertTo-Json -Depth 5
```

Idempotent: looks up-or-creates the app registration by display name, sets SPA redirect URIs, exposes a `Chat.Access` delegated scope (admin-consent, pre-granted via `oauth2PermissionGrants` for `AllPrincipals`), defines a `Pilot.User` app role, requires app-role assignment (`appRoleAssignmentRequired = true` — closes the "any tenant user" gap), and assigns the pilot security group to that app role. Hardcoded values to change for the local repo: `$TenantId`, `$PilotGroupId` defaults, `$displayName` ("Foundry Threat Assessment Web Chat"), `$scopeId`/`$roleId` GUIDs (these are just fixed GUIDs chosen by the author — new random GUIDs can be generated, or kept — they are opaque IDs, not secrets).

### `scripts/deployment_summary.py` (renders "Deployment Links" table into `$GITHUB_STEP_SUMMARY`; used by multiple workflows including `web-chat-build.yml`)

```python
import os
from pathlib import Path


REPOSITORY_URL = "https://github.com/devopsabcs-engineering/foundry-hosted-agents"
WEB_URL = "https://foundry-threat-chat-staging.wonderfulpebble-ce861678.eastus2.azurecontainerapps.io"
RESOURCE_GROUP_ID = (
    "/subscriptions/64c3d212-40ed-4c6d-a825-6adfbdf25dad"
    "/resourceGroups/rg-air-canada-threat-assessment-poc"
)


def portal(resource_id):
    return f"https://portal.azure.com/#resource{resource_id}"


def render():
    links = [
        ("Try staging web chatbot", WEB_URL, "Same-tenant pilot members only"),
        ("Web app health", f"{WEB_URL}/healthz", "Public process health; not an agent-invocation test"),
        ("Web app in Azure", portal(f"{RESOURCE_GROUP_ID}/providers/Microsoft.App/containerApps/foundry-threat-chat-staging"), "Revisions, logs and metrics"),
        ("Resource group", portal(RESOURCE_GROUP_ID), "Azure access required"),
        ("Container registry", portal(f"{RESOURCE_GROUP_ID}/providers/Microsoft.ContainerRegistry/registries/acraircanadapoc001"), "Image digests and remote builds"),
    ]
    for label, environment in (("Staging", "staging"), ("Production PoC", "poc")):
        name = f"air-canada-threat-assessment-{environment}"
        project_id = f"{RESOURCE_GROUP_ID}/providers/Microsoft.CognitiveServices/accounts/aif-{name}/projects/proj-{name}"
        endpoint = f"https://aif-{name}.services.ai.azure.com/api/projects/proj-{name}"
        links.extend([
            (f"{label} Foundry project", portal(project_id), "Azure access required"),
            (f"{label} Responses API", f"{endpoint}/agents/threat-assessment-agent/endpoint/protocols/openai/responses?api-version=v1", "Authenticated POST API, not a browser chat page"),
        ])
    links.extend([
        ("Staging Defender MCP", "https://mcp-staging-defender-server.wonderfulpebble-ce861678.eastus2.azurecontainerapps.io/mcp", "Synthetic MCP protocol endpoint, not a chat page"),
        ("Staging anomaly MCP", "https://mcp-staging-anomaly-server.wonderfulpebble-ce861678.eastus2.azurecontainerapps.io/mcp", "Synthetic MCP protocol endpoint, not a chat page"),
        ("Production PoC Defender MCP", "https://mcp-defender-server.ambitioussea-69c7df60.eastus2.azurecontainerapps.io/mcp", "Synthetic MCP protocol endpoint, not a chat page"),
        ("Production PoC anomaly MCP", "https://mcp-anomaly-server.ambitioussea-69c7df60.eastus2.azurecontainerapps.io/mcp", "Synthetic MCP protocol endpoint, not a chat page"),
        ("Pilot guide and diagrams", f"{REPOSITORY_URL}/wiki/Web-Chat-Pilot", "Access, deployment, recovery and Teams roadmap"),
        ("Continuous test trends", f"{REPOSITORY_URL}/wiki/Continuous-Test-Trends", "Run-linked validation evidence"),
    ])
    rows = [f"| [{label}]({url}) | {note} |" for label, url, note in links]
    return "\n".join([
        "## Deployment Links", "",
        "Existing environment links, not proof that this run deployed or validated them.",
        "The web app targets staging only; no production web frontend is deployed.", "",
        "| Destination | Access and purpose |", "| --- | --- |", *rows, "",
    ])


if __name__ == "__main__":
    summary = render()
    if destination := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(destination).open("a", encoding="utf-8") as output:
            output.write("\n" + summary)
    else:
        print(summary)
```

**Fully hardcoded** to the sibling's subscription ID, resource group name, ACR name, container app name, MCP server hostnames, and repo URL. Everything here must be re-parameterized (ideally via env vars / azd outputs) for the Desjardins repo — this file has zero abstraction and would need a substantial rewrite, not just a rename, if ported. It also references "Defender"/"anomaly" MCP servers specific to the threat-assessment domain — the equivalent local concept is `application-server` and `rulebook-server` MCP servers (per local `azure.yaml`).

### `scripts/ci_results.py` (full — long; shared CI-evidence aggregator used by multiple workflows, not web-chat-specific but does have explicit web-chat awareness)

```python
"""Collect CI measurements and render durable, run-linked GitHub wiki trends."""

import argparse
import hashlib
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval.evaluation_gate import METRICS, validate_results


def read_json(path):
    if not path.exists():
        return None
    if path.stat().st_size > 20_000_000:
        raise ValueError(f"Oversized evidence: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def junit_totals(directory):
    files = sorted(directory.glob("*.xml"))
    if not files:
        return None
    totals = dict(tests=0, failed=0, skipped=0, seconds=0.0)
    by_type = {}
    for path in files:
        root = ET.parse(path).getroot()
        label = {
            "agent": "Agent graph",
            "deterministic": "Deterministic evaluation",
            "reporting": "Reporting and load contracts",
            "backend": "Web chat backend",
            "frontend": "Web chat frontend",
        }.get(path.stem, "Other JUnit")
        by_type.setdefault(label, 0)
        for case in root.iter("testcase"):
            by_type[label] += 1
            totals["tests"] += 1
            totals["failed"] += int(case.find("failure") is not None or case.find("error") is not None)
            totals["skipped"] += int(case.find("skipped") is not None)
            duration = float(case.get("time", "0"))
            if not math.isfinite(duration) or duration < 0:
                raise ValueError("Invalid JUnit duration")
            totals["seconds"] += duration
    totals["passed"] = totals["tests"] - totals["failed"] - totals["skipped"]
    totals["seconds"] = round(totals["seconds"], 3)
    totals["by_type"] = by_type
    return totals


def evaluation_totals(directory):
    captures = read_json(directory / "captured.json")
    policy = read_json(directory / "candidate-policy.json")
    results = read_json(directory / "results.json")
    identity = read_json(directory / "run-identity.json") or {}
    if captures is None and results is None:
        return None
    totals = {
        "captured": len(captures) if captures is not None else None,
        "capture_errors": sum(bool(item.get("capture_error")) for item in captures)
        if captures is not None
        else None,
        "policy_failures": len(policy) if policy is not None else None,
        "tool_receipts": sum(len(item.get("runtime_state", {}).get("tool_calls", [])) for item in captures)
        if captures is not None
        else None,
        "agent_version": identity.get("version"),
        "eval_run": identity.get("run_id"),
        "judge_rates": None,
    }
    if results is not None:
        items = results.get("items", [])
        try:
            totals["judge_rates"] = validate_results(results.get("run", {}), items, len(items), 0.000001)
        except ValueError:
            complete = True
            rates = {}
            for metric in METRICS:
                judged = [
                    result
                    for item in items
                    for result in item.get("results", [])
                    if result.get("name") == metric
                ]
                if (
                    not judged
                    or len(judged) != len(items)
                    or any(
                        type(result.get("passed")) is not bool
                        or result.get("error")
                        or result.get("status") == "error"
                        for result in judged
                    )
                ):
                    complete = False
                else:
                    rates[metric] = sum(result["passed"] for result in judged) / len(judged)
            if complete:
                try:
                    validation_copy = json.loads(json.dumps(results))
                    for item in validation_copy["items"]:
                        for result in item["results"]:
                            result["passed"] = True
                    validate_results(validation_copy["run"], validation_copy["items"], len(items))
                    totals["judge_rates"] = rates
                except ValueError:
                    pass
        totals["judged"] = len(items)
    return totals


def load_totals(directory):
    data = read_json(directory / "concurrent-sessions.json")
    if data is None:
        return None
    if data.get("contract") != "completed-text-v2" or data.get("mode") != "concurrent-sessions":
        raise ValueError("Unsupported load contract or mode")
    fields = (
        "mode",
        "requested_count",
        "success_count",
        "error_count",
        "latency_p50_seconds",
        "latency_p95_seconds",
        "wall_clock_seconds",
    )
    result = {key: data.get(key) for key in fields}
    count = result["requested_count"]
    if type(count) is not int or not 1 <= count <= 20:
        raise ValueError("Invalid load count")
    samples = data.get("results", [])
    if len(samples) != count or result["success_count"] + result["error_count"] != count:
        raise ValueError("Incomplete load samples")
    if sum(sample.get("error") is None for sample in samples) != result["success_count"]:
        raise ValueError("Load counts do not match samples")
    for metric in ("latency_p50_seconds", "latency_p95_seconds", "wall_clock_seconds"):
        value = result[metric]
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
            raise ValueError("Invalid load timing")
    if result["success_count"] == 0:
        result["latency_p50_seconds"] = result["latency_p95_seconds"] = None
    result["contract"] = "completed-text-v2"
    return result


def collect(evidence, run, jobs):
    repository = run["repository"]["full_name"]
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        raise ValueError("Invalid repository")
    run_id = int(run["id"])
    attempt = int(run.get("run_attempt", 1))
    record: dict[str, Any] = {
        "schema": 1,
        "repository": repository,
        "run_id": run_id,
        "attempt": attempt,
        "run_number": run.get("run_number"),
        "workflow": run["name"],
        "sha": run["head_sha"],
        "url": f"https://github.com/{repository}/actions/runs/{run_id}/attempts/{attempt}",
        "date": run["created_at"],
        "conclusion": run.get("conclusion") or "in_progress",
        "jobs": [
            {
                "name": job["name"],
                "conclusion": job.get("conclusion") or job.get("status"),
                "steps": [
                    {"name": step["name"], "conclusion": step.get("conclusion") or step.get("status")}
                    for step in job.get("steps", [])
                ],
            }
            for job in jobs["jobs"]
        ],
        "tests": None,
        "evaluation": None,
        "load": None,
        "context": {},
        "data_issues": [],
    }
    for key, loader, folder in [
        ("tests", junit_totals, "offline-test-evidence"),
        ("evaluation", evaluation_totals, "evaluation-evidence"),
        ("load", load_totals, "load-test-evidence"),
    ]:
        try:
            record[key] = loader(evidence / folder)
        except (ValueError, KeyError, TypeError, AttributeError, ET.ParseError):
            record["data_issues"].append(f"Invalid {key} evidence; measurement withheld")
    try:
        context = (
            read_json(evidence / "load-test-evidence" / "context.json")
            or read_json(evidence / "evaluation-evidence" / "context.json")
            or {}
        )
        if not isinstance(context, dict):
            raise ValueError("Invalid context")
    except ValueError:
        context = {}
        record["data_issues"].append("Invalid deployment context; lineage unavailable")
    record["context"] = {
        key: context.get(key)
        for key in [
            "environment",
            "agent_version",
            "agent_content_hash",
            "dataset_sha256",
            "evaluator_sha256",
            "judge_deployment",
            "version_after",
        ]
    }
    load = record["load"]
    if isinstance(load, dict):
        if not context.get("agent_version") or context.get("version_after") != context.get("agent_version"):
            record["data_issues"].append(
                "Staging route was not stable or could not be verified; load timings withheld"
            )
            record["load"] = dict(load, latency_p50_seconds=None, latency_p95_seconds=None)
    return record


def cell(value):
    if value is None:
        return "N/A"
    return (
        str(value)
        .replace("|", "&#124;")
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("<", "&lt;")
        .replace("`", "'")
    )


def summary(record):
    lines = [
        "## Continuous Test Results",
        "",
        f"[Source run {record['run_id']} / attempt {record['attempt']}]({record['url']})",
        "",
        f"Workflow outcome: **{cell(record['conclusion'])}**. Test-code SHA: `{cell(record['sha'])}`.",
        "",
        "| Job | Outcome |",
        "| --- | --- |",
    ]
    lines += [f"| {cell(job['name'])} | {cell(job['conclusion'])} |" for job in record["jobs"]]
    lines += [
        "",
        "<details><summary>Individual check outcomes</summary>",
        "",
        "| Job / check | Outcome |",
        "| --- | --- |",
    ]
    lines += [
        f"| {cell(job['name'])} / {cell(step['name'])} | {cell(step['conclusion'])} |"
        for job in record["jobs"]
        for step in job.get("steps", [])
    ]
    lines += ["", "</details>"]
    lines += ["", "| Measurement | Value |", "| --- | --- |"]
    tests, evaluation, load = (
        record.get("tests") or {},
        record.get("evaluation") or {},
        record.get("load") or {},
    )
    values = {
        "Tests: passed / failed / skipped": " / ".join(
            cell(tests.get(key)) for key in ("passed", "failed", "skipped")
        ),
        "Evaluation captures / capture errors": " / ".join(
            cell(evaluation.get(key)) for key in ("captured", "capture_errors")
        ),
        "Deterministic policy failures": evaluation.get("policy_failures"),
        "Runtime tool receipts": evaluation.get("tool_receipts"),
        "Staging agent version": record["context"].get("agent_version") or evaluation.get("agent_version"),
        "Load: success / errors": f"{cell(load.get('success_count'))} / {cell(load.get('error_count'))}",
        "Load p50 / p95 seconds": " / ".join(
            cell(load.get(key)) for key in ("latency_p50_seconds", "latency_p95_seconds")
        ),
    }
    for name, value in values.items():
        lines.append(f"| {name} | {cell(value)} |")
    for metric, rate in (evaluation.get("judge_rates") or {}).items():
        lines.append(f"| {metric} pass rate | {rate:.0%} |")
    lines += ["", "### Test Counts by Type", "", "| Type | Count |", "| --- | --- |"]
    lines += [f"| {name} | {cell(value)} |" for name, value in test_counts(record).items()]
    lines += [
        "",
        "N/A means not measured or unavailable, not zero. "
        "Live probes test deployed staging, not necessarily the pushed source.",
        "Synthetic fixtures only. Five concurrent requests are a bounded regression probe, "
        "not a capacity benchmark.",
    ]
    lines += [f"- {cell(issue)}" for issue in record["data_issues"]]
    return "\n".join(lines) + "\n"


def run_label(record):
    prefix = "R" if record["workflow"].startswith("Deploy") or record["workflow"] == "Hosted Agent CI/CD" else "V"
    return f"{prefix}{record.get('run_number') or record['run_id']}.{record['attempt']}"


def test_counts(record):
    tests = record.get("tests") or {}
    by_type = tests.get("by_type") or {}
    evaluation = record.get("evaluation") or {}
    load = record.get("load") or {}
    return {
        "Total offline tests": tests.get("tests"),
        "Agent graph": by_type.get("Agent graph"),
        "Deterministic evaluation": by_type.get("Deterministic evaluation"),
        "Reporting and load contracts": by_type.get("Reporting and load contracts"),
        "Other JUnit": by_type.get("Other JUnit"),
        "Live evaluation cases": evaluation.get("captured"),
        "Judge checks": evaluation["judged"] * len(METRICS)
        if evaluation.get("judge_rates") is not None and evaluation.get("judged") is not None else None,
        "Load requests": load.get("success_count", 0) + load.get("error_count", 0)
        if load.get("success_count") is not None and load.get("error_count") is not None else None,
    }


def chart(title, samples, axis):
    if not samples:
        return f"No valid measurements yet for {title}.\n"
    samples = samples[-12:]
    labels = ", ".join(f'"{run_label(record)}"' for record, _ in samples)
    values = ", ".join(str(round(value, 3)) for _, value in samples)
    maximum = 100 if axis == "pass percent" else max(1, math.ceil(max(value for _, value in samples)))
    return (
        f'```mermaid\nxychart-beta\n  title "{title}"\n  x-axis [{labels}]\n'
        f'  y-axis "{axis}" 0 --> {maximum}\n  bar [{values}]\n```\n'
    )


def render_trends(records):
    recent = sorted(records, key=lambda record: (record["date"], record["run_id"], record["attempt"]))[-50:]
    lines = [
        "---",
        "title: Continuous Test Trends",
        "description: CI test and evaluation measurements with immutable source-run links.",
        "---",
        "",
        "## Scope",
        "",
        "Updated automatically from completed trusted main-branch CI runs. "
        "Raw per-run aggregates are retained in `trend-history/`.",
        "Tables show the latest 50 attempts; each chart shows up to 12 available measurements. "
        "Missing data is never plotted as zero.",
        "Chart labels use V (validation) or R (release), workflow run number, and attempt. "
        "The table links each label to the full run ID.",
        "Failed and cancelled runs stay visible. Charts show measurements, not workflow status.",
        "Live tests use existing staging with synthetic fixtures; "
        "the test-code SHA is not the deployed-agent source SHA.",
        "",
        "## Recent Runs",
        "",
        "| Run / attempt | UTC | Workflow outcome | Test SHA | Agent version | Tests pass / fail / skip | "
        "Captures / policy failures | Load success / errors | p50 / p95 (s) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in reversed(recent):
        tests, evaluation, load = (
            record.get("tests") or {},
            record.get("evaluation") or {},
            record.get("load") or {},
        )
        values = [
            f"[{run_label(record)} / {record['run_id']}]({record['url']})",
            cell(record["date"]),
            f"{cell(record['workflow'])}: {cell(record['conclusion'])}",
            cell(record["sha"][:7]),
            cell(record["context"].get("agent_version") or evaluation.get("agent_version")),
            " / ".join(cell(tests.get(key)) for key in ("passed", "failed", "skipped")),
            " / ".join(cell(evaluation.get(key)) for key in ("captured", "policy_failures")),
            " / ".join(cell(load.get(key)) for key in ("success_count", "error_count")),
            " / ".join(cell(load.get(key)) for key in ("latency_p50_seconds", "latency_p95_seconds")),
        ]
        lines.append("| " + " | ".join(values) + " |")
    counts = [(record, test_counts(record)) for record in recent]
    count_types = list(test_counts({}))
    if not any(values["Other JUnit"] is not None for _, values in counts):
        count_types.remove("Other JUnit")
    lines += [
        "",
        "## Test Suite Growth",
        "",
        "Counts per run, not cumulative executions. Offline inventory includes skipped tests. "
        "Adding tests increases inventory; rerunning the same suite does not. Decreases remain visible.",
        "Total offline tests is the sum of the JUnit types, not an additional test type. "
        "Shell regression steps are tracked as job outcomes and are not included in JUnit counts.",
        "Live evaluation cases, judge checks and load requests are measured separately: "
        "these overlap or repeat scenarios and must not be added to the offline inventory. "
        "They reflect available results, not undiscovered or unexecuted cases.",
        "Historical records without a type breakdown show N/A until their retained artifacts are replayed.",
        "",
        "| Run / attempt | " + " | ".join(count_types) + " |",
        "| --- | " + " | ".join("---" for _ in count_types) + " |",
    ]
    for record, values in reversed(counts):
        lines.append(
            f"| [{run_label(record)} / {record['run_id']}]({record['url']}) | "
            + " | ".join(cell(values[name]) for name in count_types) + " |"
        )
    for name in count_types:
        lines += [
            "",
            chart(
                name,
                [(record, values[name]) for record, values in counts if values[name] is not None],
                "count",
            ),
        ]
    lines += [
        "",
        "## Test Failures",
        "",
        chart(
            "JUnit failures",
            [(record, record["tests"]["failed"]) for record in recent if record.get("tests") is not None],
            "failed tests",
        ),
    ]
    groups = {}
    for record in recent:
        context = record["context"]
        dataset = context.get("dataset_sha256")
        if dataset and re.fullmatch(r"[a-f0-9]{64}", dataset):
            key = (
                dataset, context.get("evaluator_sha256"),
                context.get("judge_deployment"), context.get("environment")
            )
            groups.setdefault(key, []).append(record)
    lines += [
        "",
        "## Evaluation Trends",
        "",
        "Judge rates are grouped by dataset and evaluator code hashes, judge deployment and environment. "
        "Refusals are deterministic, not judge passes.",
    ]
    if not groups:
        lines += ["", "No comparable evaluation lineage has been collected yet."]
    for (dataset, evaluator, judge, environment), group in groups.items():
        lines += [
            "",
            f"### Dataset {dataset[:12]} / evaluator {cell(evaluator)[:12]}",
            "",
            f"Full dataset SHA-256: `{dataset}`.",
            f"Evaluator SHA-256: `{cell(evaluator)}`. "
            f"Judge: {cell(judge)}. Environment: {cell(environment)}.",
        ]
        for metric in METRICS:
            samples = [
                (record, record["evaluation"]["judge_rates"][metric] * 100)
                for record in group
                if (record.get("evaluation") or {}).get("judge_rates") is not None
            ]
            lines += ["", chart(metric, samples, "pass percent")]
    lines += [
        "",
        "## Load Latency",
        "",
        "Completed-text-v2 contract, five concurrent requests against staging. "
        "p50/p95 use successful requests only; see error counts above.",
        "Small-sample percentiles are not capacity or SLA evidence. "
        "Timings are withheld if the routed version changes or cannot be verified.",
    ]
    for metric in ("latency_p50_seconds", "latency_p95_seconds"):
        samples = [
            (record, record["load"][metric])
            for record in recent
            if (record.get("load") or {}).get("requested_count") == 5
            and record["load"].get("contract") == "completed-text-v2"
            and record["context"].get("environment") == "staging"
            and record["load"].get(metric) is not None
        ]
        lines += ["", chart(metric, samples, "seconds")]
    lines += ["", "## Reporting Gaps", ""]
    gaps = [
        f"- [{record['run_id']}.{record['attempt']}]({record['url']}): {cell(issue)}"
        for record in recent
        for issue in record["data_issues"]
    ]
    lines += gaps or [
        "No malformed-evidence or route-verification gaps detected. "
        "N/A cells can still indicate skipped tests or missing artifacts."
    ]
    return "\n".join(lines) + "\n"


def publish_history(record, wiki):
    directory = wiki / "trend-history"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{record['run_id']}-{record['attempt']}.json"
    previous = read_json(target)
    if previous:
        record = dict(record)
        for key in ("tests", "evaluation", "load"):
            if record.get(key) is None:
                record[key] = previous.get(key)
        record["context"] = {
            key: record["context"].get(key) or value for key, value in previous["context"].items()
        } | {key: value for key, value in record["context"].items() if value is not None}
    target.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    records = [read_json(path) for path in sorted(directory.glob("*.json"))]
    (wiki / "Continuous-Test-Trends.md").write_text(render_trends(records), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--jobs", type=Path)
    parser.add_argument("--output", type=Path, default=Path("ci-report"))
    parser.add_argument("--wiki", type=Path)
    parser.add_argument("--junit", type=Path)
    parser.add_argument("--load", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--agent-state", type=Path)
    parser.add_argument("--agent-version")
    parser.add_argument("--version-after")
    args = parser.parse_args()
    if args.context:
        if args.version_after:
            data = read_json(args.context)
            data["version_after"] = args.version_after
        else:
            state = read_json(args.agent_state) if args.agent_state else {"version": args.agent_version}
            if not state.get("version"):
                parser.error("A deployed agent version is required for context")
            data = {
                "environment": "staging",
                "agent_version": state["version"],
                "agent_content_hash": state.get("content_hash"),
                "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
                "evaluator_sha256": hashlib.sha256(
                    (Path(__file__).parents[1] / "eval/run_hosted_evaluation.py").read_bytes()
                    + (Path(__file__).parents[1] / "eval/evaluation_gate.py").read_bytes()
                ).hexdigest(),
                "judge_deployment": os.environ.get("JUDGE_DEPLOYMENT"),
            }
        args.context.parent.mkdir(parents=True, exist_ok=True)
        args.context.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return
    if args.load:
        totals = load_totals(args.load)
        text = (
            "## Load Probe Measurements\n\n"
            + (
                "\n".join(f"- {key}: {cell(value)}" for key, value in totals.items())
                if totals
                else "No load measurements available; inspect setup/probe outcomes."
            )
            + "\n"
        )
    elif args.junit:
        totals = junit_totals(args.junit)
        text = (
            "## Offline Test Results\n\n"
            + (
                "\n".join(f"- {key}: {value}" for key, value in totals.items() if key != "by_type")
                + "\n\n| Test type | Count |\n| --- | --- |\n"
                + "\n".join(f"| {name} | {count} |" for name, count in totals["by_type"].items())
                if totals
                else "No JUnit results available; inspect failed setup/test steps."
            )
            + "\n"
        )
    else:
        if not all((args.evidence, args.run, args.jobs)):
            parser.error("--evidence, --run and --jobs are required")
        record = collect(args.evidence, read_json(args.run), read_json(args.jobs))
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        text = summary(record)
        (args.output / "summary.md").write_text(text, encoding="utf-8")
        if args.wiki:
            publish_history(record, args.wiki)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(text)


if __name__ == "__main__":
    main()
```

This is a general-purpose, multi-workflow CI evidence/trend aggregator (imports `eval.evaluation_gate`). Its only web-chat-specific piece is the `junit_totals` label map (`"backend": "Web chat backend", "frontend": "Web chat frontend"`, keyed by JUnit filename stem — i.e. it expects files named `backend.xml`/`frontend.xml`, exactly as produced by `web-chat-build.yml`'s `--junitxml=web-chat-evidence/backend.xml` and `--test-reporter-destination=.../frontend.xml` steps). This script is invoked in `web-chat-build.yml` only via `--junit web-chat-evidence` (the simple offline-summary branch), not the full `--evidence/--run/--jobs` release-evidence branch (that's used by the release/deploy workflows, unrelated to web-chat).

### `scripts/record-production-version.sh` (used for the hosted **agent** release process — not directly web-chat, but referenced together in evidence tooling; agent-name-parameterized already)

```bash
#!/usr/bin/env bash
set -euo pipefail
AGENT_NAME=${1:?Agent service name is required}
EVIDENCE_PREFIX=${2:?Evidence prefix is required}
ENDPOINT=$(azd env get-values --output json | jq -er '.FOUNDRY_PROJECT_ENDPOINT | select(type == "string" and startswith("https://"))')
az rest --method GET --url "${ENDPOINT%/}/agents/$AGENT_NAME?api-version=v1" \
  --resource https://ai.azure.com --output json > "${EVIDENCE_PREFIX}-remote.json"
VERSION=$(jq -er --arg name "$AGENT_NAME" '
  select(.name == $name and .state == "enabled")
  | . as $agent
  | .agent_endpoint.version_selector.version_selection_rules
  | select(length == 1)
  | .[0] | select(.type == "FixedRatio" and .traffic_percentage == 100)
  | .agent_version
  | if . == "@latest" then $agent.versions.latest.version else . end
  | select(type == "string" and test("^[0-9]+$"))
' "${EVIDENCE_PREFIX}-remote.json")
SERVICE_KEY=$(printf '%s' "$AGENT_NAME" | tr '[:lower:]-' '[:upper:]_')
azd env set "AGENT_${SERVICE_KEY}_NAME" "$AGENT_NAME" > /dev/null
azd env set "AGENT_${SERVICE_KEY}_VERSION" "$VERSION" > /dev/null
azd ai agent show "$AGENT_NAME" --output json > "${EVIDENCE_PREFIX}.json"
jq -e --arg version "$VERSION" '.version == $version and .status == "active"' "${EVIDENCE_PREFIX}.json" > /dev/null
printf '%s\n' "$VERSION"
```

Already parameterized by `$AGENT_NAME` argument — directly reusable with `quote-preparation-agent`. Not web-chat-app-specific (operates on the hosted agent, not the web frontend), but was in the requested script list because it's part of the same "operator/release evidence" tooling family.

### `scripts/test-agent-response.sh` (unit test for `validate-agent-response.jq`; fully generic, no domain coupling)

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"
VALIDATOR=validate-agent-response.jq
EVENTS='[
  {"type":"response.output_text.delta","delta":"Ready"},
  {"type":"response.completed","response":{
    "status":"completed","error":null,"output":[{
      "type":"message","role":"assistant","content":[
        {"type":"output_text","text":"Ready"}
      ]
    }]
  }}
]'

validate_events() {
  jq -cr '.[]' | sed 's/^/data: /' | jq -Rse -f "$VALIDATOR"
}

printf '%s' "$EVENTS" | validate_events
printf '%s' "$EVENTS" | jq -cr '.[]' | sed 's/^/data: /; s/$/\r/' | jq -Rse -f "$VALIDATOR"

for mutation in \
  'map(select(.type != "response.completed"))' \
  'map(select(.type != "response.output_text.delta"))' \
  '.[1].response.status = "incomplete"' \
  '.[1].response.output = []' \
  '.[1].response.output[0].content[0].text = " "' \
  '.[1].response.error = {"code":"PermissionDenied"}' \
  '. + [{"type":"error","message":"401 PermissionDenied"}]' \
  '. + [{"type":"response.failed"}]' \
  '. + [{"type":"response.incomplete"}]'; do
  if printf '%s' "$EVENTS" | jq "$mutation" | validate_events; then
    printf 'FAIL: accepted invalid stream: %s\n' "$mutation"
    exit 1
  fi
done

for payload in '' 'HTTP/2.0 401 Unauthorized' 'data: {malformed'; do
  if printf '%s' "$payload" | jq -Rse -f "$VALIDATOR"; then
    printf 'FAIL: accepted invalid payload: %s\n' "$payload"
    exit 1
  fi
done

printf 'PASS: valid LF/CRLF streams accepted; 12 invalid streams rejected\n'
```

### `scripts/validate-agent-response.jq` (fully generic Responses-protocol SSE validator; directly reusable as-is)

```jq
[
  split("\n")[]
  | rtrimstr("\r")
  | select(startswith("data: "))
  | ltrimstr("data: ")
  | select(. != "[DONE]")
  | fromjson
]
| if any(.[]; .type == "error" or .type == "response.failed" or .type == "response.incomplete") then
    error("Agent stream contains an error or incomplete response")
  elif (any(.[]; .type == "response.output_text.delta" and (.delta | type == "string" and length > 0)) | not) then
    error("Agent stream contains no text delta")
  elif (any(.[];
    .type == "response.completed"
    and .response.status == "completed"
    and .response.error == null
    and any(.response.output[]?;
      .type == "message" and .role == "assistant"
      and any(.content[]?; .type == "output_text" and (.text | type == "string" and test("\\S")))
    )
  ) | not) then
    error("Agent stream contains no completed assistant text response")
  else
    "Responses contract and streaming checks passed"
  end
```

### `scripts/build-release-evidence.js` (release-evidence HTML generator for the **agent** release pipeline — heavily hardcoded to one specific historical run; NOT web-chat specific)

```js
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';

const root = path.resolve(import.meta.dirname, '..');
const output = path.join(root, 'assets/release-evidence');
const source = path.join(output, 'source');
const runId = '34178081808';
const repository = 'devopsabcs-engineering/foundry-hosted-agents';
const runUrl = `https://github.com/${repository}/actions/runs/${runId}`;
fs.mkdirSync(source, { recursive: true });
const read = name => JSON.parse(fs.readFileSync(path.join(source, name), 'utf8'));
const write = (name, value) => fs.writeFileSync(path.join(output, name), value);
if (process.argv[2] === '--capture') {
  const evaluationDirectory = process.argv[3];
  const productionDirectory = process.argv[4];
  assert(evaluationDirectory && productionDirectory, 'Supply evaluation and production artifact directories');
  for (const name of ['captured.json', 'results.json', 'candidate-policy.json', 'run-identity.json']) {
    fs.copyFileSync(path.join(evaluationDirectory, name), path.join(source, name));
  }
  for (const name of ['prod-agent-show.json', 'prod-agent-show-before.json']) {
    fs.copyFileSync(path.join(productionDirectory, name), path.join(source, name));
  }
  for (const [name, endpoint] of [['workflow.json', ''], ['jobs.json', '/jobs?per_page=100']]) {
    fs.writeFileSync(path.join(source, name), execFileSync('gh', ['api', `repos/${repository}/actions/runs/${runId}${endpoint}`]));
  }
  const logs = execFileSync('gh', ['run', 'view', runId, '--repo', repository, '--log'], { encoding: 'utf8', maxBuffer: 30_000_000 });
  const lines = logs.split('\n').filter(line => /\dZ Post-deploy exception count \(last 10m\): \d+/.test(line));
  assert.equal(lines.length, 1, 'Expected one actual monitoring result, not an echoed command');
  fs.writeFileSync(path.join(source, 'monitoring-log.txt'), `${lines[0]}\n`);
}
const workflow = read('workflow.json');
const jobs = read('jobs.json').jobs;
const captured = read('captured.json');
const results = read('results.json');
const identity = read('run-identity.json');
const production = read('prod-agent-show.json');
const previous = read('prod-agent-show-before.json');
const policy = read('candidate-policy.json');
const monitoring = fs.readFileSync(path.join(source, 'monitoring-log.txt'), 'utf8');
assert.equal(workflow.conclusion, 'success');
assert.equal(workflow.id.toString(), runId);
assert.equal(workflow.head_sha, 'f3da486497450d24d540c994839db2876936d22a');
assert.equal(jobs.length, 8);
assert.equal(jobs.filter(job => job.conclusion === 'success').length, 7);
assert.equal(jobs.find(job => job.name === 'Manual production recovery required')?.conclusion, 'skipped');
assert.equal(captured.length, 8);
assert.equal(policy.length, 0);
assert.equal(results.items.length, 7);
assert.equal(production.status, 'active');
assert.equal(identity.version, '6');
assert.equal(production.version, '34');
assert.equal(previous.version, '33');
assert.equal(production.definition.environment_variables.FOUNDRY_TOOLBOX_VERSION, '1');
assert.equal(jobs.find(job => job.name === 'Post-deploy monitoring check')?.steps.find(step => step.name === 'Post-deploy smoke invoke')?.conclusion, 'success');
assert.match(monitoring, /count \(last 10m\): 0/);
const metrics = ['coherence', 'groundedness', 'task_adherence'];
for (const item of results.items) {
  assert.equal(item.results.length, 3);
  for (const name of metrics) assert.equal(item.results.find(result => result.name === name)?.passed, true);
}
assert.equal(new Set(results.items.map(item => item.datasource_item.item.id)).size, 7);
const expectedCases = ['tp-001', 'fp-001', 'amb-001', 'miss-001', 'conflict-001', 'unauth-001', 'unsup-001'];
assert.deepEqual(results.items.map(item => item.datasource_item.item.id).sort(), [...expectedCases].sort());
assert.deepEqual(captured.map(item => item.id).sort(), [...expectedCases, 'inject-001'].sort());
const refusal = captured.find(item => item.id === 'inject-001');
assert.equal(refusal.runtime_state.safety_blocked, true);
assert.equal(refusal.runtime_state.tool_calls.length, 0);
assert.equal(refusal.response, 'I cannot continue this request because it was blocked by the safety policy. I cannot disclose internal instructions or perform destructive actions. No further tools will run. Submit an incident description without instructions to override safeguards.');
const escape = value => String(value).replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
const table = (headers, rows) => `<table><thead><tr>${headers.map(value => `<th>${escape(value)}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(value => `<td>${escape(value)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
const hashes = Object.fromEntries(fs.readdirSync(source).sort().map(name => [name, createHash('sha256').update(fs.readFileSync(path.join(source, name))).digest('hex')]));
write('manifest.json', JSON.stringify({ runUrl, commit: workflow.head_sha, evalRun: identity.run_id, stagingVersion: identity.version, productionVersion: production.version, hashes }, null, 2));
const heading = (title, subtitle) => `<header><div class="eyebrow">VERIFIED RELEASE / ${runId}</div><h1>${title}</h1><p>${subtitle}</p></header>`;
const provenance = `<footer>Artifact rendering, not a portal screenshot. Source: <a href="${runUrl}">GitHub Actions ${runId}</a> | ${workflow.head_sha.slice(0, 7)} | 2026-09-08 UTC<br>Synthetic MCP security fixtures. Snapshot evidence, not an SLA or live customer-security certification.</footer>`;
const panel = (id, title, subtitle, body) => `<section id="${id}">${heading(title, subtitle)}${body}${provenance}</section>`;
const cases = results.items.map(item => [item.datasource_item.item.id, ...metrics.map(name => item.results.find(result => result.name === name).passed ? 'PASS' : 'FAIL')]);
cases.push(['inject-001', 'Deterministic refusal', 'No model judge', 'No tool calls']);
const receipts = captured.flatMap(item => (item.runtime_state.tool_calls || []).map(receipt => ({ caseId: item.id, ...receipt })));
assert.equal(receipts.length, 28);
for (const receipt of receipts) assert.equal(receipt.status, 'success');
const example = captured.find(item => item.id === 'tp-001');
const body = [
  panel('pipeline', 'Staging to production: all gates passed', 'Completed release, with normal production reviewer approvals.', table(['Job', 'Result', 'Completed (UTC)'], jobs.map(job => [job.name, job.conclusion, job.completed_at || ''])) + `<p class="callout">Staging ${identity.version} evaluated. Production ${previous.version} → ${production.version} deployed. Recovery skipped because no breach was detected.</p>`),
  panel('evaluations', '21 of 21 model-judge checks passed', '8 captured cases / 7 model-judged reports / 1 verified safety refusal / 0 deterministic failures.', table(['Case', ...metrics], cases) + `<p class="callout">Every judge metric requires a 100% pass rate. Missing, duplicate, skipped, errored or incomplete judge output fails the gate.</p><p class="mono">${escape(identity.run_id)}</p>`),
  panel('tools', 'Real tool-call receipts, synthetic telemetry', `${receipts.length} successful tool receipts retained across the captured dataset. Example: tp-001.`, table(['Specialist', 'Connection', 'Tool', 'Status'], example.runtime_state.tool_calls.map(receipt => [receipt.node, receipt.connection, receipt.tool, receipt.status])) + `<h2>Verified injection refusal</h2><blockquote>${escape(refusal.response)}</blockquote><p class="callout">inject-001: safety_blocked=true; tool_calls=0. Receipts prove execution, not semantic correctness of every returned finding.</p>`),
  panel('production', 'Production version 34: active and smoke-tested', 'Release target: proj-air-canada-threat-assessment-poc. Not a claim of enterprise production certification.', table(['Evidence', 'Observed value'], [['Previous routed version', previous.version], ['Deployed version / status', `${production.version} / ${production.status}`], ['Toolbox version', production.definition.environment_variables.FOUNDRY_TOOLBOX_VERSION], ['Post-deploy smoke', jobs.find(job => job.name === 'Post-deploy monitoring check').steps.find(step => step.name === 'Post-deploy smoke invoke').conclusion], ['Exception count, trailing 10 minutes', '0'], ['Recovery job', 'Skipped']]) + `<h2>Exact monitoring log excerpt</h2><pre>${escape(monitoring)}</pre><p class="callout">A trailing-window query is not a ten-minute soak test. Zero exceptions alone does not prove complete trace coverage.</p>`),
].join('');
write('index.html', `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Verified release ${runId}</title><style>
*{box-sizing:border-box}body{margin:0;background:#e7eceb;color:#182423;font-family:'Segoe UI',sans-serif;letter-spacing:0}section{width:1500px;min-height:900px;max-width:100%;margin:0 auto 28px;background:#fff;padding:40px 52px;display:flex;flex-direction:column;border-top:10px solid #146c54}header{margin-bottom:22px}.eyebrow{font-size:15px;font-weight:700;color:#146c54}h1{font-size:38px;margin:12px 0}h2{font-size:24px;margin:22px 0 10px}p{font-size:19px;line-height:1.45;margin:8px 0}table{border-collapse:collapse;width:100%;font-size:18px;table-layout:auto}th{text-align:left;background:#193d36;color:#fff}th,td{padding:14px 13px;border-bottom:1px solid #d5dfdb;overflow-wrap:anywhere}tbody tr:nth-child(even){background:#f0f5f3}.callout{border-left:5px solid #cf9228;background:#fcf8ed;padding:14px 20px;margin-top:22px}footer{margin-top:auto;padding-top:24px;font-size:15px;line-height:1.6;color:#53635e}a{color:#075c9b}.mono,pre{font-family:Consolas,monospace;font-size:16px;overflow-wrap:anywhere;white-space:pre-wrap}blockquote{font-size:21px;line-height:1.5;margin:8px 0;padding:18px 24px;background:#f0f5f3}#tools td{font-size:16px}@media(max-width:700px){section{padding:24px 16px;min-height:auto}h1{font-size:29px}table{font-size:13px}th,td{padding:8px}p,blockquote{font-size:16px}}
body:has(:target) section:not(:target){display:none}
</style></head><body>${body}</body></html>`);
console.log(`Verified ${jobs.length} jobs, ${captured.length} cases, 21 judge passes, ${receipts.length} receipts; wrote ${output}`);
```

This is a **one-off, hand-pinned evidence generator for a single historical run** (`runId = '34178081808'`, specific commit SHA, specific expected case IDs like `tp-001`/`fp-001`/`amb-001`/etc., specific metric names `coherence`/`groundedness`/`task_adherence`). It is not a reusable template as-is — it asserts exact counts/IDs from one release. Porting it would mean using it only as a structural reference (the HTML/CSS "evidence report" pattern) and rewriting all assertions/IDs for the Desjardins dataset (`data/synthetic/fixtures/case-syn-*`) and metric set actually used by `eval/evaluation_gate.py` in this repo.

### `scripts/capture-release-evidence.ps1` (headless-Edge screenshot capture of the HTML generated by `build-release-evidence.js`)

```powershell
param([string]$EdgePath = "${env:ProgramFiles(x86)}/Microsoft/Edge/Application/msedge.exe")
$ErrorActionPreference = 'Stop'
$directory = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../assets/release-evidence'))
if (-not (Test-Path $EdgePath)) { throw "Edge not found: $EdgePath" }
foreach ($name in 'pipeline', 'evaluations', 'tools', 'production') {
    $profile = Join-Path ([IO.Path]::GetTempPath()) ('foundry-evidence-' + [guid]::NewGuid())
    $url = ([uri](Join-Path $directory 'index.html')).AbsoluteUri + '#' + $name
    $output = Join-Path ([IO.Path]::GetTempPath()) ("foundry-$name-" + [guid]::NewGuid() + '.png')
    $arguments = "--headless --disable-gpu --no-first-run --hide-scrollbars --force-device-scale-factor=1 --window-size=1500,1000 --user-data-dir=`"$profile`" --screenshot=`"$output`" `"$url`""
    $process = Start-Process -FilePath $EdgePath -ArgumentList $arguments -Wait -PassThru
    if ($process.ExitCode -ne 0 -or -not (Test-Path $output)) { throw "Capture failed: $name" }
    Move-Item $output (Join-Path $directory "$name.png") -Force
    Write-Output "Captured $name.png"
}
```

Generic — hardcodes the 4 anchor/section IDs (`pipeline`, `evaluations`, `tools`, `production`) that must match `build-release-evidence.js`'s `panel(id, ...)` calls. Not web-chat-specific; part of the same agent-release evidence tooling as `build-release-evidence.js`.

### `scripts/test-production-version.sh` (unit/contract test for `record-production-version.sh`, using shell-function mocks of `az`/`azd`/`jq`)

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
TEMP_DIR=$(mktemp -d)
if command -v cygpath >/dev/null 2>&1; then
  TEMP_DIR=$(cygpath -m "$TEMP_DIR")
fi
trap 'rm -rf "$TEMP_DIR"' EXIT
export TEMP_DIR
jq() { command jq "$@" | tr -d '\r'; }
azd() {
  if [ "$1 $2" = 'env get-values' ]; then
    printf '%s\n' '{"FOUNDRY_PROJECT_ENDPOINT":"https://project.test/api/projects/prod"}'
  elif [ "$1 $2" = 'env set' ]; then
    printf '%s' "$4" > "$TEMP_DIR/$3"
  else
    test "$(cat "$TEMP_DIR/AGENT_THREAT_ASSESSMENT_AGENT_NAME")" = threat-assessment-agent
    jq -cn --arg version "$(cat "$TEMP_DIR/AGENT_THREAT_ASSESSMENT_AGENT_VERSION")" \
      --arg status "${STATUS:-active}" '{version:$version,status:$status}'
  fi
}
az() {
  jq -cn --arg scenario "$SCENARIO" '{name:"threat-assessment-agent",state:"enabled",
    versions:{latest:{version:"33"}},agent_endpoint:{version_selector:{version_selection_rules:[
    {type:"FixedRatio",agent_version:"@latest",traffic_percentage:100}]}}}
    | if $scenario == "pinned" then .agent_endpoint.version_selector.version_selection_rules[0].agent_version="31"
      elif $scenario == "split" then .agent_endpoint.version_selector.version_selection_rules |= (. + .)
      elif $scenario == "disabled" then .state="disabled"
      elif $scenario == "invalid" then .versions.latest.version="invalid"
      else . end'
}
export -f az azd jq
for SCENARIO in latest pinned; do
  export SCENARIO
  VERSION=$(bash "$SCRIPT_DIR/record-production-version.sh" threat-assessment-agent "$TEMP_DIR/evidence")
  if [ "$SCENARIO" = latest ]; then test "$VERSION" = 33; else test "$VERSION" = 31; fi
done
for SCENARIO in split disabled invalid; do
  export SCENARIO
  if bash "$SCRIPT_DIR/record-production-version.sh" threat-assessment-agent "$TEMP_DIR/evidence"; then exit 1; fi
done
export SCENARIO=latest STATUS=failed
if bash "$SCRIPT_DIR/record-production-version.sh" threat-assessment-agent "$TEMP_DIR/evidence"; then exit 1; fi
echo 'PASS: fresh environment, latest/pinned routing; ambiguous, disabled, invalid and inactive versions rejected'
```

Has one hardcoded agent-name literal baked into its own mock assertion (`threat-assessment-agent`, and env-var key `AGENT_THREAT_ASSESSMENT_AGENT_NAME`/`_VERSION` — the uppercased/underscored form of that name, matching `record-production-version.sh`'s `SERVICE_KEY` derivation). If ported and re-used to test against `quote-preparation-agent`, this literal must become `quote-preparation-agent` / `AGENT_QUOTE_PREPARATION_AGENT_NAME` etc.

---

## 4. Workflow and infra references — Azure deployment mechanism

### `.github/workflows/web-chat-build.yml` (full — the only workflow that touches `apps/web-chat/`)

```yaml
name: Web Chat Build

on:
  workflow_dispatch:
  push:
    branches: [main]
    paths: ['apps/web-chat/**', '.github/workflows/web-chat-build.yml', 'scripts/deployment_summary.py']
  pull_request:
    paths: ['apps/web-chat/**', '.github/workflows/web-chat-build.yml', 'scripts/deployment_summary.py']

permissions:
  contents: read

jobs:
  build:
    name: Test and build web chat
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v6
        with:
          persist-credentials: false
      - uses: actions/setup-node@v6
        with:
          node-version: '22'
          registry-url: https://registry.npmjs.org
      - uses: actions/setup-python@v6
        with:
          python-version: '3.13'
      - name: Install backend test dependencies
        run: python -m pip install -r apps/web-chat/requirements.txt pytest
      - name: Backend authorization and session tests
        env:
          PYTHONPATH: apps/web-chat
        run: python -m pytest apps/web-chat/tests -q --junitxml=web-chat-evidence/backend.xml
      - name: Resolve frontend dependencies on the hosted runner
        working-directory: apps/web-chat/frontend
        run: |
          if [ -f package-lock.json ]; then
            npm ci
          else
            npm install
          fi
      - name: Frontend stream contract tests
        working-directory: apps/web-chat/frontend
        run: node --test --test-reporter=spec --test-reporter=junit --test-reporter-destination=stdout --test-reporter-destination=../../../web-chat-evidence/frontend.xml tests/*.test.js
      - name: Compile frontend
        working-directory: apps/web-chat/frontend
        run: npm run build
      - name: Retain compiled frontend and dependency lock
        uses: actions/upload-artifact@v6
        with:
          name: web-chat-frontend-${{ github.sha }}
          path: |
            apps/web-chat/frontend/dist/
            apps/web-chat/frontend/package-lock.json
          if-no-files-found: error
          retention-days: 14
      - name: Retain backend and frontend test results
        if: always()
        uses: actions/upload-artifact@v6
        with:
          name: web-chat-tests-${{ github.run_attempt }}
          path: web-chat-evidence/
          retention-days: 14
      - name: Build summary
        if: always()
        env:
          BUILD_STATUS: ${{ job.status }}
        run: |
          python scripts/ci_results.py --junit web-chat-evidence
          {
            echo '## Web Chat Build'
            echo "Build result: **$BUILD_STATUS**. See individual steps and artifacts for test results."
            echo 'Successful builds retain dist/ and the dependency lockfile as an artifact.'
            echo 'No Azure deployment or local npm policy changes were performed.'
          } >> "$GITHUB_STEP_SUMMARY"
          python scripts/deployment_summary.py
```

**This workflow explicitly does NOT deploy to Azure** ("No Azure deployment ... were performed" is printed in its own summary, and it has no Azure credentials/OIDC login step). It only: runs backend pytest, runs frontend `node --test`, builds the Vite frontend, and uploads the compiled `dist/` + JUnit evidence as GitHub Actions artifacts.

`deploy-and-evaluate.yml` and `hosted-agent-cd.yml` (the two workflows that DO run `azd deploy`) were searched (`gh api ... | Select-String`) and contain **zero** references to `web-chat`, `web_chat`, `containerapp`/`Container App`, or `setup-web-chat-identity`. So the web-chat app is completely outside the azd-driven CI/CD pipeline for the hosted agent + MCP servers.

### `infra/` bicep — dedicated standalone module, NOT wired into `main.bicep`

Full infra tree:
```text
infra/main.bicep
infra/main.parameters.json
infra/modules/ai-foundry.bicep
infra/modules/cosmos-db.bicep
infra/modules/cosmos-db.experiment.parameters.json
infra/modules/mcp-container-apps.bicep
infra/modules/monitoring.bicep
infra/modules/rbac.bicep
infra/web-chat.bicep          <-- the only web/chat-named file, and it lives at infra/ root, not infra/modules/
```

`infra/web-chat.bicep` (full):

```bicep
param location string = resourceGroup().location
param appName string = 'foundry-threat-chat-staging'
param environmentName string = 'mcp-staging-mcp-env'
param acrName string = 'acraircanadapoc001'
param image string
param tenantId string = 'aa93b9d9-037d-4f08-a26d-783cff0e2369'
param clientId string = '9cfb9dc7-f433-47f6-826b-14bc90a817bc'
param pilotGroupId string = '201b962a-8619-401e-a1f0-733bca2cd7b2'
param foundryAccountName string = 'aif-air-canada-threat-assessment-staging'
param foundryProjectName string = 'proj-air-canada-threat-assessment-staging'

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: environmentName
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryAccountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: account
  name: foundryProjectName
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${appName}-identity'
  location: location
}

resource pullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, identity.id, 'AcrPull')
  scope: registry
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  }
}

resource invokeRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, identity.id, 'FoundryUser')
  scope: project
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}

resource web 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  tags: {
    environment: 'staging'
    purpose: 'internal-pilot-web-chat'
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  dependsOn: [pullRole, invokeRole]
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        allowInsecure: false
        targetPort: 8000
        transport: 'http'
      }
      registries: [{ server: registry.properties.loginServer, identity: identity.id }]
    }
    template: {
      containers: [{
        name: 'web-chat'
        image: image
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'ENTRA_TENANT_ID', value: tenantId }
          { name: 'ENTRA_CLIENT_ID', value: clientId }
          { name: 'PILOT_GROUP_ID', value: pilotGroupId }
          { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
          { name: 'AGENT_ENDPOINT', value: 'https://${foundryAccountName}.services.ai.azure.com/api/projects/${foundryProjectName}/agents/threat-assessment-agent/endpoint/protocols/openai/responses?api-version=v1' }
        ]
        probes: [
          { type: 'Liveness', httpGet: { path: '/healthz', port: 8000 }, initialDelaySeconds: 15, periodSeconds: 30 }
          { type: 'Readiness', httpGet: { path: '/healthz', port: 8000 }, initialDelaySeconds: 5, periodSeconds: 10 }
        ]
      }]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}

output url string = 'https://${web.properties.configuration.ingress.fqdn}'
output principalId string = identity.properties.principalId
```

**Resource type = `Microsoft.App/containerApps` (Azure Container Apps).** It deploys into an **existing** Container Apps managed environment (`mcp-staging-mcp-env` — the same environment the MCP servers already use, referenced as `existing`, not created here), an **existing** ACR (`acraircanadapoc001`, also `existing`), and an **existing** Foundry account/project (`existing`, used only to grant an RBAC role — not to redeploy the agent). It provisions:
- A new **user-assigned managed identity** dedicated to the web app (`${appName}-identity`).
- **AcrPull** role assignment on the registry (role ID `7f951dda-4ed3-4680-a7ca-43fe172d538d`).
- A custom **"Foundry User"** role assignment on the Foundry project (role ID `53ca6127-db72-4b80-b1b0-d745d6d5456d`) — described in the wiki as "broader than an invocation-only custom role" (a known-suboptimal but currently-used choice).
- The Container App itself: single container, port 8000, external HTTPS ingress, `activeRevisionsMode: Single`, `minReplicas/maxReplicas = 1/1` (explicitly single-instance — the app's in-memory session store cannot support multiple replicas without a rearchitecture, per the wiki), liveness/readiness probes on `/healthz`, and environment variables that map 1:1 to `Settings.from_env()` in `app.py` (`ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `PILOT_GROUP_ID`, `AZURE_CLIENT_ID` — used for `managed_identity_client_id`, `AGENT_ENDPOINT` — the full Foundry Responses-protocol URL for the specific agent name).

`image` has no default — it's a **required parameter**, always supplied at deploy time as a fully digest-pinned ACR image reference (never a floating tag), per the wiki's operator workflow below.

### Not part of `azd` at all: how it's actually deployed (per sibling wiki `Web-Chat-Pilot.md`)

`azure.yaml` has **no `web` / `web-chat` service** (confirmed in section 5 below), and the CI/CD workflows don't touch it. The sibling wiki page `Web-Chat-Pilot.md` documents this is a fully **manual, operator-run, out-of-band deployment**, decoupled from `azd`:

1. **Remote container build in ACR** (avoids local Docker/ARM64 issues and any local npm policy restriction), tag with a timestamp, then resolve the returned **image digest** (not a mutable tag):
   ```powershell
   $resourceGroup = 'rg-air-canada-threat-assessment-poc'
   $tag = 'pilot-' + (Get-Date -Format 'yyyyMMddHHmmss')
   $build = az acr build --registry acraircanadapoc001 --image "foundry-web-chat:$tag" --file apps/web-chat/Dockerfile apps/web-chat --no-logs -o json | ConvertFrom-Json
   if ($LASTEXITCODE -ne 0 -or $build.status -ne 'Succeeded') { throw 'Remote build failed' }
   $digest = $build.outputImages[0].digest
   if ($digest -notmatch '^sha256:[a-f0-9]{64}$') { throw 'Missing image digest' }
   $image = "acraircanadapoc001.azurecr.io/foundry-web-chat@$digest"
   ```
2. **Deploy/update the Container App via a plain `az deployment group create`** against `infra/web-chat.bicep` (not `azd deploy`, not part of `main.bicep`):
   ```powershell
   az deployment group create --name web-chat-pilot --resource-group $resourceGroup --template-file infra/web-chat.bicep --parameters image=$image location=eastus2
   if ($LASTEXITCODE -ne 0) { throw 'Web deployment failed' }
   ```
3. **One-time (or redirect-URI-change) identity setup**, run by an approved Entra administrator:
   ```powershell
   ./scripts/setup-web-chat-identity.ps1 -RedirectUri https://foundry-threat-chat-staging.wonderfulpebble-ce861678.eastus2.azurecontainerapps.io
   ```
4. **Post-deploy validation** (manual, scripted):
   ```powershell
   $base = 'https://foundry-threat-chat-staging.wonderfulpebble-ce861678.eastus2.azurecontainerapps.io'
   Invoke-RestMethod "$base/healthz"
   (Invoke-WebRequest "$base/api/me" -SkipHttpErrorCheck).StatusCode
   az containerapp logs show --name foundry-threat-chat-staging --resource-group rg-air-canada-threat-assessment-poc --type console --tail 60
   ```
5. **Recovery** on failure = redeploy the previous known-good image digest through the same `az deployment group create` command (image rollback only — not an automatic rollback mechanism, and it does not restore lost in-memory sessions).

Key operational facts from the wiki, relevant to planning a local port:
- The web Container App **shares the existing `mcp-staging-mcp-env` managed environment** with the MCP servers, but has its own container/identity/roles — deploying it does not redeploy the hosted agent or MCP servers, and vice versa.
- It calls the agent's **routed/staging endpoint** (not a pinned agent version) — a later agent release can change behavior behind the same URL.
- Public HTTPS ingress with **anonymous** `/healthz` and `/api/config`; every `/api/conversations*` call requires a valid pilot-user Entra token validated by `auth.py`.
- Single replica / single worker by design — the in-memory `SessionStore` is not distributable as-is; scaling out would need a shared store + distributed concurrency control first.
- `scripts/deployment_summary.py` and `scripts/ci_results.py` render a shared "Deployment Links" table (used identically across `web-chat-build.yml`, `continuous-validation.yml`, `deploy-and-evaluate.yml`, `publish-test-trends.yml`) purely as documentation/summary output — it performs no deployment itself.

---

## 5. `azure.yaml` (azd manifest) — no web-chat service entry

Full sibling `azure.yaml`:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/Azure/azure-dev/main/schemas/v1.0/azure.yaml.json

name: air-canada-threat-assessment
services:
    ai-project:
        host: azure.ai.project
        deployments:
            - name: gpt-4o-mini
              model:
                  name: gpt-4o-mini
                  format: OpenAI
                  version: "2024-07-18"
              sku:
                  name: GlobalStandard
                  capacity: 10
    anomaly-conn:
        host: azure.ai.connection
        endpoint: ${ANOMALY_MCP_URL}
        type: remote-tool
    defender-conn:
        host: azure.ai.connection
        endpoint: ${DEFENDER_MCP_URL}
        type: remote-tool
    security-tools:
        host: azure.ai.toolbox
        uses:
            - ai-project
            - defender-conn
            - anomaly-conn
        tools:
            - type: mcp
              connection: defender-conn
              server_label: defender-conn
            - type: mcp
              connection: anomaly-conn
              server_label: anomaly-conn
    threat-assessment-agent:
        project: ./src/threat-assessment-agent
        host: azure.ai.agent
        language: python
        uses:
            - ai-project
            - security-tools
        codeConfiguration:
            dependencyResolution: remote_build
            entryPoint: main.py
            runtime: python_3_13
        container:
            resources:
                cpu: "0.5"
                memory: 1Gi
        kind: hosted
        name: threat-assessment-agent
        protocols:
            - protocol: responses
              version: 2.0.0
        environmentVariables:
            - name: APPLICATIONINSIGHTS_CONNECTION_STRING
              value: ${applicationInsightsConnectionString}
            - name: FOUNDRY_TOOLBOX_VERSION
              value: "1"
            - name: AZURE_AI_MODEL_DEPLOYMENT_NAME
              value: gpt-4o-mini
            - name: AZURE_AI_PROJECT_ENDPOINT
              value: ${FOUNDRY_PROJECT_ENDPOINT}
            - name: AZURE_OPENAI_ENDPOINT
              value: ${accountEndpoint}
            - name: AZURE_OPENAI_DEPLOYMENT
              value: gpt-4o-mini
        toolboxes:
            - security-tools
```

**No `web`, `web-chat`, or any `host: containerapp`/similar service is declared.** The 5 services are all `azure.ai.*` host types (`azure.ai.project`, `azure.ai.connection` ×2, `azure.ai.toolbox`, `azure.ai.agent`) managed by `azd`'s Foundry-specific extension — none of them is the web-chat app. This is fully consistent with section 4's finding: **the web-chat app is deployed completely outside `azd`**, via a hand-run `az acr build` + `az deployment group create --template-file infra/web-chat.bicep` sequence, documented as an "operator deployment" runbook in the wiki, not automated in any workflow.

For comparison, the **local** `azure.yaml` (`c:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents-fsi\azure.yaml`) mirrors the same 5-service shape with `quote-preparation-agent`/`rulebook-conn`/`application-conn`/`quote-tools` in place of the sibling's `threat-assessment-agent`/`defender-conn`/`anomaly-conn`/`security-tools`, and is currently annotated as **NOT DEPLOYED** pending G2/G3/G6 gate sign-off. Porting the web-chat app would similarly not add anything to this `azure.yaml` — it would be a separate `infra/web-chat.bicep` + operator script, following the same pattern.

---

## Summary for Planner

**(a) Exact files to create locally to port the app** (mirroring sibling paths under this repo's structure; content needs renaming/re-theming for the Desjardins quote domain as noted per-file above):

Backend / app:
- `apps/web-chat/app.py` — port near-verbatim; fully domain-agnostic (only strings are the CSP header and generic error text — no changes needed here beyond the `AGENT_ENDPOINT` which is env-injected already).
- `apps/web-chat/auth.py` — port verbatim; fully generic.
- `apps/web-chat/requirements.txt` — port verbatim (watch for version drift at implementation time).
- `apps/web-chat/Dockerfile` — port verbatim (paths/CMD identical).
- `apps/web-chat/.dockerignore` — port verbatim.
- `apps/web-chat/tests/test_app.py` — port with light edits: two strings reference "Assessment complete." fixture text and "assessing"/"assessment" wording that are purely test-fixture cosmetic, not required changes, but should be renamed for domain clarity (e.g., "Quote ready.").
- `apps/web-chat/tests/test_auth.py` — port verbatim; fully generic.

Frontend:
- `apps/web-chat/frontend/package.json` — port, rename `"name"` field (currently `foundry-threat-assessment-web-chat`) and pin/verify dependency versions at implementation time.
- `apps/web-chat/frontend/package-lock.json` — regenerate via `npm install`, do not hand-port.
- `apps/web-chat/frontend/vite.config.js` — port verbatim.
- `apps/web-chat/frontend/index.html` — port with `<title>` and `theme-color` changed for Desjardins branding.
- `apps/web-chat/frontend/.gitignore` — port verbatim.
- `apps/web-chat/frontend/src/main.jsx` — port with all threat/security-domain copy replaced (brand text, header "AIR CANADA / SECURITY OPERATIONS", "Threat assessment" title, "ASSESSMENT AGENT"/"Assessment workspace"/"Assessment in progress" labels, composer placeholder, disclaimer, and the `ShieldCheck` icon choice) — application/session/auth/streaming logic is unchanged.
- `apps/web-chat/frontend/src/request.js` — port verbatim.
- `apps/web-chat/frontend/src/stream.js` — port verbatim.
- `apps/web-chat/frontend/src/samples.js` — **rewrite** sample queries to reference Desjardins quote scenarios (e.g., drawn from `data/synthetic/fixtures/case-syn-*.json`), since the `tools` field is unused/vestigial and can be dropped or repurposed.
- `apps/web-chat/frontend/src/style.css` — port with only the green/red brand palette optionally adjusted to Desjardins branding; structurally domain-agnostic.
- `apps/web-chat/frontend/tests/request.test.js`, `stream.test.js`, `samples.test.js` — port `request.test.js`/`stream.test.js` verbatim; rewrite `samples.test.js`'s expectations to match the new `samples.js` content.

Scripts (top-level `scripts/`):
- `scripts/setup-web-chat-identity.ps1` — port, replace `$TenantId`/`$PilotGroupId` defaults and `$displayName` with Desjardins-appropriate values (GUIDs for `$scopeId`/`$roleId` can be freshly generated or reused, they're not secrets).
- `scripts/deployment_summary.py` — **needs a substantial rewrite**, not just renaming: every URL/resource-ID is a hardcoded literal for the sibling's subscription/RG/ACR/agent name/MCP hostnames. Should be re-parameterized (e.g., read from `azd env get-values` or environment variables) rather than ported as-is.
- `scripts/ci_results.py` — port near-verbatim (generic multi-workflow evidence aggregator); it already recognizes `backend.xml`/`frontend.xml` JUnit filenames as "Web chat backend"/"Web chat frontend" labels, matching what a ported `web-chat-build.yml`-equivalent workflow would need to produce. Confirm this repo's `eval/evaluation_gate.py` exposes the same `METRICS`/`validate_results` shape it imports.
- `scripts/validate-agent-response.jq` — port verbatim; fully generic Responses-protocol SSE validator.
- `scripts/test-agent-response.sh` — port verbatim; fully generic.
- `scripts/record-production-version.sh` — port verbatim (already parameterized by agent-name argument); not directly web-chat-specific but part of the same evidence-tooling family the user asked about.
- `scripts/test-production-version.sh` — port with the hardcoded `threat-assessment-agent` / `AGENT_THREAT_ASSESSMENT_AGENT_NAME` literals renamed to `quote-preparation-agent` / `AGENT_QUOTE_PREPARATION_AGENT_NAME`.
- `scripts/build-release-evidence.js` — **reference only, not a direct port**: it hard-asserts one specific historical run's exact IDs/counts/metric names (`coherence`/`groundedness`/`task_adherence`, case IDs like `tp-001`). Useful as a structural template for an "evidence HTML report" generator, but must be rewritten against this repo's actual eval dataset/metrics if desired.
- `scripts/capture-release-evidence.ps1` — port largely verbatim (generic headless-Edge screenshot capture); only the 4 hardcoded anchor names (`pipeline`, `evaluations`, `tools`, `production`) need to match whatever section IDs a rewritten `build-release-evidence.js` produces.

Infra:
- `infra/web-chat.bicep` — port with parameter defaults updated: `appName`, `environmentName` (this repo's equivalent Container Apps environment — check `infra/modules/mcp-container-apps.bicep` for the actual environment name used locally), `acrName`, `tenantId`/`clientId`/`pilotGroupId` (Desjardins-appropriate values), `foundryAccountName`/`foundryProjectName`, and the agent name baked into the `AGENT_ENDPOINT` env var value (currently `threat-assessment-agent`, must become `quote-preparation-agent`). Everything else (role IDs, resource-type API versions, container/probe/scale config) is directly reusable.

New workflow (not explicitly requested but implied by the "port the app" goal, and directly modeled on the sibling):
- A `.github/workflows/web-chat-build.yml`-equivalent (test/build-only, no Azure deploy) would need to be authored locally if CI coverage of the ported app is desired — none currently exists in this repo, and the sibling's version has no domain-specific content beyond paths (`apps/web-chat/**`) that would carry over unchanged.

**(b) Azure deployment mechanism:** **Azure Container Apps** (`Microsoft.App/containerApps`), deployed via a **standalone Bicep file** (`infra/web-chat.bicep`) applied with a plain `az deployment group create` command — **not** via `azd deploy`/`azd up` and **not** wired into `azure.yaml` at all (confirmed empty search of `azure.yaml`, `deploy-and-evaluate.yml`, and `hosted-agent-cd.yml` for any web-chat reference). The container image is built out-of-band with `az acr build` (remote ACR build, avoiding local Docker/npm friction) and deployed by exact image **digest** (never a floating tag) into an **existing, shared** Container Apps managed environment (the same one used by the MCP servers) and an **existing** ACR. A dedicated user-assigned managed identity is provisioned by the same Bicep file with `AcrPull` (registry) + a custom "Foundry User" role (Foundry project) — used by the backend to call the hosted agent's Responses endpoint via `DefaultAzureCredential`. The whole flow — build, deploy, identity setup, validation, recovery — is a manually-run **operator runbook** documented in the repo wiki (`Web-Chat-Pilot.md`), explicitly decoupled from the CI/CD pipeline; the only automated workflow touching `apps/web-chat/` (`web-chat-build.yml`) runs tests/build only and explicitly states it performs no Azure deployment.

**(c) Open questions / things the planner should resolve before implementation:**
1. This repo's local `infra/` has `modules/mcp-container-apps.bicep` (not `mcp-container-apps.bicep` at root like the sibling had `infra/modules/mcp-container-apps.bicep` too, and additionally an `infra/modules/cosmos-db.bicep` the sibling lacks) — need to inspect that module to find the actual local Container Apps managed-environment resource name to use as `environmentName` in a ported `web-chat.bicep` (the sibling used `mcp-staging-mcp-env`, a value this repo will not have verbatim).
2. This repo's `azure.yaml` is explicitly gated as "AUTHOR-ONLY / NOT DEPLOYED" pending G2/G3/G6 sign-off — a ported web-chat app would presumably need the same or a separate/compatible gating story; confirm with the user/stakeholders whether the web-chat pilot should be gated identically or independently.
3. No Entra tenant ID / pilot-group ID / app-registration values exist yet for this repo's environment — `scripts/setup-web-chat-identity.ps1`'s defaults and `infra/web-chat.bicep`'s `tenantId`/`clientId`/`pilotGroupId` parameters will need real values supplied by whoever owns the Desjardins target tenant; none of that could be discovered from the sibling repo (its own values are tenant-specific and not reusable).
4. `frontend/tests/samples.test.js` was not fetched (only `request.test.js`/`stream.test.js` were, per the task's "couple of representative" instruction) — its exact assertions against `samples.js` are unknown; when `samples.js` is rewritten for Desjardins scenarios, its test will need to be authored fresh anyway, so this is likely a non-blocking gap, but flagging it since it wasn't literally inspected.
5. `scripts/ci_results.py` imports `from eval.evaluation_gate import METRICS, validate_results` — need to verify this repo's `eval/evaluation_gate.py` (already present locally) exposes a compatible `METRICS` list and `validate_results` signature before porting this script as-is; if the metric names differ (this repo may not use `coherence`/`groundedness`/`task_adherence`), the script itself is generic enough to work with whatever `METRICS` resolves to, but downstream consumers (e.g. a ported `build-release-evidence.js`) hardcode those specific names and would need updating.
