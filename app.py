import hashlib
import hmac
import html as html_std
import json
import os
import random
import re
import secrets
import smtplib
import threading
import unicodedata
import sqlite3
import ssl
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage
from functools import wraps
from flask import Flask, jsonify, make_response, request, render_template, g, redirect, session

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'data', 'amenah.db')
SCHEMA_FILE = os.path.join(BASE_DIR, 'sql', 'schema.sql')
MYSQL_HOST = (os.environ.get('MYSQL_HOST') or '').strip()
USE_MYSQL = bool(MYSQL_HOST) and (os.environ.get('AMENAH_USE_SQLITE') or '').strip() not in ('1', 'true', 'yes')

def _mysql_connect():
    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except ImportError as e:
        raise RuntimeError('MYSQL_HOST est défini mais pymysql est absent. Installez : pip install pymysql') from e
    dbname = (os.environ.get('MYSQL_DATABASE') or os.environ.get('MYSQL_DB') or 'amenah').strip()
    return pymysql.connect(host=MYSQL_HOST, user=(os.environ.get('MYSQL_USER') or 'root').strip(), password=os.environ.get('MYSQL_PASSWORD') or '', database=dbname, charset='utf8mb4', cursorclass=DictCursor)

def get_db():
    if 'db' not in g:
        if USE_MYSQL:
            g.db = _mysql_connect()
        else:
            os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
            g.db = sqlite3.connect(DATABASE)
            g.db.row_factory = sqlite3.Row
    return g.db

def db_exec(db, sql, params=None):
    params = params or ()
    if USE_MYSQL:
        sql = sql.replace('?', '%s')
        cur = db.cursor()
        cur.execute(sql, params)
        return cur
    return db.execute(sql, params)

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def _slugify_donation_slug(text: str) -> str:
    if not (text or '').strip():
        return 'organisme'
    s = unicodedata.normalize('NFKD', str(text))
    s = s.encode('ascii', 'ignore').decode('ascii')
    s = s.lower().strip()
    s = re.sub('[^a-z0-9]+', '-', s)
    s = re.sub('-+', '-', s).strip('-')
    return s[:80] if s else 'organisme'

def _unique_donation_slug(db, base: str) -> str:
    base = (base or 'organisme')[:80]
    n = 0
    while n < 60:
        cand = base if n == 0 else f'{base}-{n}'
        cur = db_exec(db, 'SELECT 1 FROM donation_agencies WHERE slug = ?', (cand,))
        if not cur.fetchone():
            return cand
        n += 1
    return f'{base}-{random.randint(10000, 99999)}'

def _next_donation_sort_order(db):
    cur = db_exec(db, 'SELECT COALESCE(MAX(sort_order), 0) + 1 AS n FROM donation_agencies')
    row = cur.fetchone()
    if not row:
        return 1
    r = dict(row)
    return int(r.get('n') or 1)

def _generate_ean13() -> str:
    digits = [random.randint(0, 9) for _ in range(12)]
    s = sum((digits[i] * (1 if i % 2 == 0 else 3) for i in range(12)))
    check = (10 - s % 10) % 10
    return ''.join(map(str, digits)) + str(check)

SECRET_FILE = os.path.join(BASE_DIR, 'data', '.secret')

def _get_or_create_secret_key() -> bytes:
    env = (os.environ.get('AMENAH_SECRET_KEY') or '').strip()
    if env:
        return env.encode('utf-8')
    os.makedirs(os.path.dirname(SECRET_FILE), exist_ok=True)
    if os.path.exists(SECRET_FILE):
        try:
            with open(SECRET_FILE, 'rb') as f:
                data = f.read().strip()
                if data:
                    return data
        except OSError:
            pass
    key = secrets.token_hex(32).encode('utf-8')
    try:
        with open(SECRET_FILE, 'wb') as f:
            f.write(key)
        try:
            os.chmod(SECRET_FILE, 0o600)
        except OSError:
            pass
    except OSError:
        pass
    return key

_PW_ITERATIONS = 240000

def _hash_password(pw: str, salt: bytes = None, iterations: int = _PW_ITERATIONS) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', (pw or '').encode('utf-8'), salt, iterations)
    return f'pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}'

def _verify_password(pw: str, stored: str) -> bool:
    try:
        parts = (stored or '').split('$')
        if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
            return False
        iters = int(parts[1])
        salt = bytes.fromhex(parts[2])
        target = bytes.fromhex(parts[3])
    except (ValueError, TypeError):
        return False
    dk = hashlib.pbkdf2_hmac('sha256', (pw or '').encode('utf-8'), salt, iters)
    return hmac.compare_digest(dk, target)

