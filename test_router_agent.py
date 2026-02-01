#!/usr/bin/env python3
"""
Continuous test for Router Agent - Tests connectivity to 1-bit LLM
"""
import os
import sys
import django
import time
import json
from datetime import datetime
import uuid

# Setup Django
sys.path.insert(0, '/home/dukejer/axon_bbs')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')
django.setup()

from messaging.models import Message, MessageBoard
from core.models import User

class RouterAgentTester:
    def __init__(self):
        # Get the RouterAgent board
        try:
            self.board = MessageBoard.objects.get(name='RouterAgent')
            print(f"✅ Found RouterAgent board (id={self.board.id})")
        except MessageBoard.DoesNotExist:
            print("❌ RouterAgent board not found!")
            sys.exit(1)

        # Get router_agent user
        try:
            self.agent_user = User.objects.get(username='router_agent', is_agent=True)
            print(f"✅ Found router_agent user")
        except User.DoesNotExist:
            print("❌ router_agent user not found!")
            sys.exit(1)

        # Get a regular user for posting queries
        try:
            self.test_user = User.objects.filter(is_agent=False).first()
            if not self.test_user:
                print("❌ No regular user found for testing!")
                sys.exit(1)
            print(f"✅ Using test user: {self.test_user.username}")
        except:
            print("❌ Error getting test user!")
            sys.exit(1)

        self.stats = {
            'sent': 0,
            'received': 0,
            'timeouts': 0,
            'errors': 0
        }

    def post_query(self, prompt):
        """Post a RouterQuery to the board"""
        query_id = str(uuid.uuid4())

        try:
            Message.objects.create(
                board=self.board,
                subject='RouterQuery',
                body=json.dumps({
                    'query_id': query_id,
                    'query': prompt,
                    'mode': 'local',  # Use local BitNet
                    'model': 'bitnet'
                }),
                author=self.test_user,
                pubkey=self.test_user.pubkey if self.test_user.pubkey else '',
                agent_status='pending'
            )
            self.stats['sent'] += 1
            return query_id
        except Exception as e:
            print(f"❌ Error posting query: {e}")
            self.stats['errors'] += 1
            return None

    def wait_for_response(self, query_id, timeout=5.0):
        """Poll for RouterResponse for the given query_id"""
        start_time = time.time()
        poll_interval = 0.1  # 100ms

        while time.time() - start_time < timeout:
            try:
                # Look for RouterResponse with matching query_id
                responses = Message.objects.filter(
                    board=self.board,
                    subject='RouterResponse'
                ).order_by('-created_at')[:10]

                for resp in responses:
                    try:
                        data = json.loads(resp.body)
                        if data.get('query_id') == query_id:
                            elapsed = time.time() - start_time
                            self.stats['received'] += 1
                            return data, elapsed
                    except json.JSONDecodeError:
                        continue

                time.sleep(poll_interval)
            except Exception as e:
                print(f"❌ Error polling: {e}")
                self.stats['errors'] += 1
                return None, None

        self.stats['timeouts'] += 1
        return None, None

    def run_test(self, num_queries=10, delay=2.0):
        """Run continuous test"""
        print(f"\n🧪 Starting continuous test ({num_queries} queries, {delay}s delay)")
        print("=" * 60)

        test_prompts = [
            "What is 2+2?",
            "Hello, how are you?",
            "What color is the sky?",
            "Count to 5",
            "Say yes or no",
        ]

        for i in range(num_queries):
            prompt = test_prompts[i % len(test_prompts)]
            print(f"\n[{i+1}/{num_queries}] Query: '{prompt}'")

            # Post query
            query_id = self.post_query(prompt)
            if not query_id:
                print(f"  ❌ Failed to post query")
                continue

            print(f"  📤 Posted (query_id={query_id[:8]}...)")

            # Wait for response
            response, elapsed = self.wait_for_response(query_id, timeout=5.0)

            if response:
                answer = response.get('answer', 'N/A')[:50]
                provider = response.get('metadata', {}).get('provider', 'unknown')
                processing_time = response.get('metadata', {}).get('processing_time', 0)

                print(f"  ✅ Response in {elapsed:.2f}s")
                print(f"     Provider: {provider}")
                print(f"     Processing: {processing_time*1000:.1f}ms")
                print(f"     Answer: {answer}...")
            else:
                print(f"  ⏱️  Timeout after 5s (no response)")

            # Show stats
            success_rate = (self.stats['received'] / self.stats['sent'] * 100) if self.stats['sent'] > 0 else 0
            print(f"  📊 Stats: {self.stats['received']}/{self.stats['sent']} received ({success_rate:.1f}%), {self.stats['timeouts']} timeouts")

            # Delay before next query
            if i < num_queries - 1:
                time.sleep(delay)

        # Final stats
        print("\n" + "=" * 60)
        print("📊 FINAL RESULTS")
        print("=" * 60)
        print(f"Queries sent:     {self.stats['sent']}")
        print(f"Responses rcvd:   {self.stats['received']}")
        print(f"Timeouts:         {self.stats['timeouts']}")
        print(f"Errors:           {self.stats['errors']}")
        success_rate = (self.stats['received'] / self.stats['sent'] * 100) if self.stats['sent'] > 0 else 0
        print(f"Success rate:     {success_rate:.1f}%")
        print("=" * 60)

if __name__ == '__main__':
    tester = RouterAgentTester()

    # Run test with 20 queries, 2 second delay between each
    tester.run_test(num_queries=20, delay=2.0)
