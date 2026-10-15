#!/usr/bin/env python3
"""Live integration check against examples/control-demo.c (synthetic data only)."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--prefix',required=True);p.add_argument('--wine',required=True);p.add_argument('--display',required=True);p.add_argument('--xauthority',required=True);p.add_argument('--helper',required=True);p.add_argument('--flatpak',action='store_true');a=p.parse_args()
b=['python3',str(Path(__file__).parents[1]/'scripts/winapp.py'),'--prefix',a.prefix,'--wine',a.wine,'--display',a.display,'--xauthority',a.xauthority]
if a.flatpak:b+=['--flatpak']
b+=['ui']
def snap():return json.loads(subprocess.check_output(b+['snapshot','--helper',a.helper],timeout=20))
s=snap();pid=next(x['pid'] for x in s if x['class']=='LinuxWindowsAppsDemo');c={x['id']:x for x in s if x['pid']==pid and x['id']}
def act(op,id,*extra,stamp=None):
 x=c[id];return subprocess.run(b+[op,'--helper',a.helper,'--hwnd',x['hwnd'],'--pid',str(pid),'--started',stamp or x['started'],*extra],capture_output=True,text=True,timeout=20)
for op,id,args in [('text',101,['--value','Controlled from Linux - verified']),('select',102,['--index','1']),('click',103,[])]:
 r=act(op,id,*args);assert r.returncode==0,(op,r.stdout,r.stderr)
d={x['id']:x for x in snap() if x['pid']==pid and x['id']}
assert d[104]['text']=='Controlled from Linux - verified',d
assert d[102]['text']=='Native control selected',d
assert d[105]['redacted'] and d[105]['text']=='[password]'
r=act('text',105,'--value','not-a-secret');assert r.returncode!=0 and 'non-password' in r.stderr,r
r=act('click',103,stamp='1');assert r.returncode!=0 and 'stale' in r.stderr,r
print(json.dumps({'text_verified':True,'combo_verified':True,'button_result_verified':True,'password_redacted':True,'password_write_refused':True,'stale_creation_time_refused':True,'synthetic_data_only':True},indent=2))
