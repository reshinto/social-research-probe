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

# Used by the corroboration host: given a claim and a list of source excerpts,
# ask the LLM to evaluate whether the sources support, refute, or are
# inconclusive about the claim.
CORROBORATION_PROMPT = """\
You are a fact-checker. Evaluate whether the following claim is supported by the provided sources.

Claim: {claim}
Sources:
{sources}

Respond in JSON with keys: verdict (supported|refuted|inconclusive), confidence (0.0-1.0), reasoning (str).
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
