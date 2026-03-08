# Project: Secure Chat Room

## 1. Introduction
### Overview
We plan to design a simple encrypted messaging service, a centralized chat room, where users can log in and communicate securely. There will also be an option for a user to communicate insecurely within the same chat room.

When a user selects the secure chat room option, the client is configured to transmit messages in plaintext. This serves as a demonstration of the effect which encryption has on the data. In encrypted mode the user is provided with full privacy, and the messages are unreadable to unauthorized parties. In the insecure mode, the client cannot decrypt encrypted messages, but all plain text messages from other users remain readable. 

This feature is added to demonstrate the effect encryption has on messages. 

### Project Significance/Relevance
* **Public key handling:** Implementing infrastructure to share keys between clients and the server 
* **Encryption:** Applying cryptography and/or steganography to real-time data 
* **Secure data transfer**
* **Private key handling**

## 2. Background and Literature Review

### Existing Research
1. **There is the key distribution problem:** One of the primary challenges is the secure exchange of keys between two parties without an interceptor gaining access to the keys.

### Gaps

## 3. Methodology
The project will use a simple client/server configuration. A client will run a Python script on their machine which connects to the remote server running any accompanying server-side script. 

### Responsibilities of the Client and the Server:

### Flow:
1. Establish basic socket connection
2. Implement RSA/AES key exchange protocols
3. Develop the toggle for plaintext vs. ciphertext transmission
4. Build the UX/CLI

 **Describe the research design or methodology that will be used to achieve the project objectives.
 **Explain the data collection methods, tools, or techniques that will be employed.
 **Outline the steps or procedures that will be followed to conduct the project.
    * A flowchart/diagram is required to show the steps or procedures.

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
* Describe the anticipated results or outcomes of the project.

## 5. Timeline:
* Provide a detailed timeline or schedule for the project, including key milestones and deadlines.
* Break down the project into smaller tasks or phases and allocate time accordingly.

## 6. Resources:
* Identify the resources required to complete the project (e.g., equipment, software, materials).
* Mention any collaborations or partnerships that will be involved in the project.

### Resources:

* Hardware
1. Client Device
2. Server Device

 * Software


## 7. Ethical Considerations:
* Discuss any ethical considerations or potential risks associated with the project.
* Explain how ethical guidelines or protocols will be followed during the project.

## 8. Conclusion:
* Summarize the key points of the project proposal.
* Emphasize the potential impact or significance of the project.

## 9. References:

### For analysis of zero-trust architectures in real-time communnication systems
* Bhoite, Harshraj. Zero-Trust Architecture in Streaming Dataflows. TechRxiv, 20 July 2025, https://doi.org/10.36227/techrxiv.175303721.12297807/v1

* Include a list of references cited in the proposal using the appropriate citation style (e.g., APA, MLA).
