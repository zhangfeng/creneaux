import sqlite3
from flask import Flask, session, render_template, g, Response, request, url_for, redirect
from hashlib import sha1
import datetime

# DATABASE = '/home/emmanuel/creneaux/creneaux.db'
DATABASE = 'creneaux.db'
SECRET_KEY = "043ecbddfef85390d149352d9ccd430bd7caa7fc Site Devisport Web"
DEBUG = 1

app = Flask('creneaux')

app.config.from_object(__name__)
# app.config['APPLICATION_ROOT'] = '/agenda'

def add_presence(a,b):
	if a == "":
		return b
	else:
		p = a.split(",")
		if p.count(b) < 1:
			p.append(b)
		return ",".join(sorted(p))

def sub_presence(a,b):
	if a == "":
		return a
	else:
		return ",".join(sorted([x for x in a.split(",") if x.lower() != b.lower()]))

def connect_db():
	db = sqlite3.connect(app.config['DATABASE'])
	db.row_factory = sqlite3.Row
	db.create_function("add_presence", 2, add_presence)
	db.create_function("sub_presence", 2, sub_presence)
	return db

def check_auth(user, passwd):
	sh_pass = sha1(passwd).hexdigest()
	cur = g.db.execute('select * from users where name=? and passwd=? and role<16', [user, sh_pass])
	return cur.fetchone() is not None

def is_admin():
	if 'username' not in session: return False
	cur = g.db.execute('select * from users where name=? and role%2=0', [session['username']])
	return cur.fetchone() is not None

def is_organizer():
	if 'username' not in session: return False
	cur = g.db.execute('select * from users where name=? and role&14>0', [session['username']])
	return cur.fetchone() is not None

def authenticate():
	return Response('Connexion requise, veuillez entrer vos identifiants', 401,
		{'WWW-Authenticate': 'Basic realm="Creneaux"'})

def requires_auth(f):
	@wraps(f)
	def decorated(*args, **kwargs):
		auth = request.authorization
		if not auth or not check_auth(auth.username, auth.password):
			return authenticate()
		return f(*args, **kwargs)
	return decorated

def get_users(db, roles=15):
	""" Get list of users, filtered by roles if specified """
	if roles == 0:
		users = {x['id']:x['name'] for x in db.execute('select id, name from users')}
		return users
	else:
		users = {x['id']:x['name'] for x in db.execute('select id, name from users where role&? > 0', [roles])}
		return users

def generate_saison(start, end):
	cur_date = datetime.date(*start)
	end_date = datetime.date(*end)
	week = datetime.timedelta(days=7)
	dates = []
	while cur_date < end_date:
		dates.append(cur_date.__str__())
		cur_date += week
	return dates

def add_event(db, dat, participants=None):
	""" Add an event """
	if participants is None:
		participants = get_users(db, roles=15)
	presences = ','.join(sorted(participants.values()))
	if isinstance(dat, str):
		dat = [dat]
	sql_cmd = 'insert into sessions (date, org, presents) values (?,0,?)'
	sql_params = [(d,presences) for d in dat]
	db.executemany(sql_cmd, sql_params)
	db.commit()

@app.before_request
def before_request():
	g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
	db = getattr(g, 'db', None)
	if db is not None:
		db.close()

@app.route("/agenda/")
def index():
	sessions = g.db.execute("select date, org, presents, alieu, id from sessions where date >= DATE() order by date");
	users = get_users(g.db)
	creneaux = []
	for s in sessions:
		d = s['date'].split('-');
		comments = [{'id':x['id'], 'note':x['note']} for x in g.db.execute("select * from comments where session=?", [s['id']])]
		org = 'Personne'
		if s['org']:
			org = users[s['org']]
		entry = {
			'date': '{0}/{1}/{2}'.format(d[2], d[1], d[0]),
			'org':  org,
			'presents': s['presents'].replace(",", ", ") or "Personne",
			'alieu': s['alieu'],
			'comments': comments
		};
		creneaux.append(entry);
	return render_template('index.html', creneaux=creneaux)

