"""Prompt templates for LLM calls made by the pipeline and corroboration host.

Why this exists: centralising prompt strings here keeps them version-controlled
and easy to review, tweak, or A/B-test without touching runner or pipeline code.

Who calls it: synthesize (pipeline step that writes summaries) and the
corroboration host. Callers use .format(**kwargs) to fill in the placeholders.
"""

from __future__ import annotations

# Used by the synthesis step: given collected evidence for a topic on a
# platform, ask the LLM to produce a structured summary.
SYNTHESIS_PROMPT = """\
You are a research analyst. Given the following evidence report, write a concise synthesis.

Rules:
- Ground claims in items, source_validation_summary, platform_engagement_summary,
  evidence_summary, stats_highlights, or chart_takeaways. Acknowledge mixed or weak evidence.
- Stats and charts cover coverage.fetched; item-level detail covers only coverage.enriched.
- Return three distinct fields:
  - compiled_synthesis: the bottom-line synthesis of what the evidence says.
  - opportunity_analysis: the practical opportunity or strategic implication.
  - report_summary: one integrated executive summary that weaves together the
    key statistics, chart signals, compiled synthesis, and opportunity analysis.

Topic: {topic}
Platform: {platform}
Evidence:
{evidence}

Respond in JSON matching the schema: {schema}
"""

# Used by the llm_search corroboration provider: ask the active LLM runner to
# fact-check a claim originating from a known source (e.g. a YouTube video URL)
# using OTHER, independent text-based evidence. The supplied ``origin_sources``
# is the URL the claim came from — it must NOT be used as evidence for itself.
# The model must look elsewhere (independent text sources it knows of) and
# cite those references in ``sources``. Audio and video hosts are excluded
# because their content cannot be verified from a URL alone.
LLM_SEARCH_CORROBORATION_PROMPT = """\
You are a fact-checker. The following claim originated from the source(s) listed below. Independently verify the claim using OTHER evidence — do not treat the originating source as evidence for itself.

Claim: {claim_text}
Originating source(s) (DO NOT cite these as evidence):
{origin_sources}

Rules:
- Verify the claim using independent sources you know of (other URLs, papers, datasets, canonical references). Do not rely on, quote, or cite the originating source(s).
- Do NOT cite audio or video hosts (e.g. youtube.com, vimeo.com, tiktok.com, soundcloud.com, podcast feeds) — their content cannot be verified from a URL and is not considered reliable evidence here.
- If you cannot find independent text-based corroborating or refuting evidence, return "inconclusive".

Respond in JSON only. Schema:
{{
  "verdict": "supported" | "refuted" | "inconclusive",
  "confidence": <number in [0.0, 1.0]>,
  "reasoning": "<short plain-English explanation grounded in independent text-based evidence>",
  "sources": [<up to 5 independent text-based source references — URLs, paper titles, or canonical names — that you actually relied on; never include the originating source(s); never include audio or video hosts>]
}}
"""


# Used by the enrichment step when both a transcript-based summary and a
# runner-direct URL summary exist for the same video. Produces one reconciled
# summary and flags any disagreement between the two inputs.
RECONCILE_SUMMARY_PROMPT = """\
You are merging two independent summaries of the same video into a single
accurate summary of approximately {word_limit} words. Prefer claims that
appear in both; flag any material disagreement briefly inside the summary.
Do not reveal that two sources were merged. Do not start with 'This video'.

Title: {title}
Channel: {channel}

Transcript-based summary:
{transcript_summary}

URL-based summary:
{url_summary}
"""

# Used by suggest-topics: given existing topics, ask the LLM to propose new ones.
SUGGEST_TOPICS_PROMPT = """\
You are helping expand a research topic registry.

Existing topics: {existing_topics}

Suggest {count} NEW research topic labels that are meaningfully different from the existing ones.

Rules:
- 1-4 word lowercase hyphenated label (e.g. "ai", "quantitative-finance", "climate-change")
- Must NOT duplicate or closely paraphrase any existing topic
- Include a brief reason for each suggestion

Output JSON only: {{"suggestions": [{{"value": "...", "reason": "..."}}]}}
"""

# Used by suggest-purposes: given existing purposes, ask the LLM to propose new ones.
SUGGEST_PURPOSES_PROMPT = """\
You are helping expand a research purpose registry.

Existing purposes: {existing_purposes}

Suggest {count} NEW research purposes that are meaningfully different from the existing ones.

Rules:
- name: 1-4 word lowercase hyphenated label (e.g. "latest-news", "job-opportunities")
- method: 3-8 word phrase describing how to research this
- Must NOT duplicate or closely paraphrase any existing purpose

Output JSON only: {{"suggestions": [{{"name": "...", "method": "..."}}]}}
"""

