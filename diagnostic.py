# diagnostic_app.py - Minimal test to identify the issue
from flask import Flask, render_template, request, jsonify
from flask_restx import Api, Resource, fields
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'test-secret-key'

# Test if this is the issue - initialize API AFTER defining regular routes
print("Setting up Flask app...")

# ============================================================================
# REGULAR FLASK ROUTES FIRST
# ============================================================================

@app.route('/')
def home():
    """Serve the main chat interface"""
    print("Home route called!")
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Template error: {e}")
        # Fallback HTML
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>TradeUP FAQ App</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                .endpoint {{ background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 TradeUP FAQ App is Running!</h1>
                <p><strong>All systems loaded successfully!</strong></p>
                
                <h2>Available Endpoints:</h2>
                <div class="endpoint"> <a href="/docs/">API Documentation (Swagger)</a></div>
                <div class="endpoint"> <a href="/health">Health Check</a></div>
                <div class="endpoint">ℹ <a href="/version">Version Info</a></div>
                <div class="endpoint"> <a href="/test">Test Route</a></div>
                <div class="endpoint"> <a href="/api/system-status">System Status</a></div>
                
                <h2>Quick Test:</h2>
                <div class="endpoint">
                    <strong>FAQ Test:</strong> 
                    <code>POST /api/ask</code> with <code>{{"question": "How do I open an account?"}}</code>
                </div>
                
                <p><em>Note: Template not found, using fallback HTML. Error: {str(e)}</em></p>
            </div>
        </body>
        </html>
        """

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    print("Health route called!")
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'message': 'TradeUP FAQ App is running'
    })

@app.route('/version')
def version():
    """Get application version info"""
    print("Version route called!")
    return jsonify({
        'app_name': 'TradeUP Enhanced FAQ App',
        'version': '2.0',
        'flask_version': '2.x',
        'description': 'Smart FAQ System with Market Data and Memory'
    })

@app.route('/test')
def test_route():
    """Simple test route to verify Flask is working"""
    print("Test route called!")
    return jsonify({
        'message': 'Flask routes are working correctly!',
        'timestamp': datetime.now().isoformat(),
        'routes_working': True,
        'available_routes': [
            '/ - Home page',
            '/health - Health check',  
            '/version - Version info',
            '/test - This test route',
            '/docs/ - Swagger API documentation',
            '/api/ask - Main FAQ endpoint',
            '/api/system-status - System status'
        ]
    })

@app.route('/debug-routes')
def debug_routes():
    """Debug route to see all registered routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': str(rule)
        })
    return jsonify({
        'total_routes': len(routes),
        'routes': routes
    })

print("Regular routes defined...")

# ============================================================================
# NOW INITIALIZE API
# ============================================================================

api = Api(app, 
    doc='/docs/', 
    title='TradeUP Enhanced FAQ API', 
    description='Smart FAQ System with Market Data and Memory',
    version='2.0'
)

print("API initialized...")

# Define API models
ask_model = api.model('Question', {
    'question': fields.String(required=True, description='The FAQ question to ask', example='How do I open an account?')
})

# ============================================================================
# API ROUTES
# ============================================================================

@api.route('/api/system-status')
class SystemStatus(Resource):
    def get(self):
        """Get system status"""
        return {
            'timestamp': datetime.now().isoformat(),
            'status': 'active',
            'message': 'Diagnostic version - basic functionality test',
            'routes_registered': True
        }

@api.route('/api/ask')
class DiagnosticAsk(Resource):
    @api.expect(ask_model)
    def post(self):
        """Diagnostic FAQ endpoint"""
        data = request.get_json()
        question = data.get('question', '').strip()
        
        return {
            'success': True,
            'response': f'Diagnostic response for: {question}',
            'system_used': 'diagnostic',
            'timestamp': datetime.now().isoformat()
        }

print("API routes defined...")

if __name__ == '__main__':
    print("Starting diagnostic Flask app...")
    print("Testing route registration...")
    
    # Debug: Print all routes
    print("\nRegistered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.methods} {rule}")
    
    print(f"\nStarting server on http://localhost:8000/")
    print("Test these URLs:")
    print("  http://localhost:8000/")
    print("  http://localhost:8000/health") 
    print("  http://localhost:8000/test")
    print("  http://localhost:8000/debug-routes")
    print("  http://localhost:8000/docs/")
    
    app.run(debug=True, host='0.0.0.0', port=8000)