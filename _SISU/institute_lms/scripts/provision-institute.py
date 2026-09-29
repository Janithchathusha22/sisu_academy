#!/usr/bin/env python3
"""Run inside a Linux bench. Reserve globally unique codes in one fleet registry.

All provisioning workers must share this registry file on a lock-capable filesystem.
Run `bench new-site` and install LMS first; this tool never handles passwords.
"""
import argparse
import fcntl
import json
import re
import subprocess
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--site',required=True)
parser.add_argument('--code',required=True)
parser.add_argument('--title',required=True)
parser.add_argument('--admin-email',required=True)
parser.add_argument('--base-fee',type=float,required=True)
parser.add_argument('--registry',type=Path,default=Path('sites/institute-registry.json'))
args=parser.parse_args()
code=args.code.upper().strip()
if not re.fullmatch(r'[A-Z][A-Z0-9]{1,11}',code): parser.error('Invalid institute code')
if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.-]+',args.site): parser.error('Invalid site hostname')
if not (Path('sites')/args.site/'site_config.json').is_file(): parser.error('Create the Frappe site first')
args.registry.parent.mkdir(parents=True,exist_ok=True)
with args.registry.open('a+',encoding='utf-8') as stream:
    fcntl.flock(stream,fcntl.LOCK_EX)
    stream.seek(0)
    raw=stream.read()
    registry=json.loads(raw) if raw else {}
    if code in registry: parser.error(f'Code {code} is already reserved')
    if any(v['site']==args.site for v in registry.values()): parser.error('Site already reserved in fleet registry')
    registry[code]={'site':args.site,'title':args.title,'status':'provisioning'}
    stream.seek(0);stream.truncate();json.dump(registry,stream,indent=2);stream.flush()
    try:
        subprocess.run(['bench','--site',args.site,'install-app','institute_lms'],check=True)
        subprocess.run(['bench','--site',args.site,'execute','institute_lms.setup.configure','--kwargs',json.dumps({
            'code':code,'title':args.title,'admin_email':args.admin_email,'base_fee':args.base_fee})],check=True)
        registry[code]['status']='ready'
    except subprocess.CalledProcessError:
        registry[code]['status']='needs_review'
        raise
    finally:
        stream.seek(0);stream.truncate();json.dump(registry,stream,indent=2);stream.flush()
