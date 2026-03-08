# Project: Secure Chat Room

## A Perfect Cryptographic Suite: Confidentiality, Integrity & Authenticity

---

## 1. Introduction

### 1.1 Functional Overview

This project implements a double-enveloped security model combining MQTTS (TLS 1.2/1.3) for transport security with Elliptic Curve Cryptography (ECC). The architecture performs a standard mTLS handshake, then upgrades the established tunnel for a custom binary protocol. Critically, packet signatures are designed to appear as normal browser requests to passive observers.

Two user classes coexist in the same chatroom simultaneously:

- **Type 1 — Authenticated (Secure):** Privileged users who send, encrypt, and decrypt messages end-to-end. Full E2EE applies.
- **Type 2 — Unauthenticated (Insecure):** Users who send and read plaintext. Encrypted messages are invisible to them — not visible as ciphertext gibberish, but entirely hidden via steganography.

### 1.2 Project Significance

This project demonstrates practical implementation of the following security disciplines:

- Public key infrastructure (PKI) and key distribution between clients and server
- Applied cryptography and steganography on real-time streaming data
- Secure data transfer across an untrusted network (Zero-Trust Architecture)
- Private key handling and hardware-backed identity simulation
- Cryptographic protocol design grounded in modern academic standards

---

## 2. Background & Literature Review

### 2.1 The Key Distribution Problem

One of the primary challenges in secure communication is the secure exchange of keys between parties without an interceptor gaining access. This is addressed in our architecture through an ephemeral X25519 Diffie-Hellman exchange where the broker routes but never sees the derived secret.

### 2.2 Signal Protocol Precedent

Signal's Double Ratchet protocol enables asynchronous authenticated messaging with end-to-end confidentiality. It mixes Diffie-Hellman shared secrets with a key refresh mechanism. The security goals it establishes — message authenticity, no replays, no key-compromise impersonation, forward secrecy — directly inform the goals of this project. Our system addresses the same threat model but without the ratcheting mechanism, relying instead on session-bounded keys.

Note: We must address explicitly how long our system is expected to stay secure. This is a fundamental cryptographic consideration. The proposal is per-session keys (see Section 3.4).

### 2.3 The Trust Model — Zero Trust Architecture (ZTA)

We adopt a Zero Trust Architecture (ZTA), defined by the principle: never trust, always verify. Unlike traditional perimeter-based security, ZTA assumes the network is already compromised. This is well-suited for IoT and modern IT environments (Bhoite).

| ZTA Pillar | Implementation Requirement |
|---|---|
| Strict Identity | All entities verify via credentials, certificates, or cryptographic tokens before any resource access. |
| Least Privilege | Fine-grained access policies (RBAC/ABAC) limit blast radius of any compromised credential. |
| Micro-Segmentation | Network divided into zones to prevent lateral movement after a breach. |
| Continuous Monitoring | All transactions are logged and analyzed in real-time. Logs are append-only and tamper-resistant. |

### 2.4 Gaps in Existing Approaches

Current simple chat tutorials and demonstrations routinely ignore lateral movement post-compromise. Proprietary protocols are often built and tweaked without formal specifications (Kobeissi), which raises accountability and auditability concerns. Our specification-first approach addresses this. The "Code First, Specify Later" anti-pattern is common in production systems and is why many modern data breach incidents involve hard-coded credentials in pipelines.

---

## 3. Cryptographic Architecture

### 3.1 Algorithm Selection Rationale

ECC is chosen over RSA because it provides equivalent security at significantly smaller key sizes. This matters for embedded/IoT contexts and reduces packet overhead.

| Algorithm | Role & Justification |
|---|---|
| Ed25519 | Authentication & signing. Designed to resist side-channel attacks. Widely deployed in SSH, Signal, and modern TLS. Uses the twisted Edwards curve (RFC 8032). |
| X25519 | Diffie-Hellman key exchange. Montgomery curve variant of Curve25519. Provides forward secrecy for each session. Used in TLS 1.3 natively. |
| AES-256-GCM | Symmetric encryption of message payloads after shared secret derivation. Provides confidentiality and authentication in one pass. |
| HMAC-SHA256 | Message integrity validation within the 'd' field structure. 32-byte MAC over the ciphertext. |
| HKDF | Key derivation from the X25519 shared secret to produce separate RX and TX session keys. |

### 3.2 C Implementation — Library Stack

