#!/usr/bin/env python3
"""DNX Project Manager - private, unofficial hobby project."""
import os, re, json, sqlite3, hashlib, secrets, subprocess, shutil, time, uuid
import html
from pathlib import Path
from functools import wraps
from flask import Flask, request, session, redirect, url_for, abort, send_file, render_template_string, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

ROOT=Path(os.environ.get('DNX_PM_ROOT','/opt/dnx-project-manager'))
DB=ROOT/'database/projects.sqlite3'; FILES=ROOT/'files'; QUAR=ROOT/'quarantine'; PREV=ROOT/'previews'; LOGS=ROOT/'logs'
MAX_FILE=int(os.environ.get('DNX_PM_MAX_FILE',500*1024*1024)); MAX_USER=int(os.environ.get('DNX_PM_MAX_USER',10*1024*1024*1024))
ALLOWED={'.zip','.gz','.sh','.md','.txt','.json','.csv','.pdf','.png','.jpg','.jpeg','.svg','.html'}
app=Flask(__name__);app.secret_key=os.environ.get('DNX_PM_SECRET') or secrets.token_hex(32);app.config['MAX_CONTENT_LENGTH']=MAX_FILE+1024*1024
for p in (DB.parent,FILES,QUAR,PREV,LOGS):p.mkdir(parents=True,exist_ok=True)

def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA journal_mode=WAL');return c

def init_db():
 with db() as c:
  c.executescript('''
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE COLLATE NOCASE,password TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'user',status TEXT NOT NULL DEFAULT 'pending',created INTEGER NOT NULL,failed INTEGER NOT NULL DEFAULT 0,locked_until INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,csrf TEXT NOT NULL,expires INTEGER NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,owner_id INTEGER NOT NULL,title TEXT NOT NULL,summary TEXT,description TEXT,category TEXT,version TEXT,license TEXT,compatibility TEXT,dependencies TEXT,source_url TEXT,docs_url TEXT,changelog TEXT,filename TEXT NOT NULL,stored TEXT NOT NULL,size INTEGER NOT NULL,sha256 TEXT NOT NULL,mime TEXT,status TEXT NOT NULL,scan TEXT,created INTEGER NOT NULL,downloads INTEGER NOT NULL DEFAULT 0,FOREIGN KEY(owner_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,ts INTEGER,user_id INTEGER,action TEXT,details TEXT);
''')
init_db()

def clean(v,n=500):return re.sub(r'[\x00-\x1f]','',str(v or ''))[:n].strip()
def h(v,n=500):return html.escape(clean(v,n),quote=True)
def current():
 sid=request.cookies.get('dnxpm_session');
 if not sid:return None
 with db() as c:
  row=c.execute('SELECT u.*,s.csrf,s.expires FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.id=?',(sid,)).fetchone()
  if not row or row['expires']<time.time():return None
  return row
def csrf():
 u=current();return u['csrf'] if u else ''
def check_csrf():
 u=current();return bool(u and secrets.compare_digest(request.form.get('csrf','') or request.headers.get('X-CSRF-Token',''),u['csrf']))
def login_required(fn):
 @wraps(fn)
 def w(*a,**k):
  u=current()
  if not u:return redirect(url_for('login',next=request.path))
  if u['status']!='active':flash('Konto ist noch nicht freigegeben oder gesperrt.');return redirect(url_for('home'))
  return fn(*a,**k)
 return w
def admin_required(fn):
 @wraps(fn)
 def w(*a,**k):
  u=current()
  if not u or u['role']!='admin':abort(403)
  return fn(*a,**k)
 return w
def audit(action,details=''):
 u=current()
 with db() as c:c.execute('INSERT INTO audit(ts,user_id,action,details) VALUES(?,?,?,?)',(int(time.time()),u['id'] if u else None,action,clean(details,2000)))

