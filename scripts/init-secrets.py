#!/usr/bin/env python3
import secrets
import os

def generate_secrets():
    env_path = ".env"
    example_path = ".env.example"
    
    if os.path.exists(env_path):
        print(f"⚠️  {env_path} already exists. Skipping initialization.")
        return

    if not os.path.exists(example_path):
        print(f"❌ {example_path} not found.")
        return

    jwt_secret = secrets.token_urlsafe(32)
    pg_password = secrets.token_urlsafe(16)
    
    with open(example_path, "r") as f:
        content = f.read()

    content = content.replace("your_super_secret_key_here", jwt_secret)
    content = content.replace("DB_PASSWORD=postgres", f"DB_PASSWORD={pg_password}")
    
    with open(env_path, "w") as f:
        f.write(content)
    
    print(f"✅ Created {env_path} with generated secrets.")
    print(f"🔑 JWT_SECRET: {jwt_secret}")
    print(f"🐘 DB_PASSWORD: {pg_password}")

if __name__ == "__main__":
    generate_secrets()
