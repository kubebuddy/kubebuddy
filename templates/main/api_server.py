"""
Flask API for OTP-based Authentication in KubeBuddy
Provides endpoints for sending OTP and verifying login
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from email_service import EmailService, OTPManager
import os
from datetime import datetime
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# Configuration
SMTP_CONFIG = {
    'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', 587)),
    'sender_email': os.getenv('SENDER_EMAIL'),
    'sender_password': os.getenv('SENDER_PASSWORD')
}

# Initialize services
email_service = EmailService(**SMTP_CONFIG)
otp_manager = OTPManager(expiry_minutes=10)

# Global email config storage
email_config = {}

# Initialize with env vars if available
if SMTP_CONFIG['sender_email'] and SMTP_CONFIG['sender_password']:
    email_config = SMTP_CONFIG.copy()

def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'KubeBuddy OTP Service'
    }), 200


@app.route('/api/auth/send-otp', methods=['POST'])
def send_otp():
    """
    Send OTP to user's email
    
    Request body:
        {
            "email": "user@example.com"
        }
    
    Response:
        {
            "success": true,
            "message": "OTP sent successfully",
            "expiryMinutes": 10
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'email' not in data:
            return jsonify({
                'success': False,
                'message': 'Email is required'
            }), 400
        
        email = data['email'].strip().lower()
        
        # Validate email format
        if not validate_email(email):
            return jsonify({
                'success': False,
                'message': 'Invalid email format'
            }), 400
        
        # Generate OTP
        otp = otp_manager.generate_and_store_otp(email)
        
        # Send OTP email
        email_sent = email_service.send_otp_email(email, otp, expiry_minutes=10)
        
        if email_sent:
            return jsonify({
                'success': True,
                'message': 'OTP sent successfully to your email',
                'expiryMinutes': 10
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send OTP. Please try again later.'
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error in send_otp: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred. Please try again.'
        }), 500


@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    """
    Verify OTP and authenticate user
    
    Request body:
        {
            "email": "user@example.com",
            "otp": "123456"
        }
    
    Response:
        {
            "success": true,
            "message": "Login successful",
            "token": "jwt-token-here"  # In production, generate JWT
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'email' not in data or 'otp' not in data:
            return jsonify({
                'success': False,
                'message': 'Email and OTP are required'
            }), 400
        
        email = data['email'].strip().lower()
        otp = data['otp'].strip()
        
        # Validate email format
        if not validate_email(email):
            return jsonify({
                'success': False,
                'message': 'Invalid email format'
            }), 400
        
        # Verify OTP
        verified, message = otp_manager.verify_otp(email, otp)
        
        if verified:
            # In production, generate JWT token here
            # token = generate_jwt_token(email)
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'email': email,
                # 'token': token  # Include JWT in production
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 401
            
    except Exception as e:
        app.logger.error(f"Error in verify_otp: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred. Please try again.'
        }), 500


@app.route('/api/auth/resend-otp', methods=['POST'])
def resend_otp():
    """
    Resend OTP to user's email
    
    Request body:
        {
            "email": "user@example.com"
        }
    
    Response:
        {
            "success": true,
            "message": "OTP resent successfully"
        }
    """
    # Same logic as send_otp
    return send_otp()


@app.route('/api/admin/email-config', methods=['POST'])
def save_email_config():
    """
    Save email configuration from admin interface
    
    Request body:
        {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "your-email@gmail.com",
            "sender_password": "your-app-password"
        }
    
    Response:
        {
            "success": true,
            "message": "Configuration saved!"
        }
    """
    global email_service, email_config
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['smtp_host', 'smtp_port', 'sender_email', 'sender_password']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Store configuration
        email_config = {
            'smtp_host': data['smtp_host'],
            'smtp_port': data['smtp_port'],
            'sender_email': data['sender_email'],
            'sender_password': data['sender_password']
        }
        
        # Reinitialize email service with new config
        email_service = EmailService(**email_config)
        
        return jsonify({
            'success': True,
            'message': 'Configuration saved successfully!'
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error in save_email_config: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to save configuration: {str(e)}'
        }), 500


@app.route('/api/admin/test-email', methods=['POST'])
def test_email():
    """
    Send test OTP email to verify configuration
    
    Request body:
        {
            "email": "test@example.com"
        }
    
    Response:
        {
            "success": true,
            "message": "Test email sent!"
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'email' not in data:
            return jsonify({
                'success': False,
                'message': 'Email address is required'
            }), 400
        
        email = data['email'].strip()
        
        # Validate email format
        if not validate_email(email):
            return jsonify({
                'success': False,
                'message': 'Invalid email format'
            }), 400
        
        # Check if email is configured
        if not email_config or not email_config.get('sender_email'):
            return jsonify({
                'success': False,
                'message': 'Email not configured. Please configure email settings first.'
            }), 400
        
        # Generate test OTP
        test_otp = otp_manager.generate_and_store_otp(email)
        
        # Send test email
        success = email_service.send_otp_email(email, test_otp)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Test email sent successfully to {email}'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send test email. Please check your configuration.'
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error in test_email: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error sending test email: {str(e)}'
        }), 500


# Cleanup task (in production, use a scheduler like APScheduler)
@app.before_request
def cleanup_expired_otps():
    """
    Cleanup expired OTPs before each request
    In production, use a background scheduler
    """
    otp_manager.cleanup_expired_otps()


if __name__ == '__main__':
    # Check if email configuration is set
    if not SMTP_CONFIG['sender_email'] or not SMTP_CONFIG['sender_password']:
        print("⚠️  WARNING: Email configuration not set!")
        print("Please configure email using the admin interface at:")
        print("http://localhost:8080/email_config.html")
        print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)