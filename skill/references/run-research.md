# run-research

<!-- Fully filled in Phase P4. Skeleton below is for P2 wire-up. -->

1. Pre-flight: `srp config check-secrets --needed-for run-research --platform youtube --output json`.
2. If `missing` is non-empty, instruct the user to run `srp config set-secret <name>` in their
   terminal (hidden-input prompt). Never ask the user to paste a key into chat. Stop.
3. Otherwise: `srp run-research --mode skill --platform youtube '<topics>'`.
4. Parse the emitted `SkillPacket` JSON. Fill `compiled_synthesis` (≤150 words) and
   `opportunity_analysis` (≤150 words) per the packet's `response_schema`.
5. Stitch sections 1–11 and emit to the user.
