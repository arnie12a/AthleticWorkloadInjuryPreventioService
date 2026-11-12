
import os
import getpass

import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]

email = input("Email: ")
password = getpass.getpass("Password: ")

response = httpx.post(
    f"{SUPABASE_URL}/auth/v1/token",
    params={"grant_type": "password"},
    headers={
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json"
    },
    json={
        "email": email,
        "password": password
    },
    timeout=15.0
)

if response.status_code != 200:
    print("Login failed:", response.status_code)
    print(response.text)
    raise SystemExit(1)

data = response.json()

print("\nLogin successful!")
print("Access token:")
print(data["access_token"])