**Primary: libsodium** — The reference implementation for Curve25519/Ed25519 in C. Provides the following primitives we use directly:

```c
/* libsodium primitives used in this project */

/* Ed25519 — Identity signing */
crypto_sign_keypair(pk, sk);                    // Generate signing keypair
crypto_sign_detached(sig, NULL, msg, len, sk);  // Sign a challenge
crypto_sign_verify_detached(sig, msg, len, pk); // Verify at broker

/* X25519 — Ephemeral key exchange */
crypto_kx_keypair(client_pk, client_sk);        // Generate ephemeral KX keys
crypto_kx_client_session_keys(rx, tx,
    client_pk, client_sk, server_pk);           // Derive RX and TX session keys

/* AES-256-GCM — Message encryption */
crypto_aead_aes256gcm_encrypt(c, &clen,
    m, mlen, ad, adlen, NULL, nonce, key);      // Encrypt + authenticate
crypto_aead_aes256gcm_decrypt(m, &mlen,
    NULL, c, clen, ad, adlen, nonce, key);      // Decrypt + verify

/* Randomness */
randombytes_buf(nonce, 16);                     // Cryptographically secure nonce
```

**Alternative: wolfSSL / mbedTLS** — wolfSSL is portable C, smaller than OpenSSL, supports all modern ECC curves, and provides a custom I/O callback feature allowing us to wrap encrypted data in fake HTTP headers. mbedTLS offers clean separation of cryptographic and transport concerns.

### 3.3 Mutual Authentication (mTLS) — Step A

Before any data moves, the Client and Broker exchange Ed25519 public keys via X.509 certificates. This is the Zero Trust identity layer.

```c
/* Step A: Mutual Authentication in C using libsodium + POSIX sockets */

/* --- CLIENT SIDE --- */
unsigned char client_pk[crypto_sign_PUBLICKEYBYTES];
unsigned char client_sk[crypto_sign_SECRETKEYBYTES];
unsigned char challenge[32];
unsigned char sig[crypto_sign_BYTES];

/* 1. Generate long-term identity keypair (done once, stored securely) */
crypto_sign_keypair(client_pk, client_sk);

/* 2. Broker sends a random challenge to prevent replay */
recv(sock, challenge, sizeof(challenge), 0);

/* 3. Client signs the challenge with Ed25519 private key */
crypto_sign_detached(sig, NULL, challenge, sizeof(challenge), client_sk);

/* 4. Send public key + signature over TLS-mimicked port 443 */
send(sock, client_pk, sizeof(client_pk), 0);
send(sock, sig,       sizeof(sig),       0);

/* --- BROKER SIDE --- */
unsigned char recv_pk[crypto_sign_PUBLICKEYBYTES];
unsigned char recv_sig[crypto_sign_BYTES];

recv(sock, recv_pk,  sizeof(recv_pk),  0);
recv(sock, recv_sig, sizeof(recv_sig), 0);

/* 5. Broker verifies against the X.509 certificate's public key */
if (crypto_sign_verify_detached(recv_sig, challenge, sizeof(challenge), recv_pk) != 0) {
    // Authentication failed — close connection
    close(sock);
    return -1;
}
/* Client identity confirmed. Proceed to key exchange. */
```

### 3.4 Ephemeral Key Exchange (X25519 ECDHE) — Step B

After identity is confirmed, each party generates a fresh ephemeral X25519 keypair. The shared secret is derived using Diffie-Hellman and never transmitted. The broker routes the public keys but cannot derive the secret. Separate RX and TX keys are derived via HKDF.

```c
/* Step B: X25519 Key Exchange — Low-level C using libsodium */

#include <sodium.h>
#include <string.h>
#include <sys/socket.h>

int perform_key_exchange(int sock, int is_client) {
    unsigned char my_pk[crypto_kx_PUBLICKEYBYTES];
    unsigned char my_sk[crypto_kx_SECRETKEYBYTES];
    unsigned char their_pk[crypto_kx_PUBLICKEYBYTES];
    unsigned char rx[crypto_kx_SESSIONKEYBYTES];  /* receive key */
    unsigned char tx[crypto_kx_SESSIONKEYBYTES];  /* transmit key */

    /* 1. Generate ephemeral keypair — fresh per session */
    crypto_kx_keypair(my_pk, my_sk);

    /* 2. Exchange public keys through broker (broker sees keys, NOT secret) */
    send(sock, my_pk, sizeof(my_pk), 0);
    recv(sock, their_pk, sizeof(their_pk), 0);

    /* 3. Derive session keys — broker CANNOT compute this */
    int ret;
    if (is_client) {
        ret = crypto_kx_client_session_keys(rx, tx, my_pk, my_sk, their_pk);
    } else {
        ret = crypto_kx_server_session_keys(rx, tx, my_pk, my_sk, their_pk);
    }

    if (ret != 0) {
        return -1; /* Key exchange failed — peer keys may be invalid */
    }

    /* 4. Securely wipe ephemeral private key from memory */
    sodium_memzero(my_sk, sizeof(my_sk));

    /* rx and tx are now the session encryption keys */
    /* Store them in your session context struct */
    return 0;
}
```

