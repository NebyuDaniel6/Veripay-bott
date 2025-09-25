import os
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

port = int(os.environ.get("PORT", 8080))
server = HTTPServer(('0.0.0.0', port), Handler)
server.serve_forever()
