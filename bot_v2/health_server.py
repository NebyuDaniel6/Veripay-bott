"""
Simple HTTP health server for Render keep-alive
Runs alongside the Telegram bot
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import os

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK - Bot is running')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def start_health_server():
    """Start HTTP health server on port 8080"""
    port = int(os.environ.get('HEALTH_PORT', '8080'))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"Health server started on port {port}")
    server.serve_forever()

def run_health_server():
    """Run health server in background thread"""
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    return health_thread