> **Time-Boundedness Policy:** Keys are per-session. On disconnect or after a configurable timeout (e.g., 1 hour), both parties discard rx/tx keys and `sodium_memzero()` the buffers. A new ECDHE handshake must be performed to rejoin. This provides forward secrecy — compromise of a key does not expose previous sessions.

### 3.5 Session Key Upgrade — Insecure to Secure Mode

When a user switches from insecure to secure mode mid-session, they perform the X25519 handshake with all currently-authenticated members. They then receive the current session key (encrypted to their new public key). Subsequent messages switch to encrypted payloads automatically.

```c
/* Mid-session upgrade: insecure → secure mode */

/* New user broadcasts their X25519 public key */
broadcast_to_room(room_id, MSG_TYPE_KX_REQUEST, my_pk, sizeof(my_pk));

/* Each secure member responds with the session key,
   encrypted to the new user's public key using crypto_box */
unsigned char encrypted_session_key[crypto_box_MACBYTES + SESSION_KEY_LEN];
crypto_box_easy(encrypted_session_key,
    current_session_key, SESSION_KEY_LEN,
    nonce, new_user_pk, my_sk);

send_to_peer(new_user_sock, MSG_TYPE_SESSION_KEY,
    encrypted_session_key, sizeof(encrypted_session_key));

/* New user decrypts the session key with their private key */
crypto_box_open_easy(session_key, encrypted_session_key,
    sizeof(encrypted_session_key), nonce, sender_pk, my_sk);
```

---

## 4. Steganographic Packet Design

### 4.1 The Stealth JSON Envelope

Rather than exposing visible ciphertext to unauthenticated users, every message — secure or plaintext — is wrapped in an identical outer envelope. Insecure clients see a normal chatroom. The encrypted payload is hidden inside a field that appears to be random noise, routing metadata, or a heartbeat ping.

```json
{
  "user":   "alice",
  "ts":     1704892800,
  "status": "online",
  "ping":   "8f3a9c2d",
  "seq":    42,
  "d":      "<base64 blob>"
}
```

- `seq` — sequence number allowing the client to reorder messages before attempting decryption
- `d` — always present, always the same length, always looks like random noise
- Insecure clients render `user`, `ts`, and any plaintext channel messages
- Secure clients extract `d`, validate HMAC, decrypt, and reassemble in `seq` order

### 4.2 The 'd' Field Binary Structure

The `d` field is a base64-encoded binary structure. Its length is padded to a fixed size so all messages appear identical on the wire.

```
[ version:    1 byte  ]
[ key_id:     4 bytes ]
[ iv/nonce:  16 bytes ]
[ hmac:      32 bytes ]
[ ciphertext: n bytes ]
```

| Field | Description |
|---|---|
| version (1 byte) | Protocol version. Currently 0x01. |
| key_id (4 bytes) | Identifies which session key was used. Allows rotation without full re-handshake. |
| iv / nonce (16 bytes) | Unique per message. Generated with `randombytes_buf()`. Never reused. |
| hmac (32 bytes) | HMAC-SHA256 over (version \|\| key_id \|\| iv \|\| ciphertext). Validated before decryption. |
| ciphertext (n bytes) | AES-256-GCM encrypted payload. Padded to fixed block size to prevent length leakage. |