def layout(body,title='DNX Projekte'):
 return render_template_string('''<!doctype html><html lang=de><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>{{title}}</title><style>
body{margin:0;background:#0e1820;color:#fff;font:14px Arial}a{color:#77eaff}.top{background:#12394a;padding:14px;position:sticky;top:0;z-index:3}.top b{font-size:20px}.nav{float:right}.nav a{margin-left:12px}.wrap{max-width:1250px;margin:auto;padding:15px}.card,.box{background:#17242c;border:1px solid #ffffff22;border-radius:10px;padding:12px;margin-bottom:10px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px}.grid .card{margin:0}input,select,textarea,button{background:#24343d;color:#fff;border:1px solid #ffffff33;border-radius:6px;padding:8px}button{cursor:pointer;font-weight:800}.form{display:grid;grid-template-columns:160px 1fr;gap:9px}.badge{padding:3px 7px;border-radius:99px;background:#28566a}.published{background:#197348}.pending{background:#846012}.rejected,.blocked{background:#8d2936}.msg{background:#6b5112;padding:8px;border-radius:7px;margin:8px 0}.meta{color:#b9cbd4;font-size:12px}.danger{background:#8d2936}.ok{background:#197348}table{width:100%;border-collapse:collapse}th,td{padding:7px;border-bottom:1px solid #ffffff22;text-align:left}@media(max-width:700px){.form{grid-template-columns:1fr}.nav{float:none;margin-top:8px}}
</style></head><body><div class=top><b>📦 DNX Projekte</b><span class=nav><a href="/">Projekte</a>{% if user %}<a href="/upload">Upload</a><a href="/mine">Meine Projekte</a>{% if user.role=='admin' %}<a href="/admin">Admin</a>{% endif %}<a href="/logout">Abmelden ({{user.username}})</a>{% else %}<a href="/login">Anmelden</a><a href="/register">Registrieren</a>{% endif %}</span><div>Privates, inoffizielles Hobbyprojekt – keine Verbindung zu OpenWebRX.</div></div><main class=wrap>{% with ms=get_flashed_messages() %}{% for m in ms %}<div class=msg>{{m}}</div>{% endfor %}{% endwith %}{{body|safe}}</main></body></html>''',title=title,body=body,user=current())

@app.get('/')
def home():
 q=clean(request.args.get('q',''),100);cat=clean(request.args.get('category',''),80)
 sql='SELECT p.*,u.username FROM projects p JOIN users u ON u.id=p.owner_id WHERE p.status="published"';args=[]
 if q:sql+=' AND (p.title LIKE ? OR p.summary LIKE ? OR p.description LIKE ?)';args += ['%'+q+'%']*3
 if cat:sql+=' AND p.category=?';args.append(cat)
 sql+=' ORDER BY p.created DESC'
 with db() as c:rows=c.execute(sql,args).fetchall()
 cards=''.join(f'''<article class=card><h3>{h(r['title'],120)}</h3><span class="badge published">veröffentlicht</span> {h(r['category'],80)} · v{h(r['version'],40)}<p>{h(r['summary'],240)}</p><p class=meta>Autor {h(r['username'],60)} · {r['size']/1048576:.2f} MB · Downloads {r['downloads']} · SHA-256 {r['sha256'][:16]}…</p><a href="/download/{r['id']}"><button>Download</button></a> <a href="/project/{r['id']}">Details</a></article>''' for r in rows) or '<div class=box>Keine veröffentlichten Projekte.</div>'
 return layout(f'''<form class=box><input name=q value="{h(q)}" placeholder="Suchen"><input name=category value="{cat}" placeholder="Kategorie"><button>Suchen</button></form><div class=grid>{cards}</div>''')

