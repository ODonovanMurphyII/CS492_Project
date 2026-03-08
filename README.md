# Secure Chat Room
## A Cryptographic Suite: Confidentiality, Integrity & Authenticity
### Revised Specification — wolfSSL Transport, 12-byte Nonce, Payload Signatures, Key Rotation

---

## 1. Introduction

### 1.1 Functional Overview

This project implements a double-enveloped security model: real TLS 1.3 (via wolfSSL) for transport, with Elliptic Curve Cryptography (ECC) for end-to-end payload security inside the tunnel. The outer TLS layer handles the handshake legitimately — no fake headers, no raw socket mimicry. The inner layer is a custom binary protocol carrying AEAD-encrypted, Ed25519-signed message payloads disguised inside a stealth JSON envelope.

Two user classes coexist in the same chatroom simultaneously:

- **Type 1 — Authenticated (Secure):** Privileged users who send, encrypt, sign, and decrypt messages end-to-end. Full E2EE applies. Every message carries an Ed25519 signature over the plaintext, verifiable by other authenticated members.
- **Type 2 — Unauthenticated (Insecure):** Users who send and read plaintext. Encrypted messages are hidden from them via envelope normalisation — the `avatar` field is always present, always the same padded length, and indistinguishable from legitimate client metadata.

### 1.2 Project Significance

This project demonstrates practical implementation of:

- Public key infrastructure (PKI) and key distribution between clients and server
- Applied cryptography and traffic normalisation on real-time streaming data
- Secure data transfer across an untrusted network (Zero-Trust Architecture)
- Private key handling and hardware-backed identity simulation
- Cryptographic protocol design grounded in modern academic standards

---

## 2. Background & Literature Review

### 2.1 The Key Distribution Problem

One of the primary challenges in secure communication is the secure exchange of keys between parties without an interceptor gaining access. This is addressed through an ephemeral X25519 Diffie-Hellman exchange where the broker routes but never sees the derived secret.

### 2.2 Signal Protocol Precedent

Signal's Double Ratchet protocol enables asynchronous authenticated messaging with end-to-end confidentiality. The security goals it establishes — message authenticity, no replays, no key-compromise impersonation, forward secrecy — directly inform this project. Our system addresses the same threat model but without the ratcheting mechanism, relying instead on session-bounded keys with rotation on member departure.

**Stated limitation:** Without per-message ratcheting, compromise of the session key exposes all messages within that session. This is an accepted trade-off for implementation scope, explicitly bounded by session lifetime.

### 2.3 The Trust Model — Zero Trust Architecture (ZTA)

We adopt Zero Trust Architecture (ZTA): never trust, always verify. The broker is explicitly untrusted. All cryptographic operations happen client-side. The broker is a postman — it routes messages but cannot read them.

| ZTA Pillar | Implementation |
|---|---|
| Strict Identity | Ed25519 challenge-response + X.509 mTLS before any resource access |
| Least Privilege | Broker sees only envelope metadata; never session keys or plaintext |
| Micro-Segmentation | Per-room session keys; key rotation on member departure prevents cross-session access |
| Continuous Monitoring | Auth attempts, subscriptions, and key exchanges logged by broker |

### 2.4 Gaps in Existing Approaches

Current simple chat tutorials ignore lateral movement post-compromise. Proprietary protocols are built without formal specifications (Kobeissi), raising accountability concerns. This specification-first approach addresses that. The "Code First, Specify Later" anti-pattern is why many data breach incidents involve hard-coded credentials in pipelines.

---

## 3. Cryptographic Architecture

### 3.1 Algorithm Selection Rationale

ECC is chosen over RSA because it provides equivalent security at significantly smaller key sizes, which matters for embedded/IoT contexts and reduces packet overhead.

| Algorithm | Role & Justification |
|---|---|
| Ed25519 | Authentication, signing. Designed to resist side-channel attacks. Used in SSH, Signal, TLS. RFC 8032. Also used for per-message payload signatures — every encrypted message carries a detached Ed25519 signature over the plaintext, bound inside the ciphertext. |
| X25519 | Diffie-Hellman key exchange. Provides forward secrecy per session. Native to TLS 1.3. |
| AES-256-GCM | Symmetric encryption of message payloads after shared secret derivation. AEAD cipher — confidentiality, integrity, and authenticity in one pass. The GCM tag replaces a separate HMAC. version, key\_id, and nonce passed as AAD. **12-byte nonce per libsodium's `crypto_aead_aes256gcm_NPUBBYTES`.** |
| HKDF | Key derivation from X25519 shared secret to produce separate RX/TX session keys. |

### 3.2 C Implementation — Library Stack

**Primary: libsodium**

