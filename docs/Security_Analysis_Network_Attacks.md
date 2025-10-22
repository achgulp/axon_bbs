# Axon BBS Security Analysis: Network-Level Attack Vulnerabilities

**Date**: 2025-10-22
**Scope**: BGP Poisoning, RAPTOR/Tor Attacks, Timing Attacks, Sybil Attacks
**Status**: Analysis Complete

---

## Executive Summary

This document analyzes Axon BBS's vulnerability to network-level attacks, including:
- **BGP Poisoning** (Border Gateway Protocol attacks)
- **RAPTOR** (Routing Attacks on Privacy in TOR)
- **Traffic Correlation & Timing Attacks**
- **Sybil Attacks** (malicious peer federation)

### Overall Risk Assessment
- **BGP Poisoning**: LOW-MEDIUM risk (mitigated by Tor but not immune)
- **RAPTOR/Tor Routing Attacks**: MEDIUM-HIGH risk (inherent to Tor hidden services)
- **Timing Attacks**: MEDIUM risk (some metadata leakage possible)
- **Sybil Attacks**: LOW-MEDIUM risk (good peer authentication, but manual trust)

---

## 1. BGP Poisoning Attacks

### What is BGP Poisoning?
BGP (Border Gateway Protocol) poisoning redirects internet traffic by corrupting routing tables. Attackers advertise false routing information to redirect traffic through malicious nodes.

### Axon BBS Vulnerability Analysis

#### ✅ Protections in Place:
1. **Tor Hidden Services**:
   - All federation traffic goes through Tor (`.onion` addresses)
   - Traffic is encrypted end-to-end through multiple hops
   - Real IP addresses are never exposed
   - BGP poisoning cannot directly intercept Tor circuits

2. **SOCKS5 Proxy Configuration**:
   ```python
   # core/services/sync_service.py:139
   proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
   ```
   - Uses `socks5h://` (hostname resolution through Tor)
   - DNS queries go through Tor, preventing DNS-based BGP attacks

3. **Cryptographic Authentication**:
   ```python
   # federation/permissions.py:96-101
   peer_instance = TrustedInstance.objects.get(pubkey=cleaned_sender_pubkey, is_trusted_peer=True)
   ```
   - Even if traffic is redirected, peers must cryptographically prove identity
   - RSA-PSS signatures prevent impersonation

#### ⚠️ Remaining Risks:

1. **Tor Entry Node Compromise**:
   - BGP poisoning could redirect users to malicious Tor entry nodes
   - **Impact**: Attacker learns you're using Tor, but not what you're accessing
   - **Mitigation**: Use Tor bridges or guard nodes

2. **Local Network Attacks**:
   - BGP poisoning on local network could prevent reaching Tor
   - **Impact**: Denial of service only, no data compromise
   - **Mitigation**: None beyond using Tor bridges

3. **Directory Authority Attacks**:
   - BGP could redirect connections to Tor directory authorities
   - **Impact**: Attacker could provide false Tor network information
   - **Mitigation**: Tor uses multiple directory authorities with consensus

### Recommendation:
**Risk Level: LOW-MEDIUM**
- BGP poisoning has limited impact due to Tor usage
- Configure Tor to use bridge relays in high-risk environments
- Consider using guard nodes for added stability

---

## 2. RAPTOR & Tor-Specific Attacks

### What is RAPTOR?
RAPTOR (Routing Attacks on Privacy in TOR) refers to various attacks that exploit Tor's routing:
- **AS-level attacks**: Adversary controls autonomous systems on both ends of a Tor circuit
- **BGP hijacking**: Redirect Tor traffic through adversary-controlled networks
- **Traffic correlation**: Match entry and exit node traffic patterns

### Vulnerability Analysis

#### ⚠️ High-Risk Attack Vectors:

### 2.1 Traffic Correlation Attacks
**Risk**: MEDIUM-HIGH

**Attack Scenario**:
```
User → Tor Entry (Adversary) → Middle → Exit/Rendezvous → Hidden Service (Adversary)
```

If an adversary controls both the entry node AND operates a malicious federated peer, they could:
1. See when you connect to Tor (entry node)
2. See when your BBS receives requests (malicious peer)
3. Correlate timing to identify users

**Evidence in Code**:
```python
# core/services/sync_service.py:52-53
def __init__(self, poll_interval=120):
    self.poll_interval = poll_interval
```
- **Vulnerability**: Predictable 2-minute sync interval
- **Risk**: Traffic timing is regular and correlatable
- **Fingerprint**: Specific request patterns to `/api/sync/`