```c
/* Packing the 'd' field in C */

#define D_VERSION       0x01
#define IV_LEN          16
#define HMAC_LEN        32
#define KEY_ID_LEN      4
#define HEADER_LEN      (1 + KEY_ID_LEN + IV_LEN + HMAC_LEN)

typedef struct {
    uint8_t  version;
    uint8_t  key_id[KEY_ID_LEN];
    uint8_t  iv[IV_LEN];
    uint8_t  hmac[HMAC_LEN];
    uint8_t  ciphertext[];  /* flexible array — padded to fixed size */
} __attribute__((packed)) d_packet_t;

int pack_d_field(d_packet_t *out, size_t out_max,
                 const uint8_t *plaintext, size_t pt_len,
                 const uint8_t *session_key, const uint8_t *key_id) {

    out->version = D_VERSION;
    memcpy(out->key_id, key_id, KEY_ID_LEN);

    /* Fresh nonce per message */
    randombytes_buf(out->iv, IV_LEN);

    /* Encrypt with AES-256-GCM */
    unsigned long long clen;
    crypto_aead_aes256gcm_encrypt(
        out->ciphertext, &clen,
        plaintext, pt_len,
        NULL, 0,           /* no additional data */
        NULL,              /* no nsec */
        out->iv, session_key
    );

    /* HMAC over version + key_id + iv + ciphertext */
    crypto_auth_hmacsha256(out->hmac,
        (uint8_t*)out, 1 + KEY_ID_LEN + IV_LEN + (size_t)clen,
        session_key);

    return 0;
}
```

---

## 5. Packet Mimicry & Protocol Stack

### 5.1 TLS Record Camouflage

Custom MQTT-like packets are encapsulated to match standard HTTPS TLS Record format. To a passive observer or shallow-inspection firewall, traffic appears as a normal browser HTTPS session.

```c
/* TLS Record header camouflage — written as raw bytes before payload */

#define TLS_APP_DATA  0x17        /* Application Data record type */
#define TLS_VERSION   0x0303      /* TLS 1.2 (wire-compat with 1.3) */

typedef struct {
    uint8_t  content_type;       /* 0x17 = Application Data */
    uint16_t version;            /* 0x0303 big-endian */
    uint16_t length;             /* size of encrypted payload, big-endian */
} __attribute__((packed)) tls_record_hdr_t;

/* HTTP Upgrade handshake sent by client to look like browser */
const char *http_upgrade =
    "GET /stream HTTP/1.1\r\n"
    "Host: yourbroker.com\r\n"
    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
    "Upgrade: custom-mqtt\r\n"
    "Connection: Upgrade\r\n"
    "\r\n";

/* After server ACKs the upgrade, switch to binary MQTT-like packets */
/* To Wireshark: looks like a long-running HTTPS session */
```

### 5.2 OSI Model Mapping

| OSI Layer | Implementation |
|---|---|
| Application (L7) | MQTT Protocol Layer — publish/subscribe topic routing, message framing |
| Presentation (L6) | TLS/SSL Layer — ECC/AES encryption lives here; data appears as TLS Application Data |
| Session (L5) | ECDHE negotiation of AES-256 session key; mTLS handshake completes here |
| Transport (L4) | Stealth JSON envelope wraps ECC-signed packets — hides the key exchange from DPI |
| Network (L3) | Port 443 — chosen to blend with HTTPS and traverse most firewalls |
| Data Link (L2) | Standard Ethernet framing — no modifications |
| Physical (L1) | Standard physical medium — no modifications |
| Identity (cross-cutting) | ECDSA (prime256v1) for Root CA and Client Certificates — ZTA identity layer |

### 5.3 Protocol Stack

```
[Frontend / CLI]
      |
[POSIX Sockets - sys/socket.h]   ← Raw TCP, total control over stream
      |
[TLS Mimic Headers]              ← 0x17 0x0303 + fake HTTP Upgrade
      |
[MQTT Broker - Mosquitto:443]    ← Pub/Sub routing (broker is postman, not translator)
      |
[X.509 mTLS + Client Certs]      ← CA-signed, ZTA identity layer
      |
[X25519 ECDHE]                   ← Broker routes handshake, cannot derive secret
      |
[AES-256-GCM Payload]            ← Encrypted 'd' field inside stealth JSON envelope
```

---

## 6. Methodology

### 6.1 Implementation Phases

The project uses a client/server architecture in C. Client-side handles all E2EE so the server never sees plaintext. Server acts as the broker (postman) only.