```c
/* Ed25519 — Identity signing and per-message payload signing */
crypto_sign_keypair(pk, sk);
crypto_sign_detached(sig, NULL, msg, len, sk);
crypto_sign_verify_detached(sig, msg, len, pk);

/* X25519 — Ephemeral key exchange */
crypto_kx_keypair(client_pk, client_sk);
crypto_kx_client_session_keys(rx, tx, client_pk, client_sk, server_pk);

/* AES-256-GCM — AEAD, 12-byte nonce */
/* NONCE_LEN = crypto_aead_aes256gcm_NPUBBYTES = 12. Never hardcode to 16. */
crypto_aead_aes256gcm_encrypt(c, &clen, m, mlen, ad, adlen, NULL, nonce, key);
crypto_aead_aes256gcm_decrypt(m, &mlen, NULL, c, clen, ad, adlen, nonce, key);

/* Randomness */
randombytes_buf(nonce, crypto_aead_aes256gcm_NPUBBYTES);  /* 12 bytes */
```

**Transport: wolfSSL**

wolfSSL is used for real TLS 1.3 — no raw socket header mimicry. The custom protocol runs inside a legitimate TLS tunnel. wolfSSL's custom I/O callbacks allow wrapping the socket cleanly.

**Alternative: mbedTLS** — clean separation of crypto and transport layers.

---

## 4. Protocol Stack & Transport

### 4.1 Real TLS via wolfSSL — Replacing Fake Headers

The previous approach of writing raw `0x17 0x0303` bytes onto a POSIX socket does not work: Mosquitto on port 443 expects a real TLS handshake and will reject a connection that skips it. The fix is to run genuine TLS and carry the custom protocol inside it.

```
Real TLS 1.3 (wolfSSL)
    └── HTTP Upgrade (inside TLS tunnel)
            └── Custom binary MQTT-like framing
                    └── Stealth JSON envelope
                            └── AES-256-GCM encrypted 'd' field
                                    └── plaintext || Ed25519 signature
```

To Wireshark, this is a long-running HTTPS session — because it is one. No fake headers required.

```c
/* Phase 1 — wolfSSL setup: real TLS 1.3, mTLS with X.509 client cert */

#include <wolfssl/ssl.h>

WOLFSSL_CTX *ctx = wolfSSL_CTX_new(wolfTLSv1_3_client_method());

/* Load client certificate and private key for mTLS */
wolfSSL_CTX_use_certificate_file(ctx, "client.crt", SSL_FILETYPE_PEM);
wolfSSL_CTX_use_PrivateKey_file(ctx, "client.key", SSL_FILETYPE_PEM);

/* Verify broker certificate against our CA */
wolfSSL_CTX_load_verify_locations(ctx, "ca.crt", NULL);
wolfSSL_CTX_set_verify(ctx, SSL_VERIFY_PEER, NULL);

/* Connect */
int sock = /* POSIX TCP socket to port 443 */;
WOLFSSL *ssl = wolfSSL_new(ctx);
wolfSSL_set_fd(ssl, sock);

if (wolfSSL_connect(ssl) != SSL_SUCCESS) {
    /* TLS handshake failed — abort */
    wolfSSL_free(ssl);
    wolfSSL_CTX_free(ctx);
    return -1;
}

/* Real TLS 1.3 handshake complete.                          */
/* Everything sent via wolfSSL_write() looks like HTTPS.     */
/* Now send HTTP Upgrade to switch to MQTT-like binary framing. */

const char *http_upgrade =
    "GET /stream HTTP/1.1\r\n"
    "Host: yourbroker.com\r\n"
    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
    "Upgrade: custom-mqtt\r\n"
    "Connection: Upgrade\r\n"
    "\r\n";

wolfSSL_write(ssl, http_upgrade, strlen(http_upgrade));
/* After broker ACKs: switch to binary MQTT-like framing over the same ssl handle */
```

### 4.2 OSI Model Mapping

| OSI Layer | Implementation |
|---|---|
| Application (L7) | MQTT pub/sub routing. Stealth JSON envelope lives here. Deep Packet Inspection operates at this layer. |
| Presentation (L6) | AES-256-GCM encryption. Data appears as TLS Application Data records. |
| Session (L5) | ECDHE negotiation of session key; mTLS handshake completes here. wolfSSL manages this layer. |
| Transport (L4) | Standard TCP on port 443. wolfSSL owns this socket. |
| Network (L3) | Standard IP routing. Port 443 chosen for firewall traversal. |
| Data Link (L2) | Standard Ethernet — no modifications. |
| Physical (L1) | Standard physical medium — no modifications. |
| Identity (cross-cutting) | ECDSA (prime256v1) for Root CA and Client Certificates — ZTA identity layer. |

---

## 5. Mutual Authentication & Key Exchange

### 5.1 Mutual Authentication (mTLS) — Step A

Before any data moves, client and broker exchange Ed25519 public keys via X.509 certificates over the wolfSSL TLS 1.3 channel. This is the Zero Trust identity layer.