# Used by the classification service: given a free-form research query,
# classify it into topic and purpose, preferring to reuse existing labels.
CLASSIFICATION_PROMPT = """\
You are classifying a research query for a social media research tool.

Classify the following query into a topic and a purpose.

QUERY: {query}

EXISTING TOPICS (prefer reuse if meaningfully similar): {existing_topics}
EXISTING PURPOSES (prefer reuse if meaningfully similar): {existing_purposes}

Rules:
- topic: 1-4 word lowercase hyphenated label for the subject area (e.g. "ai", "quantitative-finance", "climate-change").
- purpose_name: 1-4 word lowercase hyphenated label for the research goal (e.g. "latest-news", "job-opportunities", "deep-dive").
- purpose_method: 3-8 word phrase describing how to research this. Used to expand search queries.

Reuse rules:
- If an existing topic or purpose_name is even moderately similar in meaning, reuse it EXACTLY.
- Only create a new label if no existing option is a reasonable fit.
- Prefer broader existing categories over creating new narrow ones.

Output format (JSON only):
{{
  "topic": "...",
  "purpose_name": "...",
  "purpose_method": "..."
}}
"""

# Used by Claude runner agentic search: instruct Claude to use its web_search
# tool to find authoritative sources about a claim.
CLAUDE_SEARCH_PROMPT = """\
Use the web_search tool to find authoritative sources about the following claim. Then reply with a single JSON object {"answer": "...", "citations": [{"url": "...", "title": "..."}]}. Do not include citations for video hosts (youtube.com, vimeo.com, tiktok.com) — they cannot be verified from snippets.

Claim: {query}
"""

# Used by Gemini runner media summarization: instruct Gemini to summarize a
# video at the given URL with specified word limit.
GEMINI_MEDIA_PROMPT = """\
Summarize the video at this URL in approximately {word_limit} words. Cover the main topic, key arguments or findings, target audience, and any specific claims, tools, people, or data points referenced. Be specific and factual. Do not start with 'This video' or 'In this video'.

URL: {url}
"""

# Used by Codex runner agentic search: instruct Codex to use its native
# search tool to find authoritative non-video sources about a claim.
CODEX_SEARCH_PROMPT = """\
Use your native --search tool to find authoritative non-video sources about this claim. Output JSON: {{"answer": "...", "citations": [{{"url": "...", "title": "..."}}]}}.

Claim: {query}
"""

CLAIM_EXTRACTION_PROMPT = """\
You are a structured claim extractor. Given the source text below, extract up to \
{max_claims} discrete claims. Each claim must be a single sentence directly \
supported by the text.

Source title: {source_title}

Text:
{text}

Rules:
- Extract only claims explicitly stated in or directly supported by the provided text.
- Do not invent, infer, or hallucinate facts not present in the text.
- Return JSON only. No markdown, no commentary, no explanation outside the JSON object.
- Each claim_text must be at most {max_chars} characters.
- Use only the following claim_type values:
  - fact_claim: a verifiable factual assertion, often with numbers or citations
  - opinion: a subjective belief or judgment (e.g. "I think", "I believe")
  - prediction: a forward-looking statement about future events (e.g. "will", "expect")
  - recommendation: an imperative or advisory statement (e.g. "should", "must", "need to")
  - experience: a first-person account of past activity (e.g. "I've been", "we tried")
  - question: an interrogative sentence
  - objection: a counterargument or caveat (e.g. "however", "despite")
  - pain_point: a statement about difficulty or struggle
  - market_signal: a statement about market trends, adoption, or industry movement
- Output a single top-level JSON object with a "claims" array.
- Respect the max_claims limit of {max_claims}.

Output schema:
{{
  "claims": [
    {{
      "claim_text": "<exact text of the claim, max {max_chars} chars>",
      "claim_type": "<one of the 9 allowed types above>",
      "confidence": <float 0.0-1.0, how confident you are this is a valid claim>,
      "entities": ["<named entities or numbers mentioned in the claim>"],
      "needs_corroboration": <true if claim makes a verifiable factual/predictive assertion>,
      "uncertainty": "<low|medium|high>"
    }}
  ]
}}
"""
