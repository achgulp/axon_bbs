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
    # Use different parts of the hash for different colors
    r = random.Random(seed) # Use a local random instance for deterministic color generation

    # Main head color
    head_hue = r.randint(0, 359)
    head_saturation = r.randint(30, 60)
    head_lightness = r.randint(75, 90)
    head_color = f"hsl({head_hue}, {head_saturation}%, {head_lightness}%)"

    # Spot color (contrast with head)
    spot_hue = (head_hue + 180 + r.randint(-30, 30)) % 360 # Roughly opposite hue
    spot_saturation = r.randint(60, 90)
    spot_lightness = r.randint(30, 50)
    spot_color = f"hsl({spot_hue}, {spot_saturation}%, {spot_lightness}%)"

    # Muzzle color (lighter, desaturated version of head or a neutral tone)
    muzzle_color = f"hsl({head_hue}, {head_saturation // 2}%, {head_lightness + 5}%)"
    if head_lightness > 80: # Ensure muzzle is not too bright if head is already very light
        muzzle_color = "#E0E0E0" # Neutral light grey/off-white

    # Horn color (fixed)
    horn_color = "#A0522D" # SaddleBrown

    # --- Create Image Canvas ---
    img = Image.new('RGB', (128, 128), color='#FFFFFF') # White background
    draw = ImageDraw.Draw(img)
    
    # --- Draw Cow Features ---
    
    # Head (main circle)
    head_center_x, head_center_y = 64, 60
    head_radius = 45
    draw.ellipse([head_center_x - head_radius, head_center_y - head_radius, 
                  head_center_x + head_radius, head_center_y + head_radius], 
                 fill=head_color, outline='black', width=2)
    
    # Muzzle (oval)
    muzzle_width = 60
    muzzle_height = 30
    draw.ellipse([head_center_x - muzzle_width // 2, head_center_y + 15,
                  head_center_x + muzzle_width // 2, head_center_y + 15 + muzzle_height],
                 fill=muzzle_color, outline='black', width=2)

    # Eyes (small black circles)
    eye_radius = 4
    draw.ellipse([head_center_x - 20 - eye_radius, head_center_y - 15 - eye_radius, 
                  head_center_x - 20 + eye_radius, head_center_y - 15 + eye_radius], 
                 fill='black')
    draw.ellipse([head_center_x + 20 - eye_radius, head_center_y - 15 - eye_radius, 
                  head_center_x + 20 + eye_radius, head_center_y - 15 + eye_radius], 
                 fill='black')

    # Nostrils (smaller black ovals on the muzzle)
    nostril_width = 5
    nostril_height = 8
    draw.ellipse([head_center_x - 15 - nostril_width // 2, head_center_y + 25 - nostril_height // 2,
                  head_center_x - 15 + nostril_width // 2, head_center_y + 25 + nostril_height // 2],
                 fill='black')
    draw.ellipse([head_center_x + 15 - nostril_width // 2, head_center_y + 25 - nostril_height // 2,
                  head_center_x + 15 + nostril_width // 2, head_center_y + 25 + nostril_height // 2],
                 fill='black')

    # Smile (arc)
    draw.arc([head_center_x - 20, head_center_y + 35,
              head_center_x + 20, head_center_y + 55],
             start=0, end=180, fill='black', width=2)

    # Ears (triangular/leaf shape)
    ear_base_y = head_center_y - head_radius + 10
    ear_tip_y = head_center_y - head_radius - 15

    # Left ear
    draw.polygon([ (head_center_x - head_radius + 5, ear_base_y),
                   (head_center_x - head_radius - 15, ear_base_y - 10),
                   (head_center_x - head_radius + 20, ear_tip_y) ], 
                 fill=head_color, outline='black', width=2)
    
    # Right ear
    draw.polygon([ (head_center_x + head_radius - 5, ear_base_y),
                   (head_center_x + head_radius + 15, ear_base_y - 10),
                   (head_center_x + head_radius - 20, ear_tip_y) ], 
                 fill=head_color, outline='black', width=2)
    
    # Horns
    horn_bottom_y = head_center_y - head_radius - 5
    horn_tip_y = horn_bottom_y - 20
    horn_width = 8

    # Left horn
    draw.polygon([(head_center_x - 25, horn_bottom_y),
                  (head_center_x - 25 - horn_width, horn_tip_y),
                  (head_center_x - 25 + horn_width, horn_tip_y)],
                 fill=horn_color, outline='black', width=1)
    # Right horn
    draw.polygon([(head_center_x + 25, horn_bottom_y),
                  (head_center_x + 25 - horn_width, horn_tip_y),
                  (head_center_x + 25 + horn_width, horn_tip_y)],
                 fill=horn_color, outline='black', width=1)


    # --- Generate Spots (within the head circle, avoiding muzzle area) ---
    num_spots = r.randint(3, 6) # Fewer, larger spots for this style
    for _ in range(num_spots):
        # Generate coordinates within the head circle but outside the muzzle
        while True:
            spot_x = r.randint(head_center_x - head_radius + 10, head_center_x + head_radius - 10)
            spot_y = r.randint(head_center_y - head_radius + 10, head_center_y + head_radius - 10)
            
            # Check if within head and outside muzzle
            dist_to_head_center = ((spot_x - head_center_x)**2 + (spot_y - head_center_y)**2)**0.5
            is_within_head = dist_to_head_center < head_radius - 5 # A little margin

            is_over_muzzle = (head_center_x - muzzle_width // 2 < spot_x < head_center_x + muzzle_width // 2 and
                              head_center_y + 15 < spot_y < head_center_y + 15 + muzzle_height)
            
            if is_within_head and not is_over_muzzle:
                break

        spot_size_base = r.randint(20, 35) # Larger spots
        spot_size_var = r.randint(-5, 5) # Slight variation
        spot_w = spot_size_base + spot_size_var
        spot_h = spot_size_base - spot_size_var # Slightly oval

        draw.ellipse([(spot_x - spot_w // 2, spot_y - spot_h // 2), 
                      (spot_x + spot_w // 2, spot_y + spot_h // 2)], 
                     fill=spot_color, outline='black', width=1)
    
    # --- Save Image to Buffer ---
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    
    # --- Return Django ContentFile and the filename ---
    checksum = generate_checksum(pubkey)
    filename = f"cow_{checksum[:12]}.png"
    
    return ContentFile(buffer.getvalue(), name=filename), filename
