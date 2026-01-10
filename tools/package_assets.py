# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7
#
# Full path: axon_bbs/tools/package_assets.py
#
# This script packages the necessary assets for the HexGL game applet
# from the source HexGL.tar file into a deployable hexgl_assets.zip.

import tarfile
import zipfile
import os
from io import BytesIO

def create_asset_package(tar_path="HexGL.tar", zip_path="hexgl_assets.zip"):
    """
    Extracts specific game assets from the HexGL.tar archive and packages
    them into a flat .zip file for the Axon BBS applet.

    Args:
        tar_path (str): The path to the input HexGL.tar file.
        zip_path (str): The path for the output hexgl_assets.zip file.
    """
    print(f"Attempting to open TAR archive: {tar_path}")
    if not os.path.exists(tar_path):
        print(f"Error: Input file '{tar_path}' not found.")
        return

    # Corrected list of assets based on the provided tar contents.
    # The prefix for all file paths inside the archive.
    PATH_PREFIX = "HexGL/"

    # The list of individual asset files required by the game.
    asset_list = [
        "css/BebasNeue-webfont.eot", "css/BebasNeue-webfont.svg",
        "css/BebasNeue-webfont.ttf", "css/BebasNeue-webfont.woff",
        "css/title.png", "css/help-0.png", "css/help-1.png",
        "css/help-2.png", "css/help-3.png",
        "geometries/ships/feisar/feisar.js",
        "geometries/tracks/cityscape/track.js",
        "geometries/tracks/cityscape/scrapers1.js",
        "geometries/tracks/cityscape/scrapers2.js",
        "geometries/tracks/cityscape/start.js",
        "geometries/tracks/cityscape/startbanner.js",
        "textures/ships/feisar/diffuse.jpg",
        "textures/ships/feisar/normal.jpg",
        "textures/ships/feisar/specular.jpg",
        "textures/ships/feisar/booster/booster.png",
        "textures/tracks/cityscape/diffuse.jpg",
        "textures/tracks/cityscape/normal.jpg",
        "textures/tracks/cityscape/specular.jpg",
        "textures/tracks/cityscape/scrapers1/diffuse.jpg",
        "textures/tracks/cityscape/scrapers1/specular.jpg",
        "textures/tracks/cityscape/scrapers2/diffuse.jpg",
        "textures/tracks/cityscape/scrapers2/specular.jpg",
        "textures/tracks/cityscape/start/diffuse.jpg",
        "textures/tracks/cityscape/start/specular.jpg",
        "textures/skybox/dawnclouds/nx.jpg",
        "textures/skybox/dawnclouds/ny.jpg",
        "textures/skybox/dawnclouds/nz.jpg",
        "textures/skybox/dawnclouds/px.jpg",
        "textures/skybox/dawnclouds/py.jpg",
        "textures/skybox/dawnclouds/pz.jpg",
        "textures/hud/hud-bg.png",
        "textures/hud/hud-fg-shield.png",
        "textures/hud/hud-fg-speed.png",
        "textures/particles/spark.png",
        "textures/particles/cloud.png",
        "textures/particles/damage.png",
    ]

    # Prepend the directory prefix to each asset path.
    required_assets = {PATH_PREFIX + path for path in asset_list}
    found_count = 0

    try:
        with tarfile.open(tar_path, 'r') as tar, zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            print(f"Successfully opened {tar_path}. Creating ZIP file: {zip_path}")
            print("--------------------")

            for member in tar.getmembers():
                if member.name in required_assets and member.isfile():
                    # Extract the file data into memory
                    file_data = tar.extractfile(member).read()
                    
                    # Get just the filename (e.g., "diffuse.jpg") for the zip archive
                    archive_name = os.path.basename(member.name)
                    
                    # Write the data to the zip file with a flat structure
                    zipf.writestr(archive_name, file_data)
                    
                    print(f"Packed: {archive_name}")
                    found_count += 1
            
            print("--------------------")
            if found_count == len(required_assets):
                print(f"Success! Found and packed all {found_count} required files.")
                print(f"Your asset package is ready: {zip_path}")
            else:
                 print(f"Warning: Process completed, but only found {found_count} out of {len(required_assets)} required files.")
                 print("The generated zip file may be incomplete.")


    except (tarfile.ReadError, FileNotFoundError) as e:
        print(f"Error processing the TAR file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    create_asset_package()


