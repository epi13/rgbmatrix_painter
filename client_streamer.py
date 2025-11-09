# Simple network streaming client: sends frames to the Pi Flask server.
# Usage:
#   python client_streamer.py --host http://pi.local:5000 --image frame.png
#   python client_streamer.py --host http://pi.local:5000 --folder frames/ --fps 15
from __future__ import annotations
import argparse, time, os, glob, requests

def send_frame(host, path, fit=True):
    with open(path, 'rb') as f:
        r = requests.post(f"{host}/frame?fit={1 if fit else 0}", data=f.read(), headers={'Content-Type':'image/png'})
        r.raise_for_status()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--host', required=True, help='http://<pi>:5000')
    p.add_argument('--image', help='Single PNG to send')
    p.add_argument('--folder', help='Folder of PNGs to stream alphabetically')
    p.add_argument('--fps', type=int, default=10)
    p.add_argument('--loop', action='store_true')
    args = p.parse_args()

    if args.image:
        send_frame(args.host, args.image)
        return

    if args.folder:
        files = sorted(glob.glob(os.path.join(args.folder, '*.png')))
        if not files:
            print('No PNG files in folder'); return
        delay = max(1, int(1000/max(1,args.fps))) / 1000.0
        while True:
            for path in files:
                send_frame(args.host, path)
                time.sleep(delay)
            if not args.loop: break

if __name__=='__main__':
    main()