def _init_admin_users_table(conn):
    if USE_MYSQL:
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS admin_users (
            id INT NOT NULL AUTO_INCREMENT,
            username VARCHAR(80) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(32) NOT NULL DEFAULT 'team',
            created_at VARCHAR(64) NOT NULL,
            PRIMARY KEY (id),
            UNIQUE KEY idx_admin_users_username (username)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci''')
    else:
        conn.execute('''CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'team',
            created_at TEXT NOT NULL
        )''')
    conn.commit()

def _ensure_default_admin():
    conn = None
    try:
        if USE_MYSQL:
            conn = _mysql_connect()
            _init_admin_users_table(conn)
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) AS n FROM admin_users')
            row = cur.fetchone() or {}
            count = int(row.get('n') or 0)
        else:
            os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            _init_admin_users_table(conn)
            row = conn.execute('SELECT COUNT(*) AS n FROM admin_users').fetchone()
            count = int(dict(row).get('n') or 0)
        if count > 0:
            return
        username = ((os.environ.get('AMENAH_ADMIN_USER') or 'admin').strip() or 'admin').lower()
        password = (os.environ.get('AMENAH_ADMIN_PASSWORD') or '').strip()
        generated = False
        if not password:
            password = secrets.token_urlsafe(10)
            generated = True
        pw_hash = _hash_password(password)
        now = datetime.utcnow().isoformat() + 'Z'
        if USE_MYSQL:
            cur.execute(
                'INSERT INTO admin_users (username, password_hash, role, created_at) VALUES (%s, %s, %s, %s)',
                (username, pw_hash, 'admin', now),
            )
        else:
            conn.execute(
                'INSERT INTO admin_users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)',
                (username, pw_hash, 'admin', now),
            )
        conn.commit()
        print('')
        print('  ' + '=' * 60)
        print('  COMPTE ADMINISTRATEUR AMENAH CREE')
        print('  ' + '-' * 60)
        print(f'  Utilisateur : {username}')
        print(f'  Mot de passe: {password}')
        if generated:
            print('  (mot de passe genere aleatoirement - notez-le !)')
        print('  Page de connexion : /admin/login')
        print('  ' + '=' * 60)
        print('')
    except Exception:
        import traceback
        print('  [avertissement] impossible de creer le compte admin par defaut')
        traceback.print_exc()
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

def init_db():
    if USE_MYSQL:
        _ensure_default_admin()
        return
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    try:
        conn.execute("ALTER TABLE waiting ADD COLUMN suggestion_type TEXT NOT NULL DEFAULT 'boycott'")
    except sqlite3.OperationalError as e:
        if 'duplicate column' not in str(e).lower():
            raise
    try:
        conn.execute('ALTER TABLE produits ADD COLUMN code_barre TEXT')
    except sqlite3.OperationalError as e:
        if 'duplicate column' not in str(e).lower():
            raise
    conn.commit()
    conn.close()
    _ensure_default_admin()
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'), static_url_path='/static')
app.secret_key = _get_or_create_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)
app.teardown_appcontext(close_db)
with app.app_context():
    init_db()

def require_admin_api(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('admin_user_id'):
            return (jsonify({'ok': False, 'error': 'Authentification requise.', 'auth_required': True}), 401)
        return fn(*args, **kwargs)
    return wrapper

def require_admin_page(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('admin_user_id'):
            nxt = request.path or '/admin'
            return redirect(f'/admin/login?next={nxt}')
        return fn(*args, **kwargs)
    return wrapper
FEEDBACK_EMAIL_DEFAULT_TO = 'amenah@amenah.com'
GAZA_NEWS_RSS = (('https://feeds.bbci.co.uk/news/world/middle_east/rss.xml', 'BBC News', False), ('https://www.aljazeera.com/xml/rss/all.xml', 'Al Jazeera', False))
GAZA_NEWS_TTL_SEC = 300
_gaza_news_cache: dict = {'t': 0.0, 'payload': None}
GAZA_KEYWORDS = ('gaza', 'rafah', 'palestin', 'palestinian', 'israel', 'israeli', 'west bank', 'jerusalem', 'hamas', 'idf', 'occupation', 'settler', 'netanyahu', 'al-aqsa', 'hebron', 'jenin', 'nablus')

def _fetch_rss_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': 'AmenahGazaNews/1.0 (+https://github.com/)', 'Accept': 'application/rss+xml, application/xml, text/xml, */*'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()

def _strip_tags(html: str) -> str:
    t = re.sub('<[^>]+>', ' ', html or '')
    t = html_std.unescape(re.sub('\\s+', ' ', t).strip())
    return t

def _img_from_description(desc: str):
    m = re.search('src=["\\\']([^"\\\']+)["\\\']', desc or '', re.I)
    if not m:
        return None
    return m.group(1).replace('&amp;', '&').strip()
_NS_CONTENT_ENCODED = '{http://purl.org/rss/1.0/modules/content/}encoded'
_OG_IMAGE_RES = (re.compile('property=["\\\']og:image["\\\']\\s+content=["\\\']([^"\\\']+)["\\\']', re.I), re.compile('content=["\\\']([^"\\\']+)["\\\']\\s+property=["\\\']og:image["\\\']', re.I))
_og_image_cache = {}
_og_lock = threading.Lock()

def _fetch_og_image(page_url: str):
    try:
        req = urllib.request.Request(page_url, headers={'User-Agent': 'Mozilla/5.0 (compatible; AmenahNews/1.1)'})
        with urllib.request.urlopen(req, timeout=12) as resp:
            chunk = resp.read(200000)
        text = chunk.decode('utf-8', 'replace')
        for rx in _OG_IMAGE_RES:
            m = rx.search(text)
            if m:
                return html_std.unescape(m.group(1).strip())
    except Exception:
        pass
    return None

def _enrich_news_images_missing(items, max_fetch=20, workers=5):
    need = [it for it in items if not it.get('image')][:max_fetch]
    if not need:
        return

    def fill_one(it):
        url = (it.get('link') or '').strip()
        if not url:
            return
        with _og_lock:
            if url in _og_image_cache:
                got = _og_image_cache[url]
                if got:
                    it['image'] = got
                return
        img = _fetch_og_image(url)
        with _og_lock:
            _og_image_cache[url] = img
        if img:
            it['image'] = img
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pool.map(fill_one, need)

def _parse_rss_items(xml_bytes, source_label, take_all):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    channel = root.find('channel')
    if channel is None:
        return []
    ns_media = '{http://search.yahoo.com/mrss/}'
    out = []
    for item in channel.findall('item'):
        title_el = item.find('title')
        raw_title = ''.join(title_el.itertext()).strip() if title_el is not None else ''
        title = _strip_tags(raw_title) or (item.findtext('title') or '').strip()
        title = html_std.unescape(title)
        link = (item.findtext('link') or '').strip()
        if not title or not link:
            continue
        pub = (item.findtext('pubDate') or '').strip()
        desc = (item.findtext('description') or '').strip()
        summary = _strip_tags(desc)
        if len(summary) > 280:
            summary = summary[:277] + '…'
        img = _img_from_description(desc)
        if not img:
            enc = item.find(_NS_CONTENT_ENCODED)
            if enc is not None and enc.text:
                img = _img_from_description(enc.text)
        if not img:
            for thumb in item.findall(f'{ns_media}thumbnail'):
                u = thumb.get('url')
                if u:
                    img = u.strip()
                    break
        if not img:
            enc_el = item.find('enclosure')
            if enc_el is not None:
                typ = (enc_el.get('type') or '').lower()
                if typ.startswith('image/') and enc_el.get('url'):
                    img = enc_el.get('url').strip()
        blob = (title + ' ' + summary).lower()
        if not take_all:
            if not any((k in blob for k in GAZA_KEYWORDS)):
                continue
            off_topic = ('ukraine', 'russia', 'putin', 'zelensky', 'moscow', 'kyiv', 'nato')
            if any((o in blob for o in off_topic)) and (not any((z in blob for z in ('gaza', 'palestin', 'israel', 'rafah', 'west bank', 'jerusalem', 'hamas')))):
                continue
        dt_iso = None
        if pub:
            try:
                dt = parsedate_to_datetime(pub)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                dt_iso = dt.isoformat()
            except (TypeError, ValueError, OverflowError):
                dt_iso = None
        out.append({'title': title, 'link': link, 'source': source_label, 'published_at': dt_iso, 'summary': summary or None, 'image': img})
    return out

def _merge_gaza_news():
    merged = []
    for (url, label, take_all) in GAZA_NEWS_RSS:
        try:
            raw = _fetch_rss_bytes(url)
            merged.extend(_parse_rss_items(raw, label, take_all))
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            app.logger.warning('RSS indisponible %s : %s', url, e)
    seen = set()
    unique = []
    for it in merged:
        key = it['link'].split('?', 1)[0].rstrip('/')
        if key in seen:
            continue
        seen.add(key)
        unique.append(it)

    def sort_key(x):
        if x.get('published_at'):
            try:
                return x['published_at']
            except Exception:
                pass
        return ''
    unique.sort(key=sort_key, reverse=True)
    sliced = unique[:28]
    _enrich_news_images_missing(sliced)
    return sliced

@app.route('/api/gaza-news', methods=['GET'])
def gaza_news():
    now = time.monotonic()
    if _gaza_news_cache['payload'] is not None and now - _gaza_news_cache['t'] < GAZA_NEWS_TTL_SEC:
        return jsonify(_gaza_news_cache['payload'])
    try:
        items = _merge_gaza_news()
        payload = {'ok': True, 'items': items}
    except Exception:
        app.logger.exception('gaza_news')
        payload = {'ok': False, 'error': 'Impossible de charger les flux pour le moment.', 'items': []}
    _gaza_news_cache['t'] = now
    _gaza_news_cache['payload'] = payload
    return jsonify(payload)

def _send_feedback_email(message: str, feedback_id: int, created_at: str) -> bool:
    to_addr = (os.environ.get('FEEDBACK_EMAIL_TO') or FEEDBACK_EMAIL_DEFAULT_TO).strip()
    smtp_host = (os.environ.get('SMTP_HOST') or '').strip()
    if not smtp_host:
        app.logger.warning('Feedback id=%s enregistré mais SMTP_HOST absent : aucun e-mail envoyé.', feedback_id)
        return False
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = (os.environ.get('SMTP_USER') or '').strip()
    smtp_password = os.environ.get('SMTP_PASSWORD') or ''
    use_tls = os.environ.get('SMTP_USE_TLS', '1').strip().lower() not in ('0', 'false', 'no', 'off')
    mail_from = (os.environ.get('SMTP_FROM') or smtp_user or 'noreply@amenah.com').strip()
    subject = f'[Amenah] Nouveau feedback #{feedback_id}'
    body = f'Un message a été envoyé depuis le formulaire Feedback du site.\n\nID : {feedback_id}\nDate (UTC) : {created_at}\n\n---\n{message}\n---\n'
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = mail_from
    msg['To'] = to_addr
    msg.set_content(body, charset='utf-8')
    try:
        if smtp_port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as smtp:
                if smtp_user:
                    smtp.login(smtp_user, smtp_password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
                smtp.ehlo()
                if use_tls:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                if smtp_user:
                    smtp.login(smtp_user, smtp_password)
                smtp.send_message(msg)
        app.logger.info('E-mail feedback envoyé vers %s (id=%s).', to_addr, feedback_id)
        return True
    except Exception:
        app.logger.exception('Échec envoi e-mail feedback id=%s', feedback_id)
        return False

@app.before_request
def api_cors_preflight():
    if request.path.startswith('/api/') and request.method == 'OPTIONS':
        r = make_response('', 204)
        r.headers['Access-Control-Allow-Origin'] = '*'
        r.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return r

@app.after_request
def api_cors_headers(resp):
    if request.path.startswith('/api/'):
        resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
@require_admin_page
def admin():
    return render_template('admin.html')

@app.route('/admin/login')
def admin_login_page():
    if session.get('admin_user_id'):
        return redirect('/admin')
    return render_template('login.html')

_LOGIN_FAIL_TRACK: dict = {}
_LOGIN_FAIL_LOCK = threading.Lock()
_LOGIN_FAIL_WINDOW = 300
_LOGIN_FAIL_MAX = 8

def _login_throttled(key: str) -> bool:
    now = time.monotonic()
    with _LOGIN_FAIL_LOCK:
        (count, first) = _LOGIN_FAIL_TRACK.get(key, (0, now))
        if now - first > _LOGIN_FAIL_WINDOW:
            _LOGIN_FAIL_TRACK[key] = (0, now)
            return False
        return count >= _LOGIN_FAIL_MAX

def _record_login_fail(key: str) -> None:
    now = time.monotonic()
    with _LOGIN_FAIL_LOCK:
        (count, first) = _LOGIN_FAIL_TRACK.get(key, (0, now))
        if now - first > _LOGIN_FAIL_WINDOW:
            count = 0
            first = now
        _LOGIN_FAIL_TRACK[key] = (count + 1, first)

def _clear_login_fail(key: str) -> None:
    with _LOGIN_FAIL_LOCK:
        _LOGIN_FAIL_TRACK.pop(key, None)

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip().lower()
    password = data.get('password') or ''
    if not username or not password:
        return (jsonify({'ok': False, 'error': 'Identifiants requis.'}), 400)
    throttle_key = (request.remote_addr or 'unknown') + ':' + username
    if _login_throttled(throttle_key):
        return (jsonify({'ok': False, 'error': 'Trop de tentatives. Réessaie dans quelques minutes.'}), 429)
    db = get_db()
    cur = db_exec(db, 'SELECT id, username, password_hash, role FROM admin_users WHERE LOWER(username) = LOWER(?)', (username,))
    row = cur.fetchone()
    if not row or not _verify_password(password, dict(row).get('password_hash') or ''):
        _record_login_fail(throttle_key)
        return (jsonify({'ok': False, 'error': 'Identifiants invalides.'}), 401)
    r = dict(row)
    session.clear()
    session['admin_user_id'] = int(r['id'])
    session['admin_username'] = r['username']
    session['admin_role'] = r.get('role') or 'team'
    session.permanent = True
    _clear_login_fail(throttle_key)
    return jsonify({'ok': True, 'user': {'username': r['username'], 'role': session['admin_role']}})

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({'ok': True})

@app.route('/api/admin/me', methods=['GET'])
def admin_me():
    if not session.get('admin_user_id'):
        return (jsonify({'ok': False, 'authenticated': False}), 401)
    return jsonify({'ok': True, 'authenticated': True, 'user': {
        'id': session.get('admin_user_id'),
        'username': session.get('admin_username'),
        'role': session.get('admin_role'),
    }})

_USERNAME_RE = re.compile(r'^[a-z0-9._-]{3,80}$')

@app.route('/api/admin/users', methods=['GET', 'POST'])
@require_admin_api
def admin_users_route():
    db = get_db()
    if request.method == 'GET':
        cur = db_exec(db, 'SELECT id, username, role, created_at FROM admin_users ORDER BY id ASC')
        rows = [dict(r) for r in cur.fetchall()]
        return jsonify({'ok': True, 'items': rows, 'current_id': session.get('admin_user_id')})
    if (session.get('admin_role') or '') != 'admin':
        return (jsonify({'ok': False, 'error': 'Seul un administrateur peut ajouter un membre.'}), 403)
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip().lower()
    password = data.get('password') or ''
    role = (data.get('role') or 'team').strip().lower()
    if role not in ('admin', 'team'):
        role = 'team'
    if not _USERNAME_RE.match(username):
        return (jsonify({'ok': False, 'error': "Nom d'utilisateur invalide (3+ caractères, a-z, 0-9, . _ -)."}), 400)
    if len(password) < 6:
        return (jsonify({'ok': False, 'error': 'Mot de passe trop court (min 6 caractères).'}), 400)
    cur = db_exec(db, 'SELECT 1 FROM admin_users WHERE LOWER(username) = LOWER(?)', (username,))
    if cur.fetchone():
        return (jsonify({'ok': False, 'error': "Ce nom d'utilisateur existe déjà."}), 409)
    pw_hash = _hash_password(password)
    now = datetime.utcnow().isoformat() + 'Z'
    db_exec(db, 'INSERT INTO admin_users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)', (username, pw_hash, role, now))
    db.commit()
    return jsonify({'ok': True, 'username': username, 'role': role})

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@require_admin_api
def admin_users_delete(user_id):
    if (session.get('admin_role') or '') != 'admin':
        return (jsonify({'ok': False, 'error': 'Seul un administrateur peut supprimer un membre.'}), 403)
    if user_id == int(session.get('admin_user_id') or 0):
        return (jsonify({'ok': False, 'error': 'Vous ne pouvez pas supprimer votre propre compte.'}), 400)
    db = get_db()
    cur = db_exec(db, 'SELECT role FROM admin_users WHERE id = ?', (user_id,))
    row = cur.fetchone()
    if not row:
        return (jsonify({'ok': False, 'error': 'Utilisateur introuvable.'}), 404)
    if (dict(row).get('role') or '').lower() == 'admin':
        cur = db_exec(db, 'SELECT COUNT(*) AS n FROM admin_users WHERE role = ?', ('admin',))
        n = int(dict(cur.fetchone() or {}).get('n') or 0)
        if n <= 1:
            return (jsonify({'ok': False, 'error': 'Impossible de supprimer le dernier administrateur.'}), 400)
    db_exec(db, 'DELETE FROM admin_users WHERE id = ?', (user_id,))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/password', methods=['POST'])
@require_admin_api
def admin_change_password():
    data = request.get_json(silent=True) or {}
    current = data.get('current') or ''
    new_pw = data.get('new') or ''
    if len(new_pw) < 6:
        return (jsonify({'ok': False, 'error': 'Mot de passe trop court (min 6 caractères).'}), 400)
    db = get_db()
    cur = db_exec(db, 'SELECT password_hash FROM admin_users WHERE id = ?', (int(session.get('admin_user_id') or 0),))
    row = cur.fetchone()
    if not row or not _verify_password(current, dict(row).get('password_hash') or ''):
        return (jsonify({'ok': False, 'error': 'Mot de passe actuel incorrect.'}), 401)
    new_hash = _hash_password(new_pw)
    db_exec(db, 'UPDATE admin_users SET password_hash = ? WHERE id = ?', (new_hash, int(session.get('admin_user_id'))))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/suggestion', methods=['POST'])
def add_suggestion():
    data = request.get_json(silent=True) or {}
    nom = (data.get('nom') or '').strip()
    if not nom:
        return (jsonify({'ok': False, 'error': 'Le nom du produit est requis.'}), 400)
    categorie = (data.get('categorie') or '').strip() or None
    description = (data.get('description') or '').strip() or None
    lien_source = (data.get('lien_source') or '').strip() or None
    email_contact = (data.get('email_contact') or '').strip() or None
    st = (data.get('suggestion_type') or 'boycott').strip().lower()
    if st not in ('boycott', 'alternative'):
        st = 'boycott'
    now = datetime.utcnow().isoformat() + 'Z'
    db = get_db()
    cur = db_exec(db, "\n        INSERT INTO waiting (nom, categorie, description, lien_source, email_contact, created_at, statut, suggestion_type)\n        VALUES (?, ?, ?, ?, ?, ?, 'en_attente', ?)\n        ", (nom, categorie, description, lien_source, email_contact, now, st))
    db.commit()
    return jsonify({'ok': True, 'id': cur.lastrowid, 'storage': 'mysql' if USE_MYSQL else 'sqlite'})

@app.route('/api/waiting', methods=['GET'])
@require_admin_api
def list_waiting():
    db = get_db()
    cur = db_exec(db, 'SELECT id, nom, categorie, description, lien_source, email_contact, created_at, statut, suggestion_type FROM waiting ORDER BY id DESC')
    rows = cur.fetchall()
    return jsonify({'items': [dict(r) for r in rows]})

@app.route('/api/waiting/<int:item_id>/accepter', methods=['POST'])
@require_admin_api
def accepter(item_id):
    db = get_db()
    cur = db_exec(db, 'SELECT * FROM waiting WHERE id = ?', (item_id,))
    row = cur.fetchone()
    if not row:
        return (jsonify({'ok': False, 'error': 'Suggestion introuvable.'}), 404)
    r = dict(row)
    now = datetime.utcnow().isoformat() + 'Z'
    kind = (r.get('suggestion_type') or 'boycott').lower()
    if kind == 'alternative':
        db_exec(db, '\n            INSERT INTO produit_alternatives (nom, categorie, description, lien_source, created_at)\n            VALUES (?, ?, ?, ?, ?)\n            ', (r['nom'], r['categorie'], r['description'], r['lien_source'], now))
    else:
        db_exec(db, '\n            INSERT INTO produits (nom, categorie, description, lien_source, accepted_from_waiting_id, created_at, code_barre)\n            VALUES (?, ?, ?, ?, ?, ?, ?)\n            ', (r['nom'], r['categorie'], r['description'], r['lien_source'], item_id, now, _generate_ean13()))
    db_exec(db, 'DELETE FROM waiting WHERE id = ?', (item_id,))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/waiting/<int:item_id>/refuser', methods=['POST'])
@require_admin_api
def refuser(item_id):
    db = get_db()
    cur = db_exec(db, 'DELETE FROM waiting WHERE id = ?', (item_id,))
    db.commit()
    if cur.rowcount == 0:
        return (jsonify({'ok': False, 'error': 'Suggestion introuvable.'}), 404)
    return jsonify({'ok': True})

@app.route('/api/produits', methods=['GET'])
def list_produits():
    db = get_db()
    cur = db_exec(db, 'SELECT id, nom, categorie, description, lien_source, created_at, code_barre FROM produits ORDER BY id DESC')
    rows = cur.fetchall()
    return jsonify({'items': [dict(r) for r in rows]})

@app.route('/api/produit-alternatives', methods=['GET'])
def list_produit_alternatives():
    db = get_db()
    cur = db_exec(db, 'SELECT id, nom, categorie, description, lien_source, created_at FROM produit_alternatives ORDER BY id DESC')
    rows = cur.fetchall()
    return jsonify({'items': [dict(r) for r in rows]})

@app.route('/api/donation-suggestions', methods=['GET', 'POST'])
def donation_suggestions():
    db = get_db()
    if request.method == 'GET':
        if not session.get('admin_user_id'):
            return (jsonify({'ok': False, 'error': 'Authentification requise.', 'auth_required': True, 'items': []}), 401)
        try:
            cur = db_exec(db, 'SELECT id, nom, description, lien_source, email_contact, created_at, statut FROM donation_suggestions ORDER BY id DESC')
            rows = cur.fetchall()
            return jsonify({'ok': True, 'items': [dict(r) for r in rows]})
        except Exception:
            app.logger.exception('donation_suggestions list')
            return jsonify({'ok': False, 'error': 'Table donation_suggestions indisponible.', 'items': []})
    data = request.get_json(silent=True) or {}
    nom = (data.get('nom') or '').strip()
    if not nom:
        return (jsonify({'ok': False, 'error': 'Le nom de l’organisme ou de la personne est requis.'}), 400)
    description = (data.get('description') or '').strip() or None
    lien_source = (data.get('lien_source') or '').strip() or None
    email_contact = (data.get('email_contact') or '').strip() or None
    now = datetime.utcnow().isoformat() + 'Z'
    try:
        cur = db_exec(db, "\n            INSERT INTO donation_suggestions (nom, description, lien_source, email_contact, created_at, statut)\n            VALUES (?, ?, ?, ?, ?, 'en_attente')\n            ", (nom, description, lien_source, email_contact, now))
        db.commit()
    except Exception:
        app.logger.exception('donation_suggestions insert')
        return (jsonify({'ok': False, 'error': 'Enregistrement impossible (table donation_suggestions manquante ?).'}), 500)
    return jsonify({'ok': True, 'id': cur.lastrowid, 'storage': 'mysql' if USE_MYSQL else 'sqlite'})

@app.route('/api/donation-suggestions/<int:item_id>/accepter', methods=['POST'])
@require_admin_api
def accepter_donation_suggestion(item_id):
    db = get_db()
    cur = db_exec(db, 'SELECT * FROM donation_suggestions WHERE id = ? AND statut = ?', (item_id, 'en_attente'))
    row = cur.fetchone()
    if not row:
        return (jsonify({'ok': False, 'error': 'Suggestion introuvable ou déjà traitée.'}), 404)
    r = dict(row)
    nom = (r.get('nom') or '').strip()
    if not nom:
        return (jsonify({'ok': False, 'error': 'Nom manquant.'}), 400)
    desc = (r.get('description') or '').strip()
    raw_lien = (r.get('lien_source') or '').strip()
    if raw_lien and (not (raw_lien.startswith('http://') or raw_lien.startswith('https://'))):
        raw_lien = ''
    donate_url = raw_lien if raw_lien else '#'
    card_summary = desc if len(desc) <= 400 else desc[:397] + '…'
    if not card_summary:
        card_summary = nom[:400]
    body_text = desc + '\n\n— Fiche créée à partir d’une suggestion sur le site.' if desc else 'Cette fiche provient d’une suggestion d’utilisateur·rice. Complétez les textes, le logo et l’image d’en-tête dans la base de données si besoin.'
    base_slug = _slugify_donation_slug(nom)
    slug = _unique_donation_slug(db, base_slug)
    sort_order = _next_donation_sort_order(db)
    try:
        db_exec(db, "\n            INSERT INTO donation_agencies (\n                slug, name, card_summary, body_text, hero_image_url, logo_url, gallery_json, donate_url, sort_order\n            )\n            VALUES (?, ?, ?, ?, NULL, NULL, '[]', ?, ?)\n            ", (slug, nom, card_summary, body_text, donate_url, sort_order))
        db_exec(db, 'DELETE FROM donation_suggestions WHERE id = ?', (item_id,))
        db.commit()
    except Exception:
        app.logger.exception('accepter_donation_suggestion')
        db.rollback()
        return (jsonify({'ok': False, 'error': 'Impossible d’enregistrer l’organisme (conflit ou base indisponible).'}), 500)
    return jsonify({'ok': True, 'slug': slug})

@app.route('/api/donation-suggestions/<int:item_id>/refuser', methods=['POST'])
@require_admin_api
def refuser_donation_suggestion(item_id):
    db = get_db()
    cur = db_exec(db, 'DELETE FROM donation_suggestions WHERE id = ?', (item_id,))
    db.commit()
    rc = getattr(cur, 'rowcount', 0) or 0
    if rc == 0:
        return (jsonify({'ok': False, 'error': 'Suggestion introuvable.'}), 404)
    return jsonify({'ok': True})

@app.route('/api/donation-agencies', methods=['GET'])
def list_donation_agencies():
    db = get_db()
    try:
        cur = db_exec(db, 'SELECT slug, name, card_summary, body_text, hero_image_url, logo_url, gallery_json, donate_url, sort_order FROM donation_agencies ORDER BY sort_order ASC, id ASC')
        rows = cur.fetchall()
    except Exception:
        app.logger.exception('donation_agencies table missing or query error')
        return jsonify({'ok': False, 'error': 'Table donation_agencies indisponible.', 'items': []})
    out = []
    for r in rows:
        d = dict(r)
        raw_g = (d.pop('gallery_json', None) or '').strip()
        try:
            gallery = json.loads(raw_g) if raw_g else []
            if not isinstance(gallery, list):
                gallery = []
        except json.JSONDecodeError:
            gallery = []
        d['gallery'] = gallery
        out.append(d)
    return jsonify({'ok': True, 'items': out})

CHAT_HISTORY_TOPICS = [
    {
        'id': 'nakba',
        'title': 'La Nakba (1948)',
        'keywords': ('nakba', 'naqba', 'catastrophe', '1948', 'exode palestinien', 'deir yassin'),
        'reply': (
            "**La Nakba — « la catastrophe » (1948)**\n\n"
            "Entre décembre 1947 et 1949, environ **750 000 Palestinien·ne·s** (≈ 80 % de la population arabe de ce qui devint Israël) "
            "ont été expulsé·e·s ou forcé·e·s de fuir leurs foyers lors de la création de l'État d'Israël. "
            "Plus de **500 villages** ont été détruits ou vidés (Tantura, Lydda, Deir Yassin…). "
            "Le **massacre de Deir Yassin** (9 avril 1948), commis par les milices Irgoun et Lehi, a tué une centaine de villageois "
            "et accéléré la fuite massive par la peur.\n\n"
            "La Nakba n'est pas seulement un événement de 1948 : les réfugié·e·s et leurs descendant·e·s (aujourd'hui **~6 millions**) "
            "se voient toujours refuser le **droit au retour** reconnu par la résolution 194 de l'ONU."
        ),
        'chips': ('La Naksa (1967)', 'Première Intifada', 'Droit au retour', 'Ouvrir les News'),
    },
    {
        'id': 'naksa',
        'title': 'La Naksa (1967)',
        'keywords': ('naksa', 'guerre des six jours', 'six-day war', '1967', 'six days war'),
        'reply': (
            "**La Naksa — « le revers » (juin 1967)**\n\n"
            "Pendant la **guerre des Six Jours**, Israël occupe la **Cisjordanie**, **Jérusalem-Est**, la **bande de Gaza**, "
            "le **plateau du Golan** syrien et le **Sinaï** égyptien. Environ **300 000 Palestinien·ne·s** sont à nouveau déplacé·e·s.\n\n"
            "Depuis cette date, la Cisjordanie, Gaza et Jérusalem-Est sont sous **occupation militaire israélienne** — "
            "une occupation qualifiée d'illégale par la Cour internationale de Justice (avis du **19 juillet 2024**)."
        ),
        'chips': ('La Nakba (1948)', 'Les colonies', 'Le mur de séparation'),
    },
    {
        'id': 'first_intifada',
        'title': 'Première Intifada (1987-1993)',
        'keywords': ('première intifada', 'premiere intifada', 'first intifada', 'intifada des pierres', '1987'),
        'reply': (
            "**La Première Intifada — « le soulèvement » (décembre 1987 – 1993)**\n\n"
            "Soulèvement populaire palestinien principalement **non-violent** (grèves, désobéissance civile, jets de pierres) "
            "contre l'occupation. Déclenché le 9 décembre 1987 à Jabalia (Gaza) après la mort de quatre ouvriers palestiniens.\n\n"
            "Bilan : environ **1 200 Palestinien·ne·s tué·e·s** (dont plus de 200 enfants) et ~160 Israélien·ne·s. "
            "A conduit aux **accords d'Oslo** (1993), qui n'ont jamais débouché sur un État palestinien."
        ),
        'chips': ('Seconde Intifada', 'Accords d\'Oslo', 'Les colonies'),
    },
    {
        'id': 'second_intifada',
        'title': 'Seconde Intifada (2000-2005)',
        'keywords': ('seconde intifada', 'deuxième intifada', 'deuxieme intifada', 'second intifada', 'al-aqsa intifada', 'intifada al-aqsa', '2000 intifada'),
        'reply': (
            "**La Seconde Intifada — Intifada Al-Aqsa (septembre 2000 – février 2005)**\n\n"
            "Déclenchée après la visite provocatrice d'**Ariel Sharon** sur l'esplanade des Mosquées (28 septembre 2000). "
            "Affrontements armés, attentats et vastes opérations militaires israéliennes en Cisjordanie (opération *Bouclier Défensif*, "
            "bataille de Jénine en 2002).\n\n"
            "Bilan : environ **~4 000 Palestinien·ne·s** et **~1 000 Israélien·ne·s** tué·e·s. "
            "Marque le début de la construction du **mur de séparation** (déclaré illégal par la CIJ en 2004)."
        ),
        'chips': ('Le mur de séparation', 'Le blocus de Gaza', 'Première Intifada'),
    },
    {
        'id': 'blockade',
        'title': 'Le blocus de Gaza (2007-)',
        'keywords': ('blocus', 'blockade', 'siege', 'siège', 'prison à ciel ouvert', 'ciel ouvert', 'open-air prison'),
        'reply': (
            "**Le blocus de Gaza (depuis 2007)**\n\n"
            "Après la victoire du Hamas aux élections de 2006, Israël (avec l'Égypte) impose en **juin 2007** un blocus terrestre, "
            "maritime et aérien sur la bande de Gaza — **365 km²** pour **~2,3 millions** d'habitant·e·s, souvent qualifiée de "
            "**« plus grande prison à ciel ouvert du monde »**.\n\n"
            "Conséquences : pénuries chroniques d'électricité, d'eau potable, de médicaments ; 80 % de la population dépendante "
            "de l'aide humanitaire ; chômage massif ; restrictions sur les déplacements, la pêche et les importations."
        ),
        'chips': ('Guerre de 2008-2009', 'Marche du retour 2018', 'Faire un don'),
    },
    {
        'id': 'cast_lead',
        'title': 'Opération Plomb Durci (2008-2009)',
        'keywords': ('plomb durci', 'cast lead', '2008 gaza', '2009 gaza', 'guerre de gaza 2008'),
        'reply': (
            "**Opération « Plomb Durci » — guerre de Gaza (27 déc. 2008 – 18 janv. 2009)**\n\n"
            "Offensive israélienne de 22 jours. Bilan : environ **1 400 Palestinien·ne·s tué·e·s** (dont plus de 300 enfants) "
            "selon les ONG palestiniennes et israéliennes (B'Tselem), contre **13 Israélien·ne·s**.\n\n"
            "Le **rapport Goldstone** de l'ONU (2009) a conclu à des crimes de guerre commis par les deux parties, avec une "
            "responsabilité majeure israélienne (bombardement d'écoles de l'UNRWA, usage de phosphore blanc sur des zones civiles)."
        ),
        'chips': ('Bordure Protectrice 2014', 'Le blocus de Gaza', 'Ouvrir les News'),
    },
    {
        'id': 'protective_edge',
        'title': 'Bordure Protectrice (été 2014)',
        'keywords': ('bordure protectrice', 'protective edge', '2014 gaza', 'guerre 2014', 'guerre gaza 2014'),
        'reply': (
            "**Opération « Bordure Protectrice » (8 juillet – 26 août 2014)**\n\n"
            "51 jours de bombardements et d'incursion terrestre. Bilan ONU (OCHA) : "
            "**2 251 Palestinien·ne·s tué·e·s**, dont **~1 462 civils** et **551 enfants**, "
            "**~11 000 blessé·e·s** et **~100 000 sans-abri** ; **73 Israélien·ne·s** tué·e·s (dont 6 civils).\n\n"
            "Le quartier de **Chuja'iyya**, l'école de l'ONU de **Jabalia** et la plage où **4 enfants de la famille Bakr** "
            "jouaient au football figurent parmi les épisodes documentés."
        ),
        'chips': ('Plomb Durci 2008', 'Marche du retour 2018', 'Faire un don'),
    },
    {
        'id': 'great_march',
        'title': 'Marche du Retour (2018-2019)',
        'keywords': ('marche du retour', 'great march', 'great march of return', '2018 gaza', 'marche de retour'),
        'reply': (
            "**La Grande Marche du Retour (30 mars 2018 – décembre 2019)**\n\n"
            "Manifestations hebdomadaires, majoritairement **pacifiques**, le long de la clôture séparant Gaza d'Israël, "
            "pour réclamer le **droit au retour** et la levée du blocus.\n\n"
            "Bilan ONU : **~223 Palestinien·ne·s tué·e·s** par l'armée israélienne (dont 46 enfants, 2 journalistes, des paramédics "
            "comme **Razan al-Najjar**, 21 ans) et **~9 200 blessé·e·s par balles réelles**. Une commission d'enquête de l'ONU a "
            "conclu à de possibles crimes contre l'humanité."
        ),
        'chips': ('Le blocus de Gaza', 'Journalistes tués', 'Seconde Intifada'),
    },
    {
        'id': 'may_2021',
        'title': 'Mai 2021 — Sheikh Jarrah & Gaza',
        'keywords': ('sheikh jarrah', 'mai 2021', 'may 2021', 'gaza 2021', 'gardien des murs'),
        'reply': (
            "**Mai 2021 — Sheikh Jarrah, Al-Aqsa, Gaza**\n\n"
            "Les expulsions programmées de familles palestiniennes à **Sheikh Jarrah** (Jérusalem-Est) et la répression à "
            "la mosquée **Al-Aqsa** pendant le Ramadan déclenchent 11 jours de bombardements sur Gaza (opération *Gardien des murs*).\n\n"
            "Bilan : **~260 Palestinien·ne·s tué·e·s** (dont 67 enfants) et **13 Israélien·ne·s**. La tour Al-Jalaa, qui abritait "
            "les bureaux d'**Associated Press** et **Al Jazeera**, est détruite par une frappe israélienne."
        ),
        'chips': ('Al-Aqsa', 'Colonies & expulsions', 'Ouvrir les News'),
    },
    {
        'id': 'gaza_2023',
        'title': 'Gaza depuis octobre 2023',
        'keywords': ('octobre 2023', '7 octobre', 'october 2023', 'october 7', 'gaza war', 'guerre gaza 2023', 'guerre actuelle', 'guerre en cours', 'genocide', 'génocide'),
        'reply': (
            "**Guerre sur Gaza — depuis le 7 octobre 2023**\n\n"
            "Après l'attaque du Hamas du 7 octobre 2023 (~1 200 Israélien·ne·s tué·e·s, ~240 otages), Israël lance une offensive "
            "sans précédent sur la bande de Gaza.\n\n"
            "Bilan (ministère gazaoui de la Santé / OCHA, chiffres régulièrement actualisés) : **plus de 45 000 Palestinien·ne·s tué·e·s**, "
            "dont une majorité de femmes et d'enfants ; **~100 000 blessé·e·s** ; **~1,9 million** de déplacé·e·s internes ; "
            "la quasi-totalité des hôpitaux, universités et infrastructures d'eau endommagés ou détruits.\n\n"
            "Janvier 2024 : la **CIJ** ordonne à Israël de prendre toutes les mesures pour prévenir un **génocide** "
            "(affaire Afrique du Sud c. Israël). Novembre 2024 : la **CPI** émet des mandats d'arrêt contre Benjamin Netanyahou "
            "et Yoav Gallant pour crimes de guerre et crimes contre l'humanité."
        ),
        'chips': ('Al-Shifa', 'Al-Ahli', 'Famine à Gaza', 'Ouvrir les News'),
    },
    {
        'id': 'al_ahli',
        'title': 'Hôpital Al-Ahli (oct. 2023)',
        'keywords': ('al-ahli', 'al ahli', 'ahli baptist', 'hopital baptiste', 'hôpital baptiste', 'baptist hospital'),
        'reply': (
            "**Explosion à l'hôpital Al-Ahli (17 octobre 2023)**\n\n"
            "Une explosion massive dans la cour de l'hôpital arabe **Al-Ahli** (fondé en 1882, plus ancien hôpital de Gaza) "
            "tue **plusieurs centaines** de personnes, en majorité des déplacé·e·s qui s'y étaient réfugié·e·s. "
            "Les responsabilités restent disputées, mais l'attaque illustre l'effondrement du système de santé gazaoui "
            "sous les bombardements."
        ),
        'chips': ('Al-Shifa', 'Gaza depuis oct. 2023', 'Faire un don'),
    },
    {
        'id': 'al_shifa',
        'title': 'Hôpital Al-Shifa (2023-2024)',
        'keywords': ('al-shifa', 'al shifa', 'shifa hospital', 'hopital al-shifa', 'hôpital al-shifa'),
        'reply': (
            "**Raids sur l'hôpital Al-Shifa (novembre 2023 & mars 2024)**\n\n"
            "Plus grand hôpital de Gaza. En novembre 2023 puis mars-avril 2024, l'armée israélienne y mène des opérations "
            "militaires prolongées. Des patients, du personnel médical et des déplacé·e·s sont tué·e·s ou arrêté·e·s. "
            "Après le retrait israélien d'avril 2024, l'OMS documente des **fosses communes** sur le site et des destructions massives. "
            "Les hôpitaux sont pourtant des lieux protégés par le **droit international humanitaire** (Conventions de Genève)."
        ),
        'chips': ('Al-Ahli', 'Famine à Gaza', 'Journalistes tués'),
    },
    {
        'id': 'famine',
        'title': 'Famine à Gaza',
        'keywords': ('famine', 'faim', 'starvation', 'hunger', 'nourriture gaza', 'food gaza', 'ipc'),
        'reply': (
            "**La famine à Gaza**\n\n"
            "Depuis fin 2023, les agences de l'ONU (PAM, UNICEF, OMS) alertent sur une famine provoquée par la restriction "
            "drastique de l'aide humanitaire. Le cadre international **IPC** a classé une partie de Gaza en phase 5 "
            "(famine catastrophique) en 2024. Des dizaines d'enfants sont mort·e·s de malnutrition.\n\n"
            "Les rapporteur·e·s spéciaux·ales de l'ONU qualifient l'usage de la famine comme arme de guerre de **crime de guerre**."
        ),
        'chips': ('Gaza depuis oct. 2023', 'Faire un don', 'Organismes humanitaires'),
    },
    {
        'id': 'journalists',
        'title': 'Journalistes tués à Gaza',
        'keywords': ('journaliste', 'journalist', 'press', 'presse', 'shireen', 'abu akleh', 'cpj'),
        'reply': (
            "**Les journalistes tués**\n\n"
            "Gaza est devenu, selon le **CPJ** (Committee to Protect Journalists) et **RSF**, le **conflit le plus meurtrier "
            "de l'histoire pour la presse** : plus de **170 journalistes** tué·e·s depuis octobre 2023, en majorité palestinien·ne·s.\n\n"
            "Figures marquantes : **Shireen Abu Akleh** (Al Jazeera, tuée à Jénine le 11 mai 2022 par un tir israélien selon les enquêtes "
            "de l'ONU, du Washington Post et de CNN), **Wael Dahdouh** (Al Jazeera, famille tuée en oct. 2023), "
            "**Samer Abu Daqqa**, **Issam Abdallah** (Reuters)…"
        ),
        'chips': ('Marche du retour', 'Gaza depuis oct. 2023', 'Al-Jazeera'),
    },
    {
        'id': 'settlements',
        'title': 'Colonies et expulsions',
        'keywords': ('colon', 'colons', 'colonie', 'colonies', 'settler', 'settlement', 'hébron', 'hebron', 'silwan'),
        'reply': (
            "**Les colonies israéliennes**\n\n"
            "Plus de **700 000 colons israéliens** vivent en Cisjordanie et à Jérusalem-Est occupées, dans **~280 colonies** et "
            "avant-postes. Ces implantations sont **illégales au regard du droit international** (4ᵉ Convention de Genève, "
            "résolution 2334 du Conseil de sécurité de 2016, avis consultatif de la CIJ de juillet 2024).\n\n"
            "Elles s'accompagnent d'expulsions (Sheikh Jarrah, Silwan, Masafer Yatta), de démolitions de maisons et de violences "
            "de colons — en forte hausse depuis octobre 2023."
        ),
        'chips': ('Le mur de séparation', 'Sheikh Jarrah', 'La Naksa 1967'),
    },
    {
        'id': 'wall',
        'title': 'Le mur de séparation',
        'keywords': ('mur', 'wall', 'séparation', 'separation barrier', 'apartheid wall'),
        'reply': (
            "**Le mur de séparation (depuis 2002)**\n\n"
            "Construit par Israël en Cisjordanie à partir de 2002, long de **~700 km** (deux fois la ligne verte), il coupe des "
            "villages, isole des familles, confisque des terres et de l'eau.\n\n"
            "La **Cour internationale de Justice** a rendu en **2004** un avis consultatif déclarant sa construction **contraire "
            "au droit international**. Israël n'a pas appliqué cet avis."
        ),
        'chips': ('Colonies & expulsions', 'La Naksa 1967', 'Avis CIJ 2024'),
    },
    {
        'id': 'right_of_return',
        'title': 'Droit au retour',
        'keywords': ('droit au retour', 'right of return', 'réfugiés', 'refugies', 'refugees', 'unrwa', '194'),
        'reply': (
            "**Le droit au retour**\n\n"
            "Reconnu par la **résolution 194 (III)** de l'Assemblée générale de l'ONU (décembre 1948), il stipule que les "
            "réfugié·e·s palestinien·ne·s doivent pouvoir rentrer chez eux et être indemnisé·e·s.\n\n"
            "Aujourd'hui, **~6 millions** de Palestinien·ne·s sont enregistré·e·s comme réfugié·e·s auprès de l'**UNRWA** "
            "(Jordanie, Liban, Syrie, Cisjordanie, Gaza). C'est l'un des piliers de la revendication palestinienne — "
            "et l'un des trois objectifs du mouvement **BDS**."
        ),
        'chips': ('La Nakba 1948', 'Mouvement BDS', 'Faire un don'),
    },
    {
        'id': 'bds',
        'title': 'Mouvement BDS',
        'keywords': ('bds', 'boycott divestment', 'boycott désinvestissement', 'désinvestissement', 'desinvestissement'),
        'reply': (
            "**Le mouvement BDS (Boycott, Désinvestissement, Sanctions)**\n\n"
            "Lancé le **9 juillet 2005** par plus de 170 organisations de la société civile palestinienne. Inspiré du boycott "
            "anti-apartheid de l'Afrique du Sud, il appelle à la pression économique et culturelle non-violente jusqu'à ce "
            "qu'Israël :\n\n"
            "1. mette fin à l'occupation et démantèle le mur ;\n"
            "2. reconnaisse l'égalité pleine des citoyen·ne·s palestinien·ne·s d'Israël ;\n"
            "3. respecte le **droit au retour** des réfugié·e·s (résolution 194).\n\n"
            "C'est la base méthodologique du travail d'Amenah."
        ),
        'page': 'boycott',
        'chips': ('Voir les marques à boycotter', 'À propos du projet', 'Faire un don'),
    },
    {
        'id': 'icj_icc',
        'title': 'CIJ & CPI',
        'keywords': ('cij', 'icj', 'cour internationale', 'cpi', 'icc', 'cour pénale', 'cour penale', 'mandat arrêt', 'mandat arret'),
        'reply': (
            "**Les juridictions internationales**\n\n"
            "• **CIJ (Cour internationale de Justice)** — 26 janvier 2024 : ordre provisoire à Israël de prévenir un **génocide** à Gaza "
            "(affaire Afrique du Sud c. Israël). 19 juillet 2024 : avis consultatif déclarant l'occupation **illégale** et appelant "
            "à son démantèlement.\n\n"
            "• **CPI (Cour pénale internationale)** — 21 novembre 2024 : mandats d'arrêt contre **Benjamin Netanyahou** et **Yoav Gallant** "
            "pour crimes de guerre et crimes contre l'humanité (famine utilisée comme arme, attaques contre les civils), ainsi que "
            "contre un dirigeant du Hamas."
        ),
        'chips': ('Gaza depuis oct. 2023', 'Mouvement BDS', 'Ouvrir les News'),
    },
    {
        'id': 'overview',
        'title': 'Vue d\'ensemble histoire Gaza / Palestine',
        'keywords': (
            'histoire', 'history', 'événement', 'evenement', 'événements', 'evenements', 'events',
            'tragédie', 'tragedie', 'tragedy', 'tragedies', 'massacre', 'occupation',
            'que s\'est-il passé', 'que s est il passe', 'what happened', 'palestine history', 'gaza history',
            'raconte', 'explique'
        ),
        'reply': (
            "**Histoire de la Palestine / Gaza — repères**\n\n"
            "Demande-moi des détails sur n'importe lequel de ces chapitres :\n\n"
            "• **1948** — La Nakba\n"
            "• **1967** — La Naksa et l'occupation\n"
            "• **1987-93** — Première Intifada\n"
            "• **2000-05** — Seconde Intifada (Al-Aqsa)\n"
            "• **2007** — Début du blocus de Gaza\n"
            "• **2008-09** — Guerre « Plomb Durci »\n"
            "• **2014** — Guerre « Bordure Protectrice »\n"
            "• **2018-19** — Grande Marche du Retour\n"
            "• **Mai 2021** — Sheikh Jarrah & Gaza\n"
            "• **Depuis oct. 2023** — Guerre actuelle, famine, CIJ/CPI\n\n"
            "Tu peux aussi me demander les **dernières actualités** pour des nouvelles en temps réel."
        ),
        'chips': ('La Nakba 1948', 'Blocus de Gaza', 'Gaza depuis oct. 2023', 'Dernières actualités'),
    },
    {
        'id': 'latest_news',
        'title': 'Dernières actualités',
        'keywords': (
            'dernières nouvelles', 'dernieres nouvelles', 'latest news', 'derniere actu', 'dernière actu',
            'dernières actualités', 'dernieres actualites', 'en ce moment', 'aujourd\'hui', "aujourd hui",
            'what\'s happening', 'whats happening', 'news now', 'actu du jour', 'top news'
        ),
        'reply': '',
        'dynamic': 'latest_news',
        'chips': ('Ouvrir les News', 'Gaza depuis oct. 2023', 'Faire un don'),
    },
]

CHAT_INTENTS = [
    {
        'id': 'greet',
        'keywords': ('salam', 'salaam', 'assalam', 'hello', 'hi ', 'bonjour', 'bonsoir', 'hey', 'coucou', 'salut'),
        'reply': "Salam 👋 Je suis l'assistant Amenah. Je peux t'aider sur le boycott, les alternatives éthiques, les dons, les actualités ou l'histoire de la Palestine / Gaza. Que cherches-tu ?",
        'chips': ('Voir les marques à boycotter', 'Histoire de la Palestine', 'Dernières actualités', 'Faire un don'),
    },
    {
        'id': 'boycott',
        'keywords': ('boycott', 'marque', 'marques', 'brand', 'liste des marques', 'companies', 'entreprise', 'à éviter', 'a eviter', 'eviter'),
        'reply': "La page **Boycott** répertorie les marques identifiées comme finançant ou soutenant l'occupation. Ouvre-la pour explorer par catégorie, ou dis-moi le nom d'une marque et je la cherche pour toi.",
        'page': 'boycott',
        'chips': ('Ouvrir la page Boycott', 'Chercher une marque', 'Voir les alternatives'),
    },
    {
        'id': 'alternative',
        'keywords': ('alternative', 'alternatives', 'remplacer', 'remplacement', 'éthique', 'ethique', 'que acheter', 'que buy'),
        'reply': "La page **Alternatives** propose des produits éthiques pour remplacer les marques boycottées. Chaque alternative indique sa catégorie et, si disponible, un lien vers la source.",
        'page': 'alt',
        'chips': ('Ouvrir les alternatives', 'Voir le boycott', 'Proposer une alternative'),
    },
    {
        'id': 'donation_list',
        'keywords': (
            'liste des organismes', 'liste organismes', 'list donation', 'list ong', 'quels organismes',
            'quels ong', 'which ngo', 'which ong', 'which charities', 'which charity',
            'où donner', 'ou donner', 'where to donate', 'à qui donner', 'a qui donner',
            'voir les organismes', 'voir les ong', 'see donation', 'see charities',
            'all agencies', 'toutes les agences', 'tous les organismes',
        ),
        'reply': '',
        'dynamic': 'donation_list',
        'page': 'donation',
        'chips': ('Ouvrir la page Donation', 'Suggérer un organisme', 'Famine à Gaza'),
    },
    {
        'id': 'donation',
        'keywords': ('don', 'donner', 'donation', 'donate', 'aider gaza', 'soutenir', 'charit', 'ong'),
        'reply': "La page **Donation** liste des organismes reconnus que tu peux soutenir (aide humanitaire, santé, nourriture, éducation). Amenah ne collecte aucun argent — les liens ouvrent directement les sites officiels. Tu peux aussi me demander la **liste complète** ou des précisions sur un organisme précis (UNRWA, PAM, Islamic Relief, Solidarités International…).",
        'page': 'donation',
        'chips': ('Liste complète des organismes', 'Ouvrir la page Donation', 'Suggérer un organisme'),
    },
    {
        'id': 'news',
        'keywords': ('news', 'actu', 'actualité', 'actualite', 'gaza news', 'journal', 'information'),
        'reply': "La page **News** agrège les dernières actualités (BBC, Al Jazeera) avec un filtre sur Gaza, la Palestine et la région. Le flux est mis à jour environ toutes les 5 minutes.",
        'page': 'news',
        'chips': ('Ouvrir les News', 'À propos du projet'),
    },
    {
        'id': 'add',
        'keywords': ('ajouter', 'suggérer', 'suggerer', 'proposer', 'add', 'soumettre', 'submit', 'nouvelle marque'),
        'reply': "Tu peux proposer un produit (à boycotter ou une alternative) via le bouton **+ajouter un produit** en haut à droite. L'équipe valide ensuite la suggestion avant publication.",
        'page': 'add',
        'chips': ('Ouvrir le formulaire', 'Voir les marques existantes'),
    },
    {
        'id': 'scan',
        'keywords': ('scan', 'scanner', 'code-barre', 'code barre', 'ean', 'qr', 'barcode'),
        'reply': "Utilise le bouton **scanner** (icône QR en bas à gauche) pour scanner un code-barres avec ta caméra. Tu peux aussi saisir le code manuellement si la caméra n'est pas disponible.",
        'chips': ('Voir les marques à boycotter', 'Voir les alternatives'),
    },
    {
        'id': 'about',
        'keywords': ('about', 'à propos', 'a propos', 'pourquoi', 'bds', 'qui', 'amenah', 'projet', 'mission'),
        'reply': "**Amenah** (ةنيمأ — « digne de confiance ») est un projet indépendant et non commercial qui offre une information claire et sourcée sur les marques profitant de l'occupation, et propose des alternatives éthiques. Inspiré du mouvement BDS.",
        'page': 'about',
        'chips': ('Pourquoi boycotter ?', 'Voir les alternatives'),
    },
    {
        'id': 'feedback',
        'keywords': ('feedback', 'contact', 'bug', 'erreur', 'message', 'écrire', 'ecrire'),
        'reply': "Tu peux envoyer un retour via le bouton **Feedback** (coin inférieur). Les messages sont lus par l'équipe et peuvent être transmis par e-mail.",
        'chips': ('Ouvrir le formulaire', 'À propos du projet'),
    },
    {
        'id': 'thanks',
        'keywords': ('merci', 'thanks', 'thank you', 'shukran', 'choukran'),
        'reply': "De rien — ton engagement compte. 🌱 N'hésite pas si tu as d'autres questions.",
        'chips': ('Voir les marques à boycotter', 'Faire un don'),
    },
]

CHAT_DEFAULT_CHIPS = ('Marques à boycotter', 'Histoire de la Palestine', 'Dernières actualités', 'Faire un don', 'À propos')

def _chat_get_cached_news(limit: int = 5):
    payload = _gaza_news_cache.get('payload')
    now = time.monotonic()
    fresh = payload and (now - _gaza_news_cache.get('t', 0)) < GAZA_NEWS_TTL_SEC
    if not fresh:
        try:
            items = _merge_gaza_news()
            payload = {'ok': True, 'items': items}
            _gaza_news_cache['t'] = now
            _gaza_news_cache['payload'] = payload
        except Exception:
            app.logger.exception('chat latest_news')
            payload = _gaza_news_cache.get('payload')
    if not payload or not payload.get('ok'):
        return []
    return (payload.get('items') or [])[:limit]

def _chat_format_latest_news():
    items = _chat_get_cached_news(5)
    if not items:
        return (
            "Je n'arrive pas à récupérer le flux d'actualités pour le moment. "
            "Ouvre la page **News** pour réessayer — les sources (BBC, Al Jazeera) peuvent être momentanément indisponibles."
        )
    lines = ["**Dernières actualités (BBC & Al Jazeera)** :\n"]
    for it in items:
        title = (it.get('title') or '').strip()
        link = (it.get('link') or '').strip()
        src = (it.get('source') or '').strip()
        if not title or not link:
            continue
        suffix = f" _({src})_" if src else ''
        lines.append(f"• [{title}]({link}){suffix}")
    lines.append("\nOuvre la page **News** pour la liste complète.")
    return '\n'.join(lines)

_CHAT_DONATION_STOPWORDS = {
    'comment', 'comme', 'donner', 'donate', 'aider', 'help', 'parler', 'parle', 'dire', 'dis', 'explique', 'explain',
    'sur', 'pour', 'dans', 'avec', 'chez', 'vers', 'quel', 'quels', 'quelle', 'quelles', 'what', 'where', 'which',
    'sont', 'est', 'les', 'des', 'une', 'un', 'de', 'du', 'la', 'le', 'l', 'ou', 'où', 'to', 'the', 'and', 'or',
    'don', 'dons', 'donation', 'donations', 'ong', 'ongs', 'agence', 'agency', 'organisme', 'organismes', 'organization',
    'info', 'infos', 'information', 'about', 'a', 'à', 'en', 'au', 'aux', 'that', 'this', 'from', 'by',
    'gaza', 'palestine', 'palestinien', 'palestiniens', 'palestinian',
}

def _chat_ascii_fold(text: str) -> str:
    if not text:
        return ''
    s = unicodedata.normalize('NFKD', str(text))
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()

def _chat_extract_tokens(text: str):
    base = re.sub(r'[^\w\s-]', ' ', _chat_ascii_fold(text or ''), flags=re.UNICODE)
    raw = [t.strip('-_') for t in base.split() if t.strip('-_')]
    return [t for t in raw if len(t) >= 3 and t not in _CHAT_DONATION_STOPWORDS]

def _chat_search_donations(db, query: str, limit: int = 4):
    q = (query or '').strip()
    if len(q) < 2:
        return []
    try:
        cur = db_exec(
            db,
            'SELECT slug, name, card_summary, donate_url FROM donation_agencies ORDER BY sort_order ASC, id ASC'
        )
        rows = [dict(r) for r in cur.fetchall()]
    except Exception:
        app.logger.exception('chat search donation_agencies')
        return []
    needle = _chat_ascii_fold(q)
    scored = []
    direct = []
    for r in rows:
        hay = _chat_ascii_fold((r.get('name') or '') + ' ' + (r.get('slug') or ''))
        if needle and needle in hay:
            direct.append(r)
    if direct:
        return direct[:limit]
    tokens = _chat_extract_tokens(q)
    if not tokens:
        return []
    for r in rows:
        hay = _chat_ascii_fold((r.get('name') or '') + ' ' + (r.get('slug') or ''))
        score = sum((1 for t in tokens if t in hay))
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for (_, r) in scored[:limit]]

def _chat_list_donations(db):
    try:
        cur = db_exec(
            db,
            'SELECT name, card_summary, donate_url FROM donation_agencies ORDER BY sort_order ASC, id ASC'
        )
        rows = [dict(r) for r in cur.fetchall()]
    except Exception:
        app.logger.exception('chat list donation_agencies')
        return []
    return rows

def _chat_format_donation_agency(row):
    name = (row.get('name') or '').strip()
    summary = (row.get('card_summary') or '').strip()
    url = (row.get('donate_url') or '').strip()
    parts = [f"💛 **{name}**"]
    if summary:
        parts.append(summary)
    if url and (url.startswith('http://') or url.startswith('https://')):
        parts.append(f"[→ Faire un don sur le site officiel]({url})")
    return '\n'.join(parts)

def _chat_format_donation_list(db):
    rows = _chat_list_donations(db)
    if not rows:
        return (
            "La liste des organismes n'est pas disponible pour le moment. "
            "Ouvre la page **Donation** pour la voir."
        )
    lines = [f"**Organismes référencés sur Amenah** ({len(rows)}) :\n"]
    for r in rows:
        name = (r.get('name') or '').strip()
        url = (r.get('donate_url') or '').strip()
        summary = (r.get('card_summary') or '').strip()
        if url and (url.startswith('http://') or url.startswith('https://')):
            lines.append(f"• [**{name}**]({url}) — {summary}" if summary else f"• [**{name}**]({url})")
        else:
            lines.append(f"• **{name}** — {summary}" if summary else f"• **{name}**")
    lines.append("\nTu peux me demander des précisions sur l'un·e d'entre eux (ex. « parle-moi d'UNRWA »).")
    return '\n'.join(lines)

def _chat_search_products(db, query: str, limit: int = 5):
    q = (query or '').strip()
    if len(q) < 2:
        return ([], [])
    like = f'%{q}%'
    boycotts = []
    alternatives = []
    try:
        cur = db_exec(db, 'SELECT nom, categorie FROM produits WHERE LOWER(nom) LIKE LOWER(?) ORDER BY id DESC LIMIT ?', (like, limit))
        boycotts = [dict(r) for r in cur.fetchall()]
    except Exception:
        app.logger.exception('chat search produits')
    try:
        cur = db_exec(db, 'SELECT nom, categorie FROM produit_alternatives WHERE LOWER(nom) LIKE LOWER(?) ORDER BY id DESC LIMIT ?', (like, limit))
        alternatives = [dict(r) for r in cur.fetchall()]
    except Exception:
        app.logger.exception('chat search alternatives')
    return (boycotts, alternatives)

def _chat_match_in(msg_norm: str, entries):
    for entry in entries:
        for kw in entry['keywords']:
            if kw in msg_norm:
                return entry
    return None

def _chat_match_intent(msg: str):
    q = ' ' + (msg or '').lower().strip() + ' '
    history = _chat_match_in(q, CHAT_HISTORY_TOPICS)
    if history:
        return history
    return _chat_match_in(q, CHAT_INTENTS)

def _chat_resolve_reply(intent, db=None):
    dyn = intent.get('dynamic')
    if dyn == 'latest_news':
        return _chat_format_latest_news()
    if dyn == 'donation_list':
        return _chat_format_donation_list(db if db is not None else get_db())
    return intent.get('reply') or ''

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    if not message:
        return (jsonify({'ok': False, 'error': 'Message vide.'}), 400)
    if len(message) > 600:
        message = message[:600]
    reply_parts = []
    chips = []
    page = None
    db = get_db()
    intent = _chat_match_intent(message)
    if intent:
        text = _chat_resolve_reply(intent, db=db)
        if text:
            reply_parts.append(text)
        page = intent.get('page')
        chips = list(intent.get('chips') or [])
    (boy, alt) = _chat_search_products(db, message)
    if boy or alt:
        if boy:
            names = ', '.join((f"**{b['nom']}**" + (f" ({b['categorie']})" if b.get('categorie') else '') for b in boy[:5]))
            reply_parts.append(f"🛑 Marque(s) à boycotter correspondant à ta recherche : {names}.")
            if not page:
                page = 'boycott'
        if alt:
            names = ', '.join((f"**{a['nom']}**" + (f" ({a['categorie']})" if a.get('categorie') else '') for a in alt[:5]))
            reply_parts.append(f"🌱 Alternative(s) possible(s) : {names}.")
            if not page:
                page = 'alt'
        if not chips:
            chips = ['Voir le boycott', 'Voir les alternatives']
    donation_hits = _chat_search_donations(db, message)
    if donation_hits and not (intent and intent.get('id') == 'donation_list'):
        for row in donation_hits[:3]:
            reply_parts.append(_chat_format_donation_agency(row))
        if not page:
            page = 'donation'
        if not chips:
            chips = ['Ouvrir la page Donation', 'Liste complète des organismes']
    if not reply_parts:
        reply_parts.append("Je n'ai pas trouvé de réponse directe. Essaie un mot-clé comme *boycott*, *alternative*, *don*, *scanner*, *histoire Palestine* ou le nom d'une marque / d'un organisme.")
        chips = list(CHAT_DEFAULT_CHIPS)
    return jsonify({'ok': True, 'reply': '\n\n'.join(reply_parts), 'chips': chips, 'page': page})

@app.route('/api/feedback', methods=['POST'])
def add_feedback():
    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    if not message:
        return (jsonify({'ok': False, 'error': 'Message is required.'}), 400)
    now = datetime.utcnow().isoformat() + 'Z'
    db = get_db()
    cur = db_exec(db, 'INSERT INTO feedback (message, created_at) VALUES (?, ?)', (message, now))
    db.commit()
    fid = cur.lastrowid
    email_sent = _send_feedback_email(message, fid, now)
    return jsonify({'ok': True, 'id': fid, 'email_sent': email_sent})

def _run_server():
    port = int(os.environ.get('PORT', '8080'))
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    print(f'\n  → Ouvre le site : http://{host}:{port}/')
    if USE_MYSQL:
        dbn = (os.environ.get('MYSQL_DATABASE') or os.environ.get('MYSQL_DB') or 'amenah').strip()
        print(f'  → Base de données : MySQL « {dbn} » sur {MYSQL_HOST}\n')
    else:
        if MYSQL_HOST:
            print(f'  → AMENAH_USE_SQLITE=1 : utilisation de SQLite malgré MYSQL_HOST.\n  → Base de données : SQLite (fichier {DATABASE})\n')
        else:
            print(f'  → Base de données : SQLite (fichier {DATABASE})\n')
        print('     Les suggestions vont dans ce fichier, pas dans MySQL/phpMyAdmin.\n     Pour MySQL : importez sql/schema_mysql.sql, puis définissez MYSQL_HOST, etc.\n')
    try:
        app.run(debug=True, host=host, port=port, use_reloader=True)
    except OSError as e:
        if getattr(e, 'winerror', None) == 10048 or 'address' in str(e).lower():
            print('\n  Le port', port, 'est déjà utilisé. Ferme l’autre terminal Flask, ou lance avec une autre porte, par ex. :\n     set PORT=5000\n     python app.py\n')
        raise
if __name__ == '__main__':
    _run_server()
