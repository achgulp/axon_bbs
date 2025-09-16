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
import math
from PIL import Image, ImageDraw
from io import BytesIO
from django.core.files.base import ContentFile
from .encryption_utils import generate_checksum

def generate_cow_avatar(pubkey: str):
    """
    Generates a unique, deterministic cartoon cow avatar based on a user's public key.
    """
    seed = hashlib.sha256(pubkey.encode()).digest()
    r = random.Random(seed)
    
    # --- Color Palette Generation ---
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
        muzzle_color = "#F5E6D3"

    ear_inner_color = "#E0B080"

    # --- Create Image Canvas ---
    img = Image.new('RGB', (128, 128), color='#FFFFFF')
    draw = ImageDraw.Draw(img)
    
    # --- Draw Cow Features ---
    head_center_x, head_center_y = 64, 64
    head_radius = 45

    # Ears
    ear_width, ear_height = 28, 40
    draw.ellipse([head_center_x - head_radius - 5, head_center_y - head_radius + 5, head_center_x - head_radius + ear_width - 5, head_center_y - head_radius + ear_height + 5], fill=head_color, outline='black', width=2)
    draw.ellipse([head_center_x - head_radius + 2, head_center_y - head_radius + 15, head_center_x - head_radius + 12, head_center_y - head_radius + ear_height - 5], fill=ear_inner_color)
    draw.ellipse([head_center_x + head_radius - ear_width + 5, head_center_y - head_radius + 5, head_center_x + head_radius + 5, head_center_y - head_radius + ear_height + 5], fill=head_color, outline='black', width=2)
    draw.ellipse([head_center_x + head_radius - 12, head_center_y - head_radius + 15, head_center_x + head_radius - 2, head_center_y - head_radius + ear_height - 5], fill=ear_inner_color)
    
    # Head
    draw.ellipse([head_center_x - head_radius, head_center_y - head_radius, head_center_x + head_radius, head_center_y + head_radius], fill=head_color, outline='black', width=2)
    
    # Muzzle
    muzzle_width = 60
    muzzle_height = 35
    draw.ellipse([head_center_x - muzzle_width // 2, head_center_y + 12, head_center_x + muzzle_width // 2, head_center_y + 12 + muzzle_height], fill=muzzle_color, outline='black', width=2)

    # --- START FIX: Reworked Spot Generation ---
    num_spots = r.choice([1, 1, 1, 2, 2]) # Make one spot more common
    spot_sizes = [r.randint(15, 22), r.randint(8, 14)] # One large, one small
    r.shuffle(spot_sizes)

    for i in range(num_spots):
        spot_radius = spot_sizes[i]
        
        while True:
            # Place spots towards the periphery, not in the center
            angle = r.uniform(0, 2 * math.pi)
            distance_from_center = r.uniform(head_radius * 0.4, head_radius - spot_radius - 2) # Keep spots away from the edge
            spot_x = head_center_x + distance_from_center * math.cos(angle)
            spot_y = head_center_y + distance_from_center * math.sin(angle)
            
            # Ensure spot doesn't overlap the muzzle area
            is_over_muzzle = (head_center_y + 12 < spot_y + spot_radius)
            if not is_over_muzzle:
                break
        
        # Decide if the spot is an ellipse or a polygon
        if r.choice([True, False]):
            # Draw a slightly irregular ellipse
            spot_w = spot_radius * 2 * r.uniform(0.8, 1.2)
            spot_h = spot_radius * 2 * r.uniform(0.8, 1.2)
            draw.ellipse([(spot_x - spot_w / 2, spot_y - spot_h / 2), (spot_x + spot_w / 2, spot_y + spot_h / 2)], fill=spot_color, outline='black', width=1)
        else:
            # Draw a random polygon
            points = []
            num_vertices = r.randint(3, 6)
            for j in range(num_vertices):
                angle_vert = (2 * math.pi / num_vertices) * j
                radius_vert = spot_radius * r.uniform(0.7, 1.3)
                px = spot_x + radius_vert * math.cos(angle_vert)
                py = spot_y + radius_vert * math.sin(angle_vert)
                points.append((px, py))
            draw.polygon(points, fill=spot_color, outline='black', width=1)
    
    # --- END FIX ---

    # Eyes, Nostrils, and Smile are drawn LAST
    eye_radius = 5
    draw.ellipse([head_center_x - 20 - eye_radius, head_center_y - 10 - eye_radius, head_center_x - 20 + eye_radius, head_center_y - 10 + eye_radius], fill='black')
    draw.ellipse([head_center_x + 20 - eye_radius, head_center_y - 10 - eye_radius, head_center_x + 20 + eye_radius, head_center_y - 10 + eye_radius], fill='black')

    nostril_width, nostril_height = 6, 8
    draw.ellipse([head_center_x - 15 - nostril_width // 2, head_center_y + 28 - nostril_height // 2, head_center_x - 15 + nostril_width // 2, head_center_y + 28 + nostril_height // 2], fill='black')
    draw.ellipse([head_center_x + 15 - nostril_width // 2, head_center_y + 28 - nostril_height // 2, head_center_x + 15 + nostril_width // 2, head_center_y + 28 + nostril_height // 2], fill='black')

    draw.arc([head_center_x - 18, head_center_y + 38, head_center_x + 18, head_center_y + 58], start=20, end=160, fill='black', width=2)
    
    # --- Save Image to Buffer ---
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    
    # --- Return Django ContentFile and the filename ---
    checksum = generate_checksum(pubkey)
    filename = f"cow_{checksum[:12]}.png"
    
    return ContentFile(buffer.getvalue()), filename