```c
/* Step A: Ed25519 challenge-response inside the established TLS tunnel */

/* --- CLIENT SIDE --- */
unsigned char client_sign_pk[crypto_sign_PUBLICKEYBYTES];
unsigned char client_sign_sk[crypto_sign_SECRETKEYBYTES];
unsigned char challenge[32];
unsigned char sig[crypto_sign_BYTES];

/* Long-term signing keypair — generated once, stored securely */
crypto_sign_keypair(client_sign_pk, client_sign_sk);

/* Broker sends a random 32-byte challenge */
wolfSSL_read(ssl, challenge, sizeof(challenge));

/* Client signs the challenge */
crypto_sign_detached(sig, NULL, challenge, sizeof(challenge), client_sign_sk);

/* Send public key + signature */
wolfSSL_write(ssl, client_sign_pk, sizeof(client_sign_pk));
wolfSSL_write(ssl, sig,            sizeof(sig));

/* --- BROKER SIDE --- */
unsigned char recv_pk[crypto_sign_PUBLICKEYBYTES];
unsigned char recv_sig[crypto_sign_BYTES];

wolfSSL_read(ssl, recv_pk,  sizeof(recv_pk));
wolfSSL_read(ssl, recv_sig, sizeof(recv_sig));

if (crypto_sign_verify_detached(recv_sig, challenge, sizeof(challenge), recv_pk) != 0) {
    wolfSSL_shutdown(ssl);
    return -1;  /* Authentication failed */
}
/* Identity confirmed. Proceed to key exchange. */
```

### 5.2 Ephemeral Key Exchange (X25519 ECDHE) — Step B

After identity is confirmed, each party generates a fresh ephemeral X25519 keypair. The shared secret is never transmitted. The broker routes public keys but cannot derive the secret. Separate RX/TX keys are derived via HKDF.

```c
/* Step B: X25519 ECDHE inside the TLS tunnel */

int perform_key_exchange(WOLFSSL *ssl, int is_client,
                         uint8_t rx[crypto_kx_SESSIONKEYBYTES],
                         uint8_t tx[crypto_kx_SESSIONKEYBYTES]) {

    unsigned char my_pk[crypto_kx_PUBLICKEYBYTES];
    unsigned char my_sk[crypto_kx_SECRETKEYBYTES];
    unsigned char their_pk[crypto_kx_PUBLICKEYBYTES];

    crypto_kx_keypair(my_pk, my_sk);

    /* Exchange public keys through broker — broker sees keys, NOT the secret */
    wolfSSL_write(ssl, my_pk, sizeof(my_pk));
    wolfSSL_read(ssl, their_pk, sizeof(their_pk));

    int ret;
    if (is_client) {
        ret = crypto_kx_client_session_keys(rx, tx, my_pk, my_sk, their_pk);
    } else {
        ret = crypto_kx_server_session_keys(rx, tx, my_pk, my_sk, their_pk);
    }

    /* Always wipe ephemeral private key from memory */
    sodium_memzero(my_sk, sizeof(my_sk));

    return (ret == 0) ? 0 : -1;
}
```

**Key lifetime policy:** Keys are per-session. On disconnect or after a configurable timeout (e.g., 1 hour), both parties call `sodium_memzero()` on all key material. A new ECDHE handshake is required to rejoin. This provides forward secrecy — compromise of session keys does not expose previous sessions.

---

## 6. Message Security — Signatures Inside the Payload

### 6.1 Why Signatures Go Inside the Ciphertext

Ed25519 signatures are embedded in the plaintext *before* encryption, not appended to the outside of the ciphertext. This is non-negotiable for two reasons:

1. **Authenticity within the group:** A single shared session key means any member can forge ciphertext. The Ed25519 signature, verifiable against the sender's known long-term public key, provides proof that a specific identity produced this message. The GCM tag proves integrity; the Ed25519 signature proves authorship.
2. **Signature confidentiality:** An external signature leaks metadata — it reveals who sent a message even to an observer who cannot decrypt it. Encrypting the signature hides sender identity from unauthenticated users.

```
Plaintext structure before encryption:
[ length prefix: 2 bytes (big-endian) ]
[ message content: variable            ]
[ Ed25519 signature: 64 bytes          ]  <- signs the message content only
[ padding: to MAX_PT_LEN               ]
```