1. **Phase 1 — Socket Foundation:** Establish raw POSIX TCP socket connection on port 443. Implement TLS-mimic headers for firewall traversal.
2. **Phase 2 — CA & Certificate Infrastructure:** Generate Root CA with `openssl ecparam -name prime256v1`. Issue client X.509 certificates. Configure Mosquitto for mTLS.
3. **Phase 3 — Mutual Authentication:** Implement Ed25519 challenge-response in C using libsodium. Broker verifies client certificates before allowing subscription.
4. **Phase 4 — Key Exchange:** Implement X25519 ECDHE per-session. Derive separate RX/TX keys via `crypto_kx_client/server_session_keys()`. Implement `sodium_memzero()` cleanup.
5. **Phase 5 — Message Encryption:** Implement AES-256-GCM payload encryption. Build the `d` field packer/unpacker with HMAC-SHA256 integrity validation.
6. **Phase 6 — Steganographic Envelope:** Wrap all messages in identical JSON envelopes. Implement sequence numbering for out-of-order reassembly. Verify Wireshark capture shows uniform traffic.
7. **Phase 7 — UX Toggle & CLI:** Build secure/insecure mode switch. Implement mid-session upgrade handshake. Demonstration mode showing encrypted vs. plaintext view.
8. **Phase 8 — Immutable Logging:** Implement append-only access logs. Log all auth attempts, subscriptions, and key exchanges. Log format should be tamper-evident (hash-chained).

### 6.2 Key Design Decisions

| Decision | Resolution |
|---|---|
| Encryption scope | Client-side (E2EE). Server/broker never sees plaintext. Zero-trust: broker is untrusted. |
| Data model | Streaming (real-time). Not ETL. Messages are continuous; no batch dumps. |
| Message history | Session-only. No archival. Keys are ephemeral — past messages cannot be decrypted after session ends. |
| Key lifetime | Per-session. On disconnect, `sodium_memzero()` all key material. New session = new ECDHE. |
| Firewall traversal | Port 443 + HTTP Upgrade header. Custom binary protocol behind standard-looking HTTPS. |

### 6.3 Component Responsibilities

**Client:** Sends ClientHello-style HTTP Upgrade. Performs mTLS with X.509 cert. Runs X25519 ECDHE. Encrypts payloads before hitting the broker. Wraps in stealth JSON. Decrypts received `d` fields.

**Server/Broker (Mosquitto):** Routes MQTT pub/sub messages. Validates client certificates (mTLS). Routes key exchange messages between clients. Never derives or sees session keys.

**Both:** A time-server synchronization check helps prevent replay attacks. If a client's clock is too far from the server's, packets are rejected as potentially replayed.

---

## 7. Expected Outcomes

This project simulates the environment of modern endpoints and streaming platforms where interconnected entities — whether human users or IoT devices — must communicate securely over untrusted infrastructure.

Unlike consumer-facing applications, internal data pipelines are often less stringently audited despite being equally vulnerable. Many modern data breach incidents involved hard-coded credentials in such pipelines. In ZTA infrastructure, every pipeline component must be assumed untrusted until verified (Bhoite).

The final demonstration will show, via Wireshark capture, that encrypted and plaintext messages are indistinguishable at the network layer. An unauthenticated observer sees only uniform background traffic — heartbeats, pings, status metadata — with no visible ciphertext and no indication that a high-security key exchange is occurring.

---

## 8. Timeline

| Phase | Tasks |
|---|---|
| To Do | Socket infrastructure, port 443 setup, HTTP Upgrade mimic, Mosquitto broker configuration |
| To Do | CA generation (OpenSSL), X.509 client certificates, mTLS configuration |
| To Do | Ed25519 mutual authentication, challenge-response in C, libsodium integration |
| To Do | X25519 ECDHE key exchange, session key derivation, sodium_memzero cleanup |
| To Do | AES-256-GCM payload encryption, 'd' field packer, HMAC validation, sequence numbers |
| To Do | Steganographic envelope, JSON wrapping, Wireshark verification |
| To Do | UX/CLI toggle, mid-session upgrade handshake, secure/insecure mode demo |
| To Do | Immutable logging, final integration, VMware multi-client demonstration |

---

## 9. Resources

### Hardware

- Client Device: Raspberry Pi (simulates constrained IoT endpoint)
- Network: Router (demonstrates real network traversal)
- Server Device: Linux machine running Mosquitto broker
- Demonstration: Windows 10 VM in VMware (multi-client simulation)

### Software Stack