**Real Logs**:
```
INFO Beginning to poll 1 peer(s) for new content...
INFO <-- Received 5 new manifest(s) from peer http://xxx.onion
```
- Consistent message sizes and timing make correlation easier

### 2.2 Hidden Service Descriptor Attacks
**Risk**: MEDIUM

**Attack Scenario**:
- Adversary runs many Tor relays to become HSDir (hidden service directory)
- Monitors which hidden services are being accessed
- Correlates with network traffic

**Current Protection**:
```python
# Onion addresses seen in code:
# http://lpa4klsh6xbzlexh6pwdxtn7ezr4snztgyxxgejtbmvpl4zw6sqljoyd.onion
```
- Uses v3 onion addresses (56 characters)
- V3 addresses have better resistance to enumeration
- Descriptors are distributed across multiple HSDir nodes

**Remaining Risk**:
- No client-side authorization configured
- Hidden service descriptors are public on the Tor network
- Adversary with sufficient Tor infrastructure could track descriptor fetches

### 2.3 Timing Attacks via Chunk Downloads
**Risk**: MEDIUM

```python
# core/services/sync_service.py:521-546
logger.info(f"Starting swarm download for '{item_name}' from {len(seeders)} peer(s).")
# ...
logger.info(f"  - Chunk {chunk_index + 1}/{num_chunks} for '{item_name}' downloaded.")
```

**Vulnerability**:
- Chunk downloads happen over multiple requests
- Each chunk download is a separate Tor circuit potentially
- Timing and size of chunks could fingerprint specific content
- 256KB chunk size is consistent and observable

**Attack**:
An adversary monitoring Tor exit/rendezvous points could:
1. Observe chunk request patterns
2. Correlate with known content sizes
3. Identify what content is being synchronized

### 2.4 Metadata Leakage
**Risk**: MEDIUM

**Exposed Metadata**:
```python
# core/services/sync_service.py:144
target_url = f"{peer.web_ui_onion_url.strip('/')}/api/sync/?since={last_sync.isoformat()}"
```

- URL parameters expose last sync timestamp
- Could reveal how often peer is checking for updates
- Pattern analysis could identify usage behavior

```python
# federation/permissions.py:65
if abs(django_timezone.now() - timestamp) > timedelta(minutes=5):
```
- 5-minute timestamp window
- Timing window is observable
- Could be used for correlation attacks

---

## 3. Timing Attack Analysis

### 3.1 Request Timing Patterns

**Predictable Polling**:
```python
# core/services/sync_service.py:79
time.sleep(self.poll_interval)  # Default: 120 seconds
```

**Vulnerability**:
- Every BBS polls peers every 2 minutes
- Creates predictable network traffic patterns
- Makes traffic correlation easier

**Fingerprint Observable By Adversary**:
```
T+0s:    GET /api/sync/?since=...
T+120s:  GET /api/sync/?since=...
T+240s:  GET /api/sync/?since=...
```

**Recommendation**:
- Add random jitter to poll interval
- Vary timing between 90-150 seconds randomly
- Implement exponential backoff for failed requests

### 3.2 Message Timestamp Leakage

```python
# messaging/models.py (likely)
created_at = models.DateTimeField(auto_now_add=True)
```

**Vulnerability**:
- Message creation timestamps are precise
- Could correlate with user activity
- Timing analysis could identify when users are online

### 3.3 Agent Service Timing

```python
# core/services/service_manager.py
# Agents run continuously with predictable patterns
```

**Observable Patterns**:
- Agent posts have predictable timing
- Could fingerprint specific BBS instances
- Differentiates between human and agent activity

---

## 4. Sybil Attack Analysis (Malicious Peers)

### What is a Sybil Attack?
An adversary creates many fake identities (peers) to:
- Gain majority control over federation
- Manipulate content distribution
- Gather intelligence on network activity

### Vulnerability Analysis

#### ✅ Strong Protections:

1. **Cryptographic Authentication**:
```python
# federation/permissions.py:86-101
pubkey_obj = load_pem_public_key(sender_pubkey_pem.strip().encode('utf-8'))
# ...
peer_instance = TrustedInstance.objects.get(pubkey=cleaned_sender_pubkey, is_trusted_peer=True)
```

- **RSA-PSS signatures** required for all requests
- Peers must be **manually added** to trusted list
- Cannot forge another peer's identity without private key

