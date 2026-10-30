# Notification recovery

Before combining Yahoo scores with future games, the live pipeline checks the
score capture, matchup identity and dated tipoffs. A recent cached tipoff remains
valid across Eastern midnight, for at most 72 hours. A successful refresh uses
the NBA schedule first, the NBA CDN second, then ESPN's dated scoreboard. ESPN
times are accepted only when both team codes and the Eastern date match every
cached game on that date. A failed request never advances the cache timestamp.
GitHub Actions preserves the verified schedule between runs.

The daily model does not estimate residual production for games in progress.
When this blocks a fresh forecast, Telegram may show the last valid forecast
for the same week and verified Yahoo teams, at most 24 hours old. Its timestamp
is explicit; displayed counts and probabilities belong to that older snapshot.
Older add/drop recommendations are hidden. The new blocked forecast remains
blocked in the prediction archive; the display fallback is not new evidence.
Delivery receipts identify and hash the older displayed record separately.

No automation schedule is changed by this recovery behavior.
