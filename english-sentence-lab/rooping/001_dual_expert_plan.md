# Rooping 001 — dual-expert recovery

Goal: improve long/chaotic sentence Role accuracy without catastrophic forgetting or tuning directly on Chaos Long50.

## Experts
- Long-context expert: v1.6.1 GRU3 + self-attention checkpoint. Historically strongest on long synthetic stress data.
- Gold-domain expert: v1.7.5 GRU3 + self-attention checkpoint trained with synthetic Gold + EWT + MASC + UD replay.

## Rule
Do not fine-tune either expert in this loop. Combine logits or route between experts. Select blend/routing parameters on non-Chaos development data only. Chaos Long50 is diagnostic/test-only.

## Anti-overfit gates
1. No Chaos50 labels may be used to choose blend weight, confidence threshold, or routing threshold.
2. Check a separate complex holdout and a long-sentence development set before testing Chaos50.
3. Reject a change if it improves one stress set but materially damages broad-domain validation.
4. Save each experiment/result as a separate small commit rather than replacing prior checkpoints.
