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

# Full path: axon_bbs/core/agents/router_agent_service.py
"""
Router Agent Service - Local LLM Integration for AiRobotWars

This agent polls for RouterQuery events and executes queries against
local LLMs (Ollama) using router_cli.py, then posts RouterResponse events.
"""

import threading
import time
import logging
import json
import subprocess
import os
from pathlib import Path
from messaging.models import Message
from applets.models import Applet
from core.models import User

# NEW: Import llama-cpp-python for direct BitNet loading
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logging.warning("llama-cpp-python not available - autopilot will not work")

logger = logging.getLogger(__name__)


class RouterAgentService:
    """Agent service that polls for RouterQuery events and processes them via local LLM."""

    def __init__(self, poll_interval=0.016, query_timeout=90):  # Changed to 16ms for 60fps
        self.poll_interval = poll_interval
        self.query_timeout = query_timeout
        self.shutdown_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

        self.agent_username = "router_agent"
        self.applet_name = "AiRobotWars"  # Monitor AiRobotWars event board
        self.agent_user = None
        self.event_board = None
        self.applet = None
        self.is_initialized = False
        self.processed_query_ids = set()

        # NEW: BitNet 1-bit model for autopilot (auto-managed llama-server)
        self.bitnet_server_process = None  # llama-server subprocess (auto-started)
        self.bitnet_session = None  # Persistent HTTP session
        self.bitnet_available = False
        self.bitnet_server_url = "http://127.0.0.1:8082"
        self.bitnet_server_bin = Path(__file__).resolve().parent.parent.parent / 'KairoKensei' / 'BitNet' / 'build' / 'bin' / 'llama-server'
        self.bitnet_model_path = Path(__file__).resolve().parent.parent.parent / 'KairoKensei' / 'BitNet' / 'models' / 'BitNet-b1.58-2B-4T' / 'ggml-model-i2_s.gguf'

        # Path to router_cli.py (fallback for consensus mode)
        self.router_cli_path = Path(__file__).resolve().parent.parent.parent / 'KairoKensei' / 'router_cli.py'
        self.venv_python = Path(__file__).resolve().parent.parent.parent / 'KairoKensei' / '.venv' / 'bin' / 'python'

    def start(self):
        self.thread.start()
        logger.info("Router Agent Service thread started.")

    def stop(self):
        logger.info(f"Stopping Router Agent Service...")
        self.shutdown_event.set()

        # Close HTTP session
        if self.bitnet_session:
            self.bitnet_session.close()
            self.bitnet_session = None

        # Stop llama-server ONLY if we spawned it
        if self.bitnet_server_process:
            logger.info("Stopping llama-server subprocess...")
            try:
                self.bitnet_server_process.terminate()
                self.bitnet_server_process.wait(timeout=5)
                logger.info("llama-server stopped gracefully")
            except:
                logger.warning("Force killing llama-server...")
                try:
                    self.bitnet_server_process.kill()
                except:
                    pass
            self.bitnet_server_process = None

        self.bitnet_available = False

    def _initialize_agent(self):
        """Initialize the agent by finding required database objects."""
        try:
            self.agent_user = User.objects.get(username=self.agent_username, is_agent=True)
            self.applet = Applet.objects.get(name=self.applet_name)
            self.event_board = self.applet.event_board
            
            if not self.event_board:
                logger.warning(f"Agent '{self.agent_username}' cannot initialize: Event board not set for applet '{self.applet_name}'.")
                return False
            
            logger.info(f"Router Agent '{self.agent_user.username}' is monitoring board '{self.event_board.name}'.")
            self.is_initialized = True
            return True
            
        except User.DoesNotExist:
            logger.warning(f"Agent '{self.agent_username}' cannot initialize: User not found. Create via Django admin.")
            return False
        except Applet.DoesNotExist:
            logger.warning(f"Agent '{self.agent_username}' cannot initialize: Applet '{self.applet_name}' not found.")
            return False

    def _initialize_bitnet_model(self):
        """Auto-start BitNet llama-server if not running, create persistent HTTP session."""
        if not self.bitnet_server_bin.exists():
            logger.warning(f"BitNet llama-server not found: {self.bitnet_server_bin}")
            return False

        if not self.bitnet_model_path.exists():
            logger.warning(f"BitNet model not found: {self.bitnet_model_path}")
            return False

        try:
            import requests

            # Check if llama-server is already running on port 8082
            logger.info(f"🔍 Checking if llama-server is already running on port 8082...")
            server_already_running = False

            try:
                test_response = requests.get(f"{self.bitnet_server_url}/health", timeout=1)
                if test_response.status_code == 200:
                    server_already_running = True
                    logger.info(f"   ✅ Found existing llama-server running")
            except:
                pass

            # If not running, start it
            if not server_already_running:
                logger.info(f"🚀 Starting BitNet llama-server subprocess...")
                logger.info(f"   Model: {self.bitnet_model_path.name}")
                logger.info(f"   URL: {self.bitnet_server_url}")

                cmd = [
                    str(self.bitnet_server_bin),
                    '-m', str(self.bitnet_model_path),
                    '--port', '8082',
                    '--host', '127.0.0.1',  # Localhost only
                    '-c', '512',  # Context size
                    '-t', '4',  # Threads
                    '-ngl', '0',  # CPU only
                ]

                self.bitnet_server_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                logger.info(f"   Server PID: {self.bitnet_server_process.pid}")
                logger.info(f"   Waiting for server to load model...")

                # Wait for server to be ready
                max_wait = 30
                start = time.time()
                server_ready = False

                while time.time() - start < max_wait:
                    try:
                        response = requests.get(f"{self.bitnet_server_url}/health", timeout=1)
                        if response.status_code == 200:
                            server_ready = True
                            break
                    except:
                        pass
                    time.sleep(0.5)

                if not server_ready:
                    logger.error("Server failed to start within 30s")
                    if self.bitnet_server_process:
                        self.bitnet_server_process.kill()
                        self.bitnet_server_process = None
                    return False

                logger.info(f"   ✅ Server ready in {time.time() - start:.1f}s")

            # Create persistent HTTP session
            self.bitnet_session = requests.Session()
            self.bitnet_available = True

            logger.info(f"✅ BitNet ready for queries")
            logger.info(f"   Method: HTTP on localhost (managed subprocess)")
            logger.info(f"   Expected latency: ~20-50ms per query")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize BitNet: {e}", exc_info=True)
            if self.bitnet_server_process:
                self.bitnet_server_process.kill()
                self.bitnet_server_process = None
            return False

    def _run(self):
        """Main agent loop."""
        time.sleep(5)  # Wait for Django to fully initialize

        while not self.shutdown_event.is_set():
            try:
                if not self.is_initialized:
                    if not self._initialize_agent():
                        self.shutdown_event.wait(self.poll_interval * 5)  # Wait longer before retry
                        continue

                    # NEW: Load 1-bit LLM after agent is initialized
                    self._initialize_bitnet_model()

                self._process_pending_queries()

            except Exception as e:
                logger.error(f"Error in Router Agent loop: {e}", exc_info=True)

            self.shutdown_event.wait(self.poll_interval)

        logger.info("Router Agent Service has shut down gracefully.")

    def _process_pending_queries(self):
        """Poll for RouterQuery messages and process them."""
        # Find pending RouterQuery messages
        query_posts = Message.objects.filter(
            board=self.event_board,
            subject='RouterQuery',
            agent_status='pending'
        ).order_by('created_at')

        for post in query_posts:
            try:
                body = json.loads(post.body)
                query_id = body.get('query_id')

                # Skip if already processed
                if query_id in self.processed_query_ids:
                    post.agent_status = 'processed'
                    post.save()
                    continue

                logger.info(f"Processing RouterQuery: {query_id[:8]}...")
                
                # Process the query
                response_data = self._execute_query(body)
                
                # Post response
                self._post_response(response_data)
                
                # Mark as processed
                self.processed_query_ids.add(query_id)
                post.agent_status = 'processed'
                post.save()

            except json.JSONDecodeError:
                logger.warning(f"Skipping non-JSON RouterQuery (ID: {post.id})")
                post.agent_status = 'processed'
                post.save()
            except Exception as e:
                logger.error(f"Error processing RouterQuery: {e}", exc_info=True)
                post.agent_status = 'failed'
                post.save()

    def _query_bitnet_direct(self, prompt, max_tokens=30, temperature=0.1):
        """Query BitNet server via persistent HTTP session (~20-50ms)."""
        if not self.bitnet_available or not self.bitnet_session:
            return None

        try:
            start_time = time.time()

            # Send request to localhost server
            # Use very low max_tokens for fastest response (robot commands are 1-10 chars)
            response = self.bitnet_session.post(
                f"{self.bitnet_server_url}/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": min(max_tokens, 5),  # Cap at 5 tokens for speed
                    "temperature": temperature,
                    "stop": ["\n", ".", "|", " "]  # Stop early
                },
                timeout=2
            )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                answer = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()

                if not answer:
                    logger.warning("BitNet server returned empty response")
                    return None

                logger.debug(f"⚡ BitNet localhost: {elapsed*1000:.1f}ms - '{answer[:50]}'")

                return {
                    'answer': answer,
                    'elapsed': elapsed,
                    'provider': 'bitnet-localhost'
                }
            else:
                logger.warning(f"BitNet server error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"BitNet query error: {e}", exc_info=True)
            return None

    def _execute_query(self, query_data):
        """Execute a query - tries 1-bit BitNet first, falls back to router_cli.py."""
        query_id = query_data.get('query_id')
        query = query_data.get('query', '')
        mode = query_data.get('mode', 'local')
        model = query_data.get('model', 'local')

        # NEW: Try BitNet subprocess for 'local' mode (autopilot commands)
        if mode == 'local' and self.bitnet_available:
            result = self._query_bitnet_direct(query, max_tokens=30, temperature=0.1)

            if result:
                return {
                    'query_id': query_id,
                    'status': 'success',
                    'answer': result['answer'],
                    'metadata': {
                        'mode': 'bitnet-subprocess',
                        'model': 'BitNet-1.58bit-2B',
                        'processing_time': result['elapsed'],
                        'provider': result['provider'],
                        'speed': 0.0
                    }
                }
            else:
                logger.warning("BitNet subprocess failed, falling back to router_cli.py...")

        # FALLBACK: Build command for router_cli.py subprocess
        cmd = [str(self.venv_python), str(self.router_cli_path), query]

        if mode == 'consensus':
            cmd.append('--consensus')
            timeout = 120
        elif mode == 'local':
            cmd.append('--local')
            timeout = self.query_timeout
        else:  # direct
            cmd.extend(['-m', model])
            timeout = 60

        cmd.append('--json')

        start_time = time.time()
        logger.debug(f"Executing: {cmd[-3:]}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.router_cli_path.parent)
            )

            elapsed = time.time() - start_time

            if result.returncode == 0:
                try:
                    output = json.loads(result.stdout)
                    return {
                        'query_id': query_id,
                        'status': 'success',
                        'answer': output.get('text', 'No answer returned'),
                        'metadata': {
                            'mode': mode,
                            'model': model if mode == 'direct' else None,
                            'processing_time': elapsed,
                            'provider': output.get('provider'),
                            'speed': output.get('speed')
                        }
                    }
                except json.JSONDecodeError as e:
                    return {
                        'query_id': query_id,
                        'status': 'error',
                        'error': f'Failed to parse router output: {e}'
                    }
            else:
                return {
                    'query_id': query_id,
                    'status': 'error',
                    'error': result.stderr or 'Router execution failed'
                }

        except subprocess.TimeoutExpired:
            return {
                'query_id': query_id,
                'status': 'timeout',
                'error': f'Query timed out after {timeout}s'
            }
        except FileNotFoundError:
            return {
                'query_id': query_id,
                'status': 'error',
                'error': f'router_cli.py not found at {self.router_cli_path}'
            }
        except Exception as e:
            return {
                'query_id': query_id,
                'status': 'error',
                'error': str(e)
            }

    def _post_response(self, response_data):
        """Post a RouterResponse message to the event board."""
        try:
            Message.objects.create(
                board=self.event_board,
                subject='RouterResponse',
                body=json.dumps(response_data),
                author=self.agent_user,
                pubkey=self.agent_user.pubkey if self.agent_user.pubkey else '',
                agent_status='processed'
            )
            logger.info(f"Posted RouterResponse for query {response_data.get('query_id', 'unknown')[:8]}")
        except Exception as e:
            logger.error(f"Failed to post RouterResponse: {e}", exc_info=True)
