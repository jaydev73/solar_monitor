#!/usr/bin/env python3
"""Set the dashboard password safely.

Asks twice (so typos are caught), writes the hash straight into .env
(no copy/paste), then re-reads .env and proves the saved hash matches.
Run it from the same folder as app.py:   python set_password.py
"""
import getpass
import os
import sys
from werkzeug.security import generate_password_hash, check_password_hash

ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
KEY = "DASH_PASS_HASH"

if not os.path.exists(ENV):
    sys.exit(f"No .env found at {ENV}. Copy .env.example to .env first.")

p1 = getpass.getpass("New password: ")
p2 = getpass.getpass("Repeat it:    ")
if p1 != p2:
    sys.exit("Passwords did not match. Nothing was changed.")
if len(p1) < 10:
    sys.exit("Use at least 10 characters (a few random words works well). Nothing was changed.")

new_line = f"{KEY}='{generate_password_hash(p1)}'\n"
lines = open(ENV, encoding="utf-8").read().splitlines(keepends=True)
out, replaced = [], False
for ln in lines:
    if ln.split("=", 1)[0].strip() == KEY:
        if not replaced:
            out.append(new_line)
        replaced = True          # drops duplicate DASH_PASS_HASH lines too
    else:
        out.append(ln)
if not replaced:
    if out and not out[-1].endswith("\n"):
        out[-1] += "\n"
    out.append(new_line)
open(ENV, "w", encoding="utf-8").writelines(out)
os.chmod(ENV, 0o600)

# Re-read the file exactly the way app.py will, and verify.
try:
    from dotenv import dotenv_values
    stored = dotenv_values(ENV)[KEY]
except ImportError:
    stored = next(l.split("=", 1)[1].strip().strip("'") for l in open(ENV) if l.startswith(KEY + "="))
ok = check_password_hash(stored, p1)
print(f"\nSaved to {ENV}")
print("Verification:", "OK - this password will work." if ok else "FAILED - do not use, tell Claude.")
print("Now restart app.py (the .env file is only read at startup).")
