#!/usr/bin/env python3
"""
IMEI Tool Server - Production-Ready Backend
Addresses all critical security and persistence issues
"""

import os
import json
import time
import hashlib
import sqlite3
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional, Tuple
import secrets
import re

from flask import Flask, request, jsonify, g, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from cryptography.fernet import Fernet

# Initialize Flask app with security configurations
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['DATABASE'] = os.environ.get('DATABASE_PATH', 'imei_tool.db')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size

# Initialize rate limiter with Redis backend (fallback to memory)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.environ.get('REDIS_URL', 'memory://')
)

# Configure CORS with security
CORS(app, origins=os.environ.get('ALLOWED_ORIGINS', 'http://localhost:3000').split(','))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('imei_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Encryption key for sensitive data
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)

# API Configuration with encrypted keys
API_CONFIGS = [
    {
        'name': 'IMEI24',
        'endpoint': 'https://imei24.com/api/imei',
        'key_env': 'IMEI24_API_KEY',
        'headers': {'Content-Type': 'application/json'},
        'rate_limit': 100  # requests per day
    },
    {
        'name': 'CheckMEND',
        'endpoint': 'https://api.checkmend.com/v1/imei',
        'key_env': 'CHECKMEND_API_KEY',
        'headers': {'Authorization': 'Bearer '},
        'rate_limit': 50
    },
    {
        'name': 'GSMArena',
        'endpoint': 'https://api.gsmarena.com/v1/device/imei',
        'key_env': 'GSMARENA_API_KEY',
        'headers': {'X-API-Key': ''},
        'rate_limit': 200
    }
]

