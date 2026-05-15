"""
Downloads React 18 + Babel standalone into web/vendor/.
Run once:  python setup_web.py
"""
import urllib.request
from pathlib import Path

VENDOR = Path("web/vendor")

FILES = {
    "react.production.min.js":      "https://unpkg.com/react@18.3.1/umd/react.production.min.js",
    "react-dom.production.min.js":  "https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js",
    "babel.min.js":                 "https://unpkg.com/@babel/standalone@7.24.7/babel.min.js",
    "qrcodejs.min.js":              "https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js",
}


def main():
    VENDOR.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        dest = VENDOR / name
        if dest.exists():
            print(f"  ok {name} (already present)")
            continue
        print(f"  dl {name} ...", end=" ", flush=True)
        urllib.request.urlretrieve(url, dest)
        size = dest.stat().st_size // 1024
        print(f"{size} KB")
    print("\nDone. Run:  python main.py")


if __name__ == "__main__":
    main()