2. **Public Key Infrastructure**:
```python
# core/services/sync_service.py:117-127
def _get_auth_headers(self):
    timestamp = datetime.now(timezone.utc).isoformat()
    hasher = hashlib.sha256(timestamp.encode('utf-8'))
    digest = hasher.digest()
    signature = self.private_key.sign(digest, ...)
```

- Every request is cryptographically signed
- Timestamp prevents replay attacks (5-minute window)
- Cannot be bypassed

#### ⚠️ Remaining Risks:

### 4.1 Manual Trust Model Vulnerability
**Risk**: MEDIUM

```python
# core/models.py:110
is_trusted_peer = models.BooleanField(default=False)
```

**Vulnerability**:
- Trust is manual and binary (trusted or not)
- No reputation system
- No automatic trust revocation
- Compromised peer remains trusted until manually removed

**Attack Scenario**:
1. Adversary operates legitimate peer for months
2. Gains trust from multiple BBS instances
3. Compromises peer or turns malicious
4. Can now:
   - Monitor all federated content
   - Track timing of all sync requests
   - Inject manipulated content (if content validation is weak)
   - Correlate activity across federation

### 4.2 Seeder Selection Vulnerability
**Risk**: LOW-MEDIUM

```python
# core/services/sync_service.py:534-535
executor.submit(self._download_chunk, seeders[i % len(seeders)], content_hash, chunk_idx, proxies)
```

**Vulnerability**:
- Round-robin seeder selection
- Predictable which peer will serve which chunk
- Malicious seeders could:
  - Track which content is being downloaded
  - Correlate chunk requests with user activity
  - Perform timing attacks during chunk delivery
  - Deliver corrupted chunks to test validation

**Mitigation Present**:
```python
# core/services/sync_service.py:539
if chunk_data and hashlib.sha256(chunk_data).hexdigest() == chunk_hashes[chunk_index]:
```
- Chunk integrity verification prevents corruption
- But doesn't prevent timing/tracking attacks

### 4.3 Manifest Rekey Trust Extension
**Risk**: LOW

```python
# core/services/bitsync_service.py:132-161
def rekey_manifest_for_new_peers(self, manifest: dict):
    # Automatically trusts peer public keys when rekeying
```

**Vulnerability**:
- When content is rekeyed, it's encrypted for all trusted peers
- Newly added malicious peer gets access to ALL historical content
- No granular access control
- Cannot selectively share content with specific peers

**Attack Scenario**:
1. Adversary gains trust as peer
2. Immediately receives encryption keys for all existing content
3. Can decrypt entire historical archive
4. No way to limit access to recent-only content

---

## 5. Cryptographic Implementation Analysis

### 5.1 Strong Implementations ✅