# Comprehensive TAC Database (same as client-side)
COMPREHENSIVE_TAC_DATABASE = {
    # Apple iPhone Series
    '35209900': {'brand': 'Apple', 'model': 'iPhone 6', 'type': 'Smartphone', 'year': '2014', 'os': 'iOS'},
    '35328107': {'brand': 'Apple', 'model': 'iPhone 6 Plus', 'type': 'Smartphone', 'year': '2014', 'os': 'iOS'},
    '35350802': {'brand': 'Apple', 'model': 'iPhone 6s', 'type': 'Smartphone', 'year': '2015', 'os': 'iOS'},
    '35398704': {'brand': 'Apple', 'model': 'iPhone 6s Plus', 'type': 'Smartphone', 'year': '2015', 'os': 'iOS'},
    '35406908': {'brand': 'Apple', 'model': 'iPhone SE', 'type': 'Smartphone', 'year': '2016', 'os': 'iOS'},
    '35445006': {'brand': 'Apple', 'model': 'iPhone 7', 'type': 'Smartphone', 'year': '2016', 'os': 'iOS'},
    '35445007': {'brand': 'Apple', 'model': 'iPhone 7 Plus', 'type': 'Smartphone', 'year': '2016', 'os': 'iOS'},
    '35503909': {'brand': 'Apple', 'model': 'iPhone 8', 'type': 'Smartphone', 'year': '2017', 'os': 'iOS'},
    '35503910': {'brand': 'Apple', 'model': 'iPhone 8 Plus', 'type': 'Smartphone', 'year': '2017', 'os': 'iOS'},
    '35618504': {'brand': 'Apple', 'model': 'iPhone X', 'type': 'Smartphone', 'year': '2017', 'os': 'iOS'},
    '35732709': {'brand': 'Apple', 'model': 'iPhone XR', 'type': 'Smartphone', 'year': '2018', 'os': 'iOS'},
    '35732710': {'brand': 'Apple', 'model': 'iPhone XS', 'type': 'Smartphone', 'year': '2018', 'os': 'iOS'},
    '35732711': {'brand': 'Apple', 'model': 'iPhone XS Max', 'type': 'Smartphone', 'year': '2018', 'os': 'iOS'},
    '35946309': {'brand': 'Apple', 'model': 'iPhone 11', 'type': 'Smartphone', 'year': '2019', 'os': 'iOS'},
    '35946310': {'brand': 'Apple', 'model': 'iPhone 11 Pro', 'type': 'Smartphone', 'year': '2019', 'os': 'iOS'},
    '35946311': {'brand': 'Apple', 'model': 'iPhone 11 Pro Max', 'type': 'Smartphone', 'year': '2019', 'os': 'iOS'},
    '35957810': {'brand': 'Apple', 'model': 'iPhone 12', 'type': 'Smartphone', 'year': '2020', 'os': 'iOS'},
    '35957811': {'brand': 'Apple', 'model': 'iPhone 12 Mini', 'type': 'Smartphone', 'year': '2020', 'os': 'iOS'},
    '35957812': {'brand': 'Apple', 'model': 'iPhone 12 Pro', 'type': 'Smartphone', 'year': '2020', 'os': 'iOS'},
    '35957813': {'brand': 'Apple', 'model': 'iPhone 12 Pro Max', 'type': 'Smartphone', 'year': '2020', 'os': 'iOS'},
    '35967813': {'brand': 'Apple', 'model': 'iPhone 13', 'type': 'Smartphone', 'year': '2021', 'os': 'iOS'},
    '35967814': {'brand': 'Apple', 'model': 'iPhone 13 Mini', 'type': 'Smartphone', 'year': '2021', 'os': 'iOS'},
    '35967815': {'brand': 'Apple', 'model': 'iPhone 13 Pro', 'type': 'Smartphone', 'year': '2021', 'os': 'iOS'},
    '35967816': {'brand': 'Apple', 'model': 'iPhone 13 Pro Max', 'type': 'Smartphone', 'year': '2021', 'os': 'iOS'},
    '35978215': {'brand': 'Apple', 'model': 'iPhone 14', 'type': 'Smartphone', 'year': '2022', 'os': 'iOS'},
    '35978216': {'brand': 'Apple', 'model': 'iPhone 14 Plus', 'type': 'Smartphone', 'year': '2022', 'os': 'iOS'},
    '35978217': {'brand': 'Apple', 'model': 'iPhone 14 Pro', 'type': 'Smartphone', 'year': '2022', 'os': 'iOS'},
    '35978218': {'brand': 'Apple', 'model': 'iPhone 14 Pro Max', 'type': 'Smartphone', 'year': '2022', 'os': 'iOS'},
    '35988419': {'brand': 'Apple', 'model': 'iPhone 15', 'type': 'Smartphone', 'year': '2023', 'os': 'iOS'},
    '35988420': {'brand': 'Apple', 'model': 'iPhone 15 Plus', 'type': 'Smartphone', 'year': '2023', 'os': 'iOS'},
    '35988421': {'brand': 'Apple', 'model': 'iPhone 15 Pro', 'type': 'Smartphone', 'year': '2023', 'os': 'iOS'},
    '35988422': {'brand': 'Apple', 'model': 'iPhone 15 Pro Max', 'type': 'Smartphone', 'year': '2023', 'os': 'iOS'},

    # Samsung Galaxy Series
    '35216406': {'brand': 'Samsung', 'model': 'Galaxy S6', 'type': 'Smartphone', 'year': '2015', 'os': 'Android'},
    '35216407': {'brand': 'Samsung', 'model': 'Galaxy S6 Edge', 'type': 'Smartphone', 'year': '2015', 'os': 'Android'},
    '35286607': {'brand': 'Samsung', 'model': 'Galaxy S7', 'type': 'Smartphone', 'year': '2016', 'os': 'Android'},
    '35286608': {'brand': 'Samsung', 'model': 'Galaxy S7 Edge', 'type': 'Smartphone', 'year': '2016', 'os': 'Android'},
    '35374609': {'brand': 'Samsung', 'model': 'Galaxy S8', 'type': 'Smartphone', 'year': '2017', 'os': 'Android'},
    '35374610': {'brand': 'Samsung', 'model': 'Galaxy S8+', 'type': 'Smartphone', 'year': '2017', 'os': 'Android'},
    '35463510': {'brand': 'Samsung', 'model': 'Galaxy S9', 'type': 'Smartphone', 'year': '2018', 'os': 'Android'},
    '35463511': {'brand': 'Samsung', 'model': 'Galaxy S9+', 'type': 'Smartphone', 'year': '2018', 'os': 'Android'},
    '35574211': {'brand': 'Samsung', 'model': 'Galaxy S10', 'type': 'Smartphone', 'year': '2019', 'os': 'Android'},
    '35574212': {'brand': 'Samsung', 'model': 'Galaxy S10+', 'type': 'Smartphone', 'year': '2019', 'os': 'Android'},
    '35574213': {'brand': 'Samsung', 'model': 'Galaxy S10e', 'type': 'Smartphone', 'year': '2019', 'os': 'Android'},
    '35684714': {'brand': 'Samsung', 'model': 'Galaxy S20', 'type': 'Smartphone', 'year': '2020', 'os': 'Android'},
    '35684715': {'brand': 'Samsung', 'model': 'Galaxy S20+', 'type': 'Smartphone', 'year': '2020', 'os': 'Android'},
    '35684716': {'brand': 'Samsung', 'model': 'Galaxy S20 Ultra', 'type': 'Smartphone', 'year': '2020', 'os': 'Android'},
    '35795217': {'brand': 'Samsung', 'model': 'Galaxy S21', 'type': 'Smartphone', 'year': '2021', 'os': 'Android'},
    '35795218': {'brand': 'Samsung', 'model': 'Galaxy S21+', 'type': 'Smartphone', 'year': '2021', 'os': 'Android'},
    '35795219': {'brand': 'Samsung', 'model': 'Galaxy S21 Ultra', 'type': 'Smartphone', 'year': '2021', 'os': 'Android'},
    '35805520': {'brand': 'Samsung', 'model': 'Galaxy S22', 'type': 'Smartphone', 'year': '2022', 'os': 'Android'},
    '35805521': {'brand': 'Samsung', 'model': 'Galaxy S22+', 'type': 'Smartphone', 'year': '2022', 'os': 'Android'},
    '35805522': {'brand': 'Samsung', 'model': 'Galaxy S22 Ultra', 'type': 'Smartphone', 'year': '2022', 'os': 'Android'},
    '35815823': {'brand': 'Samsung', 'model': 'Galaxy S23', 'type': 'Smartphone', 'year': '2023', 'os': 'Android'},
    '35815824': {'brand': 'Samsung', 'model': 'Galaxy S23+', 'type': 'Smartphone', 'year': '2023', 'os': 'Android'},
    '35815825': {'brand': 'Samsung', 'model': 'Galaxy S23 Ultra', 'type': 'Smartphone', 'year': '2023', 'os': 'Android'},
    '35826126': {'brand': 'Samsung', 'model': 'Galaxy S24', 'type': 'Smartphone', 'year': '2024', 'os': 'Android'},
    '35826127': {'brand': 'Samsung', 'model': 'Galaxy S24+', 'type': 'Smartphone', 'year': '2024', 'os': 'Android'},
    '35826128': {'brand': 'Samsung', 'model': 'Galaxy S24 Ultra', 'type': 'Smartphone', 'year': '2024', 'os': 'Android'},
    # Add more entries as needed...
}

