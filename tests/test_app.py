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
