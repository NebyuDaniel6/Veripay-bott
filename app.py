print("Starting VeriPay Bot...")
import os
print(f"PORT: {os.environ.get('PORT', 'NOT_SET')}")
print(f"BOT_TOKEN: {'SET' if os.environ.get('BOT_TOKEN') else 'NOT_SET'}")

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {"status": "VeriPay Bot is running", "path": self.path}
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {"status": "POST received", "path": self.path}
        self.wfile.write(json.dumps(response).encode())

port = int(os.environ.get("PORT", 10000))
print(f"Starting server on port {port}")
server = HTTPServer(('0.0.0.0', port), Handler)
print("Server started successfully!")
server.serve_forever()
