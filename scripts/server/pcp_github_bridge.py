#!/usr/bin/env python3
import argparse,json,os,sys,urllib.error,urllib.parse,urllib.request
API='https://api.github.com'
def env(n,d=None,required=False):
 v=os.environ.get(n,d)
 if required and not v: raise SystemExit('missing environment variable: '+n)
 return v
OWNER=env('PCP_GITHUB_OWNER',required=True); REPO=env('PCP_GITHUB_REPO',required=True); WORKFLOW=env('PCP_GITHUB_WORKFLOW','pcp-build.yml'); REF=env('PCP_GITHUB_REF','main'); TOKEN=env('PCP_GITHUB_TOKEN',required=True); API_VERSION=env('PCP_GITHUB_API_VERSION','2026-03-10')
def request(method,path,payload=None):
 data=None if payload is None else json.dumps(payload).encode()
 req=urllib.request.Request(API+path,data=data,method=method)
 for k,v in [('Accept','application/vnd.github+json'),('Authorization','Bearer '+TOKEN),('X-GitHub-Api-Version',API_VERSION),('User-Agent','vis-sol-pcp-github-bridge/1')]: req.add_header(k,v)
 try:
  with urllib.request.urlopen(req,timeout=20) as r:
   raw=r.read(); return r.status,(json.loads(raw.decode()) if raw else {})
 except urllib.error.HTTPError as e:
  raw=e.read().decode('utf-8','replace'); print(json.dumps({'ok':False,'http_status':e.code,'error':raw},ensure_ascii=False)); raise SystemExit(20)
 except Exception as e:
  print(json.dumps({'ok':False,'error':'github_transport_error','detail':str(e)},ensure_ascii=False)); raise SystemExit(21)
def dispatch(a):
 wf=urllib.parse.quote(WORKFLOW,safe='')
 st,b=request('POST',f'/repos/{OWNER}/{REPO}/actions/workflows/{wf}/dispatches',{'ref':REF,'inputs':{'job_id':a.job_id,'target':a.target,'sketch_path':a.sketch_path}})
 print(json.dumps({'ok':st in (200,201,204),'http_status':st,'job_id':a.job_id,'workflow_run_id':b.get('workflow_run_id'),'run_url':b.get('run_url'),'html_url':b.get('html_url'),'response':b},ensure_ascii=False))
def status(a):
 st,b=request('GET',f'/repos/{OWNER}/{REPO}/actions/runs/{a.run_id}')
 print(json.dumps({'ok':st==200,'run_id':b.get('id'),'status':b.get('status'),'conclusion':b.get('conclusion'),'html_url':b.get('html_url')},ensure_ascii=False))
def artifacts(a):
 st,b=request('GET',f'/repos/{OWNER}/{REPO}/actions/runs/{a.run_id}/artifacts')
 print(json.dumps({'ok':st==200,'run_id':a.run_id,'artifacts':[{'id':x.get('id'),'name':x.get('name'),'size_in_bytes':x.get('size_in_bytes'),'expired':x.get('expired'),'archive_download_url':x.get('archive_download_url')} for x in b.get('artifacts',[])]},ensure_ascii=False))
p=argparse.ArgumentParser(); s=p.add_subparsers(dest='cmd',required=True)
d=s.add_parser('dispatch'); d.add_argument('--job-id',required=True); d.add_argument('--target',required=True,choices=('uno','esp32','esp32s3','esp8266','rpipico','rpipico2')); d.add_argument('--sketch-path',required=True); d.set_defaults(func=dispatch)
q=s.add_parser('status'); q.add_argument('run_id',type=int); q.set_defaults(func=status)
a=s.add_parser('artifacts'); a.add_argument('run_id',type=int); a.set_defaults(func=artifacts)
args=p.parse_args(); args.func(args)
