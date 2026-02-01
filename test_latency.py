#!/usr/bin/env python3
"""
Test AiRobotWars autopilot latency
Measures end-to-end time for RouterQuery -> RouterResponse
"""
import os
import django
import time
import json
import uuid
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')
django.setup()

from messaging.models import Message, MessageBoard
from applets.models import Applet
from core.models import User

def test_autopilot_latency(num_tests=5):
    """Test latency by posting RouterQuery and waiting for RouterResponse"""

    # Get required objects
    try:
        agent_user = User.objects.get(username='test_user')
    except User.DoesNotExist:
        agent_user = User.objects.filter(is_active=True).first()
        if not agent_user:
            print("❌ No users found. Create a user first.")
            return

    try:
        applet = Applet.objects.get(name='AI Router Test')
        board = applet.event_board
    except Applet.DoesNotExist:
        print("❌ AI Router Test applet not found")
        return

    if not board:
        print("❌ Event board not configured")
        return

    print(f"Testing autopilot latency on board: {board.name}")
    print(f"Board poll interval: {board.local_poll_interval}s ({1/board.local_poll_interval:.1f} fps)")
    print(f"Running {num_tests} tests...\n")

    latencies = []

    for i in range(num_tests):
        query_id = str(uuid.uuid4())

        # Tactical prompt (same format as AiRobotWars.js)
        prompt = f"H80 E300 @45/200 G. S|C|D|R|M?"

        # Post RouterQuery
        start_time = time.time()

        Message.objects.create(
            author=agent_user,
            board=board,
            subject='RouterQuery',
            body=json.dumps({
                'query_id': query_id,
                'query': prompt,
                'mode': 'local',
                'model': 'local'
            })
        )

        print(f"[{i+1}] Posted query {query_id[:8]}... - Prompt: {prompt}")

        # Wait for RouterResponse (with timeout)
        timeout = 5.0
        response_found = False

        while (time.time() - start_time) < timeout:
            # Check for RouterResponse with matching query_id
            responses = Message.objects.filter(
                board=board,
                subject='RouterResponse',
                created_at__gte=datetime.fromtimestamp(start_time)
            ).order_by('-created_at')

            for msg in responses:
                try:
                    data = json.loads(msg.body)
                    if data.get('query_id') == query_id:
                        elapsed = time.time() - start_time
                        latencies.append(elapsed * 1000)  # Convert to ms

                        answer = data.get('answer', '')
                        processing_time = data.get('metadata', {}).get('processing_time', 0) * 1000
                        provider = data.get('metadata', {}).get('provider', 'unknown')

                        print(f"    ✅ Response: {answer[:30]} (Total: {elapsed*1000:.1f}ms, LLM: {processing_time:.1f}ms, Provider: {provider})")
                        response_found = True
                        break
                except:
                    pass

            if response_found:
                break

            time.sleep(0.010)  # Poll every 10ms

        if not response_found:
            print(f"    ❌ Timeout after {timeout}s")

        # Wait between tests
        if i < num_tests - 1:
            time.sleep(0.5)

    # Print statistics
    if latencies:
        print(f"\n{'='*60}")
        print(f"LATENCY STATISTICS ({len(latencies)} successful tests)")
        print(f"{'='*60}")
        print(f"  Min:     {min(latencies):.1f} ms")
        print(f"  Max:     {max(latencies):.1f} ms")
        print(f"  Average: {sum(latencies)/len(latencies):.1f} ms")
        print(f"  Target:  < 100 ms")

        avg = sum(latencies) / len(latencies)
        if avg < 100:
            print(f"\n  ✅ PASSED - Average latency is sub-100ms!")
        else:
            print(f"\n  ❌ FAILED - Average latency exceeds 100ms")
            print(f"     Need to implement persistent LLM connection per AIWARPLAN.md")
    else:
        print("\n❌ No successful responses received")

if __name__ == '__main__':
    test_autopilot_latency(num_tests=5)