@app.route("/agenda/sessions/list")
def sessionsList():
	sessions = g.db.execute("select * from sessions where date >= DATE() order by date");
	users = get_users(g.db)
	today = datetime.date.today()
	creneaux = []
	for s in sessions:
		d = s['date'].split('-');
		comments = [{'id':x['id'], 'note':x['note']} for x in g.db.execute("select * from comments where session=?", [s['id']])]
		org = 'Personne'
		if s['org']:
			org = users[s['org']].title()
		entry = {
			'id': s['id'],
			'date': '{0}/{1}/{2}'.format(d[2], d[1], d[0]),
			'org': org,
			'presents': s['presents'].title().replace(",", ", ") or "Personne",
			'alieu': s['alieu'],
			'comments': comments
		};
		creneaux.append(entry);
	if 'username' in session:
		sorted_users = users.values()
		sorted_users.sort()
		return render_template('sessions.html', creneaux=creneaux, user=session['username'], users=sorted_users, admin=is_admin(), organizer=is_organizer(), today=today)
	else:
		return redirect(url_for('index'))

@app.route("/agenda/sessions/season", methods=['POST'])
def sessionsSeason():
	if 'username' not in session:
		return redirect(url_for('index'))
	if is_admin() and request.method == 'POST' and hasattr(request, 'form'):
		form1 = request.form
		start = (int(form1['s_year']), int(form1['s_month']), int(form1['s_day']))
		end = (int(form1['e_year']), int(form1['e_month']), int(form1['e_day']))
		add_event(g.db, generate_saison(start, end))
		return redirect(url_for('sessionsList'))
	else:
		return redirect(url_for('index'))

@app.route("/agenda/sessions/organize/<sid>", methods=['GET', 'POST'])
def sessionsOrganize(sid):
	if 'username' not in session:
		return redirect(url_for('index'))
	users = {x['name']:x for x in g.db.execute('select * from users')}
	if is_admin() and request.method == 'POST' and hasattr(request, 'form'):
		s = g.db.execute("select org, presents from sessions where id=?", [sid]).fetchone()
		if s is not None:
			if s['presents'].find(request.form['organiseur']) >= 0:
				g.db.execute("UPDATE sessions SET org=? WHERE id=?",
					[users[request.form['organiseur']]['id'], sid])
			else:
				g.db.execute("UPDATE sessions SET org=?, presents=add_presence(presents,?) WHERE id=?",
					[users[request.form['organiseur']]['id'], request.form['organiseur'], sid])
	else:
		s = g.db.execute("select org, presents from sessions where id=? and org=0", [sid]).fetchone()
		if s is not None:
			if s['presents'].find(session['username']) >= 0:
				g.db.execute("UPDATE sessions SET org=? WHERE id=?",
					[users[session['username']]['id'], sid])
			else:
				g.db.execute("UPDATE sessions SET org=?, presents=add_presence(presents,?) WHERE id=?",
					[users[session['username']]['id'], session['username'], sid])
	g.db.commit()
	return redirect(url_for('sessionsList'))

@app.route("/agenda/sessions/notes/add", methods=['POST'])
def addNote():
	if 'username' not in session:
		return redirect(url_for('index'))
	if not is_organizer():
		return redirect(url_for('sessionsList'))
	if hasattr(request, 'form'):
		note = request.form['note']
		sid = request.form['sid']
		if len(note) > 0:
			g.db.execute("INSERT INTO comments (note,session) VALUES (?,?)", [note, sid])
			g.db.commit()
	return redirect(url_for('sessionsList'))

@app.route("/agenda/sessions/notes/remove", methods=['POST'])
def removeNote():
	if 'username' not in session:
		return redirect(url_for('index'))
	if not is_organizer():
		return redirect(url_for('sessionsList'))
	if hasattr(request, 'form'):
		id = request.form['cid']
		if id is not None:
			g.db.execute("DELETE FROM comments WHERE id=?", [id])
			g.db.commit()
	return redirect(url_for('sessionsList'))

