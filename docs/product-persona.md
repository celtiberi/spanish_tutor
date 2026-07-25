# Product persona (locked 2026-07-25)

**Decision:** Adult conversational A1 — **false-beginner friendly**, true zeros welcome.

| | Choice |
|--|--------|
| Voice | Adult, boat/café life OK — not a kids flashcard app |
| Blank sheet | **Unknown**, not proven beginner |
| Placement | Adaptive wide ceiling (2–3 turns), not a fixed Hola→Estoy ladder |
| Teaching | Association-first Spanish; English lifeline only |
| Structure | AI decides the move; **code** owns sheet evidence + **output gate** |

### Explicit non-goals
- Pure true-zero product with multi-turn forced floor for everyone  
- Scripted social probe queue as the default agenda  
- Chat-buddy with no teach move  

### Architecture implication (Claude + Grok adjudication)
- AI = voice + move selection  
- Code = hard observer (sheet), output gate (Spanish ratio, loops, teach move), optional image  

See `docs/reviews-claude-idea-spar.md`.
