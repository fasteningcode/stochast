# stochast

Testing framework for AI features that don't behave the same way twice.

---

The standard way to test software doesn't work for LLMs. When you ask an AI the same question twice, you get two different answers. So asserting `output == expected` is useless — and mocking the model just means you're testing your mock.

Stochast takes a different approach: run the test N times, assert that it passes *enough* of them.

```python
@stochast.test(runs=20, threshold=0.90)
async def test_sentiment_classifier(ctx):
    output = await llm("Classify: 'This product is amazing!'")
    return output, BehavioralProperty(
        fn=lambda out, c: out.text.strip().lower() in {"positive", "negative", "neutral"},
        name="valid_label"
    )
```

If 18 out of 20 runs return a valid label, the test passes. If your next prompt change drops it to 12 out of 20, the test fails and CI catches it before users do.

---

## Install

```bash
pip install stochast
```

LiteLLM is bundled — one install gives you access to every major provider (Gemini, OpenAI, Anthropic, Ollama, Mistral, and [100+ more](https://docs.litellm.ai/docs/providers)). Just set the right environment variable for the model you're using.

---

## Quickstart

```python
# tests/test_my_feature.py
import stochast
from stochast.providers import LiteLLMAdapter
from stochast.assertions import LLMJudge

llm = LiteLLMAdapter("gemini/gemini-2.5-flash")  # or "gpt-4o", "anthropic/claude-sonnet-4-6", ...

@stochast.test(runs=20, threshold=0.85)
async def test_support_response_tone(ctx):
    output = await llm(
        "A customer says their order is late and they're angry. Reply as support."
    )
    return output, LLMJudge(
        provider=llm,
        criteria="Response must be empathetic, professional, and offer a concrete next step.",
        score_threshold=0.8,
    )
```

```bash
stochast run tests/
```

```
 Running test_support_response_tone    20/20 runs
   ████████████████████░░░░  17/20 passed  (85.0%)  threshold: 85%  ✓ PASS

────────────────────────────────────────────────────────
 1 test  •  20 LLM calls  •  ~$0.01  •  12.4s
 All 1 tests passed
```

---

## Core concepts

### `@stochast.test(runs, threshold)`

Every test function runs `runs` times in parallel. The test passes if at least `threshold` fraction of runs pass all assertions.

```python
@stochast.test(runs=30, threshold=0.90)
async def test_something(ctx):
    ...
```

The `ctx` argument carries the run index and any metadata you want to thread through to assertions.

### Returning results

Your test function returns a `(output, assertion)` tuple:

```python
async def test_fn(ctx):
    output = await llm("...")
    return output, BehavioralProperty(
        fn=lambda out, c: "refund" in out.text,
        name="mentions_refund"
    )
```

The runner evaluates the assertion against the output for each run independently.

### Assertions

**`BehavioralProperty`** — any Python callable that returns `True` or `False`:

```python
BehavioralProperty(
    fn=lambda out, ctx: 0.05 <= float(out.raw["score"]) <= 0.95,
    name="score_in_range"
)
```

**`LLMJudge`** — use a model to grade the output against criteria:

```python
LLMJudge(
    provider=llm,
    criteria="Must not recommend any medical treatments.",
    score_threshold=0.85,
)
```

**`RegexMatcher`** — assert on format:

```python
RegexMatcher(pattern=r"^(yes|no)$", flags=re.IGNORECASE)
```

**`SchemaValidator`** — validate against a Pydantic model:

```python
SchemaValidator(MyResponseModel)
```

**`SemanticSimilarity`** — embedding-based similarity check (requires `stochast[semantic]`):

```python
SemanticSimilarity(reference="Refunds take 5–7 business days.", threshold=0.80)
```

### Composing assertions

`All` requires every assertion to pass. `Any` requires at least one:

```python
return output, All(
    RegexMatcher(pattern=r"^\w+$"),
    LLMJudge(provider=llm, criteria="Must be a single descriptive word."),
)
```

---

## Providers

Stochast uses [LiteLLM](https://docs.litellm.ai/docs/providers) to support every major provider out of the box. Pass any model string LiteLLM accepts:

```python
from stochast.providers import LiteLLMAdapter

llm = LiteLLMAdapter("gemini/gemini-2.5-flash")   # Google Gemini
llm = LiteLLMAdapter("gpt-4o-mini")               # OpenAI
llm = LiteLLMAdapter("anthropic/claude-haiku-4-5") # Anthropic
llm = LiteLLMAdapter("ollama/llama3")              # local via Ollama
llm = LiteLLMAdapter("mistral/mistral-large")      # Mistral
```

API keys are read from environment variables following LiteLLM conventions (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.).

---

## CLI

```
stochast run [PATH]             discover and run tests (default: tests/)
  --runs N                      override run count for all tests
  --threshold T                 override pass-rate threshold (0.0–1.0)
  --junit-xml PATH              write JUnit XML for CI test result parsers
  --json-out PATH               write JSON results
  --filter NAME                 only run tests whose name contains NAME
  --fail-fast                   stop after first failing test
  --concurrency N               max parallel LLM calls (default: 10)
```

---

## CI integration

```yaml
# .github/workflows/ai-tests.yml
- name: Run AI tests
  env:
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  run: stochast run tests/ --junit-xml .stochast/results.xml

- name: Publish results
  if: always()
  uses: EnricoMi/publish-unit-test-result-action@v2
  with:
    files: .stochast/results.xml
```

Exit codes: `0` all passed · `1` threshold failure · `3` infrastructure error · `5` no tests found.

---

## Sample size warnings

Stochast warns when your run count is too small to be statistically meaningful for the threshold you've set:

```
UserWarning: 5 runs is statistically insufficient to reliably confirm a 90%
pass rate. Consider using runs>=35.
```

This uses the Wilson score lower bound. It's a warning, not a hard error — lower counts for local iteration, higher for CI.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