@app.route("/agenda/sessions/absent/<sid>")
def sessionsAbsent(sid):
	if 'username' not in session:
		return redirect(url_for('index'))
	users = {x['name']:x for x in g.db.execute('select * from users')}
	s = g.db.execute("select org, presents from sessions where id=?", [sid]).fetchone()
	if s is not None:
		presents = s['presents'].split(",")
		if session['username'] in presents:
			presents.remove(session['username'])
			presents.sort()
			presents = ",".join(presents)
			g.db.execute("UPDATE sessions SET presents=? WHERE id=?",
				[presents, sid])
			if s['org'] == users[session['username']]['id']:
				g.db.execute("UPDATE sessions SET org=NULL WHERE id=?", [sid])
			g.db.commit()
	return redirect(url_for('sessionsList'))

@app.route("/agenda/sessions/present/<sid>")
def sessionsPresent(sid):
	if 'username' not in session:
		return redirect(url_for('index'))
	users = {x['name']:x for x in g.db.execute('select * from users')}
	s = g.db.execute("select org, presents from sessions where id=?", [sid]).fetchone()
	if s is not None:
		if s['presents']:
			presents = s['presents'].split(",")
		else:
			presents = []
		if session['username'] not in presents:
			presents.append(session['username'])
			presents.sort()
			presents = ",".join(presents)
			g.db.execute("UPDATE sessions SET presents=? WHERE id=?",
				[presents, sid])
			g.db.commit()
	return redirect(url_for('sessionsList'))

@app.route("/agenda/sessions/presences/<sid>", methods=['GET','POST'])
def sessionsPresences(sid):
	if 'username' not in session:
		return redirect(url_for('index'))
	if not is_admin():
		return redirect(url_for('sessionsList'))
	users = {x['name']:x for x in g.db.execute('select * from users where id > 0')}
	if request.method == 'POST' and hasattr(request, 'form'):
		presences = ','.join(request.form.getlist('presences'))
		g.db.execute("UPDATE sessions SET presents=? WHERE id=?", [presences, sid])
		g.db.commit()
	s = g.db.execute("select * from sessions where id=?", [sid]).fetchone()
	presents = ""
	if s is not None:
		if s['presents']:
			presents = s['presents'].split(",")
		else:
			presents = []
#		presents = ",".join(presents)
	return render_template('presences.html', seance=s, presents=presents, users=users, admin=is_admin())

@app.route("/agenda/sessions/annule/<sid>")
def sessionsAnnule(sid):
	if 'username' not in session:
		return redirect(url_for('index'))
	s = g.db.execute("select org, presents from sessions where id=?", [sid]).fetchone()
	if s is not None and is_admin():
		g.db.execute("UPDATE sessions SET alieu=0 WHERE id=?", [sid])
		g.db.commit()
	return redirect(url_for('sessionsList'))

@app.route("/agenda/sessions/supprime/<sid>")
def sessionsSupprime(sid):
	if 'username' not in session:
		return redirect(url_for('index'))
	if not is_admin():
		return redirect(url_for('sessionsList'))
	g.db.execute("DELETE FROM sessions WHERE id=?", [sid])
	g.db.commit()
	return redirect(url_for('sessionsList'))

@app.route("/agenda/login", methods=['POST'])
def login():
	if hasattr(request, "form") and check_auth(request.form['username'], request.form['passwd']):
		session['username'] = request.form['username']
	return redirect(url_for('sessionsList'))

@app.route("/agenda/logout")
def logout():
	if 'username' in session:
		del session['username']
	return redirect(url_for('index'))

@app.route("/agenda/users/list")
def usersList():
	if 'username' not in session:
		return redirect(url_for('index'))
	if not is_admin():
		return redirect(url_for('index'))
	users = {x['id']:x for x in g.db.execute('select * from users')}
	roles = {x['id']:x['name'] for x in g.db.execute('select id, name from roles')}
	return render_template("users.html", users=users, roles=roles, admin=is_admin())

