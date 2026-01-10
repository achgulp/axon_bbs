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

# Full path: axon_bbs/accounts/avatar_generator.py
import hashlib
import math
from PIL import Image, ImageDraw
from io import BytesIO
from django.core.files.base import ContentFile
from core.services.encryption_utils import generate_checksum

def get_int_from_bytes(byte_slice):
    """Helper to convert a slice of bytes into an integer."""
    return int.from_bytes(byte_slice, 'big')

def generate_cow_avatar(pubkey: str):
    """
    Generates a unique, deterministic cartoon cow avatar based on a user's public key.
    This version uses direct hash slicing to be cross-platform/version consistent.
    """
    seed = hashlib.sha256(pubkey.encode()).digest()
    
    # --- Color Palette Generation from Hash Bytes ---
    head_hue = get_int_from_bytes(seed[0:2]) % 360
    head_saturation = 30 + (seed[2] % 31)
    head_lightness = 75 + (seed[3] % 16)
    head_color = f"hsl({head_hue}, {head_saturation}%, {head_lightness}%)"

    spot_hue = (head_hue + 180 + (get_int_from_bytes(seed[4:6]) % 61) - 30) % 360
    spot_saturation = 60 + (seed[6] % 31)
    spot_lightness = 30 + (seed[7] % 21)
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

    # --- Spot Generation from Hash Bytes ---
    num_spots = 1 if seed[8] % 5 < 3 else 2
    spot_sizes = [15 + (seed[9] % 8), 8 + (seed[10] % 7)]
    if seed[11] % 2 == 0:
        spot_sizes.reverse()

    for i in range(num_spots):
        spot_radius = spot_sizes[i]
        
        angle_byte = seed[12 + (i*2)]
        dist_byte = seed[13 + (i*2)]

        angle = (angle_byte / 255.0) * 2 * math.pi
        distance_from_center = head_radius * (0.4 + (dist_byte / 255.0) * 0.4)
        spot_x = head_center_x + distance_from_center * math.cos(angle)
        spot_y = head_center_y + distance_from_center * math.sin(angle)
        
        if (head_center_y + 12 < spot_y + spot_radius):
            spot_y = head_center_y - (spot_y - head_center_y)

        # MODIFIED: Removed the polygon-drawing logic. All spots are now guaranteed to be
        # single, simple ellipses with varying dimensions.
        w_offset_byte = seed[17 + i]
        h_offset_byte = seed[18 + i]
        spot_w = spot_radius * 2 * (0.8 + (w_offset_byte / 255.0) * 0.4)
        spot_h = spot_radius * 2 * (0.8 + (h_offset_byte / 255.0) * 0.4)
        draw.ellipse([(spot_x - spot_w / 2, spot_y - spot_h / 2), (spot_x + spot_w / 2, spot_y + spot_h / 2)], fill=spot_color, outline='black', width=1)
    
    # Eyes, Nostrils, and Smile are drawn LAST
    eye_radius = 5
    draw.ellipse([head_center_x - 20 - eye_radius, head_center_y - 10 - eye_radius, head_center_x - 20 + eye_radius, head_center_y - 10 + eye_radius], fill='black')
    draw.ellipse([head_center_x + 20 - eye_radius, head_center_y - 10 - eye_radius, head_center_x + 20 + eye_radius, head_center_y - 10 + eye_radius], fill='black')

    nostril_width, nostril_height = 6, 8
    draw.ellipse([head_center_x - 15 - nostril_width // 2, head_center_y + 28 - nostril_height // 2, head_center_x - 15 + nostril_width // 2, head_center_y + 28 + nostril_height // 2], fill='black')
    draw.ellipse([head_center_x + 15 - nostril_width // 2, head_center_y + 28 - nostril_height // 2, head_center_x + 15 + nostril_width // 2, head_center_y + 28 + nostril_height // 2], fill='black')

    draw.arc([head_center_x - 18, head_center_y + 38, head_center_x + 18, head_center_y + 58], start=20, end=160, fill='black', width=2)
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    
    checksum = generate_checksum(pubkey)
    filename = f"cow_{checksum[:12]}.png"
    
    return ContentFile(buffer.getvalue()), filename
