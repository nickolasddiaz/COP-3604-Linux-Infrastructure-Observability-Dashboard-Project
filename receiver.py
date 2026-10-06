#!/usr/bin/env python3
# based on https://gist.github.com/mdonkers/63e115cc0c79b4f6b8b3a6b797e485c7

from http.server import BaseHTTPRequestHandler, HTTPServer
import asyncio
from named_pipe import NamedPipe

def start_receiver(port: int = 8080):
    """
    Starts a web server that receives requests/metrics
    Once received it will send that data to the named pipe
    """
    namedPipe: NamedPipe = NamedPipe()
    asyncio.run(namedPipe.set_writing_mode())

    # BaseHTTPRequestHandler to handle the post request
    class Server(BaseHTTPRequestHandler):
        def _set_response(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

        def do_POST(self):
            content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
            post_data = self.rfile.read(content_length) # <--- Gets the data itself

            print(post_data)
            # send data to the named pipe
            asyncio.run(namedPipe.send_message(post_data))

            self._set_response()
            self.wfile.write("POST request for {}".format(self.path).encode('utf-8'))


    def run(server_class=HTTPServer, handler_class=Server):
        server_address = ('', port)
        httpd = server_class(server_address, handler_class)
        print(f"Starting httpd server on {port}\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()
        print('Stopping Server\n')


    run()

if __name__ == "__main__":
    start_receiver()