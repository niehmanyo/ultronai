"""Single-owner password login with signed, expiring Secure HttpOnly cookie."""
import base64, hashlib, hmac, os, time
from fastapi import HTTPException, Request
COOKIE='ultron_session'
TTL=7*24*3600
def configured():
    return bool(os.getenv('ULTRON_ADMIN_PASSWORD') and os.getenv('ULTRON_SESSION_SECRET') and os.getenv('DATABASE_URL'))
def require_setup():
    if not configured(): raise HTTPException(503,'Private chat is not configured yet')
def password_valid(submitted):
    secret=os.getenv('ULTRON_SESSION_SECRET',''); saved=os.getenv('ULTRON_ADMIN_PASSWORD','')
    if not secret or len(saved)<16: return False
    a=hmac.new(secret.encode(),submitted.encode(),hashlib.sha256).digest()
    b=hmac.new(secret.encode(),saved.encode(),hashlib.sha256).digest()
    return hmac.compare_digest(a,b)
def make_token(now=None):
    stamp=str(int(time.time() if now is None else now))
    signature=hmac.new(os.environ['ULTRON_SESSION_SECRET'].encode(),f'owner:{stamp}'.encode(),hashlib.sha256).digest()
    return stamp+'.'+base64.urlsafe_b64encode(signature).decode().rstrip('=')
def is_authenticated(request):
    secret=os.getenv('ULTRON_SESSION_SECRET'); token=request.cookies.get(COOKIE,'')
    if not secret or '.' not in token:return False
    stamp,_=token.split('.',1)
    if not stamp.isdigit():return False
    now=int(time.time());issued=int(stamp)
    if issued>now+30 or now-issued>TTL:return False
    return hmac.compare_digest(token,make_token(issued))
def owner(request):
    require_setup()
    if not is_authenticated(request):raise HTTPException(401,'Sign in to access private chats')
    return 'owner'
def verify_origin(request:Request):
    origin=request.headers.get('origin','').rstrip('/')
    scheme='https' if request.headers.get('x-forwarded-proto')=='https' else request.url.scheme
    if not origin or origin!=f'{scheme}://{request.url.netloc}':
        raise HTTPException(403,'Invalid request origin')
