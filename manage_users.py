"""Gestion des comptes admin/equipe Amenah.

Usage :
    python manage_users.py list
    python manage_users.py add <username> <password> [admin|team]
    python manage_users.py set-password <username> <new_password>
    python manage_users.py delete <username>

Fonctionne en SQLite (par defaut) ou en MySQL si les variables MYSQL_* sont definies.
"""
import os
import sys
from datetime import datetime

from app import (
    USE_MYSQL,
    DATABASE,
    _mysql_connect,
    _hash_password,
    _init_admin_users_table,
)


def _connect():
    if USE_MYSQL:
        return _mysql_connect()
    import sqlite3
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def _exec(conn, sql, params=()):
    if USE_MYSQL:
        sql = sql.replace('?', '%s')
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur
    return conn.execute(sql, params)


def cmd_list(conn):
    cur = _exec(conn, 'SELECT id, username, role, created_at FROM admin_users ORDER BY id ASC')
    rows = cur.fetchall()
    if not rows:
        print('(aucun compte)')
        return
    print(f'{"id":>3}  {"username":<20} {"role":<8} created_at')
    print('-' * 60)
    for r in rows:
        d = dict(r)
        print(f'{d["id"]:>3}  {d["username"]:<20} {d.get("role") or "":<8} {d.get("created_at") or ""}')


def cmd_add(conn, username, password, role='admin'):
    username = username.strip().lower()
    role = (role or 'admin').strip().lower()
    if role not in ('admin', 'team'):
        role = 'team'
    if len(password) < 6:
        print('Mot de passe trop court (min 6 caracteres).')
        sys.exit(2)
    cur = _exec(conn, 'SELECT 1 FROM admin_users WHERE LOWER(username)=?', (username,))
    if cur.fetchone():
        print(f'Le compte "{username}" existe deja. Utilisez set-password pour le mettre a jour.')
        sys.exit(2)
    pw_hash = _hash_password(password)
    now = datetime.utcnow().isoformat() + 'Z'
    _exec(
        conn,
        'INSERT INTO admin_users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)',
        (username, pw_hash, role, now),
    )
    conn.commit()
    print(f'+ Compte cree : {username} (role={role})')


def cmd_set_password(conn, username, password):
    username = username.strip().lower()
    if len(password) < 6:
        print('Mot de passe trop court (min 6 caracteres).')
        sys.exit(2)
    cur = _exec(conn, 'SELECT id FROM admin_users WHERE LOWER(username)=?', (username,))
    row = cur.fetchone()
    if not row:
        print(f'Compte introuvable : {username}')
        sys.exit(2)
    pw_hash = _hash_password(password)
    _exec(conn, 'UPDATE admin_users SET password_hash=? WHERE LOWER(username)=?', (pw_hash, username))
    conn.commit()
    print(f'~ Mot de passe mis a jour pour {username}')


def cmd_delete(conn, username):
    username = username.strip().lower()
    cur = _exec(conn, 'DELETE FROM admin_users WHERE LOWER(username)=?', (username,))
    conn.commit()
    if getattr(cur, 'rowcount', 0) == 0:
        print(f'Aucun compte supprime (introuvable : {username}).')
    else:
        print(f'- Compte supprime : {username}')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1].lower()
    conn = _connect()
    try:
        _init_admin_users_table(conn)
        if cmd == 'list':
            cmd_list(conn)
        elif cmd == 'add' and len(sys.argv) >= 4:
            role = sys.argv[4] if len(sys.argv) >= 5 else 'admin'
            cmd_add(conn, sys.argv[2], sys.argv[3], role)
        elif cmd == 'set-password' and len(sys.argv) == 4:
            cmd_set_password(conn, sys.argv[2], sys.argv[3])
        elif cmd == 'delete' and len(sys.argv) == 3:
            cmd_delete(conn, sys.argv[2])
        else:
            print(__doc__)
            sys.exit(1)
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()
