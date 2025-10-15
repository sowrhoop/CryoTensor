# Security Policy

Our primary goal is to ensure the protection and confidentiality of sensitive data stored by users on open-webui.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| others  | :x:                |

## Zero Tolerance for External Platforms

Based on a precedent of an unacceptable degree of spamming and unsolicited communications from third-party platforms, we forcefully reaffirm our stance. **We refuse to engage with, join, or monitor any platforms outside of GitHub for vulnerability reporting.** Our reasons are not just procedural but are deep-seated in the ethos of our project, which champions transparency and direct community interaction inherent in the open-source culture. Any attempts to divert our processes to external platforms will be met with outright rejection. This policy is non-negotiable and understands no exceptions.

Any reports or solicitations arriving from sources other than our designated GitHub repository will be dismissed without consideration. We’ve seen how external engagements can dilute and compromise the integrity of community-driven projects, and we’re not here to gamble with the security and privacy of our user community.

## Reporting a Vulnerability

We appreciate the community's interest in identifying potential vulnerabilities. However, effective immediately, we will **not** accept low-effort vulnerability reports. To ensure that submissions are constructive and actionable, please adhere to the following guidelines:

Reports not submitted through our designated GitHub repository will be disregarded, and we will categorically reject invitations to collaborate on external platforms. Our aggressive stance on this matter underscores our commitment to a secure, transparent, and open community where all operations are visible and contributors are accountable.

1. **No Vague Reports**: Submissions such as "I found a vulnerability" without any details will be treated as spam and will not be accepted.

2. **In-Depth Understanding Required**: Reports must reflect a clear understanding of the codebase and provide specific details about the vulnerability, including the affected components and potential impacts.

3. **Proof of Concept (PoC) is Mandatory**: Each submission must include a well-documented proof of concept (PoC) that demonstrates the vulnerability. If confidentiality is a concern, reporters are encouraged to create a private fork of the repository and share access with the maintainers. Reports lacking valid evidence will be disregarded.

4. **Required Patch Submission**: Along with the PoC, reporters must provide a patch or actionable steps to remediate the identified vulnerability. This helps us evaluate and implement fixes rapidly.

5. **Streamlined Merging Process**: When vulnerability reports meet the above criteria, we can consider them for immediate merging, similar to regular pull requests. Well-structured and thorough submissions will expedite the process of enhancing our security.

**Non-compliant submissions will be closed, and repeat violators may be banned.** Our goal is to foster a constructive reporting environment where quality submissions promote better security for all users.

## Product Security

We regularly audit our internal processes and system architecture for vulnerabilities using a combination of automated and manual testing techniques. We are also planning to implement SAST and SCA scans in our project soon.

For immediate concerns or detailed reports that meet our guidelines, please create an issue in our [issue tracker](/open-webui/open-webui/issues) or contact us on [Discord](https://discord.gg/5rJgQTnV4s).

## Sensitive Credential Storage

CryoTensor now treats third-party API keys (OpenAI, Azure OpenAI, Gemini, etc.) as sensitive secrets. To persist these credentials at rest you **must** set the `CONFIG_ENCRYPTION_KEY` environment variable before starting the backend. The value can be any high-entropy string; it is hashed and used to encrypt secrets before they are written to the database. When `CONFIG_ENCRYPTION_KEY` is missing, all sensitive keys stay in-memory only and are flushed on restart—this is the safest mode for working with untrusted API keys.

Additional hardening shipped with this release:

- Admin APIs and the UI only expose masked fingerprints of stored keys. Updating a connection requires re-entering the key or explicitly clearing it, eliminating the risk of accidental key disclosure in logs or browser storage.
- Redis replication is automatically skipped for sensitive configuration values, avoiding accidental propagation of secrets to shared cache nodes.
- Bulk configuration imports encrypt any embedded secrets on write; imports without `CONFIG_ENCRYPTION_KEY` drop sensitive fields instead of persisting them in plain text.
- Chat transcripts saved in the database are transparently encrypted with the same key. Without `CONFIG_ENCRYPTION_KEY` the server keeps chat history in plaintext so that you can still operate, but we strongly advise running without history persistence or setting the key before production use.
- When chat data is encrypted at rest, full-text SQL searches across message bodies are disabled to prevent leaking prompts through query planning. The web UI still loads history after decryption, but content searches fall back to client-side filtering.
- To prevent hostile proxying, only OpenAI endpoints listed in the `OPENAI_ALLOWED_API_BASE_URLS` environment variable are accepted (default: `https://api.openai.com/v1`). Any attempt to configure a different upstream is rejected by the admin API and UI.
- Local encryption is optional: set `ENABLE_LOCAL_ENCRYPTION=true` alongside `CONFIG_ENCRYPTION_KEY` when you want encrypted-at-rest storage. Leave it unset (the default) to keep local data in plaintext without warnings or feature changes on trusted machines.

If you rotate your secrets, supply the new key through the Admin UI or environment variables. We recommend backing up the encryption key alongside other critical deployment secrets, as it is required to decrypt existing values.

---

_Last updated on **2024-08-19**._