@app.route("/agenda/users/add", methods=['POST'])
def usersAdd():
	if 'username' not in session:
		return redirect(url_for('index'))
	if not is_admin():
		return redirect(url_for('index'))
	if hasattr(request, "form") and len(request.form['username']) > 0 and len(request.form['userpasswd']) > 0:
		sh_pass = sha1(request.form['userpasswd']).hexdigest()
		if 'useremail' in request.form and len(request.form['useremail']) > 0:
			g.db.execute("INSERT INTO users (name, email, passwd, role) VALUES (?, ?, ?, ?)", [
				request.form['username'], 
				request.form['useremail'],
				sh_pass,
				request.form['role']])
		else:
			g.db.execute("INSERT INTO users (name, passwd, role) VALUES (?, ?, ?)", [
				request.form['username'], 
				sh_pass,
				request.form['role'] ])
		if request.form['role'] < 17:
			g.db.execute('update sessions set presents=add_presence(presents, ?) where date >= DATE() AND presents IS NOT NULL', [request.form['username']])
			g.db.execute("update sessions set presents=? where date > DATE() AND presents IS NULL", [request.form['username']])
		g.db.commit()
	return redirect(url_for('usersList'))

@app.route("/agenda/users/modify", methods=['POST'])
def usersModify():
	if 'username' not in session:
		return redirect(url_for('index'))
	if hasattr(request, "form") and ('id' in request.form) and len(request.form['id']) > 0:
		userID = request.form['id']
		userEntry = g.db.execute('select name, email, passwd, role from users where id=?', [userID]).fetchone()
		if not is_admin() and userEntry['name'] != session['username']:
			return redirect(url_for('sessionsList'))
		if request.form['action'] == 'Modifier':
			userRecord = { x:userEntry[x] for x in ('email', 'passwd', 'role') }
			if 'userpassword' in request.form and len(request.form['userpassword']) > 0:
				sh_pass = sha1(request.form['userpassword']).hexdigest()
				userRecord['passwd'] = sh_pass
			if 'useremail' in request.form and len(request.form['useremail']) > 0:
				userRecord['email'] = request.form['useremail']
			if userRecord['role'] != request.form['role']:
				userRecord['role'] = request.form['role']
			g.db.execute("UPDATE users SET email=?,passwd=?,role=? WHERE id=?", [
				userRecord['email'], userRecord['passwd'], userRecord['role'], userID
			])
			if userRecord['role'] != userEntry['role']:
				if userRecord['role'] > 16:
					g.db.execute('UPDATE sessions SET presents=sub_presence(presents,?) WHERE date>DATE()', [
						userEntry['name']
					])
				elif userEntry['role'] > 16:
					g.db.execute('UPDATE sessions SET presents=add_presence(presents,?) WHERE date>DATE()', [
						userEntry['name']
					])
		elif request.form['action'] == "Absences":
			g.db.execute('UPDATE sessions SET presents=sub_presence(presents,?) WHERE date>DATE()', [
				userEntry['name']
			])
		elif request.form['action'] == "Presences":
			g.db.execute('UPDATE sessions SET presents=add_presence(presents,?) WHERE date>DATE()', [
				userEntry['name']
			])
		elif request.form['action'] == "Supprimer":
			g.db.execute("DELETE FROM users WHERE id=?", [userID])
			g.db.execute('UPDATE sessions SET presents=sub_presence(presents,?) WHERE date>DATE()', [
				userEntry['name']
			])
		g.db.commit()
	if is_admin():
		return redirect(url_for('usersList'))
	else:
		return redirect(url_for('compte'))

@app.route("/agenda/compte")
def compte():
	if 'username' not in session:
		return redirect(url_for('index'))
	user = g.db.execute('select * from users where name=?', [session['username']]).fetchone()
	if user is None:
		return redirect(url_for('index'))
	roles = {x['id']:x['name'] for x in g.db.execute('select id, name from roles')}
	return render_template("compte.html", u=user, admin=is_admin())

if __name__ == '__main__':
	app.run(debug=True)
