# Project: AirRoute — Pollution-Aware Navigation System

### **Technical Summary for Resume**

**Technologies:** Python (FastAPI), OSMnx, Scikit-Learn, NetworkX, Pandas, React.js, K-D Trees, REST APIs.

*   **Pollution-Aware Routing Engine**: Architected a custom navigation algorithm using **Dijkstra’s algorithm** with a dynamically weighted **"Pollution Tax"** cost function, enabling the system to prioritize cleaner air paths (parks/residential areas) over high-traffic corridors.
*   **Multi-Source Data Fusion**: Engineered a high-availability ingestion pipeline that fuses real-time data from 4+ global APIs (**OpenAQ, IQAir, WAQI, Luchtmeetnet**) with local hardware sensors, utilizing a weighted fusion algorithm (70/30 split) for localized ground-truth accuracy.
*   **Predictive Analytics**: Developed a spatiotemporal forecasting engine using **Random Forest Regressors** to predict AQI trends up to 7 days in advance, allowing for proactive, health-conscious route planning.
*   **Geospatial Performance Optimization**: Leveraged **K-D Trees** for efficient node-level air quality mapping and **OSMnx** for memory-efficient road network graph processing, achieving sub-second path calculation for complex urban environments.
*   **Security & Resilience Architecture**: Designed a "Defensive Backend" featuring **Pydantic**-hardened data validation, thread-locked lazy loading for resource management, and a metadata-obfuscated "Ghost Vault" for secure environment variable handling.
*   **Privacy-by-Design**: Implemented an anonymized routing architecture that processes user traces in-memory without persistent PII storage, ensuring **GDPR/CCPA compliance** through zero-trace data handling.

---

# Project: SecureLocal Drive (Anti-grav)

### **Technical Summary for Resume**

**Technologies:** Python (FastAPI), Cryptography.io, React.js, SQLite, JWT, Bcrypt, AES-256-CBC.

*   **Zero-Knowledge Architecture**: Developed a high-security file management system where encryption keys are derived on-the-fly in RAM and never stored on disk, ensuring data remains mathematically inaccessible even if the hardware is compromised.
*   **Enterprise-Grade Cryptography**: Implemented a hardened security stack utilizing **AES-256-CBC** for file encryption and **PBKDF2-HMAC-SHA256** with 100,000 iterations for brute-force resistant key derivation.
*   **Data Integrity Protection**: Engineered an automated auditing layer using **SHA-256 bit-by-bit integrity checks**, preventing unauthorized modifications or bit-rot through proactive fingerprint verification.
*   **Metadata Obfuscation**: Designed a **"Ghost Vault"** file system that masks sensitive filenames by renaming physical disk assets to random 32-character **UUID4 strings**, effectively neutralizing OS-level search indexing and metadata snooping.
*   **Version Control & Recovery**: Built an **append-only state-management system** that preserves file histories during edits, providing a robust disaster recovery mechanism and protection against accidental data loss.
*   **Secure Access Control**: Integrated **Bcrypt** password hashing and **JWT-based session management** with a custom multi-user permission matrix for fine-grained file-level access control.
