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

# Full path: axon_bbs/core/services/avatar_generator.py
import hashlib
import random
from PIL import Image, ImageDraw
from io import BytesIO
from django.core.files.base import ContentFile
from .encryption_utils import generate_checksum

def generate_cow_avatar(pubkey: str):
    """
    Generates a unique, deterministic cartoon cow avatar based on a user's public key.
    """
    # Use a hash of the pubkey to seed the generator for deterministic results
    seed = hashlib.sha256(pubkey.encode()).digest()
    
    # --- Color Palette Generation ---
    r = random.Random(seed) 
    head_hue = r.randint(0, 359)
    head_saturation = r.randint(30, 60)
    head_lightness = r.randint(75, 90)
    head_color = f"hsl({head_hue}, {head_saturation}%, {head_lightness}%)"

    spot_hue = (head_hue + 180 + r.randint(-30, 30)) % 360
    spot_saturation = r.randint(60, 90)
    spot_lightness = r.randint(30, 50)
    spot_color = f"hsl({spot_hue}, {spot_saturation}%, {spot_lightness}%)"
    
    muzzle_color = f"hsl({head_hue}, {head_saturation // 2}%, {head_lightness + 5}%)"
    if head_lightness > 80:
        muzzle_color = "#E0E0E0"

    horn_color = "#A0522D"

    # --- Create Image Canvas ---
    img = Image.new('RGB', (128, 128), color='#FFFFFF')
    draw = ImageDraw.Draw(img)
    
    # --- Draw Cow Features ---
    head_center_x, head_center_y = 64, 60
    head_radius = 45
    
    # Head (main circle)
    draw.ellipse([head_center_x - head_radius, head_center_y - head_radius, 
                  head_center_x + head_radius, head_center_y + head_radius], 
                 fill=head_color, outline='black', width=2)
    
    # Muzzle (oval)
    muzzle_width = 60
    muzzle_height = 30
    draw.ellipse([head_center_x - muzzle_width // 2, head_center_y + 15,
                  head_center_x + muzzle_width // 2, head_center_y + 15 + muzzle_height],
                 fill=muzzle_color, outline='black', width=2)

    # --- START FIX: Drawing order and ear position ---

    # Ears (moved closer to the head)
    ear_color = '#E0B080'
    draw.polygon([ (head_center_x - head_radius + 15, head_center_y - head_radius + 20),
                   (head_center_x - head_radius - 10, head_center_y - head_radius),
                   (head_center_x - head_radius + 5, head_center_y - head_radius - 10) ], 
                 fill=ear_color, outline='black', width=2)
    draw.polygon([ (head_center_x + head_radius - 15, head_center_y - head_radius + 20),
                   (head_center_x + head_radius + 10, head_center_y - head_radius),
                   (head_center_x + head_radius - 5, head_center_y - head_radius - 10) ], 
                 fill=ear_color, outline='black', width=2)
    
    # Horns
    horn_bottom_y = head_center_y - head_radius + 5
    horn_tip_y = horn_bottom_y - 20
    horn_width = 8
    draw.polygon([(head_center_x - 20, horn_bottom_y), (head_center_x - 20 - horn_width, horn_tip_y), (head_center_x - 20 + horn_width, horn_tip_y)], fill=horn_color, outline='black', width=1)
    draw.polygon([(head_center_x + 20, horn_bottom_y), (head_center_x + 20 - horn_width, horn_tip_y), (head_center_x + 20 + horn_width, horn_tip_y)], fill=horn_color, outline='black', width=1)

    # Generate Spots FIRST
    num_spots = r.randint(3, 6)
    for _ in range(num_spots):
        while True:
            spot_x = r.randint(head_center_x - head_radius + 10, head_center_x + head_radius - 10)
            spot_y = r.randint(head_center_y - head_radius + 10, head_center_y + 10) # Keep spots in upper area
            dist_to_head_center = ((spot_x - head_center_x)**2 + (spot_y - head_center_y)**2)**0.5
            if dist_to_head_center < head_radius - 5:
                break
        spot_size_base = r.randint(20, 35)
        spot_size_var = r.randint(-5, 5)
        spot_w, spot_h = spot_size_base + spot_size_var, spot_size_base - spot_size_var
        draw.ellipse([(spot_x - spot_w // 2, spot_y - spot_h // 2), (spot_x + spot_w // 2, spot_y + spot_h // 2)], fill=spot_color, outline='black', width=1)

    # Eyes, Nostrils, and Smile are drawn LAST so they are always on top
    eye_radius = 4
    draw.ellipse([head_center_x - 20 - eye_radius, head_center_y - 15 - eye_radius, head_center_x - 20 + eye_radius, head_center_y - 15 + eye_radius], fill='black')
    draw.ellipse([head_center_x + 20 - eye_radius, head_center_y - 15 - eye_radius, head_center_x + 20 + eye_radius, head_center_y - 15 + eye_radius], fill='black')

    nostril_width, nostril_height = 5, 8
    draw.ellipse([head_center_x - 15 - nostril_width // 2, head_center_y + 25 - nostril_height // 2, head_center_x - 15 + nostril_width // 2, head_center_y + 25 + nostril_height // 2], fill='black')
    draw.ellipse([head_center_x + 15 - nostril_width // 2, head_center_y + 25 - nostril_height // 2, head_center_x + 15 + nostril_width // 2, head_center_y + 25 + nostril_height // 2], fill='black')

    draw.arc([head_center_x - 20, head_center_y + 35, head_center_x + 20, head_center_y + 55], start=0, end=180, fill='black', width=2)
    # --- END FIX ---
    
    # --- Save Image to Buffer ---
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    
    # --- Return Django ContentFile and the filename ---
    checksum = generate_checksum(pubkey)
    filename = f"cow_{checksum[:12]}.png"
    
    return ContentFile(buffer.getvalue()), filename
