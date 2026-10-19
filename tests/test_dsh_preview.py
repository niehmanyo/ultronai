"""Safe auth tests for the DSH preview. Do not require an API key or SDK runtime."""
import time
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('ULTRON_ADMIN_PASSWORD','a-really-long-private-password-123')
    monkeypatch.setenv('ULTRON_SESSION_SECRET','z'*48)
    monkeypatch.setenv('OPENAI_API_KEY','test_key_only')
    monkeypatch.delenv('ULTRON_DSH_UNSAFE_AGENT_PREVIEW',raising=False)
    import agent_app
    return TestClient(agent_app.app,base_url='https://testserver')

def test_unauthenticated_is_rejected(client):
    r=client.post('/api/dsh/run',json={'prompt':'hello'},headers={'Origin':'https://testserver'})
    assert r.status_code==401

def test_origin_required(client):
    r=client.post('/api/dsh/login',json={'password':'a-really-long-private-password-123'})
    assert r.status_code==403

def test_login_and_unsafe_gate(client):
    r=client.post('/api/dsh/login',json={'password':'a-really-long-private-password-123'},headers={'Origin':'https://testserver'})
    assert r.status_code==200
    assert 'httponly' in r.headers['set-cookie'].lower()
    assert 'secure' in r.headers['set-cookie'].lower()
    assert client.get('/api/dsh/status').json()['authenticated']
    r=client.post('/api/dsh/run',json={'prompt':'hello'},headers={'Origin':'https://testserver'})
    assert r.status_code==503
    assert 'sandbox' in r.json()['detail']

def test_cookie_tampering_rejected(client):
    import dsh_security
    class Dummy: cookies={dsh_security.COOKIE:dsh_security.sign(int(time.time()))+'bad'}
    assert not dsh_security.authorized(Dummy())

def test_input_too_long_rejected(client):
    client.post('/api/dsh/login',json={'password':'a-really-long-private-password-123'},headers={'Origin':'https://testserver'})
    r=client.post('/api/dsh/run',json={'prompt':'x'*5000},headers={'Origin':'https://testserver'})
    assert r.status_code==422
