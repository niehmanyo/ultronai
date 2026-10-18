import pytest
from fastapi.testclient import TestClient
import main

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, 'RATE', 100)
    main._hits.clear()
    return TestClient(main.app)

def test_health(client):
    assert client.get('/health').json() == {'status':'ok'}

def test_static(client):
    assert client.get('/').status_code == 200
    assert client.get('/static/app.js').status_code == 200

def test_missing_messages(client):
    assert client.post('/api/chat', json={}).status_code == 422

def test_bad_role(client):
    assert client.post('/api/chat', json={'messages':[{'role':'system','content':'hi'}]}).status_code == 422

def test_bad_type(client):
    assert client.post('/api/chat', json={'messages':'hello'}).status_code == 422

def test_long_message(client):
    assert client.post('/api/chat', json={'messages':[{'role':'user','content':'x'*(main.MAX_CHARS+1)}]}).status_code == 422

def test_long_history(client):
    assert client.post('/api/chat', json={'messages':[{'role':'user','content':'hi'}]*(main.MAX_HISTORY+1)}).status_code == 422

def test_last_assistant(client):
    assert client.post('/api/chat', json={'messages':[{'role':'assistant','content':'hi'}]}).status_code == 422

def test_missing_key(client, monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    response=client.post('/api/chat', json={'messages':[{'role':'user','content':'hi'}]})
    assert response.status_code == 503
    assert 'key' not in response.text.lower()

def test_mock_chat(client, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    async def fake(messages): return 'Mocked answer'
    monkeypatch.setattr(main,'generate',fake)
    assert client.post('/api/chat',json={'messages':[{'role':'user','content':'hello'}]}).json() == {'reply':'Mocked answer'}

def test_upstream_failure(client, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    from openai import APITimeoutError
    async def fail(messages): raise APITimeoutError(request=__import__('httpx').Request('POST','https://example.com'))
    monkeypatch.setattr(main,'generate',fail)
    assert client.post('/api/chat',json={'messages':[{'role':'user','content':'hi'}]}).status_code == 504

def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(main,'RATE',1)
    client.get('/health')
    payload={'messages':[{'role':'user','content':'hi'}]}
    client.post('/api/chat',json=payload)
    assert client.post('/api/chat',json=payload).status_code == 429

def test_body_limit(client):
    assert client.post('/api/chat',content=b'x'*(main.MAX_BODY+1),headers={'Content-Type':'application/json'}).status_code == 413

def test_greeting_audio_served(client):
    r = client.get('/static/audio/ultron-hello-stark.wav')
    assert r.status_code == 200
    assert r.content.startswith(b'RIFF')


def test_stream_mock(client, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    async def fake_stream(messages):
        yield 'Hello'
        yield ' Stark'
    monkeypatch.setattr(main, 'generate_stream', fake_stream)
    result = client.post('/api/chat/stream', json={'messages':[{'role':'user','content':'hello'}]})
    assert result.status_code == 200
    assert 'text/event-stream' in result.headers['content-type']
    assert 'event: delta' in result.text
    assert 'Hello' in result.text and ' Stark' in result.text
    assert 'event: done' in result.text


def test_stream_missing_key(client, monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    assert client.post('/api/chat/stream', json={'messages':[{'role':'user','content':'hi'}]}).status_code == 503


def test_stream_error_is_sanitized(client, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    async def broken(messages):
        yield 'partial'
        raise RuntimeError('private upstream exception')
    monkeypatch.setattr(main, 'generate_stream', broken)
    result = client.post('/api/chat/stream', json={'messages':[{'role':'user','content':'hello'}]})
    assert 'event: error' in result.text
    assert 'private upstream exception' not in result.text
