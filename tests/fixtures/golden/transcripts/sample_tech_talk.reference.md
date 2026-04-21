Anthropic's Claude 3.5 Sonnet uses extended thinking for complex reasoning.
On GSM8K it scores 96.4%, on MMLU 88.7%, and on HumanEval 92% with extended
thinking enabled. The model gets a scratchpad of up to 64,000 tokens to
reason before producing the final answer, similar to OpenAI's o1 but trained
for faithful chain-of-thought. Target audience is ML engineers choosing
reasoning models for production workloads where correctness beats latency.
