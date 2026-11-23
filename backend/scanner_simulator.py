"""
scanner_simulator.py - a separate "device" that talks to the edge service over HTTP.

It pretends to be a network document scanner in an office: it picks up files from a
folder and POSTs them one by one to the edge service (/api/classify), then prints the
category, confidence and department that came back. Open the dashboard while it runs -
the documents appear live.

Usage:
  python scanner_simulator.py                                   # sends all demo documents once
  python scanner_simulator.py --folder ../sample_documents/abnormal
  python scanner_simulator.py --interval 3 --loop               # keep scanning every 3 s
  python scanner_simulator.py --url http://192.168.1.20:5000    # edge device on another machine
"""
import argparse
import glob
import os
import random
import time

import requests

DEFAULT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sample_documents", "normal")


def main():
    p = argparse.ArgumentParser(description="Office scanner simulator (HTTP client for the edge service)")
    p.add_argument("--url", default="http://127.0.0.1:5000", help="edge service base URL")
    p.add_argument("--folder", default=DEFAULT_FOLDER, help="folder with documents to 'scan'")
    p.add_argument("--interval", type=float, default=1.5, help="seconds between documents")
    p.add_argument("--loop", action="store_true", help="keep sending random documents forever")
    p.add_argument("--device", default="scanner-sim-01", help="device name reported to the service")
    args = p.parse_args()

    try:
        health = requests.get(f"{args.url}/api/health", timeout=5).json()
    except requests.RequestException:
        print(f"Edge service not reachable at {args.url}. Start it first:  python app.py")
        return
    print(f"Connected to {health['service']} on host '{health['host']}' (model v{health['model_version']})\n")

    files = sorted(f for f in glob.glob(os.path.join(args.folder, "*")) if os.path.isfile(f))
    if not files:
        print("No files found in", args.folder)
        return

    print(f"{'FILE':36s} {'HTTP':>4s}  {'CATEGORY':20s} {'CONF':>6s}  {'DEPARTMENT':32s} {'TIME':>8s}")
    print("-" * 115)
    sent = 0
    while True:
        batch = [random.choice(files)] if args.loop else files
        for path in batch:
            t0 = time.time()
            with open(path, "rb") as fh:
                r = requests.post(f"{args.url}/api/classify", files={"file": (os.path.basename(path), fh)},
                                  data={"source": args.device}, timeout=120)
            ms = (time.time() - t0) * 1000
            data = r.json()
            name = os.path.basename(path)[:35]
            if r.ok:
                flag = "  [REVIEW]" if data["status"] == "needs_review" else ""
                print(f"{name:36s} {r.status_code:>4d}  {data['final_category']:20s} {data['confidence'] * 100:5.1f}%  "
                      f"{data['department'][:32]:32s} {ms:6.0f}ms{flag}")
            else:
                print(f"{name:36s} {r.status_code:>4d}  REJECTED: {data.get('error')}")
            sent += 1
            time.sleep(args.interval)
        if not args.loop:
            break
    print(f"\nDone - {sent} document(s) sent over HTTP. Check the dashboard for live results.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScanner stopped.")
