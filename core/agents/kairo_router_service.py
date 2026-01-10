"""
KairoRouter Agent Service
Monitors KairoRouter MessageBoard and executes AI Router queries
"""

import os
import time
import json
import subprocess
import threading
from datetime import datetime, timedelta
from messaging.models import MessageBoard, Message
from core.models import User


class KairoRouterService:
    """Simple router agent for testing AI Router via MessageBoard"""

    def __init__(self, board_id):
        self.board_id = board_id
        self.running = False
        self.monitor_thread = None
        self.last_processed_time = datetime.now()

        # Router CLI configuration
        self.router_cli = os.getenv('KAIRO_ROUTER_CLI', '/home/dukejer/KairoKensei/router_cli.py')
        self.venv_python = os.getenv('KAIRO_ROUTER_VENV', '/home/dukejer/KairoKensei/.venv/bin/python')

    def start(self):
        """Start monitoring thread"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print(f"[KairoRouter] Service started (board_id={self.board_id})")

    def stop(self):
        """Stop monitoring thread"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("[KairoRouter] Service stopped")

    def _monitor_loop(self):
        """Poll board for new queries every second"""
        while self.running:
            try:
                board = MessageBoard.objects.get(id=self.board_id)
                messages = Message.objects.filter(
                    board=board,
                    subject='RouterQuery',
                    created_at__gt=self.last_processed_time
                ).order_by('created_at')

                for msg in messages:
                    self._process_query(msg)
                    self.last_processed_time = msg.created_at

            except MessageBoard.DoesNotExist:
                print(f"[KairoRouter] ERROR: Board {self.board_id} not found")
                time.sleep(10)
            except Exception as e:
                print(f"[KairoRouter] Error in monitor loop: {e}")
                import traceback
                traceback.print_exc()

            time.sleep(1.0)  # Poll every 1 second

    def _process_query(self, query_msg):
        """Process a router query message"""
        try:
            query_data = json.loads(query_msg.body)
            query_id = query_data['query_id']
            query = query_data['query']
            mode = query_data.get('mode', 'direct')
            model = query_data.get('model', 'gemini')

            print(f"[KairoRouter] Processing query {query_id[:8]}...")
            print(f"[KairoRouter]   Query: {query[:60]}...")
            print(f"[KairoRouter]   Mode: {mode}, Model: {model}")

            # Build command
            cmd = [self.venv_python, self.router_cli, query]

            if mode == 'consensus':
                cmd.append('--consensus')
                timeout = 120
            elif mode == 'local':
                cmd.append('--local')
                timeout = 90
            else:  # direct
                cmd.extend(['-m', model])
                timeout = 60

            cmd.append('--json')

            # Execute router_cli.py
            start_time = time.time()
            print(f"[KairoRouter] Executing: {' '.join(cmd[-3:])}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            elapsed = time.time() - start_time
            print(f"[KairoRouter] Execution complete ({elapsed:.1f}s)")

            # Parse result
            if result.returncode == 0:
                try:
                    output = json.loads(result.stdout)
                    response_data = {
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
                    print(f"[KairoRouter] SUCCESS: {len(response_data['answer'])} chars")
                except json.JSONDecodeError as e:
                    print(f"[KairoRouter] JSON parse error: {e}")
                    print(f"[KairoRouter] stdout: {result.stdout[:200]}")
                    response_data = {
                        'query_id': query_id,
                        'status': 'error',
                        'error': f'Failed to parse router output: {e}'
                    }
            else:
                print(f"[KairoRouter] ERROR: Return code {result.returncode}")
                print(f"[KairoRouter] stderr: {result.stderr[:200]}")
                response_data = {
                    'query_id': query_id,
                    'status': 'error',
                    'error': result.stderr or 'Router execution failed'
                }

            # Post response
            self._post_response(query_msg.author, response_data)

        except subprocess.TimeoutExpired:
            print(f"[KairoRouter] TIMEOUT after {timeout}s")
            response_data = {
                'query_id': query_id,
                'status': 'timeout',
                'error': f'Query timed out after {timeout}s'
            }
            self._post_response(query_msg.author, response_data)

        except Exception as e:
            print(f"[KairoRouter] EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            response_data = {
                'query_id': query_id,
                'status': 'error',
                'error': str(e)
            }
            self._post_response(query_msg.author, response_data)

    def _post_response(self, author, response_data):
        """Post response back to board"""
        try:
            board = MessageBoard.objects.get(id=self.board_id)
            Message.objects.create(
                board=board,
                author=author,
                subject='RouterResponse',
                body=json.dumps(response_data)
            )
            print(f"[KairoRouter] Posted response for query {response_data['query_id'][:8]}")
        except Exception as e:
            print(f"[KairoRouter] Failed to post response: {e}")
            import traceback
            traceback.print_exc()


# Standalone execution for testing
if __name__ == '__main__':
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')
    django.setup()

    # Get board ID from environment or use default
    board_id = int(os.getenv('KAIRO_ROUTER_BOARD_ID', '13'))

    service = KairoRouterService(board_id=board_id)
    service.start()

    print(f"[KairoRouter] Service running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[KairoRouter] Stopping service...")
        service.stop()