```c
/* Signing and verifying inside the payload */

/* SENDER: sign plaintext, then encrypt the bundle */
unsigned char sig[crypto_sign_BYTES];  /* 64 bytes */
crypto_sign_detached(sig, NULL, message, message_len, sender_sign_sk);

/* Build plaintext bundle: message || signature */
uint8_t bundle[MAX_PT_LEN];
sodium_memzero(bundle, sizeof(bundle));

/* 2-byte big-endian length prefix for message */
bundle[0] = (message_len >> 8) & 0xFF;
bundle[1] =  message_len       & 0xFF;
memcpy(bundle + 2, message, message_len);
memcpy(bundle + 2 + message_len, sig, crypto_sign_BYTES);

/* Now encrypt bundle with AES-256-GCM (see pack_d_field below) */

/* RECEIVER: decrypt first, then verify signature */
/* CRITICAL: verify-before-use ordering */
uint16_t msg_len = ((uint16_t)plaintext[0] << 8) | plaintext[1];
const uint8_t *msg_start = plaintext + 2;
const uint8_t *sig_start = msg_start + msg_len;

/* Look up sender's long-term Ed25519 public key by their authenticated identity */
const uint8_t *sender_pk = lookup_peer_public_key(sender_id);

if (crypto_sign_verify_detached(sig_start, msg_start, msg_len, sender_pk) != 0) {
    /* Signature invalid — discard silently, do not display */
    return -1;
}
/* Message is authentic. Render it. */
```

---

## 7. Packet Design — The Stealth JSON Envelope

### 7.1 Envelope Structure

Every message — secure or plaintext — is wrapped in an identical outer envelope. The encrypted payload is hidden inside `avatar`, a field that appears to any observer as a routine client metadata token (thumbnail hash, avatar identifier, session tag). Unauthenticated clients have no reason to suspect it carries ciphertext.

```json
{
  "user":    "alice",
  "ts":      1704892800,
  "status":  "online",
  "session": "8f3a9c2d",
  "seq":     42,
  "avatar":  "<base64 blob>"
}
```

- **`seq`** — monotonic sequence number per sender. Receiver rejects any message whose `seq` is not strictly greater than the last accepted value from that sender (replay prevention within session).
- **`avatar`** — always present, always padded to a fixed maximum base64 length. Ciphertext is length-normalised before encryption; a 2-byte length prefix inside the plaintext signals the true message boundary after decryption. All messages appear identical on the wire.
- Unauthenticated clients render `user`, `ts`, and any plaintext channel messages. Authenticated clients extract `avatar`, validate the GCM tag (verify-before-decrypt), decrypt, verify the Ed25519 signature, and render in `seq` order.

### 7.2 The `avatar` Field Binary Structure

The `avatar` field is a base64-encoded binary packet. All fields use network (big-endian) byte order.

```
[ version:    1 byte  ]  <- AAD start
[ key_id:     4 bytes ]  <- AAD
[ nonce:     12 bytes ]  <- AAD end  (crypto_aead_aes256gcm_NPUBBYTES = 12)
[ gcm_tag:   16 bytes ]  <- appended by libsodium to front of ciphertext[]
[ ciphertext: n bytes ]  <- AES-256-GCM encrypted bundle (padded to MAX_PT_LEN)
                            bundle = length_prefix || message || Ed25519_sig || padding
```

| Field | Description |
|---|---|
| version (1 byte) | Protocol version. Currently `0x01`. Passed as AAD. |
| key\_id (4 bytes) | Identifies which session key was used. Allows rotation without full re-handshake. Treated as an opaque byte array. If used as a numeric value, serialise with `htonl()`. Passed as AAD. |
| nonce (12 bytes) | **12 bytes — `crypto_aead_aes256gcm_NPUBBYTES`.** Unique per message. Generated with `randombytes_buf()`. Never reused. Passed as AAD. |
| gcm\_tag (16 bytes) | AES-256-GCM authentication tag. libsodium prepends this to `ciphertext[]`. Covers ciphertext AND AAD (version \|\| key\_id \|\| nonce). No separate HMAC required. |
| ciphertext (n bytes) | AES-256-GCM encrypted bundle, padded to `MAX_PT_LEN`. Contains: 2-byte length prefix \|\| message \|\| Ed25519 signature (64 bytes) \|\| padding. |

