# AxonChat Federation Setup Guide

AxonChat now supports BBS-to-BBS federation, allowing users on different Axon BBS instances to chat together in real-time!

## How It Works

- Each AxonChat applet can specify which trusted BBS instances to federate with
- Messages are synchronized every 5 seconds using authenticated requests
- Federation uses the same cryptographic authentication as BitSync

## Setup Instructions

### 1. Configure Trusted Instances

First, make sure both BBS instances have each other as trusted peers in the admin panel:
- Go to Admin > Trusted Instances
- Add the peer's .onion URL
- Mark as "Is Trusted Peer"

### 2. Configure AxonChat Parameters

When running AxonChat, set the `parameters` field in JSON format:

```json
{
  "trusted_peers": [
    "http://peer1abc123xyz.onion",
    "http://peer2def456uvw.onion"
  ]
}
```

**Via Django Admin:**
1. Go to Admin > Applets
2. Find the AxonChat applet
3. Edit the "Parameters" field
4. Add the JSON configuration above with your peer URLs
5. Save

**Via API/Code:**
```python
from applets.models import Applet
import json

applet = Applet.objects.get(name='AxonChat')
applet.parameters = json.dumps({
    "trusted_peers": [
        "http://yourpeer.onion"
    ]
})
applet.save()
```

### 3. Restart the Chat Agent

After updating the parameters:
```bash
sudo systemctl restart axon-bbs.service
```

Or if running manually:
```bash
python3 manage.py runserver 0.0.0.0:8000
```

### 4. Test Federation

1. Send a message from BBS Instance A
2. Wait 5-10 seconds for synchronization
3. Check BBS Instance B - the message should appear!

## Technical Details

- **Endpoint**: `/api/applets/{applet_id}/shared_state/`
- **Authentication**: X-Pubkey, X-Timestamp, X-Signature headers (RSA-PSS)
- **Sync Interval**: 5 seconds (configurable via `poll_interval` parameter)
- **Transport**: Tor SOCKS5 proxy (127.0.0.1:9050)

## Troubleshooting

### Messages not syncing?

1. Check that both instances have each other as trusted peers
2. Verify the `trusted_peers` parameter is set correctly
3. Check logs: `tail -f logs/bbs.log | grep ChatAgent`
4. Ensure Tor is running and peers are reachable

### Authentication errors?

- Verify both instances have valid cryptographic identities
- Check that the local instance has an encrypted_private_key set

## Security Notes

- Only peers explicitly listed in `trusted_peers` can participate in the chat
- All requests are authenticated with RSA signatures
- Federation traffic is routed through Tor for anonymity
- User avatars and public keys are shared across federated instances

