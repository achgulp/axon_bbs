# Full path: axon_bbs/core/services/high_score_service.py
import threading
import time
import logging
import json
from django.db import transaction
from core.models import AppletData, HighScore, Applet

logger = logging.getLogger(__name__)

class HighScoreService:
    def __init__(self, poll_interval=300): # Poll every 5 minutes
        self.poll_interval = poll_interval
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()
        logger.info("High Score Service thread started.")

    def _run(self):
        time.sleep(60) # Initial delay before first run
        while True:
            try:
                self.process_scores()
            except Exception as e:
                logger.error(f"Error in high score service poll loop: {e}", exc_info=True)
            
            time.sleep(self.poll_interval)
    
    def process_scores(self):
        from .service_manager import service_manager
        logger.info("Starting high score processing run...")

        # Find applet data for applets categorized as 'Game'
        game_applet_data = AppletData.objects.filter(applet__category__name__iexact='Game')
        
        if not game_applet_data.exists():
            logger.info("No game applet data found to process.")
            return

        processed_count = 0
        with transaction.atomic():
            for data_instance in game_applet_data:
                try:
                    # Decrypt the manifest content
                    manifest = data_instance.data_manifest
                    decrypted_bytes = service_manager.sync_service.get_decrypted_content(manifest)
                    
                    if not decrypted_bytes:
                        continue

                    content = json.loads(decrypted_bytes.decode('utf-8'))
                    applet_saved_data = content.get('data', {})

                    # Check for the standardized 'score' key
                    if isinstance(applet_saved_data, dict) and 'score' in applet_saved_data:
                        score_value = int(applet_saved_data['score'])
                        # UPDATED: Get the win count, defaulting to 0 if not present
                        win_count = int(applet_saved_data.get('wins', 0))
                        owner_pubkey = content.get('owner_pubkey')
                        
                        # Use the owner's nickname, or a default if not found
                        owner_nickname = data_instance.owner.nickname if data_instance.owner and data_instance.owner.nickname else f"user-{owner_pubkey[:8]}"

                        # Update or create the high score entry
                        HighScore.objects.update_or_create(
                            applet=data_instance.applet,
                            owner_pubkey=owner_pubkey,
                            defaults={
                                'score': score_value,
                                'wins': win_count, # UPDATED: Save the win count
                                'owner_nickname': owner_nickname,
                                'last_updated': data_instance.last_updated
                            }
                        )
                        processed_count += 1

                except (ValueError, TypeError, json.JSONDecodeError) as e:
                    logger.warning(f"Could not process score for data instance {data_instance.id}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error processing score for {data_instance.id}: {e}", exc_info=True)
        
        logger.info(f"High score processing run complete. Updated or created {processed_count} scores.")
