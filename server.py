"""
DEVMARKET - Developer Marketplace Platform
Backend: Python Flask
Author: Devmarket Engineering
"""

from flask import Flask, request, jsonify, session
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import bcrypt
import jwt
import datetime
import uuid
import cloudinary
import cloudinary.uploader
import cloudinary.api
import requests
import json
import re
from functools import wraps

# ─────────────────────────────────────────────
# CONFIGURATION (plain text as requested)
# ─────────────────────────────────────────────

# PostgreSQL Database
DB_URL = "postgresql://extravagantmeals_user:V9EijyegMbl2Hcwn0Ajaj61ROYlXnOpH@dpg-d7ktnq8sfn5c73cqeto0-a.frankfurt-postgres.render.com/extravagantmeals"

# JWT Secret
JWT_SECRET = "devmarket_jwt_secret_key_2024_multibillion"

# Cloudinary
CLOUDINARY_CLOUD_NAME = "ddusfl7pi"
CLOUDINARY_API_KEY = "599965682593626"
CLOUDINARY_API_SECRET = "pUcb90_1jtv-rDlHXRRsfDcBK5k"

# Mistral AI
MISTRAL_API_KEY = "yjvknUyDmAP6SKLQAUtqM5FH65cP69Id"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Tavily Search
TAVILY_API_KEY = "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"
TAVILY_API_URL = "https://api.tavily.com/search"

# ─────────────────────────────────────────────
# CLOUDINARY SETUP
# ─────────────────────────────────────────────
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

# ─────────────────────────────────────────────
# FLASK APP
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = JWT_SECRET

# Allow requests from any origin (GitHub Pages, file://, custom domains, etc.)
CORS(app, resources={r"/api/*": {
    "origins": "*",
    "supports_credentials": False,
    "allow_headers": ["Content-Type", "Authorization"],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
}})

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response


# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
def get_db():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True  # Each statement auto-commits; simpler for this architecture
    return conn