@app.route('/register',methods=['GET','POST'])
def register():
 if request.method=='POST':
  name=clean(request.form.get('username'),50);pw=request.form.get('password','')
  if not re.fullmatch(r'[A-Za-z0-9_.-]{3,50}',name):flash('Ungültiger Benutzername.');return redirect('/register')
  if len(pw)<8:flash('Passwort muss mindestens 8 Zeichen haben.');return redirect('/register')
  try:
   with db() as c:c.execute('INSERT INTO users(username,password,created) VALUES(?,?,?)',(name,generate_password_hash(pw,method='scrypt'),int(time.time())))
   flash('Registrierung gespeichert. Ein Administrator muss das Konto freigeben.');return redirect('/login')
  except sqlite3.IntegrityError:flash('Benutzername existiert bereits.')
 return layout('''<div class=box><h2>Registrieren</h2><form method=post class=form><label>Benutzername</label><input name=username required minlength=3><label>Passwort</label><input name=password type=password required minlength=8><span></span><button>Registrieren</button></form></div>''','Registrieren')

@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  name=clean(request.form.get('username'),50);pw=request.form.get('password','');now=int(time.time())
  with db() as c:
   u=c.execute('SELECT * FROM users WHERE username=? COLLATE NOCASE',(name,)).fetchone()
   if not u or u['locked_until']>now or not check_password_hash(u['password'],pw):
    if u:
     failed=u['failed']+1;lock=now+900 if failed>=5 else 0;c.execute('UPDATE users SET failed=?,locked_until=? WHERE id=?',(0 if lock else failed,lock,u['id']))
    flash('Anmeldung fehlgeschlagen.');return redirect('/login')
   if u['status']!='active':flash('Konto wartet auf Freigabe oder ist gesperrt.');return redirect('/login')
   sid=secrets.token_urlsafe(40);token=secrets.token_urlsafe(32);c.execute('DELETE FROM sessions WHERE expires<?',(now,));c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(sid,u['id'],token,now+86400*7));c.execute('UPDATE users SET failed=0,locked_until=0 WHERE id=?',(u['id'],))
  resp=redirect(request.args.get('next') or '/');resp.set_cookie('dnxpm_session',sid,max_age=86400*7,httponly=True,samesite='Lax',secure=os.environ.get('DNX_PM_SECURE_COOKIE')=='1');return resp
 return layout('''<div class=box><h2>Anmelden</h2><form method=post class=form><label>Benutzername</label><input name=username required><label>Passwort</label><input name=password type=password required><span></span><button>Anmelden</button></form></div>''','Anmelden')

@app.get('/logout')
def logout():
 sid=request.cookies.get('dnxpm_session');
 if sid:
  with db() as c:c.execute('DELETE FROM sessions WHERE id=?',(sid,))
 r=redirect('/');r.delete_cookie('dnxpm_session');return r

@app.route('/upload',methods=['GET','POST'])
@login_required
def upload():
 u=current()
 if request.method=='POST':
  if not check_csrf():abort(403)
  f=request.files.get('file');fn=secure_filename(f.filename if f else '')
  if not f or not fn or not (fn.lower().endswith('.tar.gz') or Path(fn.lower()).suffix in ALLOWED):flash('Dateityp nicht erlaubt.');return redirect('/upload')
  with db() as c:used=c.execute('SELECT COALESCE(SUM(size),0) FROM projects WHERE owner_id=?',(u['id'],)).fetchone()[0]
  pid=uuid.uuid4().hex;stored=pid+'-'+fn;dest=QUAR/stored;h=hashlib.sha256();size=0
  with open(dest,'xb') as out:
   while True:
    chunk=f.stream.read(1024*1024)
    if not chunk:break
    size+=len(chunk)
    if size>MAX_FILE or used+size>MAX_USER:out.close();dest.unlink(missing_ok=True);flash('Größenlimit überschritten.');return redirect('/upload')
    out.write(chunk);h.update(chunk)
  scan='not-installed';cl=shutil.which('clamscan')
  if cl:
   r=subprocess.run([cl,'--no-summary',str(dest)],capture_output=True,text=True,timeout=900);scan='clean' if r.returncode==0 else 'infected'
  status='published' if u['role'] in ('trusted','admin') and scan!='infected' else 'pending'
  if status=='published':os.replace(dest,FILES/stored)
  vals=[pid,u['id']]+[clean(request.form.get(x),10000 if x in ('description','changelog') else 500) for x in ('title','summary','description','category','version','license','compatibility','dependencies','source_url','docs_url','changelog')]+[fn,stored,size,h.hexdigest(),f.mimetype,status,scan,int(time.time())]
  with db() as c:c.execute('INSERT INTO projects(id,owner_id,title,summary,description,category,version,license,compatibility,dependencies,source_url,docs_url,changelog,filename,stored,size,sha256,mime,status,scan,created) VALUES('+','.join('?'*21)+')',vals)
  audit('upload',pid);flash('Upload gespeichert: '+status);return redirect('/mine')
 form='''<div class=box><h2>Projekt hochladen</h2><form method=post enctype=multipart/form-data class=form><input type=hidden name=csrf value="%s"><label>Titel</label><input name=title required maxlength=120><label>Kurzbeschreibung</label><input name=summary maxlength=240><label>Beschreibung</label><textarea name=description rows=5></textarea><label>Kategorie</label><input name=category><label>Version</label><input name=version value=1.0.0><label>Lizenz</label><input name=license value=MIT><label>Kompatibilität</label><input name=compatibility><label>Abhängigkeiten</label><input name=dependencies><label>Quellcode-Link</label><input name=source_url type=url><label>Dokumentation</label><input name=docs_url type=url><label>Änderungsprotokoll</label><textarea name=changelog></textarea><label>Datei</label><input name=file type=file required><span></span><button>Hochladen</button></form></div>'''%csrf()
 return layout(form,'Upload')

