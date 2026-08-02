# RetrievalLab Design System

RetrievalLab should feel like a calibrated research instrument: dense, legible, and serious without becoming clinical. The interface exists to explain evidence and tradeoffs.

## Principles

1. One dominant question per screen.
2. Scores always appear beside their meaning, not as unexplained decoration.
3. Baseline is neutral gray; the selected advanced strategy is chartreuse.
4. Coral is reserved for warnings, failed cases, and risky egress.
5. Avoid gradients, glass surfaces, floating card grids, and ornamental dashboards.
6. Clickable evidence must look clickable before hover.

## Tokens

| Role | Value |
|---|---|
| Canvas | `#11120f` |
| Raised canvas | `#171814` |
| Divider | `#34362d` |
| Paper | `#f0eee7` |
| Muted text | `#97998d` |
| Evidence signal | `#c9f36a` |
| Warning | `#ff7869` |
| Sans | Avenir Next, Segoe UI, Helvetica |
| Mono | SFMono-Regular, Consolas |

Spacing uses a 4 px base. Corners remain square so evidence panels read as instruments rather than consumer cards. Minimum touch target is 44 px on mobile. Motion must respect `prefers-reduced-motion`.
