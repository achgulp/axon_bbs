#!/bin/bash
# Test script to verify autopilot queries are working

echo "=== Autopilot Diagnostics ==="
echo ""
echo "1. Checking if llama-server is running..."
curl -s http://localhost:8082/health && echo " ✅ LLM server healthy" || echo " ❌ LLM server not responding"

echo ""
echo "2. Checking Django server..."
curl -s http://localhost:8000/api/health &>/dev/null && echo " ✅ Django healthy" || echo " ⚠️ Django health check unavailable"

echo ""
echo "3. Recent RouterQuery messages (last 5 minutes)..."
source /home/dukejer/axon_bbs/venv/bin/activate
python manage.py shell -c "
from messaging.models import Message, MessageBoard
from django.utils import timezone
from datetime import timedelta

board = MessageBoard.objects.get(name='Realtime Event Board')
cutoff = timezone.now() - timedelta(minutes=5)
queries = Message.objects.filter(
    board=board,
    subject='RouterQuery',
    created_at__gte=cutoff
).order_by('-created_at')

if queries.exists():
    print(f' ✅ Found {queries.count()} recent queries')
    for q in queries[:3]:
        print(f'    - Status: {q.agent_status}, Created: {q.created_at}')
else:
    print(' ⚠️ No recent queries found')
    print('    → User identity may be locked (401 errors)')
    print('    → Solution: Log out and log back in')
"

echo ""
echo "4. Checking router agent initialization..."
tail -50 nohup.out | grep -E "(Router Agent|BitNet|llama-server)" | tail -5
