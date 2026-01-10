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

# Full path: axon_bbs/core/agents/kairo_cortex_service.py

import logging
import json
import os
import subprocess
import threading
import requests
from django.utils import timezone
from messaging.models import MessageBoard, Message

logger = logging.getLogger(__name__)


class KairoCortexService:
    """
    Sub-agent for KairoCortex MessageBoard that processes semantic intents
    using the 10th Man adversarial validation pattern.
    
    Flow:
    1. Monitor KairoCortex board for SemanticIntent messages
    2. Generate candidates using API (Grok/Gemini/Claude - stubbed for now)
    3. Validate candidates using local Llama 3.2 critic
    4. Post approved CortexSuggestion back to board
    """

    def __init__(self, board_id, **kwargs):
        logger.info(f"[KairoCortex] Initializing service for board_id={board_id}")
        
        self.board_id = board_id
        
        try:
            self.board = MessageBoard.objects.get(id=self.board_id)
            if self.board.name != 'KairoCortex':
                logger.warning(f"[KairoCortex] Board name is '{self.board.name}', expected 'KairoCortex'")
        except MessageBoard.DoesNotExist:
            raise ValueError(f"MessageBoard with ID {self.board_id} does not exist.")

        # Llama configuration
        self.llama_binary = kwargs.get('llama_binary', '/home/pibbs/llama.cpp/build/bin/llama-cli')
        self.llama_model = kwargs.get('llama_model', '/home/pibbs/llama.cpp/models/Llama-3.2-1B-Instruct-Q4_K_M.gguf')
        self.llama_timeout = kwargs.get('llama_timeout', 60)

        # Rust backend configuration
        self.backend_url = os.environ.get('KAIRO_BACKEND_URL', 'http://localhost:8001')
        self.backend_timeout = int(os.environ.get('KAIRO_BACKEND_TIMEOUT', '10'))

        # Monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True, name="KairoCortex-Monitor")
        self.shutdown_event = threading.Event()
        
        # Track last processed message
        self.last_processed_time = timezone.now()

        logger.info(f"[KairoCortex] Service initialized - llama={self.llama_binary}, model={self.llama_model}")
        logger.info(f"[KairoCortex] Backend: {self.backend_url}, timeout={self.backend_timeout}s")
        
        # Check backend health (non-blocking)
        self._check_backend_health()

    def start(self):
        """Start monitoring thread"""
        logger.info(f"[KairoCortex] Starting monitor thread for board '{self.board.name}'")
        self.monitor_thread.start()
        logger.info(f"[KairoCortex] Monitor thread started: {self.monitor_thread.is_alive()}")

    def stop(self):
        """Stop monitoring thread"""
        logger.info(f"[KairoCortex] Shutting down monitor thread for board '{self.board.name}'")
        self.shutdown_event.set()
        self.monitor_thread.join(timeout=2)
        logger.info(f"[KairoCortex] Monitor thread stopped")

    def _monitor_loop(self):
        """
        Monitor MessageBoard for new SemanticIntent messages.
        Check every 1 second for new messages to process.
        """
        logger.info(f"[KairoCortex] Starting monitor loop for board '{self.board.name}'")

        try:
            while not self.shutdown_event.wait(1.0):  # Check every 1 second
                try:
                    # Query for new SemanticIntent messages
                    new_intents = Message.objects.filter(
                        board=self.board,
                        subject='SemanticIntent',
                        created_at__gt=self.last_processed_time
                    ).order_by('created_at')

                    for intent_msg in new_intents:
                        try:
                            logger.info(f"[KairoCortex] Processing intent message ID: {intent_msg.id}")
                            self._process_intent(intent_msg)
                            self.last_processed_time = intent_msg.created_at
                        except Exception as e:
                            logger.error(f"[KairoCortex] Error processing intent {intent_msg.id}: {e}", exc_info=True)

                except Exception as e:
                    logger.error(f"[KairoCortex] Error in monitor loop: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"[KairoCortex] FATAL: Monitor loop crashed: {e}", exc_info=True)

    def _process_intent(self, intent_msg):
        """
        Process semantic intent using 10th Man pattern:
        1. Parse intent from message
        2. Generate candidates (API - stubbed for now)
        3. Validate with Llama critic
        4. Post approved response or rejection
        """
        try:
            intent_data = json.loads(intent_msg.body)
            intent_id = intent_data.get('intent_id', 'unknown')
            concepts = intent_data.get('compressed_concepts', [])
            
            logger.info(f"[KairoCortex] Intent {intent_id}: concepts={concepts}")

            # Step 1: Generate candidates (stubbed)
            candidates = self._generate_candidates(intent_data)
            
            # Step 2: Validate with 10th Man critic
            for candidate in candidates:
                logger.debug(f"[KairoCortex] Testing candidate: {candidate['predictions']}")
                
                if self._llama_critic(candidate):
                    logger.info(f"[KairoCortex] ✓ Candidate PASSED 10th Man validation")
                    
                    # Post approved response
                    Message.objects.create(
                        board=self.board,
                        subject='CortexSuggestion',
                        body=json.dumps({
                            'intent_id': intent_id,
                            'predictions': candidate['predictions'],
                            'confidence': candidate['confidence'],
                            'critique_passed': True
                        }),
                        author=intent_msg.author
                    )
                    return  # First passing candidate wins
                
                logger.debug(f"[KairoCortex] ✗ Candidate REJECTED by 10th Man")

            # All candidates rejected - request clarification
            logger.warning(f"[KairoCortex] All candidates rejected for intent {intent_id}")
            Message.objects.create(
                board=self.board,
                subject='CortexSuggestion',
                body=json.dumps({
                    'intent_id': intent_id,
                    'predictions': [],
                    'confidence': 0.0,
                    'critique_passed': False,
                    'message': 'Request clarification - all candidates rejected'
                }),
                author=intent_msg.author
            )

        except json.JSONDecodeError as e:
            logger.error(f"[KairoCortex] Invalid JSON in intent message: {e}")
        except Exception as e:
            logger.error(f"[KairoCortex] Error processing intent: {e}", exc_info=True)

    def _generate_candidates(self, intent_data):
        """
        Generate prediction candidates by calling Rust backend.
        
        Returns:
            List of candidate dicts with 'predictions' and 'confidence' keys.
            Returns empty list on error (fail-safe).
        """
        try:
            # Build IntentRequest JSON for Rust backend
            request_payload = {
                'intent_id': intent_data.get('intent_id', 'unknown'),
                'intent_type': 'prediction',
                'compressed_concepts': intent_data.get('compressed_concepts', []),
                'context': intent_data.get('context', ''),
                'confidence': intent_data.get('confidence', 0.85),
                'target_helper': None
            }
            
            logger.debug(f"[KairoCortex] Calling Rust backend: POST {self.backend_url}/process_intent")
            
            # POST to Rust backend
            response = requests.post(
                f'{self.backend_url}/process_intent',
                json=request_payload,
                headers={'Content-Type': 'application/json'},
                timeout=self.backend_timeout
            )
            
            response.raise_for_status()
            
            # Parse IntentResponse JSON
            response_data = response.json()

            # Transform to expected format for _llama_critic
            # Backend returns single response, wrap as list of candidates
            candidate = {
                'predictions': response_data.get('predictions', []),
                'confidence': response_data.get('confidence', 0.0)
            }

            candidates = [candidate] if candidate['predictions'] else []

            logger.info(f"[KairoCortex] Received response from backend (helper: {response_data.get('helper_used', 'unknown')})")
            return candidates
            
        except requests.exceptions.Timeout:
            logger.error(f"[KairoCortex] Backend timeout after {self.backend_timeout}s - returning empty candidates")
            return []
        except requests.exceptions.ConnectionError:
            logger.error(f"[KairoCortex] Backend connection failed ({self.backend_url}) - returning empty candidates")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[KairoCortex] Backend request failed: {e} - returning empty candidates")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"[KairoCortex] Invalid JSON response from backend: {e} - returning empty candidates")
            return []
        except Exception as e:
            logger.error(f"[KairoCortex] Unexpected error calling backend: {e} - returning empty candidates", exc_info=True)
            return []

    def _llama_critic(self, candidate):
        """
        Run local Llama 3.2 model to critique the candidate.
        
        Returns:
            True if candidate PASSES (safe to use)
            False if candidate is REJECTED (flawed/unsafe)
        
        Fail-open: If Llama crashes or times out, allow the candidate
        """
        predictions = candidate.get('predictions', [])
        confidence = candidate.get('confidence', 0.0)
        
        # Construct critic prompt
        prompt = f"""You are an adversarial critic. Your job is to find flaws in predictions.

Predictions: {', '.join(predictions)}
Confidence: {confidence:.2f}

Are these predictions safe and reasonable? Reply with ONLY one word: PASS or REJECT."""

        try:
            logger.debug(f"[KairoCortex] Running Llama critic...")
            
            result = subprocess.run(
                [
                    self.llama_binary,
                    '-m', self.llama_model,
                    '-p', prompt,
                    '-n', '10',  # Max 10 tokens (enough for "PASS" or "REJECT")
                    '--log-disable'
                ],
                capture_output=True,
                timeout=self.llama_timeout,
                text=True
            )

            output = result.stdout.strip().upper()
            logger.debug(f"[KairoCortex] Llama output: {output[:100]}")

            # Check if output contains PASS
            if 'PASS' in output:
                return True
            elif 'REJECT' in output:
                return False
            else:
                # Unclear response - fail open (allow)
                logger.warning(f"[KairoCortex] Llama gave unclear response: {output[:50]}, defaulting to PASS")
                return True

        except subprocess.TimeoutExpired:
            logger.error(f"[KairoCortex] Llama critic timed out after {self.llama_timeout}s - failing open (PASS)")
            return True
        except FileNotFoundError:
            logger.error(f"[KairoCortex] Llama binary not found at {self.llama_binary} - failing open (PASS)")
            return True
        except Exception as e:
            logger.error(f"[KairoCortex] Llama critic failed: {e} - failing open (PASS)")
            return True

    def _check_backend_health(self):
        """
        Check if Rust backend is reachable.
        Non-blocking: logs warning if unreachable but doesn't prevent service start.
        """
        try:
            response = requests.get(
                f'{self.backend_url}/health',
                timeout=2
            )
            if response.status_code == 200:
                logger.info(f"[KairoCortex] ✓ Backend health check passed: {self.backend_url}")
            else:
                logger.warning(f"[KairoCortex] ⚠ Backend health check returned {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"[KairoCortex] ⚠ Backend health check failed: {e} - service will continue but candidate generation may fail")


# Singleton instance (optional, for easy access)
kairo_cortex_service = None
