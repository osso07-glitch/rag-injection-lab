# RAG Injection Lab — Walkthrough

## Local UI

```bash
cd rag-injection-lab
chmod +x run.sh
./run.sh
```

Open http://127.0.0.1:8505

### Happy path (Phase 0 — clean)

1. **Knowledge Base** → leave “Include poisoned” off → provider `mock` → **Build corpus**.
2. **Ask** → “How many vacation days do full-time employees get?”
3. Confirm retrieved chunks from `hr_policy.txt` and a sensible mock/live answer.
4. **Detections** → row should be **clean**.

### Attack path (Phase 1–2)

1. **Attack Lab** → **Build clean+poisoned corpus**.
2. Select **Direct override** → **Run selected attack**.
3. Expect **suspicious** verdict; retrieved chunk from `POISONED_direct_override.txt`.
4. **Detections** → filter verdict=`suspicious` (screenshot candidate).

### Mitigation path (Phase 3)

1. On **Attack Lab** or **Ask**, set mitigation to `quarantine` or `sanitize`.
2. Re-run the same attack question.
3. Compare answer and whether poisoned text still reaches the model (mock provider makes this obvious).

## Headless CLI

```bash
# offline
export RAG_LAB_PROVIDER=mock

rag-injection-lab ingest --name acme-clean --provider mock
rag-injection-lab list-corpora
rag-injection-lab ask --corpus-id <id> -q "How many vacation days do I get?"

rag-injection-lab ingest --name acme-poisoned --include-poisoned --provider mock
rag-injection-lab ask --corpus-id <id> -q "How do I reset my corporate password?"
rag-injection-lab list-queries
rag-injection-lab list-rules
```

## Live OpenAI (optional)

```bash
cp .env.example .env
# set OPENAI_API_KEY=
export RAG_LAB_PROVIDER=openai
rag-injection-lab ingest --name acme-clean --provider openai
rag-injection-lab ask --corpus-id <id> -q "What is MFA policy?" --provider openai
```

## Screenshot for README

Best frame: **Detections** page with at least one **suspicious** row expanded or selected,
showing `rule_id`, severity, and question text.