```c
/* Packing the 'avatar' field in C */

#define AVATAR_VERSION    0x01
#define NONCE_LEN         crypto_aead_aes256gcm_NPUBBYTES  /* 12 — never hardcode */
#define GCM_TAG_LEN       crypto_aead_aes256gcm_ABYTES     /* 16 */
#define KEY_ID_LEN        4
#define AAD_LEN           (1 + KEY_ID_LEN + NONCE_LEN)    /* 17 bytes */
#define SIG_LEN           crypto_sign_BYTES                /* 64 */
#define MAX_MSG_LEN       400                              /* application limit */
#define MAX_PT_LEN        (2 + MAX_MSG_LEN + SIG_LEN)     /* fixed padded plaintext size */

typedef struct {
    uint8_t version;
    uint8_t key_id[KEY_ID_LEN];
    uint8_t nonce[NONCE_LEN];   /* 12 bytes */
    uint8_t ciphertext[];       /* GCM_TAG_LEN prepended by libsodium, then padded ciphertext */
} __attribute__((packed)) avatar_packet_t;

/*
 * IMPORTANT: Never cast a raw buffer to avatar_packet_t for wire I/O.
 * Always serialise/deserialise field-by-field. The struct describes
 * the logical layout only. Multi-byte key_id must use htonl() if
 * treated numerically.
 */

int pack_avatar_field(uint8_t *out, size_t out_max,
                      const uint8_t *message, size_t msg_len,
                      const uint8_t *session_key, const uint8_t *key_id,
                      const uint8_t *sign_sk) {

    /* 1. Sign the message */
    uint8_t sig[SIG_LEN];
    crypto_sign_detached(sig, NULL, message, msg_len, sign_sk);

    /* 2. Build padded plaintext: length_prefix || message || signature || padding */
    uint8_t padded[MAX_PT_LEN];
    sodium_memzero(padded, sizeof(padded));
    padded[0] = (msg_len >> 8) & 0xFF;
    padded[1] =  msg_len       & 0xFF;
    memcpy(padded + 2,           message, msg_len);
    memcpy(padded + 2 + msg_len, sig,     SIG_LEN);

    /* 3. Build packet header */
    avatar_packet_t *pkt = (avatar_packet_t *)out;
    pkt->version = AVATAR_VERSION;
    memcpy(pkt->key_id, key_id, KEY_ID_LEN);
    randombytes_buf(pkt->nonce, NONCE_LEN);  /* fresh 12-byte nonce */

    /* 4. Build AAD: version || key_id || nonce */
    uint8_t aad[AAD_LEN];
    aad[0] = AVATAR_VERSION;
    memcpy(aad + 1,              key_id,    KEY_ID_LEN);
    memcpy(aad + 1 + KEY_ID_LEN, pkt->nonce, NONCE_LEN);

    /* 5. Encrypt — GCM tag prepended to ciphertext by libsodium */
    unsigned long long clen;
    crypto_aead_aes256gcm_encrypt(
        pkt->ciphertext, &clen,
        padded, sizeof(padded),
        aad, AAD_LEN,
        NULL, pkt->nonce, session_key
    );

    return 0;
}

int unpack_avatar_field(const uint8_t *in, size_t in_len,
                        const uint8_t *session_key,
                        uint8_t *message_out, size_t *msg_len_out,
                        peer_id_t sender_id) {

    const avatar_packet_t *pkt = (const avatar_packet_t *)in;

    /* Build AAD */
    uint8_t aad[AAD_LEN];
    aad[0] = pkt->version;
    memcpy(aad + 1,              pkt->key_id, KEY_ID_LEN);
    memcpy(aad + 1 + KEY_ID_LEN, pkt->nonce,  NONCE_LEN);

    /* STEP 1: Decrypt and verify GCM tag — verify-before-use */
    uint8_t plaintext[MAX_PT_LEN];
    unsigned long long pt_len;
    size_t ciphertext_len = in_len - offsetof(avatar_packet_t, ciphertext);

    if (crypto_aead_aes256gcm_decrypt(
            plaintext, &pt_len,
            NULL, pkt->ciphertext, ciphertext_len,
            aad, AAD_LEN, pkt->nonce, session_key) != 0) {
        return -1;  /* GCM tag invalid — discard */
    }

    /* STEP 2: Extract length prefix */
    uint16_t msg_len = ((uint16_t)plaintext[0] << 8) | plaintext[1];
    if (msg_len > MAX_MSG_LEN) return -1;

    /* STEP 3: Verify Ed25519 signature — verify-before-use */
    const uint8_t *msg_start = plaintext + 2;
    const uint8_t *sig_start = msg_start + msg_len;

    const uint8_t *sender_pk = lookup_peer_public_key(sender_id);
    if (!sender_pk) return -1;

    if (crypto_sign_verify_detached(sig_start, msg_start, msg_len, sender_pk) != 0) {
        return -1;  /* Signature invalid — discard */
    }

    /* Both checks passed. Copy message out. */
    memcpy(message_out, msg_start, msg_len);
    *msg_len_out = msg_len;
    sodium_memzero(plaintext, sizeof(plaintext));
    return 0;
}
```

---

## 8. Group Key Management

### 8.1 Session Key and Member Authenticity

A single shared AES-256-GCM session key provides confidentiality for the group but does not provide sender authenticity by itself — any member holding the key can produce valid ciphertext. This is resolved by the Ed25519 signature embedded inside every ciphertext (Section 6). Together:

- **GCM tag:** proves the ciphertext was produced by someone holding the current session key (integrity, replay detection via AAD binding)
- **Ed25519 signature:** proves the plaintext was produced by a specific authenticated identity (authenticity)

### 8.2 Member Join — Mid-Session Upgrade

When a user switches from insecure to secure mode, they perform an X25519 handshake with all current authenticated members and receive the session key encrypted point-to-point from the designated key distributor.

**Designated Key Distributor:** Held by the room creator. Transfers to the next longest-present authenticated member if the creator leaves. All other secure members suppress their key response once they observe the distributor's delivery on the channel. Joining users **must reject** session keys from any sender other than the current distributor.