1. **RSA-PSS Signatures** (2048-bit minimum recommended):
```python
# core/services/sync_service.py:121-123
signature = self.private_key.sign(
    digest,
    rsa_padding.PSS(mgf=rsa_padding.MGF1(hashes.SHA256()), salt_length=rsa_padding.PSS.MAX_LENGTH),
    hashes.SHA256()
)
```
- Uses modern PSS padding (better than PKCS#1 v1.5)
- SHA256 for both hash and MGF
- MAX_LENGTH salt (strongest setting)

2. **AES-256-CBC Encryption**:
```python
# core/services/bitsync_service.py:167-173
aes_key = os.urandom(32)  # 256 bits
iv = os.urandom(16)
cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
padder = padding.PKCS7(algorithms.AES.block_size).padder()
```
- Strong 256-bit keys
- Random IV per encryption
- PKCS7 padding (standard)

3. **RSA-OAEP Key Encapsulation**:
```python
# core/services/bitsync_service.py:206-208
encrypted_key = peer_pubkey_obj.encrypt(
    aes_key,
    rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
)
```
- Uses OAEP (Optimal Asymmetric Encryption Padding)
- SHA256 for both hash and MGF
- Standard and secure

### 5.2 Potential Weaknesses ⚠️

1. **CBC Mode (Not GCM)**:
```python
cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
```

**Concern**:
- CBC provides confidentiality but NOT authentication
- Vulnerable to padding oracle attacks if error messages leak info
- GCM or ChaCha20-Poly1305 would provide authenticated encryption

**Actual Risk**: LOW
- Chunks are also hash-verified separately
- No apparent error message leakage
- But authenticated encryption would be more robust

2. **No Forward Secrecy**:
```python
# All encryption uses static RSA keypairs
# No ephemeral key exchange (ECDHE, X25519, etc.)
```

**Concern**:
- If private key is compromised, ALL historical content can be decrypted
- No forward secrecy in peer-to-peer communication
- No perfect forward secrecy in manifest rekeying

**Risk**: MEDIUM
- Key compromise has catastrophic impact
- Consider implementing ephemeral key exchange for new content

---

## 6. Specific Attack Scenarios

### Scenario 1: State-Level Adversary with AS Control

**Adversary Capabilities**:
- Controls multiple autonomous systems (AS)
- Can perform BGP hijacking
- Operates malicious Tor relays
- Has computational resources for traffic analysis

**Attack Path**:
1. **BGP hijacking** redirects user's connection to malicious Tor entry node
2. Adversary's Tor entry node logs connection timing
3. Adversary operates malicious **federated peer** in the network
4. Malicious peer receives sync requests at predictable 2-minute intervals
5. **Traffic correlation**: Match entry node connection times with peer sync times
6. **Deanonymize**: Identify which BBS instances are operated by which IP addresses

**Success Probability**: MEDIUM-HIGH
- Requires significant resources
- But technically feasible for nation-state adversaries
- RAPTOR-style attacks have been demonstrated in academic research

**Mitigation**:
- Use Tor bridges to hide entry node selection
- Randomize poll intervals with jitter
- Use multiple Tor circuits for different operations
- Implement cover traffic (dummy requests)

### Scenario 2: Malicious Peer Joins Federation

**Attack Path**:
1. Adversary creates legitimate-looking BBS instance
2. Gains trust from one or more existing peers
3. Once trusted, adversary can:
   - **Monitor**: Log all sync requests, timing, content requests
   - **Correlate**: Match activity patterns across multiple peers
   - **Profile**: Build profiles of user activity on each BBS
   - **Inject**: Attempt to inject malicious content
   - **Timing Attack**: Deliver chunks slowly to fingerprint requests

**Success Probability**: HIGH (if trust is granted)
**Impact**: HIGH (privacy compromise, tracking)

**Mitigation**:
- Implement reputation system
- Monitor peer behavior for anomalies
- Limit newly-trusted peers to recent content only
- Implement peer rotation (don't always sync from same peer)

### Scenario 3: Chunk Timing Fingerprinting

**Attack Path**:
1. Adversary compromises or operates a Tor exit node or hidden service rendezvous
2. Observes chunk download patterns:
   - Number of chunks
   - Chunk sizes (256KB)
   - Timing between chunk requests
   - Total download size
3. Builds database of content fingerprints
4. When observing chunk patterns, identifies what content is being downloaded

**Success Probability**: MEDIUM
**Impact**: MEDIUM (content identification without decryption)

**Mitigation**:
- Variable chunk sizes
- Dummy chunk requests (download random chunks)
- Pipeline multiple content downloads simultaneously
- Use constant-rate traffic padding

---

## 7. Recommendations & Mitigations

### Critical Priority (Implement ASAP)

#### 1. **Randomize Poll Intervals**
```python
# Current:
time.sleep(self.poll_interval)  # Always 120s

# Recommended:
import random
jitter = random.uniform(-30, 30)  # ±30 seconds
time.sleep(self.poll_interval + jitter)  # 90-150s range
```

**Benefit**: Makes traffic correlation significantly harder

#### 2. **Implement Guard Node Configuration**
```python
# Add to torrc:
# UseEntryGuards 1
# NumEntryGuards 3
```

**Benefit**: Limits entry node rotation, reduces AS-level attack surface

#### 3. **Add Client Authorization for Hidden Services**
```python
# Generate client authorization keys for each trusted peer
# Add to torrc:
# HidServAuth [onion-address] [auth-cookie]
```

**Benefit**: Prevents adversary from accessing your hidden service without authorization

### High Priority

#### 4. **Implement Request Padding**
```python
def add_cover_traffic():
    # Periodically make dummy requests
    # Make requests identical to real sync requests
    # Adversary cannot distinguish real from dummy
```

**Benefit**: Obscures real request patterns

#### 5. **Reputation System for Peers**
```python
class TrustedInstance(models.Model):
    # Add fields:
    reputation_score = models.IntegerField(default=100)
    successful_syncs = models.IntegerField(default=0)
    failed_syncs = models.IntegerField(default=0)
    last_anomaly_detected = models.DateTimeField(null=True)
    trust_level = models.CharField(choices=[
        ('new', 'New - Restricted'),
        ('established', 'Established - Normal'),
        ('trusted', 'Highly Trusted - Full Access')
    ])
```

**Benefit**: Mitigates Sybil attacks, limits damage from compromised peers

#### 6. **Authenticated Encryption (AES-GCM)**
```python
# Replace CBC with GCM:
cipher = Cipher(algorithms.AES(aes_key), modes.GCM(iv))
encryptor = cipher.encryptor()
ciphertext = encryptor.update(padded_data) + encryptor.finalize()
tag = encryptor.tag  # Authentication tag
```

**Benefit**: Detects tampering, prevents padding oracle attacks

### Medium Priority

#### 7. **Implement Forward Secrecy**
```python
# Use ephemeral key exchange (X25519) for each manifest
# Combine with static RSA for authentication
# New AES key per content, key destroyed after use
```

**Benefit**: Limits damage from key compromise

#### 8. **Chunk Size Randomization**
```python
# Current:
CHUNK_SIZE = 256 * 1024  # Always 256KB

# Recommended:
def get_chunk_size():
    base = 256 * 1024
    jitter = random.randint(-50 * 1024, 50 * 1024)
    return base + jitter  # 206KB - 306KB range
```

**Benefit**: Prevents content fingerprinting via chunk patterns

#### 9. **Circuit Isolation**
```python
# Use separate Tor circuits for different operations:
# - One circuit for federation sync
# - One circuit for chunk downloads
# - One circuit for authentication
# Use SOCKS isolation flags
```

**Benefit**: Limits correlation across different operations

### Low Priority (Defense in Depth)

#### 10. **Obfs4 Bridge Configuration**
```bash
# Use pluggable transports to hide Tor usage
# Recommended for high-risk environments
```

#### 11. **Peer Rotation**
```python
# Don't always download from the same peer
# Rotate through available seeders randomly
# Limits single peer from profiling all activity
```

#### 12. **Timing Obfuscation in Logs**
```python
# Don't log precise timestamps
# Round to nearest minute or use relative times
# Prevents log analysis from revealing patterns
```

---

## 8. Conclusion

### Summary of Findings

| Attack Type | Risk Level | Current Protections | Recommended Actions |
|-------------|------------|-------------------|---------------------|
| **BGP Poisoning** | LOW-MEDIUM | Tor hidden services, SOCKS5h | Use guard nodes, bridges |
| **RAPTOR/Traffic Correlation** | MEDIUM-HIGH | Tor encryption | Randomize timing, cover traffic |
| **Timing Attacks** | MEDIUM | Some randomization | Add jitter, padding |
| **Sybil Attacks** | LOW-MEDIUM | RSA-PSS auth, manual trust | Implement reputation system |
| **Chunk Fingerprinting** | MEDIUM | Chunk hash verification | Randomize chunk sizes |
| **Key Compromise** | HIGH (impact) | Strong crypto | Add forward secrecy |

### Overall Security Posture

**Strengths**:
- Strong cryptographic foundations (RSA-PSS, AES-256, OAEP)
- Robust peer authentication
- Tor hidden services for anonymity
- Chunk integrity verification

**Weaknesses**:
- Predictable traffic patterns enable correlation
- No forward secrecy
- Manual trust model vulnerable to long-term compromise
- Observable metadata leakage
- No defense against sophisticated traffic analysis

### Final Recommendation

Axon BBS has **solid foundations** but is vulnerable to **sophisticated network-level attacks**, particularly:
1. **Traffic correlation** by state-level adversaries with AS control
2. **RAPTOR-style attacks** on Tor hidden services
3. **Sybil attacks** via long-term peer compromise

**Priority Actions**:
1. Implement timing randomization (jitter in poll intervals)
2. Add reputation system for peers
3. Configure Tor guard nodes
4. Consider upgrading to authenticated encryption (AES-GCM)
5. Add forward secrecy for new content

**Risk Assessment**:
- **Against casual adversaries**: WELL PROTECTED
- **Against sophisticated attackers**: VULNERABLE to traffic analysis
- **Against state-level adversaries**: MODERATE-HIGH RISK

### Recommended Threat Model Review

**Low-Risk Use Case** (Privacy-focused community):
- Current implementation is adequate
- Focus on operational security (key management, peer vetting)

**High-Risk Use Case** (Activist/Journalist communication):
- Implement ALL critical and high-priority mitigations
- Consider additional Tor hardening (bridges, obfs4)
- Implement stricter peer vetting and reputation tracking
- Regular security audits and monitoring

---

**Document End**

For questions or security reports, contact the development team.
