
from __future__ import annotations
import sys


 

def main():
    from flask_app import app
    # Serve on all interfaces so you can connect from another device on the LAN
    app.run(host='0.0.0.0', port=5000, debug=False)
    return 0

if __name__ == "__main__":
    sys.exit(main())
