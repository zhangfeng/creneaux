drop table if exists users;
drop table if exists sessions;
drop table if exists comments;
drop table if exists roles;
drop table if exists proposals;

create table users(
	name TEXT,
	passwd TEXT,
	email TEXT,
	role INTEGER,
	id INTEGER PRIMARY KEY AUTOINCREMENT
);

create table roles(
	name TEXT,
	id INTEGER PRIMARY KEY
);

create table sessions(
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	date DATE,
	org INT,
	presents TEXT
);

create table comments(
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	session INTEGER,
	note TEXT
);

create table proposals(
	date DATE,
	org INT
);

insert into roles (name, id) VALUES
	('administrateur', 0),
	('utilisateur', 1);

insert into users (name, passwd, role) VALUES
	('admin', '7d4e7a38e5342f9e1f2c026304d6f09ca9c6d534', 0);

insert into sessions(date) VALUES
	('2016-04-02'),
	('2016-04-09'),
	('2016-04-16'),
	('2016-04-23'),
	('2016-04-30'),
	('2016-05-07'),
	('2016-05-14'),
	('2016-05-21'),
	('2016-05-28'),
	('2016-06-04'),
	('2016-06-11'),
	('2016-06-18'),
	('2016-06-25')
;
