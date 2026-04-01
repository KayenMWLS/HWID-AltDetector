## 🛡️ Competitive Integrity Verification Client

A one-time execution verification tool designed to assess system and account trust before granting access to competitive environments.

### 🔍 Overview

This client performs a rapid integrity and risk evaluation at launch, generating a **trust score** based on system identifiers, network signals, and linked account metadata. It is built to reduce alternate account abuse and maintain fair play in competitive scenes.

### 🕵 Detection
[DISCORD BOT INTEGRATION IS IN DEVELOPMENT]
Supports Discord bot integration for pre-access verification. The client analyzes hardware and network identifiers (HWID, IP, MAC) to detect multi-account usage and flag potential alts. Admins receive detailed reports sent to a discord webhook, including failure reasons and a history of associated Discord usernames, enabling informed moderation decisions.

---

### ⚙️ Core Features

* **🧠 Risk Scoring Engine**
  Aggregates multiple signals into a dynamic **alt-account risk score**.

* **💻 System Fingerprinting**

  * HWID components
  * Disk serials
  * Device specifications
  * MAC address

* **🌐 Network Analysis**

  * IP analysis (region / country detection)
  * VPN / proxy detection
  * Consistency checks across sessions

* **🔗 Account Correlation**

  * Discord account linkage
  * Discord account creation date analysis
  * Detection of suspicious or newly created accounts

* **🔁 Alt Detection Logic**

  * Identifies potential multi-account usage patterns
  * Flags shared hardware/network indicators

* **⚡ One-Time Execution**

  * Runs once before access is granted
  * No background services or persistent processes

* **💻 Virtual-Machine Detection**
  
   * Instantly indentifies scans ran trought a VM and fails the verification 

### 🔐 Privacy & Security

* Sensitive identifiers can be **hashed or anonymized** before transmission
* Designed to collect **only necessary anti-abuse signals**
* No continuous tracking or intrusive background monitoring

---

### ⚠️ Disclaimer

This project is intended for **fair-play enforcement and abuse prevention only**.
It should be deployed transparently and in compliance with local privacy regulations and platform policies.

[THE PRODUCT IS STILL IN DEVELOPMENT]