| Component | Purpose |
|---|---|
| libsodium | Primary crypto library. Ed25519, X25519, AES-256-GCM, HMAC-SHA256. Reference implementation. |
| wolfSSL | Fallback/alternative. Portable C, smaller than OpenSSL, custom I/O callbacks for HTTP header wrapping. |
| mbedTLS | Alternative for clean separation of crypto and transport layers. |
| Mosquitto | MQTT broker, industry standard. Run on port 8883 internally, exposed via 443 proxy. |
| libmosquitto.h | C client library for MQTT. Used to connect client to broker. |
| OpenSSL (ecparam) | CA generation only: `openssl ecparam -name prime256v1`. X.509 cert issuance. |
| libuv | Asynchronous event-driven networking. Handles concurrent connections on port 443. |
| POSIX sys/socket.h | Raw socket control. Necessary to construct TLS-mimic headers and custom frames. |
| Wireshark | Demonstration tool. Verifies packet uniformity; shows traffic looks like normal HTTPS. |
| VMware | Virtualization for multi-client demonstration without additional hardware. |

---

## 10. Ethical Considerations

This project is dual-use technology. The same mechanisms that provide privacy and security — traffic camouflage, steganographic payloads, covert key exchange — could be repurposed as a command-and-control (C2) channel for malware. This section documents those risks explicitly.

The steganographic envelope and port-443 camouflage are precisely the techniques used in advanced persistent threat (APT) C2 infrastructure. Publishing this as open-source code would provide a functional blueprint for data exfiltration that bypasses standard network defenses.

Specific concerns:

- Traffic mimicry can evade deep packet inspection (DPI) firewalls with heuristic inspection.
- Steganographic payloads hide the existence of communication, not just its content.
- On open operating systems (Linux), the toolchain could be distributed without registry traces.
- If extended with a reverse shell and credential harvesting (e.g., `/etc/shadow` exfiltration), this becomes a complete intrusion toolkit.

Mitigations and ethical protocols followed in this project:

- Code is developed in a closed, air-gapped lab environment. Not published to public repositories.
- Demonstration is performed only on hardware and VMs owned by the project team.
- No real credentials, certificates, or private keys are committed to version control.
- The project is documented as an academic exercise, not a deployable tool.
- All Wireshark captures use synthetic/simulated traffic only.

---

## 11. Conclusion

This project implements a complete cryptographic suite demonstrating confidentiality, integrity, and authenticity over an untrusted network. By combining Ed25519 for identity, X25519 ECDHE for forward-secret key exchange, AES-256-GCM for payload encryption, and a steganographic JSON envelope for traffic camouflage, we produce a system that satisfies the requirements of a Zero Trust Architecture while appearing, to a network observer, as ordinary browser traffic.

The use of ECC over RSA is justified by the security-per-byte efficiency critical in constrained IoT environments. The implementation in low-level C using libsodium follows established cryptographic best practices and avoids the pitfalls of rolling custom primitives.

The dual-use nature of this technology is acknowledged and addressed. The project's significance lies not only in the implementation but in demonstrating that security and obscurity, while not substitutes, can be combined to produce robust, auditable, and practically deployable systems.

---

## 12. References

Bhoite, Harshraj. Zero-Trust Architecture in Streaming Dataflows. TechRxiv, 20 July 2025. https://doi.org/10.36227/techrxiv.175303721.12297807/v1

Kobeissi, Nadim, Karthikeyan Bhargavan, and Bruno Blanchet. Automated Verification for Secure Messaging Protocols and Their Implementations: A Symbolic and Computational Approach. 2nd IEEE European Symposium on Security and Privacy, April 2017, Paris, France. pp. 435–450. doi:10.1109/EuroSP.2017.38

Owens, D., El Khatib, R., Bisheh-Niasar, M., Azarderakhsh, R., & Mozaffari Kermani, M. (2021). Efficient and Side-Channel Resistant Ed25519 on ARM Cortex-M4. IEEE Transactions on Computers, 71(4), 850–861. https://doi.org/10.1109/TC.2021.3065620

Suárez-Albela, M., Fernández-Caramés, T. M., Fraga-Lamas, P., & Castedo, L. A Practical Performance Comparison of ECC and RSA for Resource-Constrained IoT Devices. 2018 Global Internet of Things Summit (GIoTS), Bilbao, Spain. pp. 1–6. doi:10.1109/GIOTS.2018.8534575