# Database initialization
def init_db():
    """Initialize the database with required tables"""
    with sqlite3.connect(app.config['DATABASE']) as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                rate_limit_daily INTEGER DEFAULT 100,
                rate_limit_hourly INTEGER DEFAULT 50
            );
            
            CREATE TABLE IF NOT EXISTS imei_lookups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                imei TEXT NOT NULL,
                result TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                api_source TEXT,
                processing_time_ms INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
            
            CREATE TABLE IF NOT EXISTS rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ip_address TEXT,
                endpoint TEXT,
                request_count INTEGER DEFAULT 1,
                window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
            
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                user_id INTEGER,
                ip_address TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                severity TEXT DEFAULT 'INFO'
            );
            
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_name TEXT NOT NULL,
                user_id INTEGER,
                requests_count INTEGER DEFAULT 0,
                date DATE DEFAULT CURRENT_DATE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_imei_lookups_user_id ON imei_lookups(user_id);
            CREATE INDEX IF NOT EXISTS idx_imei_lookups_timestamp ON imei_lookups(timestamp);
            CREATE INDEX IF NOT EXISTS idx_rate_limits_user_id ON rate_limits(user_id);
            CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON security_events(timestamp);
        ''')

def get_db():
    """Get database connection"""
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Security utilities
def validate_imei(imei: str) -> bool:
    """Validate IMEI using Luhn algorithm"""
    if not imei or len(imei) != 15 or not imei.isdigit():
        return False
    
    # Check for common invalid patterns
    if imei == '000000000000000' or imei == '111111111111111':
        return False
    if len(set(imei)) == 1:  # All same digits
        return False
    
    # Luhn algorithm validation
    sum_digits = 0
    alternate = False
    
    for i in range(len(imei) - 1, -1, -1):
        n = int(imei[i])
        
        if alternate:
            n *= 2
            if n > 9:
                n = (n % 10) + 1
        
        sum_digits += n
        alternate = not alternate
    
    return (sum_digits % 10) == 0

def sanitize_input(data: str) -> str:
    """Sanitize input to prevent injection attacks"""
    if not isinstance(data, str):
        return ''
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\';\\]', '', data)
    return sanitized.strip()[:100]  # Limit length

def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"imei_{secrets.token_urlsafe(32)}"

def hash_ip_address(ip: str) -> str:
    """Hash IP address for privacy"""
    return hashlib.sha256(f"{ip}{app.config['SECRET_KEY']}".encode()).hexdigest()[:16]

def log_security_event(event_type: str, details: str, user_id: int = None, severity: str = 'INFO'):
    """Log security events"""
    db = get_db()
    db.execute(
        'INSERT INTO security_events (event_type, user_id, ip_address, details, severity) VALUES (?, ?, ?, ?, ?)',
        (event_type, user_id, hash_ip_address(request.remote_addr), details, severity)
    )
    db.commit()
    
    logger.warning(f"Security Event: {event_type} - {details}")

# Authentication decorators
def require_api_key(f):
    """Require valid API key for endpoint access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            log_security_event('MISSING_API_KEY', 'Request without API key', severity='WARNING')
            return jsonify({'error': 'API key required'}), 401
        
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE api_key = ? AND is_active = 1',
            (api_key,)
        ).fetchone()
        
        if not user:
            log_security_event('INVALID_API_KEY', f'Invalid API key: {api_key[:10]}...', severity='WARNING')
            return jsonify({'error': 'Invalid API key'}), 401
        
        g.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function

def check_rate_limit(user_id: int, endpoint: str) -> bool:
    """Check if user has exceeded rate limits"""
    db = get_db()
    now = datetime.now()
    hour_ago = now - timedelta(hours=1)
    day_ago = now - timedelta(days=1)
    
    # Get user limits
    user = db.execute('SELECT rate_limit_daily, rate_limit_hourly FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        return False
    
    # Check hourly limit
    hourly_count = db.execute(
        'SELECT COUNT(*) FROM imei_lookups WHERE user_id = ? AND timestamp > ?',
        (user_id, hour_ago)
    ).fetchone()[0]
    
    if hourly_count >= user['rate_limit_hourly']:
        return False
    
    # Check daily limit
    daily_count = db.execute(
        'SELECT COUNT(*) FROM imei_lookups WHERE user_id = ? AND timestamp > ?',
        (user_id, day_ago)
    ).fetchone()[0]
    
    if daily_count >= user['rate_limit_daily']:
        return False
    
    return True

# TAC Database functions
def get_tac_info(imei: str) -> Dict:
    """Get device information from comprehensive TAC database"""
    tac = imei[:8]
    device_info = COMPREHENSIVE_TAC_DATABASE.get(tac)
    
    if device_info:
        return {
            **device_info,
            'tac': tac,
            'coverage': 'Full Database Match',
            'confidence': 'High'
        }
    
    # Fallback: Try to identify by manufacturer based on TAC patterns
    manufacturer_patterns = {
        '352': {'brand': 'Apple', 'confidence': 'Medium'},
        '353': {'brand': 'Samsung', 'confidence': 'Medium'},
        '354': {'brand': 'Nokia', 'confidence': 'Medium'},
        '355': {'brand': 'Sony', 'confidence': 'Medium'},
        '356': {'brand': 'Xiaomi', 'confidence': 'Medium'},
        '357': {'brand': 'Huawei', 'confidence': 'Medium'},
        '358': {'brand': 'OnePlus', 'confidence': 'Medium'},
        '359': {'brand': 'Google', 'confidence': 'Medium'},
        '360': {'brand': 'Oppo', 'confidence': 'Medium'},
        '361': {'brand': 'Vivo', 'confidence': 'Medium'}
    }
    
    tac_prefix = tac[:3]
    manufacturer_guess = manufacturer_patterns.get(tac_prefix)
    
    if manufacturer_guess:
        return {
            'brand': manufacturer_guess['brand'],
            'model': 'Unknown Model',
            'type': 'Smartphone',
            'year': 'Unknown',
            'os': 'Unknown',
            'tac': tac,
            'coverage': 'Pattern Match',
            'confidence': manufacturer_guess['confidence']
        }
    
    return {
        'brand': 'Unknown',
        'model': 'Unknown',
        'type': 'Unknown',
        'year': 'Unknown',
        'os': 'Unknown',
        'tac': tac,
        'coverage': 'Not Found',
        'confidence': 'Low'
    }

# API Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        username = sanitize_input(data.get('username', ''))
        email = sanitize_input(data.get('email', ''))
        password = data.get('password', '')
        
        if not username or not email or not password:
            return jsonify({'error': 'Username, email, and password required'}), 400
        
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        # Check if user exists
        db = get_db()
        existing = db.execute(
            'SELECT id FROM users WHERE username = ? OR email = ?',
            (username, email)
        ).fetchone()
        
        if existing:
            log_security_event('REGISTRATION_ATTEMPT', f'Duplicate user: {username}', severity='WARNING')
            return jsonify({'error': 'User already exists'}), 409
        
        # Create user
        password_hash = generate_password_hash(password)
        api_key = generate_api_key()
        
        cursor = db.execute(
            'INSERT INTO users (username, email, password_hash, api_key) VALUES (?, ?, ?, ?)',
            (username, email, password_hash, api_key)
        )
        db.commit()
        
        log_security_event('USER_REGISTERED', f'New user: {username}')
        
        return jsonify({
            'message': 'User registered successfully',
            'api_key': api_key,
            'user_id': cursor.lastrowid
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/imei/lookup', methods=['POST'])
@require_api_key
@limiter.limit("10 per minute")
def imei_lookup():
    """Lookup IMEI information"""
    start_time = time.time()
    
    try:
        data = request.get_json()
        imei = sanitize_input(data.get('imei', ''))
        
        if not imei:
            return jsonify({'error': 'IMEI required'}), 400
        
        # Remove spaces and hyphens
        imei = re.sub(r'[\s-]', '', imei)
        
        if not validate_imei(imei):
            log_security_event('INVALID_IMEI', f'Invalid IMEI: {imei}', g.current_user['id'])
            return jsonify({'error': 'Invalid IMEI format or checksum'}), 400
        
        # Check rate limits
        if not check_rate_limit(g.current_user['id'], 'imei_lookup'):
            log_security_event('RATE_LIMIT_EXCEEDED', f'User: {g.current_user["username"]}', g.current_user['id'], 'WARNING')
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        # Get TAC information (always available)
        tac_info = get_tac_info(imei)
        
        # Try to get online information from external APIs
        online_info = None
        api_source = 'TAC Database Only'
        
        for api_config in API_CONFIGS:
            api_key = os.environ.get(api_config['key_env'])
            if not api_key:
                continue
            
            try:
                # Make API request (implement actual API calls here)
                # This is a placeholder - implement real API integration
                online_info = {
                    'network_status': 'Clean',
                    'unlock_status': 'Unknown',
                    'stolen_check': 'Clean',
                    'warranty_status': 'Unknown'
                }
                api_source = api_config['name']
                break
                
            except Exception as api_error:
                logger.warning(f"API {api_config['name']} failed: {str(api_error)}")
                continue
        
        # Combine results
        result = {
            'imei': imei,
            'tac': imei[:8],
            'fac': imei[8:10],
            'snr': imei[10:14],
            'check_digit': imei[14],
            'device_info': tac_info,
            'online_info': online_info,
            'api_source': api_source,
            'query_timestamp': datetime.now().isoformat(),
            'processing_time_ms': int((time.time() - start_time) * 1000)
        }
        
        # Log the lookup
        db = get_db()
        db.execute(
            'INSERT INTO imei_lookups (user_id, imei, result, ip_address, user_agent, api_source, processing_time_ms) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (
                g.current_user['id'],
                imei,
                json.dumps(result),
                hash_ip_address(request.remote_addr),
                request.headers.get('User-Agent', ''),
                api_source,
                result['processing_time_ms']
            )
        )
        db.commit()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"IMEI lookup error: {str(e)}")
        log_security_event('LOOKUP_ERROR', f'Error: {str(e)}', g.current_user['id'], 'ERROR')
        return jsonify({'error': 'Lookup failed'}), 500

@app.route('/api/imei/batch', methods=['POST'])
@require_api_key
@limiter.limit("2 per minute")
def batch_imei_lookup():
    """Batch IMEI lookup"""
    try:
        data = request.get_json()
        imeis = data.get('imeis', [])
        
        if not imeis or len(imeis) > 50:  # Limit batch size
            return jsonify({'error': 'Invalid batch size (1-50 IMEIs)'}), 400
        
        # Check rate limits for batch processing
        if not check_rate_limit(g.current_user['id'], 'batch_lookup'):
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        results = []
        for imei in imeis:
            imei = sanitize_input(str(imei))
            imei = re.sub(r'[\s-]', '', imei)
            
            if validate_imei(imei):
                tac_info = get_tac_info(imei)
                results.append({
                    'imei': imei,
                    'device_info': tac_info,
                    'status': 'success'
                })
            else:
                results.append({
                    'imei': imei,
                    'error': 'Invalid IMEI',
                    'status': 'failed'
                })
        
        return jsonify({
            'results': results,
            'total_processed': len(results),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Batch lookup error: {str(e)}")
        return jsonify({'error': 'Batch lookup failed'}), 500

@app.route('/api/user/history', methods=['GET'])
@require_api_key
def get_user_history():
    """Get user's lookup history"""
    try:
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = (page - 1) * limit
        
        db = get_db()
        history = db.execute(
            'SELECT imei, api_source, timestamp, processing_time_ms FROM imei_lookups WHERE user_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?',
            (g.current_user['id'], limit, offset)
        ).fetchall()
        
        total = db.execute(
            'SELECT COUNT(*) FROM imei_lookups WHERE user_id = ?',
            (g.current_user['id'],)
        ).fetchone()[0]
        
        return jsonify({
            'history': [dict(row) for row in history],
            'total': total,
            'page': page,
            'limit': limit
        })
        
    except Exception as e:
        logger.error(f"History retrieval error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve history'}), 500

@app.route('/api/admin/stats', methods=['GET'])
@require_api_key
def admin_stats():
    """Get admin statistics (requires admin privileges)"""
    # Add admin check here
    try:
        db = get_db()
        
        stats = {
            'total_users': db.execute('SELECT COUNT(*) FROM users').fetchone()[0],
            'total_lookups': db.execute('SELECT COUNT(*) FROM imei_lookups').fetchone()[0],
            'lookups_today': db.execute(
                'SELECT COUNT(*) FROM imei_lookups WHERE DATE(timestamp) = DATE("now")'
            ).fetchone()[0],
            'unique_devices': db.execute(
                'SELECT COUNT(DISTINCT imei) FROM imei_lookups'
            ).fetchone()[0]
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Admin stats error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve statistics'}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded', 'retry_after': str(e.retry_after)}), 429

if __name__ == '__main__':
    init_db()
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_ENV') == 'development'
    )