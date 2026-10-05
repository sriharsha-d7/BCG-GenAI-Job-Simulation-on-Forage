# Financial Chatbot: answers only from verified data

[![CI](https://github.com/sriharsha-d7/bcg-genai-job-simulation-on-forage/actions/workflows/ci.yml/badge.svg)](https://github.com/sriharsha-d7/bcg-genai-job-simulation-on-forage/actions/workflows/ci.yml)

A question-answering bot for the annual financials of **Apple, Microsoft and Tesla (FY2022-2024)**, built from
the BCG GenAI Consulting job simulation on Forage. Every figure in a reply is computed from a dataset checked against
the companies' SEC 10-K filings, and the bot says so when it cannot answer instead of guessing.

```bash
pip install -e ".[dev]"
python -m fin_chatbot                                   # interactive
python -m fin_chatbot --ask "Tesla revenue growth in 2024"
pytest                                                  # 17 tests
pip install -e ".[llm]" && python -m fin_chatbot --llm  # optional: Claude parses the question (needs ANTHROPIC_API_KEY)
```

## What it does

```text
You: What was Tesla's net income in 2023?
Bot: Tesla FY2023 (year ended Dec 31, 2023) reported net income of $14,997 million ($15.0 billion).

You: compare apple and microsoft revenue in 2024
Bot: Total revenue, fiscal 2024:
  Apple FY2024 (year ended Sep 28, 2024): $391,035 million ($391.0 billion)
  Microsoft FY2024 (year ended Jun 30, 2024): $245,122 million ($245.1 billion)
Highest: Apple.

You: Tesla revenue growth in 2024
Bot: Total revenue change, FY2023 to FY2024:
  Tesla: $96,773 million ($96.8 billion) -> $97,690 million ($97.7 billion) (+0.9%)

You: which company had the lowest net income in 2024
Bot: Tesla had the lowest net income in fiscal 2024: $7,091 million ($7.1 billion).

You: what is google's revenue in 2023
Bot: I don't have data for 'google'. I cover Apple, Microsoft, Tesla for fiscal years 2022-2024.
```

Supports lookups, multi-year trends, company comparisons, "highest/lowest" rankings and year-over-year growth for
revenue, net income, total assets, total liabilities and operating cash flow, plus derived net margin,
liabilities-to-assets and equity. It tolerates year shorthand ("FY24"), tickers and small typos ("microsft"), and
reports each company's fiscal year-end because Apple's year ends in September, Microsoft's in June and Tesla's in December.

## What I changed, and why it mattered

The original notebook was three successive hard-coded chatbots (a lookup dictionary, then if/elif keyword rules). It never read the CSV it loaded, and
checking it against the filings showed the canned answers and the data file were both wrong:

| Original behaviour | Problem | Now |
|---|---|---|
| "Tesla's total liabilities in 2023 were $77,000 million" | Filed value is $43,009 million | Computed from data |
| "Microsoft's total assets in 2024 were $450,000 million" | Filed value is $512,163 million | Computed from data |
| "Tesla's net income in 2023 was $14,974 million" | Filed value is $14,997 million | Computed from data |
| Input file labelled each company's rows 2022, 2023, **2023** | Rows were really FY2023, FY2024, FY2022 (every company) | Relabelled and verified |
| Tesla 2024 net income 7,153 | Filed value is 7,091 | Corrected |
| "Microsoft revenue 2023" and "2024" gave the same canned reply | No year handling | Real year parsing |

Full provenance (SEC XBRL concepts and the list of corrections) is in [`data/SOURCES.md`](data/SOURCES.md); the original
file and notebook are kept in [`archive/`](archive/).

## How it is built

```
src/fin_chatbot/
  data.py     verified dataset + metric/company vocab, derived metrics
  parser.py   rule-based NLU: text -> structured Query (intent, metric, companies, years)
  engine.py   Query -> Answer, computed from the data, with refusals for unsupported asks
  llm.py      optional: an LLM produces the Query via tool use; the engine still computes the answer
tests/        data integrity, every stored value round-trips through the bot, parsing, refusals, LLM fallbacks
```

**The optional GenAI mode is designed so the model cannot hallucinate a number.** The LLM only translates the question
into a structured query (validated against the allowed companies, metrics and intents); the figures still come from
the dataset. If the API call fails or returns something invalid, the bot falls back to the rule-based parser. The LLM
path is unit-tested with a fake client, and has not been run against the live API in CI.

## Limitations

- Three companies and three fiscal years, by design: this is a verified data set, not a market-data feed.
- The rule-based parser handles common phrasings, not arbitrary language (use `--llm` for looser questions).
- Figures are as originally reported in 10-Ks; later restatements are not tracked.
- "2024" is not the same calendar window across companies (see fiscal year-ends above).
