# Poisoned knowledge base (lab only)

These files contain **intentional indirect prompt-injection payloads** for Phase 1 demos.

| File | Attack |
|------|--------|
| `POISONED_direct_override.txt` | Ignore previous instructions / reveal system prompt |
| `POISONED_exfiltration.txt` | Leak secrets / other users' data |
| `POISONED_system_update.txt` | Fake system update / developer message |
| `POISONED_roleplay_jailbreak.txt` | Unrestricted AI / DAN-style role-play |

**Do not** deploy these into a production RAG corpus.
All company content is fictional (Acme Corp).
