"""
Simple web server that handles both webhook and health endpoints
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import threading
from urllib.parse import urlparse, parse_qs

class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK - Bot is running')
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def do_POST(self):
        if self.path == '/webhook':
            # Forward to Telegram webhook handler
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # For now, just return OK - the actual webhook handling is done by the bot
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def start_web_server():
    """Start web server on the main port"""
    port = int(os.environ.get('PORT', '10000'))
    server = HTTPServer(('0.0.0.0', port), WebHandler)
    print(f"Web server started on port {port}")
    server.serve_forever()

def run_web_server():
    """Run web server in background thread"""
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    return web_thread
