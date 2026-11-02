"""Start the local PWA on a stable origin so saved workspaces survive restarts."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import argparse,webbrowser

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8765);p.add_argument('--no-browser',action='store_true');args=p.parse_args()
    app=Path(__file__).resolve().parent
    server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(SimpleHTTPRequestHandler,directory=str(app)))
    url=f'http://127.0.0.1:{server.server_port}/index.html'
    print('DigiBattle Deck Lab: '+url,flush=True)
    print('Keep this window open. Press Ctrl+C to stop. Your workspaces stay in this browser.',flush=True)
    if not args.no_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
