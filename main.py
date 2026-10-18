import os
import time
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
import json
import logging
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI, APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError, APIStatusError
from pydantic import BaseModel, Field, ConfigDict

BASE = Path(__file__).resolve().parent
app = FastAPI(title='Ultron Web', docs_url=None, redoc_url=None)
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')
_lock = Lock()
_hits = defaultdict(deque)
SYSTEM = 'You are Ultron, a helpful, accurate, respectful personal AI assistant. Admit uncertainty and protect user privacy.'

def setting_int(name, default, low, high):
    try:
        value = int(os.getenv(name, default))
        return max(low, min(value, high))
    except (TypeError, ValueError):
        return default

MAX_CHARS = setting_int('MAX_MESSAGE_CHARS', 4000, 1, 20000)
MAX_HISTORY = setting_int('MAX_HISTORY_MESSAGES', 20, 1, 50)
MAX_BODY = setting_int('MAX_REQUEST_BYTES', 100000, 1000, 250000)
RATE = setting_int('RATE_LIMIT_PER_MINUTE', 10, 1, 120)
MAX_TOKENS = setting_int('MAX_OUTPUT_TOKENS', 1200, 64, 4096)
MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')

class Message(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=MAX_CHARS)

class ChatRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    messages: list[Message] = Field(min_length=1, max_length=MAX_HISTORY)

class ChatResponse(BaseModel):
    reply: str

@app.middleware('http')
async def guard(request: Request, call_next):
    if request.url.path in ('/api/chat', '/api/chat/stream'):
        length = request.headers.get('content-length')
        if length:
            try:
                if int(length) > MAX_BODY:
                    return _error(413, 'Request too large')
            except ValueError:
                return _error(400, 'Invalid Content-Length')
        body = await request.body()
        if len(body) > MAX_BODY:
            return _error(413, 'Request too large')
        # Only use socket peer address; do not trust spoofable forwarded headers.
        ip = request.client.host if request.client else 'unknown'
        now = time.monotonic()
        with _lock:
            q = _hits[ip]
            while q and q[0] < now - 60:
                q.popleft()
            if len(q) >= RATE:
                return _error(429, 'Too many requests; try again shortly')
            q.append(now)
    return await call_next(request)

def _error(code, detail):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=code, content={'detail': detail})

@app.get('/')
async def index():
    return FileResponse(BASE / 'static' / 'index.html')

@app.get('/health')
async def health():
    return {'status': 'ok'}

async def generate(messages):
    client = AsyncOpenAI(api_key=os.environ['OPENAI_API_KEY'], timeout=30.0, max_retries=0)
    response = await client.responses.create(
        model=MODEL,
        instructions=SYSTEM,
        input=[{'role': m.role, 'content': m.content} for m in messages],
        max_output_tokens=MAX_TOKENS,
    )
    return response.output_text

@app.post('/api/chat', response_model=ChatResponse)
async def chat(payload: ChatRequest):
    if payload.messages[-1].role != 'user':
        raise HTTPException(422, 'Last message must be from user')
    if not os.getenv('OPENAI_API_KEY'):
        raise HTTPException(503, 'AI service is not configured')
    try:
        reply = await generate(payload.messages)
        if not reply:
            raise HTTPException(502, 'AI returned an empty response')
        return ChatResponse(reply=reply)
    except AuthenticationError:
        raise HTTPException(503, 'AI service configuration error')
    except RateLimitError:
        raise HTTPException(429, 'AI service is busy; try later')
    except (APITimeoutError, APIConnectionError):
        raise HTTPException(504, 'AI service temporarily unavailable')
    except APIStatusError:
        raise HTTPException(502, 'AI service error')


# Streaming endpoint: SSE (POST /api/chat/stream), with one event per text delta.
# Errors after stream startup are delivered as sanitized SSE error events.
def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

async def generate_stream(messages):
    client = AsyncOpenAI(api_key=os.environ['OPENAI_API_KEY'], timeout=60.0, max_retries=0)
    async with client.responses.stream(
        model=MODEL,
        instructions=SYSTEM,
        input=[{'role': m.role, 'content': m.content} for m in messages],
        max_output_tokens=MAX_TOKENS,
    ) as stream:
        async for event in stream:
            if event.type == 'response.output_text.delta':
                yield event.delta
            elif event.type == 'response.failed':
                raise RuntimeError('Response generation failed')
        final = await stream.get_final_response()
        if getattr(final, 'status', None) in ('failed', 'incomplete'):
            raise RuntimeError('Response not completed')

@app.post('/api/chat/stream')
async def chat_stream(payload: ChatRequest):
    if payload.messages[-1].role != 'user':
        raise HTTPException(422, 'Last message must be from user')
    if not os.getenv('OPENAI_API_KEY'):
        raise HTTPException(503, 'AI service is not configured')

    async def events():
        try:
            any_text = False
            async for delta in generate_stream(payload.messages):
                if delta:
                    any_text = True
                    yield sse('delta', {'text': delta})
            if not any_text:
                yield sse('error', {'message': 'AI returned an empty response'})
            else:
                yield sse('done', {})
        except AuthenticationError:
            yield sse('error', {'message': 'AI service configuration error'})
        except RateLimitError:
            yield sse('error', {'message': 'AI service rate limited or out of quota'})
        except (APITimeoutError, APIConnectionError):
            yield sse('error', {'message': 'AI service temporarily unavailable'})
        except (APIStatusError, RuntimeError):
            yield sse('error', {'message': 'AI service error'})
        except Exception:
            logging.getLogger(__name__).exception('Streaming request failed (content not logged)')
            yield sse('error', {'message': 'Unexpected AI service error'})

    return StreamingResponse(events(), media_type='text/event-stream', headers={
        'Cache-Control': 'no-cache, no-transform',
        'X-Accel-Buffering': 'no',
    })
