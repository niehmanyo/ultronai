"""Server side PostgreSQL conversations, transactional saving, parameterized queries."""
import os,uuid
from contextlib import contextmanager
@contextmanager
def db():
    import psycopg
    url=os.environ.get('DATABASE_URL')
    if not url:raise RuntimeError('DATABASE_URL not configured')
    with psycopg.connect(url,connect_timeout=8) as conn:yield conn
def init():
    with db() as conn,conn.cursor() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS conversations(id UUID PRIMARY KEY,owner TEXT NOT NULL,title TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
        c.execute("""CREATE TABLE IF NOT EXISTS messages(id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,role TEXT NOT NULL CHECK(role IN ('user','assistant')),content TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
        c.execute('CREATE INDEX IF NOT EXISTS idx_conversations_owner ON conversations(owner,updated_at DESC)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id,id)')
def list_conversations(owner):
    with db() as conn,conn.cursor() as c:
        c.execute('SELECT id::text,title,updated_at FROM conversations WHERE owner=%s ORDER BY updated_at DESC LIMIT 100',(owner,))
        return [{'id':id,'title':title,'updated_at':dt.isoformat()} for id,title,dt in c.fetchall()]
def create_conversation(owner):
    cid=str(uuid.uuid4())
    with db() as conn,conn.cursor() as c:
        c.execute('INSERT INTO conversations(id,owner,title) VALUES (%s,%s,%s)',(cid,owner,'New conversation'))
    return cid
def get_messages(owner,cid,limit=200):
    with db() as conn,conn.cursor() as c:
        c.execute('SELECT 1 FROM conversations WHERE id=%s AND owner=%s',(cid,owner))
        if not c.fetchone():return None
        c.execute('SELECT role,content FROM (SELECT id,role,content FROM messages WHERE conversation_id=%s ORDER BY id DESC LIMIT %s) m ORDER BY id ASC',(cid,limit))
        return [{'role':r,'content':body} for r,body in c.fetchall()]
def save_exchange(owner,cid,user_text,answer):
    with db() as conn,conn.cursor() as c:
        c.execute('SELECT 1 FROM conversations WHERE id=%s AND owner=%s FOR UPDATE',(cid,owner))
        if not c.fetchone():return False
        c.execute('INSERT INTO messages(conversation_id,role,content) VALUES (%s,%s,%s),(%s,%s,%s)',(cid,'user',user_text,cid,'assistant',answer))
        c.execute('UPDATE conversations SET title=CASE WHEN title=%s THEN %s ELSE title END,updated_at=now() WHERE id=%s',('New conversation',user_text[:75],cid))
    return True
def delete_conversation(owner,cid):
    with db() as conn,conn.cursor() as c:
        c.execute('DELETE FROM conversations WHERE id=%s AND owner=%s RETURNING id',(cid,owner))
        return c.fetchone() is not None
