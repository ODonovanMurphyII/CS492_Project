# Project: Secure Chat Room

## 1. Introduction
### Overview
We plan to design a simple encrypted messaging service, a centralized chat room, where users can log in and communicate securely. There will also be an option for a user to communicate insecurely within the same chat room.

When a user selects the secure chat room option, the client is configured to transmit messages in ciphertext. This serves as a demonstration of the effect which encryption has on the data. In encrypted mode the user is provided with full privacy, and the messages are unreadable to unauthorized parties. In the insecure mode, the client cannot decrypt encrypted messages, but all plain text messages from other users remain readable. 

This feature is added to demonstrate the effect encryption has on messages. 

### Project Significance/Relevance
* **Public key handling:** Implementing infrastructure to share keys between clients and the server 
* **Encryption:** Applying cryptography and/or steganography to real-time data 
* **Secure data transfer**
* **Private key handling**
* **Zero-Trust Architecture (ZTA)**
* **Cryptographic Implementation**

## 2. Background and Literature Review

### Existing Research
1. **There is the key distribution problem:** One of the primary challenges is the secure exchange of keys between two parties without an interceptor gaining access to the keys.
2. Signal protocol sought to enable asynchronous authenticated messaging between users with end-to-end confidentiality. Signal uses a key exchange protocol based on mixing Diffie-Hellman shared secrets and a key refresh mechanism called double ratcheting (Nadim). The security model is as follows:[To be continued]. Security goals set forth include the properties of message authenticity, no replays, and no key compromise impersonation. Four confidentiality goals are then set forth: secrecy, forward secrecy.

  
* note we should address how long we expect our system to stay secure for. This is an important consideration with cryptographic applications. 



### The Trust Model
We utilize a Zero Trust Architecture (ZTA). Unlike traditional perimeter-based security, ZTA assumes the network is compromised. 
* Strict Identity Verification: Occurs via credentials or cryptographic tokens
* Least-Privilege Access: Mitigates the risk of compromised credentials
* Micro-Segmentation: Dividing the network into zones to prevent laterla movement 

### Gaps
Current simple chat tutorials often ignore the lateral movement.

## 3. Methodology
The project will use a simple client/server configuration in Python. A client will run a Python script on their machine which connects to the remote server running any accompanying server-side script. 
Client Side: Handles End-to-End encryption so the server doesn't see the plaintext
Server Side: Acts as the broker for the data and presents its identity to sensors/clients

### Flow
1. Establish basic socket connection
2. Mutual authentication of all entities (each process, application, device, or user interacting must prove it's identity, preferably with a hardware-backed entity such as a client certificate or signed token when sending  data. The steraming endpoint (broker) should present it's identity to the sensors. If not using a YubiKey or TPM, we simulatate with software-based keys like RSA.
4. The consumer should autheticate before subscribing. Stream topics, queues, or API endpoints should have fine-grained access policies such as role-based access control (RBAC) or attribute based access control (ABAC) which determine where each user/device/sensor should read or write data.
5. End-to-End encryption so data is protected while in transit and at rest. Current standards are TLS 1.2/1.3 and DTLS for UDP. Only producers and intended consumers should hold the decryption keys and this prevents the data from being altered in transit.
6. There should be immutable logs as a zero-trust system requires full observability. This should include access attempts, data ingestion and commiting events and inter-process communication. Logs should be tamper resistent meaning apphend only. 
7. Implement RSA/AES key exchange protocols
8. Develop the toggle for plaintext vs. ciphertext transmission
9. Build the UX/CLI

Zero Trust Applied to the Various Components:
1. Device Authentication
2. Encrypted Transport
3. Least Privilege Access
4. Segmentation
5. Real Time Monitoring 

### Describe the research design or methodology that will be used to achieve the project objectives.
### Explain the data collection methods, tools, or techniques that will be employed.
### Outline the steps or procedures that will be followed to conduct the project.
* 
### A flowchart/diagram is required to show the steps or procedures.

### Considerations = the trust model.
* 1. Will we use client side or server side encryption? Client-side (End-to-End) means that the server will never see the plaintext but server side encryption means the server is trusted and could intercept messages.
I believe we would be using a Zero Trust Architecture (ZTA) defined by the sentiment "never trust, always verify." which is well suited for IoT and most modern IT environments (Bhoite).
Zero trust requires strong authentication (often multi-factor, strict authorization, segmentation, and continuous monitoring (Bhoite).

* Strict Identity Verification occurs via credentials, certificates, or cryptographic tokens before accessing resources.
* Least-privilege to mitigate risk of compromised credentials
* Micro-segmentation where a network is divided into zones so a successful attacker cannot move laterally
* Continuous monitoring where all transactions are logged and analyzed in real-time to detect anomalies. This privdes threat detection and forensic tracing.
  
2. Will we use a streaming model or a ETL model? Streaming meaning a continuous dataflow in real time as compared to the extract-transform-load model where data is dumped in chunks with individual records.
3. How long data will be cached? Will clients be able to access only messages being exchanged currently in the chat room or will they have archival history that can be viewed.

### Responsibilities of: 
1. **The Client:**
2. **The Server:**

## 4. Expected Outcomes:
   This project simulates the environment of many modern endpoints and streaming platforms where entites are interconnected. Whether the parties chatting are devices or users is lategely irrelevant as the connection mechanism is largely the same. Unlike consumer-facing applications, internal data pipelines often less stenuously audited despite being vulnerable to attack and many modern data breach incidents involved hard-coded credentials. In ZTA infrastructure, every pipeline component must be assumed to be untrusted until verified (Bhoite).

### Describe the anticipated results or outcomes of the project.

## 5. Timeline:
* Provide a detailed timeline or schedule for the project, including key milestones and deadlines.
* Break down the project into smaller tasks or phases and allocate time accordingly.

## 6. Resources:
* Identify the resources required to complete the project (e.g., equipment, software, materials).
* Mention any collaborations or partnerships that will be involved in the project.

### Resources:

### Hardware:
1. **Client Device**
2. **Server Device**

 ### Software: 


## 7. Ethical Considerations:
* Discuss any ethical considerations or potential risks associated with the project.
* Explain how ethical guidelines or protocols will be followed during the project.

## 8. Conclusion:
* Summarize the key points of the project proposal.
* Emphasize the potential impact or significance of the project.

## 9. References:
Include a list of references cited in the proposal using the appropriate citation style (e.g., APA, MLA).


### For analysis of zero-trust architectures in real-time communication systems
* Bhoite, Harshraj. Zero-Trust Architecture in Streaming Dataflows. TechRxiv, 20 July 2025, https://doi.org/10.36227/techrxiv.175303721.12297807/v1
*Nadim Kobeissi, Karthikeyan Bhargavan, Bruno Blanchet. Automated Verification for Secure Messaging Protocols and Their Implementations: A Symbolic and Computational Approach. 2nd IEEE
European Symposium on Security and Privacy , Apr 2017, Paris, France. pp.435 - 450, ff10.1109/EuroSP.2017.38ff. ffhal-01575923f