def init_db():
    """Initialize all Devmarket database tables."""
    conn = get_db()
    cur = conn.cursor()

    # Users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devmarket_users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name VARCHAR(100),
            bio TEXT,
            avatar_url TEXT,
            cover_url TEXT,
            github_url TEXT,
            website_url TEXT,
            twitter_url TEXT,
            linkedin_url TEXT,
            skills TEXT[],
            role VARCHAR(20) DEFAULT 'buyer',
            is_verified BOOLEAN DEFAULT FALSE,
            reputation_score INTEGER DEFAULT 0,
            total_sales INTEGER DEFAULT 0,
            total_purchases INTEGER DEFAULT 0,
            joined_at TIMESTAMP DEFAULT NOW(),
            last_active TIMESTAMP DEFAULT NOW(),
            is_online BOOLEAN DEFAULT FALSE,
            location VARCHAR(100),
            badge VARCHAR(50) DEFAULT 'newcomer'
        )
    """)

    # Categories
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devmarket_categories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            icon TEXT,
            color VARCHAR(20),
            product_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Products
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devmarket_products (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            seller_id UUID REFERENCES devmarket_users(id) ON DELETE CASCADE,
            category_id UUID REFERENCES devmarket_categories(id),
            title VARCHAR(255) NOT NULL,
            slug VARCHAR(255) UNIQUE NOT NULL,
            short_description TEXT,
            description TEXT NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            currency VARCHAR(10) DEFAULT 'USD',
            product_type VARCHAR(50) NOT NULL,
            tags TEXT[],
            tech_stack TEXT[],
            images TEXT[],
            demo_url TEXT,
            repo_url TEXT,
            documentation_url TEXT,
            live_preview_url TEXT,
            version VARCHAR(20) DEFAULT '1.0.0',
            license VARCHAR(50) DEFAULT 'MIT',
            file_size VARCHAR(20),
            downloads INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            is_featured BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            is_approved BOOLEAN DEFAULT TRUE,
            rating_avg DECIMAL(3,2) DEFAULT 0,
            review_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Orders (tracking without financial processing)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devmarket_orders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            buyer_id UUID REFERENCES devmarket_users(id),
            seller_id UUID REFERENCES devmarket_users(id),
            product_id UUID REFERENCES devmarket_products(id),
            status VARCHAR(30) DEFAULT 'pending_contact',
            negotiated_price DECIMAL(10,2),
            notes TEXT,
            buyer_confirmed BOOLEAN DEFAULT FALSE,
            seller_confirmed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Conversations
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devmarket_conversations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            participant_one UUID REFERENCES devmarket_users(id),
            participant_two UUID REFERENCES devmarket_users(id),
            product_id UUID REFERENCES devmarket_products(id),
            order_id UUID REFERENCES devmarket_orders(id),
            last_message TEXT,
            last_message_at TIMESTAMP DEFAULT NOW(),
            unread_count_one INTEGER DEFAULT 0,
            unread_count_two INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Messages
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devmarket_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID REFERENCES devmarket_conversations(id) ON DELETE CASCADE,
            sender_id UUID REFERENCES devmarket_users(id),
            content TEXT NOT NULL,
            message_type VARCHAR(20) DEFAULT 'text',
            attachment_url TEXT,
            is_read BOOLEAN DEFAULT FALSE,
            is_deleted BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Reviews
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devmarket_reviews (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            product_id UUID REFERENCES devmarket_products(id) ON DELETE CASCADE,
            reviewer_id UUID REFERENCES devmarket_users(id),
            rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
            title VARCHAR(255),
            content TEXT NOT NULL,
            helpful_votes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # AI Chat Sessions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devmarket_ai_chats (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES devmarket_users(id),
            session_id VARCHAR(100) NOT NULL,
            messages JSONB DEFAULT '[]',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Product Likes/Bookmarks
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devmarket_bookmarks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES devmarket_users(id),
            product_id UUID REFERENCES devmarket_products(id),
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, product_id)
        )
    """)

    # Notifications
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devmarket_notifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES devmarket_users(id),
            type VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            body TEXT,
            link TEXT,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Portfolio / Showcase items
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devmarket_portfolio (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES devmarket_users(id),
            title VARCHAR(255) NOT NULL,
            description TEXT,
            image_url TEXT,
            project_url TEXT,
            tech_stack TEXT[],
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Blog / Dev Articles
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devmarket_articles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            author_id UUID REFERENCES devmarket_users(id),
            title VARCHAR(500) NOT NULL,
            slug VARCHAR(500) UNIQUE NOT NULL,
            content TEXT NOT NULL,
            cover_image TEXT,
            tags TEXT[],
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            is_published BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Job Board
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devmarket_jobs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            poster_id UUID REFERENCES devmarket_users(id),
            title VARCHAR(255) NOT NULL,
            company VARCHAR(100),
            description TEXT NOT NULL,
            job_type VARCHAR(50),
            location VARCHAR(100),
            salary_range VARCHAR(100),
            tech_stack TEXT[],
            is_remote BOOLEAN DEFAULT TRUE,
            is_active BOOLEAN DEFAULT TRUE,
            applications_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Seed categories
    cur.execute("""
        INSERT INTO devmarket_categories (name, slug, description, icon, color) VALUES
        ('APIs & Integrations', 'apis', 'REST, GraphQL, WebSocket APIs and third-party integrations', '🔌', '#6366f1'),
        ('UI Templates', 'ui-templates', 'React, Vue, Angular templates and component libraries', '🎨', '#ec4899'),
        ('Developer Tools', 'dev-tools', 'CLI tools, extensions, productivity boosters', '🔧', '#f59e0b'),
        ('Scripts & Bots', 'scripts', 'Automation scripts, bots, crawlers, and schedulers', '🤖', '#10b981'),
        ('Datasets', 'datasets', 'Curated datasets for ML, analytics, and research', '📊', '#3b82f6'),
        ('Plugins & Extensions', 'plugins', 'Browser extensions, IDE plugins, CMS plugins', '🧩', '#8b5cf6'),
        ('Mobile SDKs', 'mobile', 'iOS, Android, React Native, Flutter kits', '📱', '#ef4444'),
        ('Security Tools', 'security', 'Pen-testing tools, auth libraries, encryption modules', '🔐', '#f97316'),
        ('AI & ML Models', 'ai-ml', 'Pre-trained models, fine-tuned LLMs, ML pipelines', '🧠', '#06b6d4'),
        ('DevOps & Infra', 'devops', 'Docker configs, Kubernetes charts, CI/CD pipelines', '⚙️', '#84cc16'),
        ('Blockchain & Web3', 'web3', 'Smart contracts, DeFi tools, NFT utilities', '⛓️', '#a855f7'),
        ('Game Dev Assets', 'game-dev', 'Unity assets, Unreal plugins, game frameworks', '🎮', '#f43f5e')
        ON CONFLICT (slug) DO NOTHING
    """)

    cur.close()
    conn.close()
    print("✅ Devmarket database initialized successfully")


# ─────────────────────────────────────────────
# AUTH MIDDLEWARE
# ─────────────────────────────────────────────
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        if not token:
            return jsonify({'error': 'Authentication token required'}), 401
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated


def optional_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user_id = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                current_user_id = data['user_id']
            except Exception:
                pass
        return f(current_user_id, *args, **kwargs)
    return decorated


def generate_token(user_id):
    payload = {
        'user_id': str(user_id),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30),
        'iat': datetime.datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = text.strip('-')
    return text


# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip().lower()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()

    if not all([username, email, password, full_name]):
        return jsonify({'error': 'All fields are required'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """INSERT INTO devmarket_users (username, email, password_hash, full_name, role)
               VALUES (%s, %s, %s, %s, 'seller')
               RETURNING id, username, email, full_name, role, avatar_url, badge, reputation_score, is_verified""",
            (username, email, password_hash, full_name)
        )
        user = dict(cur.fetchone())
        user['id'] = str(user['id'])
        token = generate_token(user['id'])
        return jsonify({'token': token, 'user': user}), 201
    except psycopg2.IntegrityError as e:
        if 'username' in str(e):
            return jsonify({'error': 'Username already taken'}), 409
        if 'email' in str(e):
            return jsonify({'error': 'Email already registered'}), 409
        return jsonify({'error': 'Registration failed'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('identifier', '').strip().lower()
    password = data.get('password', '')

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """SELECT * FROM devmarket_users WHERE email = %s OR username = %s""",
            (identifier, identifier)
        )
        user = cur.fetchone()
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401

        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({'error': 'Invalid credentials'}), 401

        cur.execute("UPDATE devmarket_users SET last_active=NOW(), is_online=TRUE WHERE id=%s", (user['id'],))
        token = generate_token(user['id'])

        safe_user = {
            'id': str(user['id']),
            'username': user['username'],
            'email': user['email'],
            'full_name': user['full_name'],
            'avatar_url': user['avatar_url'],
            'role': user['role'],
            'badge': user['badge'],
            'reputation_score': user['reputation_score'],
            'is_verified': user['is_verified'],
            'total_sales': user['total_sales'],
            'location': user['location']
        }
        return jsonify({'token': token, 'user': safe_user})
    finally:
        cur.close()
        conn.close()


@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_me(current_user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT id, username, email, full_name, bio, avatar_url, cover_url,
                   github_url, website_url, twitter_url, linkedin_url, skills,
                   role, is_verified, reputation_score, total_sales, total_purchases,
                   joined_at, last_active, location, badge
            FROM devmarket_users WHERE id = %s
        """, (current_user_id,))
        user = cur.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        user = dict(user)
        user['id'] = str(user['id'])
        return jsonify({'user': user})
    finally:
        cur.close()
        conn.close()


@app.route('/api/auth/update-profile', methods=['PUT'])
@token_required
def update_profile(current_user_id):
    data = request.get_json()
    allowed = ['full_name', 'bio', 'github_url', 'website_url', 'twitter_url', 'linkedin_url', 'location', 'skills']
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'error': 'Nothing to update'}), 400

    set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
    values = list(updates.values()) + [current_user_id]

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(f"UPDATE devmarket_users SET {set_clause} WHERE id = %s", values)
        return jsonify({'message': 'Profile updated'})
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# UPLOAD ROUTES (Cloudinary)
# ─────────────────────────────────────────────
@app.route('/api/upload/image', methods=['POST'])
@token_required
def upload_image(current_user_id):
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    folder = request.form.get('folder', 'devmarket/general')
    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            transformation=[{'quality': 'auto', 'fetch_format': 'auto'}]
        )
        return jsonify({
            'url': result['secure_url'],
            'public_id': result['public_id'],
            'width': result.get('width'),
            'height': result.get('height')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload/avatar', methods=['POST'])
@token_required
def upload_avatar(current_user_id):
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    try:
        result = cloudinary.uploader.upload(
            file,
            folder='devmarket/avatars',
            transformation=[
                {'width': 300, 'height': 300, 'crop': 'fill', 'gravity': 'face'},
                {'quality': 'auto', 'fetch_format': 'auto'}
            ]
        )
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE devmarket_users SET avatar_url=%s WHERE id=%s", (result['secure_url'], current_user_id))
        cur.close()
        conn.close()
        return jsonify({'url': result['secure_url']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# CATEGORIES ROUTES
# ─────────────────────────────────────────────
@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM devmarket_categories ORDER BY name")
        categories = [dict(c) for c in cur.fetchall()]
        for c in categories:
            c['id'] = str(c['id'])
        return jsonify({'categories': categories})
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# PRODUCTS ROUTES
# ─────────────────────────────────────────────
@app.route('/api/products', methods=['GET'])
@optional_auth
def get_products(current_user_id):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 12))
    category = request.args.get('category')
    search = request.args.get('search')
    sort = request.args.get('sort', 'newest')
    product_type = request.args.get('type')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    featured = request.args.get('featured')
    offset = (page - 1) * per_page

    where_clauses = ['p.is_active = TRUE', 'p.is_approved = TRUE']
    params = []

    if category:
        where_clauses.append('c.slug = %s')
        params.append(category)
    if search:
        where_clauses.append('(p.title ILIKE %s OR p.short_description ILIKE %s OR %s = ANY(p.tags))')
        params.extend([f'%{search}%', f'%{search}%', search])
    if product_type:
        where_clauses.append('p.product_type = %s')
        params.append(product_type)
    if min_price:
        where_clauses.append('p.price >= %s')
        params.append(float(min_price))
    if max_price:
        where_clauses.append('p.price <= %s')
        params.append(float(max_price))
    if featured == 'true':
        where_clauses.append('p.is_featured = TRUE')

    order_map = {
        'newest': 'p.created_at DESC',
        'oldest': 'p.created_at ASC',
        'price_asc': 'p.price ASC',
        'price_desc': 'p.price DESC',
        'popular': 'p.downloads DESC',
        'rating': 'p.rating_avg DESC',
        'trending': 'p.views DESC'
    }
    order = order_map.get(sort, 'p.created_at DESC')
    where_str = ' AND '.join(where_clauses)

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        query = f"""
            SELECT p.*, c.name as category_name, c.slug as category_slug, c.icon as category_icon,
                   u.username, u.full_name as seller_name, u.avatar_url as seller_avatar,
                   u.is_verified as seller_verified, u.badge as seller_badge
            FROM devmarket_products p
            LEFT JOIN devmarket_categories c ON p.category_id = c.id
            LEFT JOIN devmarket_users u ON p.seller_id = u.id
            WHERE {where_str}
            ORDER BY {order}
            LIMIT %s OFFSET %s
        """
        params.extend([per_page, offset])
        cur.execute(query, params)
        products = []
        for p in cur.fetchall():
            p = dict(p)
            p['id'] = str(p['id'])
            p['seller_id'] = str(p['seller_id']) if p['seller_id'] else None
            p['category_id'] = str(p['category_id']) if p['category_id'] else None
            products.append(p)

        cur.execute(f"""
            SELECT COUNT(*) FROM devmarket_products p
            LEFT JOIN devmarket_categories c ON p.category_id = c.id
            WHERE {where_str}
        """, params[:-2])
        total = cur.fetchone()['count']
        return jsonify({
            'products': products,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (int(total) + per_page - 1) // per_page
        })
    finally:
        cur.close()
        conn.close()


@app.route('/api/products/<product_id_or_slug>', methods=['GET'])
@optional_auth
def get_product(current_user_id, product_id_or_slug):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT p.*, c.name as category_name, c.slug as category_slug, c.icon as category_icon,
                   u.username, u.full_name as seller_name, u.avatar_url as seller_avatar,
                   u.bio as seller_bio, u.is_verified as seller_verified, u.badge as seller_badge,
                   u.reputation_score as seller_reputation, u.total_sales as seller_total_sales
            FROM devmarket_products p
            LEFT JOIN devmarket_categories c ON p.category_id = c.id
            LEFT JOIN devmarket_users u ON p.seller_id = u.id
            WHERE p.slug = %s OR p.id::text = %s
        """, (product_id_or_slug, product_id_or_slug))
        product = cur.fetchone()
        if not product:
            return jsonify({'error': 'Product not found'}), 404

        product = dict(product)
        product['id'] = str(product['id'])
        product['seller_id'] = str(product['seller_id']) if product.get('seller_id') else None
        product['category_id'] = str(product['category_id']) if product.get('category_id') else None

        # Increment views (use original UUID from DB, not str)
        cur.execute("UPDATE devmarket_products SET views = views + 1 WHERE id::text = %s", (product['id'],))

        # Get reviews
        cur.execute("""
            SELECT r.*, u.username, u.full_name, u.avatar_url
            FROM devmarket_reviews r
            JOIN devmarket_users u ON r.reviewer_id = u.id
            WHERE r.product_id = %s
            ORDER BY r.created_at DESC LIMIT 10
        """, (product['id'],))
        reviews = [dict(r) for r in cur.fetchall()]

        # Check if bookmarked
        is_bookmarked = False
        if current_user_id:
            cur.execute("SELECT 1 FROM devmarket_bookmarks WHERE user_id=%s AND product_id=%s",
                        (current_user_id, product['id']))
            is_bookmarked = cur.fetchone() is not None

        # Related products
        cur.execute("""
            SELECT p.id, p.title, p.slug, p.price, p.images, p.rating_avg, p.downloads,
                   u.username, u.avatar_url
            FROM devmarket_products p
            JOIN devmarket_users u ON p.seller_id = u.id
            WHERE p.category_id = %s AND p.id != %s AND p.is_active=TRUE
            ORDER BY p.rating_avg DESC LIMIT 4
        """, (product['category_id'], product['id']))
        related = [dict(r) for r in cur.fetchall()]

        return jsonify({
            'product': product,
            'reviews': reviews,
            'related': related,
            'is_bookmarked': is_bookmarked
        })
    finally:
        cur.close()
        conn.close()


@app.route('/api/products', methods=['POST'])
@token_required
def create_product(current_user_id):
    data = request.get_json()
    required = ['title', 'description', 'price', 'product_type', 'category_id']
    if not all(data.get(f) for f in required):
        return jsonify({'error': 'Missing required fields'}), 400

    slug_base = slugify(data['title'])
    slug = slug_base
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Ensure unique slug
        counter = 1
        while True:
            cur.execute("SELECT 1 FROM devmarket_products WHERE slug=%s", (slug,))
            if not cur.fetchone():
                break
            slug = f"{slug_base}-{counter}"
            counter += 1

        cur.execute("""
            INSERT INTO devmarket_products
            (seller_id, category_id, title, slug, short_description, description,
             price, product_type, tags, tech_stack, images, demo_url, repo_url,
             documentation_url, live_preview_url, version, license, file_size)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            current_user_id, data.get('category_id'), data['title'], slug,
            data.get('short_description'), data['description'],
            data['price'], data['product_type'],
            data.get('tags', []), data.get('tech_stack', []),
            data.get('images', []), data.get('demo_url'), data.get('repo_url'),
            data.get('documentation_url'), data.get('live_preview_url'),
            data.get('version', '1.0.0'), data.get('license', 'MIT'),
            data.get('file_size')
        ))
        product = dict(cur.fetchone())
        product['id'] = str(product['id'])

        # Update category count
        cur.execute("UPDATE devmarket_categories SET product_count = product_count + 1 WHERE id = %s",
                    (data.get('category_id'),))
        # Update seller total sales (potential)
        cur.execute("UPDATE devmarket_users SET total_sales = total_sales + 1 WHERE id = %s", (current_user_id,))

        return jsonify({'product': product}), 201
    finally:
        cur.close()
        conn.close()


@app.route('/api/products/<product_id>', methods=['PUT'])
@token_required
def update_product(current_user_id, product_id):
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT seller_id FROM devmarket_products WHERE id=%s", (product_id,))
        product = cur.fetchone()
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        if str(product['seller_id']) != current_user_id:
            return jsonify({'error': 'Not authorized'}), 403

        allowed = ['title', 'short_description', 'description', 'price', 'tags', 'tech_stack',
                   'images', 'demo_url', 'repo_url', 'documentation_url', 'version', 'is_active']
        updates = {k: v for k, v in data.items() if k in allowed}
        if not updates:
            return jsonify({'error': 'Nothing to update'}), 400
        updates['updated_at'] = datetime.datetime.utcnow()
        set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [product_id]
        cur.execute(f"UPDATE devmarket_products SET {set_clause} WHERE id = %s", values)
        return jsonify({'message': 'Product updated'})
    finally:
        cur.close()
        conn.close()


@app.route('/api/products/<product_id>', methods=['DELETE'])
@token_required
def delete_product(current_user_id, product_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT seller_id FROM devmarket_products WHERE id=%s", (product_id,))
        product = cur.fetchone()
        if not product or str(product['seller_id']) != current_user_id:
            return jsonify({'error': 'Not authorized'}), 403
        cur.execute("DELETE FROM devmarket_products WHERE id=%s", (product_id,))
        return jsonify({'message': 'Product deleted'})
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# BOOKMARKS / LIKES
# ─────────────────────────────────────────────
@app.route('/api/products/<product_id>/bookmark', methods=['POST'])
@token_required
def toggle_bookmark(current_user_id, product_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM devmarket_bookmarks WHERE user_id=%s::uuid AND product_id=%s::uuid",
                    (current_user_id, product_id))
        exists = cur.fetchone()
        if exists:
            cur.execute("DELETE FROM devmarket_bookmarks WHERE user_id=%s::uuid AND product_id=%s::uuid",
                        (current_user_id, product_id))
            cur.execute("UPDATE devmarket_products SET likes = GREATEST(0, likes - 1) WHERE id=%s::uuid", (product_id,))
            return jsonify({'bookmarked': False})
        else:
            cur.execute("INSERT INTO devmarket_bookmarks (user_id, product_id) VALUES (%s::uuid, %s::uuid)",
                        (current_user_id, product_id))
            cur.execute("UPDATE devmarket_products SET likes = likes + 1 WHERE id=%s::uuid", (product_id,))
            return jsonify({'bookmarked': True})
    finally:
        cur.close()
        conn.close()


@app.route('/api/bookmarks', methods=['GET'])
@token_required
def get_bookmarks(current_user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT p.id, p.title, p.slug, p.price, p.images, p.rating_avg, p.downloads,
                   p.product_type, u.username, u.avatar_url
            FROM devmarket_bookmarks b
            JOIN devmarket_products p ON b.product_id = p.id
            JOIN devmarket_users u ON p.seller_id = u.id
            WHERE b.user_id = %s
            ORDER BY b.created_at DESC
        """, (current_user_id,))
        bookmarks = [dict(b) for b in cur.fetchall()]
        return jsonify({'bookmarks': bookmarks})
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# REVIEWS
# ─────────────────────────────────────────────
@app.route('/api/products/<product_id>/reviews', methods=['POST'])
@token_required
def add_review(current_user_id, product_id):
    data = request.get_json()
    rating = data.get('rating')
    content = data.get('content', '').strip()
    title = data.get('title', '').strip()

    if not rating or not content:
        return jsonify({'error': 'Rating and content required'}), 400
    if not (1 <= int(rating) <= 5):
        return jsonify({'error': 'Rating must be between 1 and 5'}), 400

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            INSERT INTO devmarket_reviews (product_id, reviewer_id, rating, title, content)
            VALUES (%s, %s, %s, %s, %s) RETURNING *
        """, (product_id, current_user_id, rating, title, content))
        review = dict(cur.fetchone())

        # Update product rating
        cur.execute("""
            UPDATE devmarket_products SET
            rating_avg = (SELECT AVG(rating) FROM devmarket_reviews WHERE product_id=%s),
            review_count = (SELECT COUNT(*) FROM devmarket_reviews WHERE product_id=%s)
            WHERE id = %s
        """, (product_id, product_id, product_id))

        return jsonify({'review': review}), 201
    except psycopg2.IntegrityError:
        return jsonify({'error': 'You have already reviewed this product'}), 409
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# ORDERS (No financial processing — messaging-based)
# ─────────────────────────────────────────────
@app.route('/api/orders', methods=['POST'])
@token_required
def create_order(current_user_id):
    data = request.get_json()
    product_id = data.get('product_id')
    notes = data.get('notes', '')

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT seller_id, price, title FROM devmarket_products WHERE id=%s", (product_id,))
        product = cur.fetchone()
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        if str(product['seller_id']) == current_user_id:
            return jsonify({'error': 'Cannot purchase your own product'}), 400

        cur.execute("""
            INSERT INTO devmarket_orders (buyer_id, seller_id, product_id, notes, status)
            VALUES (%s, %s, %s, %s, 'pending_contact') RETURNING *
        """, (current_user_id, product['seller_id'], product_id, notes))
        order = dict(cur.fetchone())
        order['id'] = str(order['id'])

        # Auto-create conversation for payment negotiation
        cur.execute("""
            INSERT INTO devmarket_conversations (participant_one, participant_two, product_id, order_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING RETURNING id
        """, (current_user_id, product['seller_id'], product_id, order['id']))
        conv = cur.fetchone()

        if conv:
            # Welcome message from system
            cur.execute("""
                INSERT INTO devmarket_messages (conversation_id, sender_id, content, message_type)
                VALUES (%s, %s, %s, 'system')
            """, (conv['id'], current_user_id,
                  f"Hi! I'm interested in purchasing '{product['title']}'. Listed at ${product['price']}. Can we discuss payment details?"))

        return jsonify({'order': order}), 201
    finally:
        cur.close()
        conn.close()


@app.route('/api/orders', methods=['GET'])
@token_required
def get_orders(current_user_id):
    role = request.args.get('role', 'buyer')
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if role == 'buyer':
            cur.execute("""
                SELECT o.*, p.title as product_title, p.slug as product_slug, p.images as product_images,
                       u.username as seller_username, u.avatar_url as seller_avatar
                FROM devmarket_orders o
                JOIN devmarket_products p ON o.product_id = p.id
                JOIN devmarket_users u ON o.seller_id = u.id
                WHERE o.buyer_id = %s ORDER BY o.created_at DESC
            """, (current_user_id,))
        else:
            cur.execute("""
                SELECT o.*, p.title as product_title, p.slug as product_slug,
                       u.username as buyer_username, u.avatar_url as buyer_avatar
                FROM devmarket_orders o
                JOIN devmarket_products p ON o.product_id = p.id
                JOIN devmarket_users u ON o.buyer_id = u.id
                WHERE o.seller_id = %s ORDER BY o.created_at DESC
            """, (current_user_id,))
        orders = [dict(o) for o in cur.fetchall()]
        return jsonify({'orders': orders})
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# MESSAGING
# ─────────────────────────────────────────────
@app.route('/api/conversations', methods=['GET'])
@token_required
def get_conversations(current_user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT c.*,
                   p.title as product_title, p.slug as product_slug,
                   u1.username as p1_username, u1.full_name as p1_name, u1.avatar_url as p1_avatar,
                   u2.username as p2_username, u2.full_name as p2_name, u2.avatar_url as p2_avatar
            FROM devmarket_conversations c
            LEFT JOIN devmarket_products p ON c.product_id = p.id
            JOIN devmarket_users u1 ON c.participant_one = u1.id
            JOIN devmarket_users u2 ON c.participant_two = u2.id
            WHERE c.participant_one = %s OR c.participant_two = %s
            ORDER BY c.last_message_at DESC
        """, (current_user_id, current_user_id))
        conversations = [dict(c) for c in cur.fetchall()]
        return jsonify({'conversations': conversations})
    finally:
        cur.close()
        conn.close()


@app.route('/api/conversations/<conversation_id>/messages', methods=['GET'])
@token_required
def get_messages(current_user_id, conversation_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Verify participant
        cur.execute("""
            SELECT * FROM devmarket_conversations
            WHERE id=%s AND (participant_one=%s OR participant_two=%s)
        """, (conversation_id, current_user_id, current_user_id))
        conv = cur.fetchone()
        if not conv:
            return jsonify({'error': 'Conversation not found'}), 404

        cur.execute("""
            SELECT m.*, u.username, u.full_name, u.avatar_url
            FROM devmarket_messages m
            JOIN devmarket_users u ON m.sender_id = u.id
            WHERE m.conversation_id = %s AND m.is_deleted = FALSE
            ORDER BY m.created_at ASC
        """, (conversation_id,))
        messages = [dict(m) for m in cur.fetchall()]
        # Mark as read
        cur.execute("""
            UPDATE devmarket_messages SET is_read=TRUE
            WHERE conversation_id=%s AND sender_id!=%s
        """, (conversation_id, current_user_id))
        return jsonify({'messages': messages, 'conversation': dict(conv)})
    finally:
        cur.close()
        conn.close()


@app.route('/api/conversations/<conversation_id>/messages', methods=['POST'])
@token_required
def send_message(current_user_id, conversation_id):
    data = request.get_json()
    content = data.get('content', '').strip()
    attachment_url = data.get('attachment_url')
    if not content and not attachment_url:
        return jsonify({'error': 'Message cannot be empty'}), 400

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT * FROM devmarket_conversations
            WHERE id=%s AND (participant_one=%s OR participant_two=%s)
        """, (conversation_id, current_user_id, current_user_id))
        conv = cur.fetchone()
        if not conv:
            return jsonify({'error': 'Not authorized'}), 403

        cur.execute("""
            INSERT INTO devmarket_messages (conversation_id, sender_id, content, attachment_url)
            VALUES (%s, %s, %s, %s) RETURNING *
        """, (conversation_id, current_user_id, content, attachment_url))
        message = dict(cur.fetchone())

        cur.execute("""
            UPDATE devmarket_conversations SET last_message=%s, last_message_at=NOW() WHERE id=%s
        """, (content[:100], conversation_id))

        # Notify the other participant
        other_id = str(conv['participant_two']) if str(conv['participant_one']) == current_user_id else str(conv['participant_one'])
        cur.execute("""
            INSERT INTO devmarket_notifications (user_id, type, title, body)
            VALUES (%s, 'message', 'New Message', %s)
        """, (other_id, content[:100]))

        return jsonify({'message': message}), 201
    finally:
        cur.close()
        conn.close()


@app.route('/api/conversations/start', methods=['POST'])
@token_required
def start_conversation(current_user_id):
    data = request.get_json()
    other_user_id = data.get('user_id')
    product_id = data.get('product_id')
    first_message = data.get('message', 'Hello! I am interested in your product.')

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Check if conversation already exists
        cur.execute("""
            SELECT id FROM devmarket_conversations
            WHERE (participant_one=%s AND participant_two=%s)
               OR (participant_one=%s AND participant_two=%s)
        """, (current_user_id, other_user_id, other_user_id, current_user_id))
        existing = cur.fetchone()

        if existing:
            conv_id = existing['id']
        else:
            cur.execute("""
                INSERT INTO devmarket_conversations (participant_one, participant_two, product_id)
                VALUES (%s, %s, %s) RETURNING id
            """, (current_user_id, other_user_id, product_id))
            conv_id = cur.fetchone()['id']

        cur.execute("""
            INSERT INTO devmarket_messages (conversation_id, sender_id, content)
            VALUES (%s, %s, %s)
        """, (conv_id, current_user_id, first_message))
        cur.execute("UPDATE devmarket_conversations SET last_message=%s, last_message_at=NOW() WHERE id=%s",
                    (first_message[:100], conv_id))

        return jsonify({'conversation_id': str(conv_id)}), 201
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────
@app.route('/api/notifications', methods=['GET'])
@token_required
def get_notifications(current_user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT * FROM devmarket_notifications
            WHERE user_id=%s ORDER BY created_at DESC LIMIT 20
        """, (current_user_id,))
        notifications = [dict(n) for n in cur.fetchall()]
        unread = sum(1 for n in notifications if not n['is_read'])
        return jsonify({'notifications': notifications, 'unread': unread})
    finally:
        cur.close()
        conn.close()


@app.route('/api/notifications/read-all', methods=['POST'])
@token_required
def mark_notifications_read(current_user_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE devmarket_notifications SET is_read=TRUE WHERE user_id=%s", (current_user_id,))
        return jsonify({'message': 'All notifications marked as read'})
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# PORTFOLIO
# ─────────────────────────────────────────────
@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM devmarket_portfolio WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
        items = [dict(i) for i in cur.fetchall()]
        return jsonify({'portfolio': items})
    finally:
        cur.close()
        conn.close()


@app.route('/api/portfolio', methods=['POST'])
@token_required
def add_portfolio(current_user_id):
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            INSERT INTO devmarket_portfolio (user_id, title, description, image_url, project_url, tech_stack)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING *
        """, (current_user_id, data.get('title'), data.get('description'),
              data.get('image_url'), data.get('project_url'), data.get('tech_stack', [])))
        item = dict(cur.fetchone())
        return jsonify({'item': item}), 201
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# ARTICLES / DEV BLOG
# ─────────────────────────────────────────────
@app.route('/api/articles', methods=['GET'])
def get_articles():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    offset = (page - 1) * per_page
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT a.*, u.username, u.full_name, u.avatar_url
            FROM devmarket_articles a
            JOIN devmarket_users u ON a.author_id = u.id
            WHERE a.is_published=TRUE
            ORDER BY a.created_at DESC LIMIT %s OFFSET %s
        """, (per_page, offset))
        articles = [dict(a) for a in cur.fetchall()]
        return jsonify({'articles': articles})
    finally:
        cur.close()
        conn.close()


@app.route('/api/articles', methods=['POST'])
@token_required
def create_article(current_user_id):
    data = request.get_json()
    if not data.get('title') or not data.get('content'):
        return jsonify({'error': 'Title and content required'}), 400

    slug = slugify(data['title']) + '-' + str(uuid.uuid4())[:8]
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            INSERT INTO devmarket_articles (author_id, title, slug, content, cover_image, tags)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING *
        """, (current_user_id, data['title'], slug, data['content'],
              data.get('cover_image'), data.get('tags', [])))
        article = dict(cur.fetchone())
        return jsonify({'article': article}), 201
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# JOB BOARD
# ─────────────────────────────────────────────
@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    offset = (page - 1) * per_page
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT j.*, u.username, u.full_name, u.avatar_url
            FROM devmarket_jobs j
            JOIN devmarket_users u ON j.poster_id = u.id
            WHERE j.is_active=TRUE
            ORDER BY j.created_at DESC LIMIT %s OFFSET %s
        """, (per_page, offset))
        jobs = [dict(j) for j in cur.fetchall()]
        return jsonify({'jobs': jobs})
    finally:
        cur.close()
        conn.close()


@app.route('/api/jobs', methods=['POST'])
@token_required
def post_job(current_user_id):
    data = request.get_json()
    if not data.get('title') or not data.get('description'):
        return jsonify({'error': 'Title and description required'}), 400
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            INSERT INTO devmarket_jobs (poster_id, title, company, description, job_type, location, salary_range, tech_stack, is_remote)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *
        """, (current_user_id, data['title'], data.get('company'), data['description'],
              data.get('job_type', 'full-time'), data.get('location'), data.get('salary_range'),
              data.get('tech_stack', []), data.get('is_remote', True)))
        job = dict(cur.fetchone())
        return jsonify({'job': job}), 201
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# USER PROFILES
# ─────────────────────────────────────────────
@app.route('/api/users/<username>', methods=['GET'])
def get_user_profile(username):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT id, username, full_name, bio, avatar_url, cover_url,
                   github_url, website_url, twitter_url, linkedin_url, skills,
                   role, is_verified, reputation_score, total_sales, total_purchases,
                   joined_at, location, badge
            FROM devmarket_users WHERE username=%s
        """, (username,))
        user = cur.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        user = dict(user)
        user['id'] = str(user['id'])

        cur.execute("""
            SELECT p.id, p.title, p.slug, p.price, p.images, p.rating_avg, p.downloads, p.product_type
            FROM devmarket_products p
            WHERE p.seller_id=%s AND p.is_active=TRUE
            ORDER BY p.created_at DESC
        """, (user['id'],))
        products = [dict(p) for p in cur.fetchall()]

        cur.execute("SELECT * FROM devmarket_portfolio WHERE user_id=%s ORDER BY created_at DESC", (user['id'],))
        portfolio = [dict(p) for p in cur.fetchall()]

        return jsonify({'user': user, 'products': products, 'portfolio': portfolio})
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# DASHBOARD STATS
# ─────────────────────────────────────────────
@app.route('/api/dashboard/stats', methods=['GET'])
@token_required
def get_dashboard_stats(current_user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT COUNT(*) FROM devmarket_products WHERE seller_id=%s", (current_user_id,))
        total_products = cur.fetchone()['count']

        cur.execute("SELECT SUM(views) FROM devmarket_products WHERE seller_id=%s", (current_user_id,))
        total_views = cur.fetchone()['sum'] or 0

        cur.execute("SELECT SUM(downloads) FROM devmarket_products WHERE seller_id=%s", (current_user_id,))
        total_downloads = cur.fetchone()['sum'] or 0

        cur.execute("SELECT COUNT(*) FROM devmarket_orders WHERE buyer_id=%s", (current_user_id,))
        purchases = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) FROM devmarket_orders WHERE seller_id=%s", (current_user_id,))
        sales = cur.fetchone()['count']

        cur.execute("""
            SELECT COUNT(*) FROM devmarket_conversations
            WHERE participant_one=%s OR participant_two=%s
        """, (current_user_id, current_user_id))
        conversations = cur.fetchone()['count']

        cur.execute("""
            SELECT p.title, p.views, p.downloads, p.rating_avg, p.slug, p.images
            FROM devmarket_products p WHERE seller_id=%s
            ORDER BY p.views DESC LIMIT 5
        """, (current_user_id,))
        top_products = [dict(p) for p in cur.fetchall()]

        cur.execute("""
            SELECT COUNT(*) as cnt, date_trunc('day', created_at) as day
            FROM devmarket_products WHERE seller_id=%s
            GROUP BY day ORDER BY day DESC LIMIT 7
        """, (current_user_id,))
        activity = [dict(a) for a in cur.fetchall()]

        return jsonify({
            'total_products': total_products,
            'total_views': total_views,
            'total_downloads': total_downloads,
            'purchases': purchases,
            'sales': sales,
            'conversations': conversations,
            'top_products': top_products,
            'activity': activity
        })
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# PLATFORM STATS (public)
# ─────────────────────────────────────────────
@app.route('/api/stats', methods=['GET'])
def get_platform_stats():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT COUNT(*) FROM devmarket_users")
        users = cur.fetchone()['count']
        cur.execute("SELECT COUNT(*) FROM devmarket_products WHERE is_active=TRUE")
        products = cur.fetchone()['count']
        cur.execute("SELECT COUNT(*) FROM devmarket_orders")
        orders = cur.fetchone()['count']
        cur.execute("SELECT SUM(downloads) FROM devmarket_products")
        downloads = cur.fetchone()['sum'] or 0
        return jsonify({'users': users, 'products': products, 'orders': orders, 'downloads': downloads})
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# AI ASSISTANT (Mistral + Tavily)
# ─────────────────────────────────────────────
def tavily_search(query, max_results=3):
    """Search the web with Tavily for real-time info."""
    try:
        response = requests.post(TAVILY_API_URL, json={
            'api_key': TAVILY_API_KEY,
            'query': query,
            'search_depth': 'basic',
            'max_results': max_results,
            'include_answer': True
        }, timeout=10)
        data = response.json()
        results = []
        if data.get('answer'):
            results.append(f"Direct Answer: {data['answer']}")
        for r in data.get('results', [])[:3]:
            results.append(f"• {r.get('title', '')}: {r.get('content', '')[:200]}...")
        return '\n'.join(results) if results else None
    except Exception as e:
        return None


def mistral_chat(messages, system_prompt=None):
    """Call Mistral AI API."""
    all_messages = []
    if system_prompt:
        all_messages.append({'role': 'system', 'content': system_prompt})
    all_messages.extend(messages)

    try:
        response = requests.post(
            MISTRAL_API_URL,
            headers={
                'Authorization': f'Bearer {MISTRAL_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'mistral-small-latest',
                'messages': all_messages,
                'max_tokens': 1000,
                'temperature': 0.7
            },
            timeout=30
        )
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        return f"AI is temporarily unavailable. Error: {str(e)}"


@app.route('/api/ai/chat', methods=['POST'])
@optional_auth
def ai_chat(current_user_id):
    data = request.get_json()
    messages = data.get('messages', [])
    session_id = data.get('session_id', str(uuid.uuid4()))
    use_search = data.get('use_search', False)

    if not messages:
        return jsonify({'error': 'No messages provided'}), 400

    user_message = messages[-1]['content'] if messages else ''

    # Determine if we should search
    search_context = ''
    search_keywords = ['latest', 'current', 'trending', 'new', 'today', 'recent', 'news', '2024', '2025']
    should_search = use_search or any(kw in user_message.lower() for kw in search_keywords)

    if should_search:
        search_result = tavily_search(user_message)
        if search_result:
            search_context = f"\n\nReal-time web search results:\n{search_result}"

    system_prompt = f"""You are Devvy, the AI assistant for Devmarket — the world's premier developer marketplace.
You help developers find tools, APIs, templates, scripts, plugins, datasets, and more.
You provide expert advice on:
- Choosing the right developer tools and libraries
- Code architecture and best practices
- API integrations and technical implementation
- Product recommendations from Devmarket's catalog
- Career advice for developers
- Market trends in software development

You are knowledgeable, concise, and always ready to help developers succeed.
Devmarket is a platform where developers buy and sell developer assets.
The platform does not process payments directly — buyers and sellers negotiate through messaging.
{search_context}

Always be helpful, professional, and technically accurate. When relevant, suggest exploring Devmarket's marketplace."""

    response = mistral_chat(messages, system_prompt)

    # Save to DB if user logged in
    if current_user_id:
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO devmarket_ai_chats (user_id, session_id, messages)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (current_user_id, session_id, json.dumps(messages + [{'role': 'assistant', 'content': response}])))
        except Exception:
            pass
        finally:
            cur.close()
            conn.close()

    return jsonify({
        'response': response,
        'session_id': session_id,
        'searched': should_search and bool(search_context)
    })


