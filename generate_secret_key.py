# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


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