```c
/* Join: new user broadcasts X25519 public key */
broadcast_to_room(room_id, MSG_TYPE_KX_REQUEST, my_kx_pk, sizeof(my_kx_pk));

/* Distributor: encrypt and deliver session key */
if (i_am_distributor(room_id)) {
    uint8_t nonce[crypto_box_NONCEBYTES];
    randombytes_buf(nonce, sizeof(nonce));

    uint8_t encrypted_key[crypto_box_MACBYTES + SESSION_KEY_LEN];
    crypto_box_easy(encrypted_key,
        current_session_key, SESSION_KEY_LEN,
        nonce, new_user_kx_pk, my_kx_sk);

    send_to_peer(new_user_id, MSG_TYPE_SESSION_KEY, encrypted_key, sizeof(encrypted_key));
    /*
     * NOTE: crypto_box_easy uses X25519+XSalsa20-Poly1305, not AES-256-GCM.
     * This is intentional: key delivery is a point-to-point asymmetric operation.
     * Group messages use AES-256-GCM with the shared session key.
     * These are different threat models and different primitives are appropriate.
     */
}

/* Joining user: receive and decrypt session key */
if (sender_id != known_distributor_id) {
    /* Reject — only accept from authorised distributor */
    return;
}
uint8_t session_key[SESSION_KEY_LEN];
crypto_box_open_easy(session_key, encrypted_key, sizeof(encrypted_key),
                     nonce, distributor_kx_pk, my_kx_sk);
```

**Distributor failure recovery:** If no key delivery arrives within `KEY_DELIVERY_TIMEOUT_MS` (3000 ms), the joining user retransmits the request. The broker detects distributor disconnection and broadcasts `MSG_TYPE_DISTRIBUTOR_CHANGED` with the new distributor ID. The joining user resends the request to the new distributor.

```c
#define KEY_DELIVERY_TIMEOUT_MS 3000

if (wait_for_key_delivery(KEY_DELIVERY_TIMEOUT_MS) == TIMEOUT) {
    /* Broker has already promoted new distributor and broadcast the change */
    update_known_distributor_from_broker(room_id);
    broadcast_to_room(room_id, MSG_TYPE_KX_REQUEST, my_kx_pk, sizeof(my_kx_pk));
    /* Retry with new distributor */
}
```

### 8.3 Member Leave — Key Rotation

When any authenticated member leaves, the session key **must be rotated**. Without rotation, the departed member retains the ability to decrypt all future messages. This breaks the forward secrecy guarantee within a session.

Key rotation is performed by the current distributor. The `key_id` is incremented so that messages encrypted under old and new keys are distinguishable and old replays cannot be injected under the new key.

```c
void rotate_session_key_on_leave(room_t *room, peer_id_t departed_id) {

    /* Generate new session key */
    uint8_t new_key[SESSION_KEY_LEN];
    randombytes_buf(new_key, SESSION_KEY_LEN);

    /* Increment key_id — distinguishes old messages from new */
    room->current_key_id++;

    /* Deliver new key encrypted to each remaining authenticated member */
    for (int i = 0; i < room->member_count; i++) {
        if (room->members[i].id == departed_id) continue;
        if (!room->members[i].is_authenticated)  continue;

        uint8_t nonce[crypto_box_NONCEBYTES];
        randombytes_buf(nonce, sizeof(nonce));

        uint8_t encrypted[crypto_box_MACBYTES + SESSION_KEY_LEN];
        crypto_box_easy(encrypted,
            new_key, SESSION_KEY_LEN,
            nonce, room->members[i].kx_pk, my_kx_sk);

        send_to_peer(room->members[i].id, MSG_TYPE_KEY_ROTATION,
                     encrypted, sizeof(encrypted));
    }

    /* Install new key and wipe the old one */
    sodium_memzero(room->session_key, SESSION_KEY_LEN);
    memcpy(room->session_key, new_key, SESSION_KEY_LEN);
    sodium_memzero(new_key, SESSION_KEY_LEN);

    /* Distributor role: if departed member was distributor, role already transferred */
    /* Update distributor record if necessary */
}
```

**Important:** Rotation must complete before any new messages are sent. Members buffer incoming messages received during rotation and process them once the new key is installed, using `key_id` to determine which key to apply.

---

## 9. Replay Prevention

Two complementary layers prevent replay attacks. Together they ensure a replayed packet is rejected either as temporally expired or as a duplicate sequence number.

**Layer 1 — Timestamp window:** Any packet whose `ts` falls outside `[now − 600s, now + 600s]` is rejected immediately, before GCM verification. Requires time-server synchronisation.

**Layer 2 — Sequence counter:** Within a session, a message from sender `S` is accepted only if its `seq` is strictly greater than the last accepted `seq` from `S`. The sequence counter resets on session key rotation.

