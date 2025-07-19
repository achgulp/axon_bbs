import libtorrent as lt
import time
import os

# Create a dummy file for testing
dummy_file = 'test.txt'
with open(dummy_file, 'w') as f:
    f.write('Dummy data for torrent test')  # Real content for hashing

# Test session with proxy (Tor)
settings_pack = {
    'listen_interfaces': '0.0.0.0:6881',
    'enable_dht': True,
    'proxy_hostname': '127.0.0.1',
    'proxy_port': 9050,
    'proxy_type': lt.proxy_type_t.socks5,
    'anonymous_mode': True
}
session = lt.session(settings_pack)

# Add example DHT router (a known .onion Tor node; replace with your trusted)
session.add_dht_router('router.bittorrent.com', 6881)  # Clearnet example; use .onion for full Tor

# Wait for DHT to bootstrap
time.sleep(5)  # Give time to connect
print("DHT running:", session.is_dht_running())

# Create torrent from dummy file
fs = lt.file_storage()
fs.add_file(dummy_file, os.path.getsize(dummy_file))
t = lt.create_torrent(fs)
t.add_tracker("udp://tracker.opentrackr.org:1337/announce")  # Example tracker
t.set_creator('Test BBS')
lt.set_piece_hashes(t, '.')  # Current dir with real file
torrent_file = lt.bencode(t.generate())
info = lt.torrent_info(torrent_file)
print("Torrent info hash:", info.info_hash())

# Clean up dummy file
os.remove(dummy_file)

# Check alerts for errors/connections
alerts = session.pop_alerts()
for a in alerts:
    print(a.message())

print("Test complete. If no errors, BitTorrent is working.")
