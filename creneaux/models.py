from datetime import datetime
from creneaux import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(128), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    presences = db.relationship('Presence', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<user {}>'.format(self.username)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(15), index=True, unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role {}>'.format(self.name)

class Creneau(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(52), default="")
    start = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    duration = db.Column(db.Integer, default=120)
    seances = db.relationship('Seance', backref='creneau', lazy='dynamic')
    period_in_days = db.Column(db.Integer, default=7)
    period_in_months = db.Column(db.Integer, default=0)

    def __repr__(self):
        return '<Creneau {}:{}>'.format(self.id, self.label)

class Seance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creneau_id = db.Column(db.Integer, db.ForeignKey('creneau.id'))
    date = db.Column(db.DateTime)
    presences = db.relationship('Presence', backref='seance', lazy='dynamic')

    def __repr__(self):
        return '<Seance {}:{}>'.format(self.id, self.date.strftime('%F'))

class Presence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seance_id = db.Column(db.Integer, db.ForeignKey('seance.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Presence {}>'.format(self.id)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))
