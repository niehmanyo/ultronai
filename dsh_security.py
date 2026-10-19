"""Password-protected DSH preview authentication (not a tool sandbox)."""
import base64,hashlib,hmac,os,time
from collections import defaultdict,deque
from threading import Lock
from fastapi import HTTPException
COOKIE='ultron_dsh_session'
TTL=86400
_hits=defaultdict(deque);_lock=Lock()
def configured():
    return len(os.environ.get('ULTRON_ADMIN_PASSWORD',''))>=16 and len(os.environ.get('ULTRON_SESSION_SECRET',''))>=32
def sign(epoch):
    s=str(epoch);mac=hmac.new(os.environ['ULTRON_SESSION_SECRET'].encode(),s.encode(),hashlib.sha256).digest()
    return s+'.'+base64.urlsafe_b64encode(mac).decode().rstrip('=')
def authorized(request):
    if not configured():return False
    token=request.cookies.get(COOKIE,'')
    try:
        stamp=int(token.split('.',1)[0]);now=int(time.time())
        return 0<=now-stamp<TTL and hmac.compare_digest(token,sign(stamp))
    except (ValueError,IndexError):return False
def must_auth(request):
    if not configured():raise HTTPException(503,'Private agent is not configured')
    if not authorized(request):raise HTTPException(401,'Please sign in')
def same_origin(request):
    origin=request.headers.get('origin','')
    if not origin.startswith('https://') or origin.split('/',3)[2]!=request.headers.get('host'):
        raise HTTPException(403,'Invalid request origin')
def verify_login(ip,password):
    if not configured():raise HTTPException(503,'Agent password is not configured')
    with _lock:
        q=_hits[ip];now=time.monotonic()
        while q and q[0]<now-300:q.popleft()
        if len(q)>=5:raise HTTPException(429,'Too many attempts')
        q.append(now)
    secret=os.environ['ULTRON_SESSION_SECRET'].encode()
    actual=hmac.new(secret,password.encode(),hashlib.sha256).digest()
    expected=hmac.new(secret,os.environ['ULTRON_ADMIN_PASSWORD'].encode(),hashlib.sha256).digest()
    if not hmac.compare_digest(actual,expected):raise HTTPException(401,'Incorrect password')
    with _lock:_hits[ip].clear()
