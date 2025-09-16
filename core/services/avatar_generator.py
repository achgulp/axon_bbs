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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# File path: axon_bbs/core/services/avatar_generator.py

import hashlib
import random
from PIL import Image, ImageDraw
from io import BytesIO
from django.core.files.base import ContentFile
from .encryption_utils import generate_checksum

def generate_cow_avatar(pubkey: str):
    """
    Generates a unique, deterministic cow avatar based on a user's public key.
    """
    # Use a hash of the pubkey to seed the generator for deterministic results
    seed = hashlib.sha256(pubkey.encode()).digest()
    
    # --- Color Palette Generation ---
    # Use different parts of the hash for different colors
    base_hue = int.from_bytes(seed[0:2], 'big') % 360
    spot_hue = (base_hue + (int.from_bytes(seed[2:4], 'big') % 120) + 120) % 360
    
    # Main body color (less saturated)
    body_color = f"hsl({base_hue}, 40%, 85%)"
    # Spot color (more saturated)
    spot_color = f"hsl({spot_hue}, 60%, 50%)"
    # Bell color
    bell_color = f"hsl({(base_hue + 60) % 360}, 70%, 60%)"

    # --- Create Image Canvas ---
    img = Image.new('RGB', (128, 128), color=body_color)
    draw = ImageDraw.Draw(img)
    
    # --- Draw Cow Features ---
    # Head
    draw.ellipse([(30, 20), (98, 80)], fill='#FFFFFF', outline='black', width=2)
    # Body
    draw.ellipse([(10, 60), (118, 120)], fill='#FFFFFF', outline='black', width=2)
    
    # Eyes
    draw.ellipse([(45, 40), (55, 50)], fill='black')
    draw.ellipse([(73, 40), (83, 50)], fill='black')
    
    # Nostrils
    draw.ellipse([(50, 65), (60, 75)], fill=body_color, outline='black', width=1)
    draw.ellipse([(68, 65), (78, 75)], fill=body_color, outline='black', width=1)
    
    # --- Generate Spots ---
    # Use the seed to create a predictable random sequence for spots
    spot_seed = int.from_bytes(seed[4:8], 'big')
    r = random.Random(spot_seed)
    
    num_spots = r.randint(3, 7)
    for _ in range(num_spots):
        spot_x = r.randint(15, 100)
        spot_y = r.randint(30, 110)
        spot_w = r.randint(10, 30)
        spot_h = r.randint(10, 30)
        draw.ellipse([(spot_x, spot_y), (spot_x + spot_w, spot_y + spot_h)], fill=spot_color)

    # Bell
    draw.rectangle([(60, 80), (68, 88)], fill=bell_color, outline='black')
    
    # --- Save Image to Buffer ---
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    
    # --- Return Django ContentFile ---
    checksum = generate_checksum(pubkey)
    filename = f"cow_{checksum[:12]}.png"
    return ContentFile(buffer.getvalue(), name=filename)
