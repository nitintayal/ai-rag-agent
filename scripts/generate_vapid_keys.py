#!/usr/bin/env python3
"""Generate VAPID key pair for Web Push notifications.

Run once and paste the output into your .env file:
    python scripts/generate_vapid_keys.py
"""

from py_vapid import Vapid

v = Vapid()
v.generate_keys()

private_key = v.private_pem().decode().strip()
public_key = v.public_key.get_encoded().decode()

print("Add these to your .env file:\n")
print(f'VAPID_PRIVATE_KEY="{private_key}"')
print(f'VAPID_PUBLIC_KEY="{public_key}"')
print('VAPID_CLAIMS_EMAIL="mailto:you@yourdomain.com"')