```c
/* Replay check — apply before any cryptographic verification */
int check_replay(session_t *sess, peer_id_t sender, uint64_t ts, uint32_t seq) {
    uint64_t now = current_unix_time();

    /* Layer 1: timestamp window */
    if (ts < now - 600 || ts > now + 600) {
        return -1;  /* outside window */
    }

    /* Layer 2: sequence counter */
    if (seq <= sess->last_seq[sender]) {
        return -1;  /* replay or out-of-order */
    }

    sess->last_seq[sender] = seq;
    return 0;
}
```

---

## 10. Methodology

### 10.1 Implementation Phases

| Phase | Tasks |
|---|---|
| 1 — TLS Foundation | wolfSSL setup. Real TLS 1.3, mTLS with X.509 client cert. HTTP Upgrade over the tunnel. Verify with Wireshark — should show legitimate TLS Application Data. |
| 2 — CA & Certificate Infrastructure | Root CA with `openssl ecparam -name prime256v1`. Issue client X.509 certificates. Configure Mosquitto for mTLS on port 8883, proxy via 443. |
| 3 — Mutual Authentication | Ed25519 challenge-response in C using libsodium inside the TLS tunnel. Broker verifies client certificates before allowing subscription. |
| 4 — Key Exchange | X25519 ECDHE per session. Derive RX/TX keys via `crypto_kx_client/server_session_keys()`. `sodium_memzero()` cleanup on disconnect and timeout. |
| 5 — Signed & Encrypted Payloads | Ed25519 sign plaintext, embed signature in bundle before encryption. AES-256-GCM AEAD with **12-byte nonce**. Build `avatar` field packer/unpacker. Pass version \|\| key\_id \|\| nonce as AAD. GCM verify-before-decrypt. Ed25519 verify-before-render. |
| 6 — Group Key Management | Designated key distributor for join. Key rotation on leave (same implementation pass). `key_id` increment on rotation. Distributor failover with `KEY_DELIVERY_TIMEOUT_MS`. |
| 7 — Steganographic Envelope | Wrap all messages in identical JSON envelopes padded to fixed block size. Sequence numbering. Verify Wireshark shows uniform traffic. |
| 8 — UX Toggle & CLI | Secure/insecure mode switch. Mid-session upgrade handshake. Demonstration mode showing authenticated vs. plaintext view. |
| 9 — Replay Prevention & Integration | Clock-based timestamp window (10 min). Sequence counter enforcement. Full multi-client demo on VMware. |

### 10.2 Key Design Decisions

| Decision | Resolution |
|---|---|
| Transport | Real TLS 1.3 via wolfSSL. No fake headers. Custom protocol runs inside the tunnel. |
| Encryption scope | Client-side (E2EE). Broker never sees plaintext. |
| Nonce size | **12 bytes** (`crypto_aead_aes256gcm_NPUBBYTES`). Never hardcoded as 16. |
| Message authenticity | Ed25519 signature over plaintext, encrypted inside the ciphertext before AES-256-GCM. Signature verified after decryption, before render. |
| Group forward secrecy | Session key rotated on every member departure. `key_id` incremented per rotation. |
| Key distribution race | Single designated distributor. Others suppress response on observing delivery. Timeout + failover for distributor disconnection. |
| AEAD | AES-256-GCM. GCM tag covers ciphertext + AAD. No separate HMAC. |
| Point-to-point key delivery | `crypto_box_easy` (X25519+XSalsa20-Poly1305). Intentionally different from group cipher — different threat model. |
| Byte order | All multi-byte wire fields in network (big-endian) order. Structs are logical layout only; never cast to raw buffers. |
| Key lifetime | Per-session. `sodium_memzero()` all material on disconnect or timeout. |

### 10.3 Component Responsibilities

**Client:**
- Establishes wolfSSL TLS 1.3 connection with X.509 client cert
- Performs Ed25519 challenge-response for mTLS
- Runs X25519 ECDHE per session
- Signs plaintext with Ed25519 before encryption
- Encrypts payload with AES-256-GCM (12-byte nonce, AAD-bound)
- Wraps in stealth JSON envelope
- On receive: replay check → GCM verify → decrypt → Ed25519 verify → render
- Maintains per-sender sequence counter; rejects non-monotonic `seq`

**Server/Broker (Mosquitto):**
- Routes MQTT pub/sub messages
- Validates client X.509 certificates (mTLS via wolfSSL)
- Routes key exchange messages between clients
- Tracks distributor role per room; broadcasts `MSG_TYPE_DISTRIBUTOR_CHANGED` on distributor disconnection
- Never derives or sees session keys or plaintext

---

## 11. Expected Outcomes

The final demonstration will show, via Wireshark capture, that encrypted and plaintext messages are indistinguishable at the network layer. The capture shows a long-running TLS 1.3 session on port 443. Application Data records are uniform in apparent length. No ciphertext is visible to unauthenticated users — only routine chat metadata fields including the `avatar` token, which appears semantically legitimate.

