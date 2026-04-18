# suggest-topics

<!-- Filled in Phase P4. -->

1. Invoke: `srp suggest-topics --mode skill --output json`.
2. If CLI returns a packet with `kind=suggestions`, enhance per schema and pipe back:
   `echo '<json>' | srp stage-suggestions --from-stdin`.