@app.get('/mine')
@login_required
def mine():
 u=current();
 with db() as c:rows=c.execute('SELECT * FROM projects WHERE owner_id=? ORDER BY created DESC',(u['id'],)).fetchall()
 body='<h2>Meine Projekte</h2><table><tr><th>Titel</th><th>Status</th><th>Größe</th><th></th></tr>'+''.join(f'<tr><td>{clean(r["title"],120)}</td><td><span class="badge {r["status"]}">{r["status"]}</span></td><td>{r["size"]/1048576:.2f} MB</td><td><form method=post action="/delete/{r["id"]}"><input type=hidden name=csrf value="{csrf()}"><button class=danger>Löschen</button></form></td></tr>' for r in rows)+'</table>'
 return layout(body,'Meine Projekte')

@app.get('/project/<pid>')
def detail(pid):
 with db() as c:r=c.execute('SELECT p.*,u.username FROM projects p JOIN users u ON u.id=p.owner_id WHERE p.id=? AND p.status="published"',(pid,)).fetchone()
 if not r:abort(404)
 body=f'''<div class=box><h2>{h(r['title'],120)}</h2><p>{h(r['summary'],240)}</p><div style="white-space:pre-wrap">{h(r['description'],10000)}</div><p>Version {clean(r['version'])} · Lizenz {h(r['license'])} · Autor {clean(r['username'])}</p><p>Kompatibilität: {h(r['compatibility'])}<br>Abhängigkeiten: {h(r['dependencies'],1000)}</p><p>SHA-256: <code>{r['sha256']}</code></p><a href="/download/{r['id']}"><button>Download</button></a></div>'''
 return layout(body,r['title'])

@app.get('/download/<pid>')
def download(pid):
 with db() as c:
  r=c.execute('SELECT * FROM projects WHERE id=? AND status="published"',(pid,)).fetchone()
  if not r:abort(404)
  c.execute('UPDATE projects SET downloads=downloads+1 WHERE id=?',(pid,))
 path=FILES/r['stored'];
 if not path.is_file():abort(404)
 return send_file(path,as_attachment=True,download_name=r['filename'],mimetype='application/octet-stream',conditional=True)

@app.post('/delete/<pid>')
@login_required
def delete_project(pid):
 if not check_csrf():abort(403)
 u=current()
 with db() as c:
  r=c.execute('SELECT * FROM projects WHERE id=?',(pid,)).fetchone()
  if not r:abort(404)
  if r['owner_id']!=u['id'] and u['role']!='admin':abort(403)
  for base in (FILES,QUAR):(base/r['stored']).unlink(missing_ok=True)
  c.execute('DELETE FROM projects WHERE id=?',(pid,))
 audit('delete',pid);return redirect('/mine' if u['role']!='admin' else '/admin')