A second demonstration window shows two clients: one authenticated (sees decrypted, verified messages), one unauthenticated (sees chat metadata only). A third client joins mid-session, receives the session key from the distributor, and immediately begins sending and receiving encrypted messages. A fourth client disconnects, triggering a key rotation visible only in authenticated client logs.

---

## 12. Ethical Considerations

This project is dual-use technology. The steganographic envelope and port-443 TLS camouflage are techniques used in advanced persistent threat (APT) command-and-control infrastructure. Publishing this as open-source would provide a functional blueprint for data exfiltration bypassing standard network defences.

Specific concerns:

- Traffic normalisation can reduce the effectiveness of heuristic DPI firewalls
- Steganographic envelope hides the existence of communication, not just its content
- If extended with a reverse shell and credential harvesting, this becomes a complete intrusion toolkit

Mitigations and ethical protocols:

- Code developed in a closed, air-gapped lab environment. Not published to public repositories.
- Demonstration performed only on hardware and VMs owned by the project team.
- No real credentials, certificates, or private keys committed to version control.
- Project documented as an academic exercise, not a deployable tool.
- All Wireshark captures use synthetic/simulated traffic only.

---

## 13. Resources

### Hardware

- **Client Device:** Raspberry Pi (simulates constrained IoT endpoint)
- **Network:** Router (demonstrates real network traversal)
- **Server Device:** Linux machine running Mosquitto broker
- **Demonstration:** Windows 10 VM in VMware (multi-client simulation)

### Software Stack

| Component | Purpose |
|---|---|
| wolfSSL | Primary TLS library. Real TLS 1.3 with mTLS. Custom I/O callbacks. Replaces raw socket header mimicry. |
| libsodium | Crypto library. Ed25519, X25519, AES-256-GCM AEAD, HKDF. Reference implementation. |
| mbedTLS | Alternative. Clean separation of crypto and transport layers. |
| Mosquitto | MQTT broker. Port 8883 internally, exposed via 443 TLS proxy. |
| libmosquitto.h | C client library for MQTT. |
| OpenSSL (ecparam) | CA generation only: `openssl ecparam -name prime256v1`. X.509 cert issuance. |
| libuv | Async event-driven networking. Handles concurrent connections. |
| POSIX sys/socket.h | Underlying TCP socket passed to wolfSSL. Multi-byte fields serialised with `htons()`/`htonl()`. |
| Wireshark | Demonstration. Verifies uniform TLS Application Data; no visible ciphertext. |
| VMware | Virtualisation for multi-client demonstration. |

---

## 14. Conclusion

This specification implements a complete cryptographic suite demonstrating confidentiality, integrity, and authenticity over an untrusted network, with the following confirmed-correct properties:

- **Real TLS 1.3 transport** via wolfSSL — legitimate handshake, no fake headers, genuine HTTPS camouflage
- **12-byte nonces** throughout, matching `crypto_aead_aes256gcm_NPUBBYTES` — no size mismatch
- **Ed25519 signatures inside the ciphertext** — sender authenticity within the group without leaking identity to observers; verify-before-render enforced
- **Key rotation on member departure** — session-level forward secrecy; `key_id` tracks which key applies to which messages
- **Designated key distributor with failover** — no race condition on join; no message loss on distributor disconnection
- **Dual-layer replay prevention** — timestamp window eliminates stale replays; sequence counter handles in-session duplicates

The use of ECC over RSA is justified by security-per-byte efficiency critical in constrained IoT environments. The implementation in low-level C using libsodium follows established cryptographic best practices and avoids rolling custom primitives.

---

## 15. References

Bhoite, Harshraj. *Zero-Trust Architecture in Streaming Dataflows.* TechRxiv, 20 July 2025. https://doi.org/10.36227/techrxiv.175303721.12297807/v1

Kobeissi, Nadim, Karthikeyan Bhargavan, and Bruno Blanchet. *Automated Verification for Secure Messaging Protocols and Their Implementations: A Symbolic and Computational Approach.* 2nd IEEE European Symposium on Security and Privacy, April 2017, Paris, France. pp. 435–450. doi:10.1109/EuroSP.2017.38

Owens, D., El Khatib, R., Bisheh-Niasar, M., Azarderakhsh, R., & Mozaffari Kermani, M. (2021). *Efficient and Side-Channel Resistant Ed25519 on ARM Cortex-M4.* IEEE Transactions on Computers, 71(4), 850–861. https://doi.org/10.1109/TC.2021.3065620

Suárez-Albela, M., Fernández-Caramés, T. M., Fraga-Lamas, P., & Castedo, L. *A Practical Performance Comparison of ECC and RSA for Resource-Constrained IoT Devices.* 2018 Global Internet of Things Summit (GIoTS), Bilbao, Spain. pp. 1–6. doi:10.1109/GIOTS.2018.8534575
