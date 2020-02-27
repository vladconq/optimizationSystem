from sqlalchemy import Table
from sqlalchemy.sql import select
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from config import engine

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), unique=True)
    password = db.Column(db.String(80))
    role = db.Column(db.String(15))


User_tbl = Table('user', User.metadata)


def create_user_table():
    User.metadata.create_all(engine)


def add_user(username, password, role):
    hashed_password = generate_password_hash(password, method='sha256')

    ins = User_tbl.insert().values(
        username=username, password=hashed_password, role=role)

    conn = engine.connect()
    conn.execute(ins)
    conn.close()


def del_user(username):
    delete = User_tbl.delete().where(User_tbl.c.username == username)

    conn = engine.connect()
    conn.execute(delete)
    conn.close()


def show_users():
    select_st = select([User_tbl.c.username, User_tbl.c.role])

    conn = engine.connect()
    rs = conn.execute(select_st)

    for row in rs:
        print(row)

    conn.close()