@app.route('/admin',methods=['GET'])
@admin_required
def admin():
 with db() as c:users=c.execute('SELECT id,username,role,status,created FROM users ORDER BY created DESC').fetchall();projects=c.execute('SELECT p.*,u.username FROM projects p JOIN users u ON u.id=p.owner_id WHERE p.status!="published" ORDER BY p.created DESC').fetchall()
 ub=''.join(f'''<tr><td>{h(x['username'],60)}</td><td>{x['status']}</td><td>{x['role']}</td><td><form method=post action=/admin/user/{x['id']}><input type=hidden name=csrf value="{csrf()}"><select name=status><option>pending</option><option {'selected' if x['status']=='active' else ''}>active</option><option>blocked</option></select><select name=role><option>user</option><option {'selected' if x['role']=='trusted' else ''}>trusted</option><option {'selected' if x['role']=='admin' else ''}>admin</option></select><button>Speichern</button></form></td></tr>''' for x in users)
 pb=''.join(f'''<tr><td>{h(x['title'],120)}</td><td>{h(x['username'],60)}</td><td>{x['status']} / {x['scan']}</td><td><form method=post action=/admin/project/{x['id']}><input type=hidden name=csrf value="{csrf()}"><button name=action value=approve class=ok>Freigeben</button><button name=action value=reject class=danger>Ablehnen</button></form></td></tr>''' for x in projects)
 return layout('<h2>Benutzer</h2><table><tr><th>Name</th><th>Status</th><th>Rolle</th><th>Aktion</th></tr>'+ub+'</table><h2>Moderation</h2><table><tr><th>Projekt</th><th>Uploader</th><th>Status</th><th>Aktion</th></tr>'+pb+'</table>','Admin')

@app.post('/admin/user/<int:uid>')
@admin_required
def admin_user(uid):
 if not check_csrf():abort(403)
 role=request.form.get('role');status=request.form.get('status')
 if role not in ('user','trusted','admin') or status not in ('pending','active','blocked'):abort(400)
 with db() as c:c.execute('UPDATE users SET role=?,status=? WHERE id=?',(role,status,uid))
 audit('user-change',f'{uid}:{role}:{status}');return redirect('/admin')

@app.post('/admin/project/<pid>')
@admin_required
def admin_project(pid):
 if not check_csrf():abort(403)
 action=request.form.get('action')
 with db() as c:
  r=c.execute('SELECT * FROM projects WHERE id=?',(pid,)).fetchone()
  if not r:abort(404)
  if action=='approve':
   src=QUAR/r['stored'];dst=FILES/r['stored'];
   if src.exists():os.replace(src,dst)
   c.execute('UPDATE projects SET status="published" WHERE id=?',(pid,))
  elif action=='reject':c.execute('UPDATE projects SET status="rejected" WHERE id=?',(pid,))
  else:abort(400)
 audit('moderate',pid+':'+action);return redirect('/admin')

def create_admin(name,password):
 if len(password)<8:raise SystemExit('Admin-Passwort: mindestens 8 Zeichen')
 with db() as c:
  c.execute('INSERT INTO users(username,password,role,status,created) VALUES(?,?,?,?,?) ON CONFLICT(username) DO UPDATE SET password=excluded.password,role="admin",status="active"',(name,generate_password_hash(password,method='scrypt'),'admin','active',int(time.time())))

if __name__=='__main__':
 import argparse,getpass
 ap=argparse.ArgumentParser();ap.add_argument('--init-admin');ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=8094);a=ap.parse_args()
 if a.init_admin:create_admin(a.init_admin,getpass.getpass('Neues Admin-Passwort: '));print('Administrator eingerichtet.')
 else:app.run(host=a.host,port=a.port)
