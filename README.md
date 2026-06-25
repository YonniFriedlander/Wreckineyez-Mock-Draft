# Wreckineyez Mock Draft

A fantasy football mock draft simulator built for the Wreckineyez league.

**Live site:** https://yonnifriedlander.github.io/Wreckineyez-Mock-Draft/

---

## What it does

- Simulates a full 14-team keeper league draft against CPU opponents
- Loads current player rankings from FantasyPros (ECR and ADP)
- Tracks keepers, traded picks, and a full draft board
- Shows player availability probability at your next pick
- Queue system and per-player scouting notes (saved between sessions)
- End-of-draft projected standings based on a fitted ADP→points model

## League settings

- 14 teams, keeper league
- Standard (0 PPR) scoring
- Roster: QB×1, RB×2, WR×3, TE×1, FLEX×1, BN×5

---

## Updating rankings

Rankings are served as static JSON files. They will be uploaded periodcically by Yonni. Here are notes to remind him how to do it:

1. Run:
   ```
   python3 generate_rankings_json.py
   ```
2. Commit and push both `rankings.json` and `rankings-adp.json` together in one commit

## Files

| File | Purpose |
|------|---------|
| `index.html` | The app |
| `rankings.json` | ECR rankings  |
| `rankings-adp.json` | ADP rankings |
| `generate_rankings_json.py` | Script to refresh both JSON files |
| `fp_proxy.py` | Rankings-fetching engine used by the generator |

## Notes

- All draft progress, keeper settings, and notes are saved to the browser's local storage — private to each user, no server involved
- The site is purely static; there is no backend
- Projected standings use an exponential decay model fitted to 154 player-seasons (2021–2024) using FantasyPros ECR as the input variable
