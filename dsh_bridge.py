"""Official DeepSeek Harness SDK integration (not a handcrafted tool loop)."""
import os, uuid
from pathlib import Path
from typing import Callable
from deepseek_harness import DeepSeekHarness

ROOT=Path(__file__).resolve().parent
PATCH=ROOT/'dsh'/'cordis.patch.yml'

def agent_turn(prompt:str, session_id:str|None, on_event:Callable[[dict],None]):
    if not os.getenv('OPENAI_API_KEY'):
        raise RuntimeError('OPENAI_API_KEY is missing')
    home=Path(os.environ.get('ULTRON_DSH_HOME','/var/lib/ultron-dsh')).resolve()
    workspace=Path(os.environ.get('ULTRON_DSH_WORKSPACE','/var/lib/ultron-dsh/workspace')).resolve()
    home.mkdir(parents=True,exist_ok=True)
    workspace.mkdir(parents=True,exist_ok=True)
    sid=session_id or 'ultron-'+uuid.uuid4().hex
    with DeepSeekHarness(provider='openai',
                         model=os.environ.get('OPENAI_MODEL','gpt-4.1-mini'),
                         max_tokens=min(int(os.environ.get('MAX_OUTPUT_TOKENS','1200')),8192),
                         cwd=str(workspace),runtime_cwd=str(workspace),
                         dsh_home=str(home),profile='sdk',
                         patches=(str(PATCH),),request_timeout_seconds=180) as harness:
        session=harness.resume_session(sid) if session_id else harness.start_session(sid)
        def emit(n):
            if n.method=='session.event':
                e=n.payload.get('event',{})
                typ=e.get('type','') if isinstance(e,dict) else ''
                if typ in ('tool/call','tool/result','turn/start','turn/end','assistant/message'):
                    on_event({'type':'activity','event':typ})
        result=session.run(prompt,on_notification=emit)
    if result.finish_reason!='completed' or not result.final_response.strip():
        raise RuntimeError('DSH agent did not complete')
    return sid,result.final_response