@app.route('/api/ai/search', methods=['POST'])
def ai_search():
    """Tavily + Mistral powered developer knowledge search."""
    data = request.get_json()
    query = data.get('query', '')
    if not query:
        return jsonify({'error': 'Query required'}), 400

    search_results = tavily_search(query, max_results=5)
    if not search_results:
        return jsonify({'results': [], 'summary': 'No results found'})

    summary = mistral_chat(
        [{'role': 'user', 'content': f"Summarize these search results for a developer: {search_results}"}],
        "You are a technical assistant. Summarize search results concisely for developers. Be technical and accurate."
    )

    return jsonify({
        'results': search_results,
        'summary': summary,
        'query': query
    })


@app.route('/api/auth/logout', methods=['POST'])
@token_required
def logout(current_user_id):
    """Mark user offline on logout."""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE devmarket_users SET is_online=FALSE WHERE id=%s", (current_user_id,))
        return jsonify({'message': 'Logged out successfully'})
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# TRENDING & FEATURED
# ─────────────────────────────────────────────
@app.route('/api/trending', methods=['GET'])
def get_trending():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT p.id, p.title, p.slug, p.price, p.images, p.rating_avg,
                   p.downloads, p.views, p.product_type, p.tags,
                   u.username, u.avatar_url, u.is_verified,
                   c.name as category_name, c.icon as category_icon
            FROM devmarket_products p
            JOIN devmarket_users u ON p.seller_id = u.id
            LEFT JOIN devmarket_categories c ON p.category_id = c.id
            WHERE p.is_active=TRUE
            ORDER BY (p.views + p.downloads * 3 + p.likes * 5) DESC
            LIMIT 10
        """)
        trending = [dict(p) for p in cur.fetchall()]
        return jsonify({'trending': trending})
    finally:
        cur.close()
        conn.close()


@app.route('/api/featured', methods=['GET'])
def get_featured():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT p.id, p.title, p.slug, p.price, p.short_description, p.images, p.rating_avg,
                   p.downloads, p.product_type, p.tags, p.tech_stack,
                   u.username, u.full_name, u.avatar_url, u.is_verified,
                   c.name as category_name, c.icon as category_icon, c.color as category_color
            FROM devmarket_products p
            JOIN devmarket_users u ON p.seller_id = u.id
            LEFT JOIN devmarket_categories c ON p.category_id = c.id
            WHERE p.is_active=TRUE AND p.is_featured=TRUE
            ORDER BY p.rating_avg DESC, p.downloads DESC
            LIMIT 6
        """)
        featured = [dict(p) for p in cur.fetchall()]
        if len(featured) < 6:
            # Fallback to top rated
            ids = [str(f['id']) for f in featured]
            cur.execute("""
                SELECT p.id, p.title, p.slug, p.price, p.short_description, p.images, p.rating_avg,
                       p.downloads, p.product_type, p.tags, p.tech_stack,
                       u.username, u.full_name, u.avatar_url, u.is_verified,
                       c.name as category_name, c.icon as category_icon, c.color as category_color
                FROM devmarket_products p
                JOIN devmarket_users u ON p.seller_id = u.id
                LEFT JOIN devmarket_categories c ON p.category_id = c.id
                WHERE p.is_active=TRUE
                ORDER BY p.rating_avg DESC LIMIT 6
            """)
            featured = [dict(p) for p in cur.fetchall()]
        return jsonify({'featured': featured})
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# SEARCH SUGGESTIONS
# ─────────────────────────────────────────────
@app.route('/api/search/suggestions', methods=['GET'])
def get_search_suggestions():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'suggestions': []})

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT title, slug, price, product_type FROM devmarket_products
            WHERE title ILIKE %s AND is_active=TRUE
            LIMIT 8
        """, (f'%{query}%',))
        suggestions = [dict(s) for s in cur.fetchall()]
        return jsonify({'suggestions': suggestions})
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# SELLER VERIFICATION REQUEST
# ─────────────────────────────────────────────
@app.route('/api/users/request-verification', methods=['POST'])
@token_required
def request_verification(current_user_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO devmarket_notifications (user_id, type, title, body)
            VALUES (%s, 'system', 'Verification Requested',
            'Your seller verification request has been submitted. Our team will review it within 24 hours.')
        """, (current_user_id,))
        return jsonify({'message': 'Verification request submitted'})
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────
@app.route('/api/health', methods=['GET'])
def health():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {str(e)}'

    return jsonify({
        'status': 'ok',
        'platform': 'Devmarket',
        'version': '1.0.0',
        'database': db_status,
        'cloudinary': 'configured',
        'ai': 'Mistral + Tavily'
    })


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == '__main__':
    print("🚀 Starting Devmarket API Server...")
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)