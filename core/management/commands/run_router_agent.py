"""
Management command to run the AI Router Agent integrated with Axon BBS.

This agent monitors the AI Router Test applet's message board for RouterQuery events,
executes queries via router_cli.py, and posts responses back to the board.

Usage:
    python manage.py run_router_agent [--applet-id UUID] [--poll-interval SECONDS]

Benefits of running as Django command:
- No JWT authentication needed (direct database access)
- No HTTP overhead
- Proper Django ORM integration
- Better error handling and logging
"""

import time
import json
import subprocess
import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from applets.models import Applet
from messaging.models import Message
from core.models import User


class Command(BaseCommand):
    help = 'Run the AI Router Agent (monitors RouterQuery events and executes router_cli.py)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--applet-id',
            type=str,
            default='d7976779-4d4a-48e7-8f0a-0f3731ed5df6',
            help='Applet ID to monitor (default: AI Router Test)'
        )
        parser.add_argument(
            '--poll-interval',
            type=int,
            default=2,
            help='Poll interval in seconds (default: 2)'
        )
        parser.add_argument(
            '--router-cli',
            type=str,
            default=os.getenv('KAIRO_ROUTER_CLI'),
            help='Path to router_cli.py (default: KAIRO_ROUTER_CLI env var)'
        )
        parser.add_argument(
            '--user',
            type=str,
            default=os.getenv('KAIRO_AGENT_USER', 'system'),
            help='Username to post responses as (default: KAIRO_AGENT_USER env var or "system")'
        )

    def handle(self, *args, **options):
        applet_id = options['applet_id']
        poll_interval = options['poll_interval']
        router_cli = options['router_cli']
        username = options['user']

        # Validate applet exists
        try:
            applet = Applet.objects.get(id=applet_id)
        except Applet.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Applet not found: {applet_id}'))
            return

        # Validate user exists
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User not found: {username}'))
            return

        # Validate router_cli exists
        if not os.path.exists(router_cli):
            self.stdout.write(self.style.ERROR(f'Router CLI not found: {router_cli}'))
            return

        self.stdout.write(self.style.SUCCESS('============================================'))
        self.stdout.write(self.style.SUCCESS('AI Router Agent Started (Django Integration)'))
        self.stdout.write(self.style.SUCCESS('============================================'))
        self.stdout.write(f'Applet: {applet.name} ({applet_id})')
        self.stdout.write(f'Event Board: {applet.event_board.name}')
        self.stdout.write(f'Poll Interval: {poll_interval}s')
        self.stdout.write(f'Router CLI: {router_cli}')
        self.stdout.write(f'User: {username}')
        self.stdout.write('')

        # Track processed queries
        processed_query_ids = set()

        # Main loop
        try:
            while True:
                try:
                    self._poll_and_process(
                        applet=applet,
                        user=user,
                        router_cli=router_cli,
                        processed_query_ids=processed_query_ids
                    )
                except KeyboardInterrupt:
                    self.stdout.write('\n' + self.style.WARNING('Interrupted by user'))
                    break
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error: {e}'))
                    import traceback
                    traceback.print_exc()

                time.sleep(poll_interval)

        finally:
            self.stdout.write(self.style.SUCCESS('\nRouter agent stopped'))

    def _poll_and_process(self, applet, user, router_cli, processed_query_ids):
        """Poll for new queries and process them"""

        # Query for RouterQuery messages
        messages = Message.objects.filter(
            board=applet.event_board,
            subject='RouterQuery'
        ).order_by('-created_at')[:10]  # Get latest 10

        for message in messages:
            try:
                query_data = json.loads(message.body)
                query_id = query_data.get('query_id')

                # Skip if already processed
                if query_id in processed_query_ids:
                    continue

                self.stdout.write(f'[Router] New query: {query_id[:8]}... "{query_data.get("query", "")[:50]}"')
                processed_query_ids.add(query_id)

                # Execute router
                response_data = self._execute_router(
                    query_data=query_data,
                    router_cli=router_cli,
                    applet=applet,
                    user=user
                )

                # Post response
                self._post_response(
                    applet=applet,
                    user=user,
                    response_data=response_data
                )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[Router] Failed to process message {message.id}: {e}'))

    def _execute_router(self, query_data, router_cli, applet, user):
        """Execute router_cli.py and return response"""
        query_id = query_data['query_id']
        query = query_data['query']
        mode = query_data.get('mode', 'direct')
        model = query_data.get('model')

        # Build command
        cmd = ['python3', router_cli, query]

        if mode == 'direct' and model:
            cmd.extend(['-m', model])
            timeout = 90  # Increased from 60s
            self._post_stage_update(applet, user, query_id, "routing", "frontal", 0.9, {"mode": "direct", "model": model})
            self._post_stage_update(applet, user, query_id, "provider_selection", "parietal", 0.8, {"provider": model})
        elif mode == 'consensus':
            cmd.append('--consensus')
            timeout = 180  # Increased from 120s
            self._post_stage_update(applet, user, query_id, "routing", "frontal", 0.9, {"mode": "consensus"})
            providers = ["gemini-cli", "claude-cli", "grok-browser", "local"]
            self._post_stage_update(applet, user, query_id, "provider_selection", "parietal", 0.8, {"providers": providers})
            time.sleep(0.2)
            for provider in providers:
                self._post_stage_update(applet, user, query_id, "execution", "temporal", 0.7, {"active_provider": provider})
                time.sleep(0.1)
        elif mode == 'local':
            cmd.append('--local')
            timeout = 120  # Increased from 90s
            self._post_stage_update(applet, user, query_id, "routing", "frontal", 0.9, {"mode": "local"})
            self._post_stage_update(applet, user, query_id, "provider_selection", "parietal", 0.8, {"provider": "local-ollama"})

        cmd.append('--json')

        # Post input stage
        self._post_stage_update(applet, user, query_id, "input", "sensory", 1.0, {"query": query[:60]})

        # Post execution stage
        if mode == 'direct':
            self._post_stage_update(applet, user, query_id, "execution", "temporal", 0.7, {"active_provider": model})
        elif mode == 'local':
            self._post_stage_update(applet, user, query_id, "execution", "temporal", 0.7, {"active_provider": "local-ollama"})

        # Execute router
        self.stdout.write(f'[Router] Executing: {" ".join(cmd)}')
        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            elapsed = time.time() - start_time
            self.stdout.write(f'[Router] Execution complete ({elapsed:.1f}s)')

            # Post validation/consensus stages for consensus mode
            if mode == 'consensus':
                validators = ["grok", "gemini", "claude"]
                for validator in validators:
                    self._post_stage_update(applet, user, query_id, "validation", "occipital", 0.8, {"validator": validator})
                    time.sleep(0.1)

            # Parse result
            if result.returncode == 0:
                try:
                    output = json.loads(result.stdout)
                    response_data = {
                        'query_id': query_id,
                        'status': 'success',
                        'answer': output.get('answer', ''),
                        'metadata': {
                            'mode': mode,
                            'model': model,
                            'provider': output.get('provider', ''),
                            'processing_time': elapsed,
                            'speed': output.get('speed', 0)
                        }
                    }

                    # Post consensus stage for consensus mode
                    if mode == 'consensus':
                        winner = output.get('provider', 'unknown')
                        self._post_stage_update(applet, user, query_id, "consensus", "hub", 1.0, {"winner": winner})

                    self.stdout.write(self.style.SUCCESS(f'[Router] SUCCESS: {len(response_data["answer"])} chars'))
                except json.JSONDecodeError as e:
                    response_data = {
                        'query_id': query_id,
                        'status': 'error',
                        'error': f'Failed to parse router output: {e}',
                        'metadata': {'mode': mode, 'model': model, 'processing_time': elapsed}
                    }
                    self.stdout.write(self.style.ERROR(f'[Router] JSON parse error: {e}'))
            else:
                response_data = {
                    'query_id': query_id,
                    'status': 'error',
                    'error': result.stderr or 'Router execution failed',
                    'metadata': {'mode': mode, 'model': model, 'processing_time': elapsed}
                }
                self.stdout.write(self.style.ERROR(f'[Router] Execution failed: {result.stderr}'))

        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            response_data = {
                'query_id': query_id,
                'status': 'timeout',
                'error': f'Query timed out after {timeout}s',
                'metadata': {'mode': mode, 'model': model, 'processing_time': elapsed}
            }
            self.stdout.write(self.style.ERROR(f'[Router] Timeout after {timeout}s'))

        # Post output stage
        success = response_data.get('status') == 'success'
        self._post_stage_update(applet, user, query_id, "output", "motor", 1.0, {
            "success": success,
            "elapsed": response_data.get('metadata', {}).get('processing_time', 0)
        })

        return response_data

    def _post_stage_update(self, applet, user, query_id, stage, region, activity=1.0, metadata=None):
        """Post stage update to MessageBoard for brain visualization"""
        stage_data = {
            "query_id": query_id,
            "stage": stage,
            "region": region,
            "activity": activity,
            "metadata": metadata or {}
        }

        try:
            Message.objects.create(
                board=applet.event_board,
                subject='RouterStageUpdate',
                body=json.dumps(stage_data),
                author=user,
                pubkey=user.pubkey[:16] if hasattr(user, 'pubkey') and user.pubkey else 'system'
            )
        except Exception as e:
            # Don't fail query if stage update fails
            self.stdout.write(self.style.WARNING(f'[Router] Stage update failed: {e}'))

    def _post_response(self, applet, user, response_data):
        """Post response to MessageBoard"""
        try:
            Message.objects.create(
                board=applet.event_board,
                subject='RouterResponse',
                body=json.dumps(response_data),
                author=user,
                pubkey=user.pubkey[:16] if hasattr(user, 'pubkey') and user.pubkey else 'system'
            )
            self.stdout.write(f'[Router] Posted response for query {response_data["query_id"][:8]}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[Router] Failed to post response: {e}'))
