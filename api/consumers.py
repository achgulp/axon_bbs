# axon_bbs/api/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

class NostrRelayConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        message = json.loads(text_data)
        msg_type = message[0]

        if msg_type == 'REQ':
            sub_id = message[1]
            filters = message[2] if len(message) > 2 else {}
            events = await self.query_events(filters)
            for event in events:
                await self.send(text_data=json.dumps(['EVENT', sub_id, event]))
            await self.send(text_data=json.dumps(['EOSE', sub_id]))

        elif msg_type == 'EVENT':
            event = message[1]
            await self.store_event(event)
            await self.send(text_data=json.dumps(['OK', event['id'], True, '']))

        elif msg_type == 'CLOSE':
            sub_id = message[1]
            await self.send(text_data=json.dumps(['NOTICE', 'Subscription closed']))

    @sync_to_async
    def query_events(self, filters):
        # Lazy import models here to avoid AppRegistryNotReady
        from core.models import Message, MessageBoard
        # Basic query from DB; expand with filters (kinds, tags, etc.)
        messages = Message.objects.all()
        events = []
        for msg in messages:
            event = {
                'id': msg.nostr_id,
                'pubkey': msg.pubkey,
                'created_at': int(msg.created_at.timestamp()),
                'kind': 1,
                'tags': [['t', msg.board.name]],
                'content': json.dumps({'subject': msg.subject, 'body': msg.body}),
                'sig': 'dummy_sig'  # Add real sig if needed
            }
            events.append(event)
        return events

    @sync_to_async
    def store_event(self, event):
        # Lazy import models here
        from core.models import Message, MessageBoard
        # Basic store; validate and save to DB
        if event['kind'] == 1:
            content = json.loads(event['content'])
            board = MessageBoard.objects.first()  # Adjust to match tag
            Message.objects.create(
                nostr_id=event['id'],
                pubkey=event['pubkey'],
                board=board,
                subject=content.get('subject', ''),
                body=content.get('body', ''),
                created_at=datetime.fromtimestamp(event['created_at'])
            )
