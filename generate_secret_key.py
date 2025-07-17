# axon_bbs/generate_secret_key.py
import random
import string
import os

def generate_secret_key(length=50):
    """Generate a random Django SECRET_KEY."""
    chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(random.choice(chars) for _ in range(length))

if __name__ == '__main__':
    secret_key = generate_secret_key()
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    with open(env_path, 'w') as f:
        f.write("SECRET_KEY=" + secret_key + "\n")
    print("Generated SECRET_KEY and saved to " + env_path + ". Add .env to .gitignore!")
