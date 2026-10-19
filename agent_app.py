"""Separate protected DSH preview app; production main.py is untouched."""
import asyncio,json,logging,os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import FileResponse,JSONResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
import dsh_security as sec

ROOT=Path(__file__).resolve().parent
app=FastAPI(docs_url=None,redoc_url=None,title='Ultron DSH Preview')
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='ultron-dsh')
_busy=asyncio.Lock()
class Login(BaseModel):password:str=Field(min_length=1,max_length=512)
class Prompt(BaseModel):
    prompt:str=Field(min_length=1,max_length=4000)
    session_id:str|None=None
@app.get('/health')
async def health():return {'status':'ok','runtime':'dsh-sdk','configured':sec.configured()}
@app.get('/')
async def index():return FileResponse(ROOT/'static'/'agent.html')
@app.get('/api/dsh/status')
async def status(request:Request):return {'configured':sec.configured(),'authenticated':sec.authorized(request),'provider':'openai','runtime':'deepseek-harness-sdk'}
@app.post('/api/dsh/login')
async def login(request:Request,data:Login):
    sec.same_origin(request)
    sec.verify_login(request.client.host if request.client else 'unknown',data.password)
    resp=JSONResponse({'ok':True})
    resp.set_cookie(sec.COOKIE,sec.sign(int(__import__('time').time())),max_age=sec.TTL,httponly=True,secure=True,samesite='strict',path='/')
    return resp
@app.post('/api/dsh/logout')
async def logout(request:Request):
    sec.must_auth(request);sec.same_origin(request)
    resp=JSONResponse({'ok':True});resp.delete_cookie(sec.COOKIE,path='/')
    return resp
@app.post('/api/dsh/run')
async def run(request:Request,payload:Prompt):
    sec.must_auth(request);sec.same_origin(request)
    if payload.session_id and (not payload.session_id.startswith('ultron-') or len(payload.session_id)>90):
        raise HTTPException(422,'Invalid session identifier')
    if not os.environ.get('OPENAI_API_KEY'):raise HTTPException(503,'OpenAI API key is not configured')
    if os.environ.get('ULTRON_DSH_UNSAFE_AGENT_PREVIEW')!='I_ACCEPT_TOOL_RISK':
        raise HTTPException(503,'DSH execution disabled until tool sandbox is reviewed')
    if _busy.locked():raise HTTPException(429,'Another agent run is active')
    await _busy.acquire()
    async def events():
        queue=asyncio.Queue();loop=asyncio.get_running_loop()
        def run_sync():
            from dsh_bridge import agent_turn
            def callback(event):loop.call_soon_threadsafe(queue.put_nowait,event)
            try:
                sid,answer=agent_turn(payload.prompt,payload.session_id,callback)
                loop.call_soon_threadsafe(queue.put_nowait,{'type':'finished','session_id':sid,'answer':answer})
            except Exception:
                logging.getLogger(__name__).exception('DSH run failed (content omitted)')
                loop.call_soon_threadsafe(queue.put_nowait,{'type':'error','message':'DSH agent request failed'})
        future=loop.run_in_executor(_executor,run_sync)
        try:
            while True:
                try:item=await asyncio.wait_for(queue.get(),timeout=15)
                except asyncio.TimeoutError:
                    yield ': heartbeat\n\n';continue
                kind=item.pop('type')
                yield 'event: '+kind+'\ndata: '+json.dumps(item,ensure_ascii=False)+'\n\n'
                if kind in ('finished','error'):break
        finally:
            if not future.done():await asyncio.shield(future)
            _busy.release()
    return StreamingResponse(events(),media_type='text/event-stream',headers={'Cache-Control':'no-cache, no-transform','X-Accel-Buffering':'no'})
