

---

## GROK (Grok Build CLI (94172f2aa4e5)) - 2026-07-26 20:41 UTC
*Headless via grok_collab.py; genuine output appended verbatim; sandboxed cwd (inlined files only).*

I'll treat the inlined product claims as data to pressure-test, then pull learning-science evidence on dual coding, multimedia principles, and A1 multimodal practice.# Independent research round — MULTIMODAL AND DUAL CODING  
**Author:** Grok (second author / contrarian)  
**Date pinned:** 2026-07-26  
**Subject:** product claims in `docs/system-overview.md` (as of 2026-07-26) on teach images + default TTS, pressure-tested against dual coding / CTML / L2 vocabulary evidence  
**Scope of inlined data treated as DATA only:** system overview §3–4, §9–10, §19 (image latency)

---

## 1. Own picture (with dated pins)

### Core model I use (not the product’s)

| Pin | Claim | Anchors |
|-----|--------|---------|
| **P1** | Form–meaning mapping is the bottleneck at A1; dual codes (verbal + nonverbal) help **when** the nonverbal cue is diagnostic of meaning and does not steal attention from form. | Paivio dual coding (classic); Mayer CTML multimedia principle |
| **P2** | **Coherence** (strip irrelevant visuals) and **contiguity** (word next to picture) dominate “pretty pictures.” Wallpaper is load, not enrichment. | Mayer coherence / spatial contiguity (synthesized across CTML reviews, e.g. Mayer 2002–2009 lineage) |
| **P3** | **Redundancy** (same content in narration + on-screen text + graphic) hurts *L1 content* lessons; it is **not** a clean veto on L2 **reading-while-listening**, where text+audio often scaffolds orthography↔phonology for beginners. | Mayer redundancy median *d* ≈ 0.84 against animation+narration+text in science demos; L2 bimodal / RWL literature often favors simultaneous text+audio for weaker readers/listeners |
| **P4** | Pictures beat pure verbal glosses most for **concrete, imageable nouns**; they are weak or harmful for abstract lexemes, morphology, and function words. Extra modes can **divert attention from form** (Boers-type finding) and inflate immediate “I get it” without durable form encoding. | Dual-coding / gloss literature; Li, Yu, Zhang & Liu (2022) multimodal vs monomodal |
| **P5** | For true beginners, **L1 glosses** often match or beat L2 glosses on delayed retention; **picture + L1** is a strong combo. Pure “L2 word ↔ image, never L1” is an ideological shortcut, not an empirical absolute. | Yoshii (2006); Choi et al. (2016); Yanagisawa–Webb–Uchihara gloss meta (L1 glosses competitive); RHM (Kroll & Stewart 1994) L2→L1→concept early route |
| **P6** | AI images can work for nouns (Ye et al., PLOS ONE, 2026) but **instance consistency** (same boat = same boat) is load-bearing for dual coding; style drift and latency are first-class product risks. | Ye 2026; product’s own §19.5 image-latency note |

### Arithmetic pins (effect sizes cited as reported, not re-estimated)

- Mayer redundancy demos (animation+narration vs animation+narration+text): reported effect sizes 0.84, 1.65, 0.69 → **median 0.84** (learners worse when text is stacked on narration+graphics in those L1 science tasks).  
- Li et al. (2022) immediate means: EG multimodal **7.14/8** vs CG monomodal **7.25/8** → rates **7.14/8 = 89.25%** vs **7.25/8 = 90.625%** (Δ = −1.375 pp, ns). Delayed: EG **3.57/8 = 44.625%** vs CG **4.09/8 = 51.125%** (Δ = −6.5 pp, ns but direction favors monomodal). Immediate→delayed drop EG: **7.14 − 3.57 = 3.57** points ≈ **50% relative loss** ((7.14−3.57)/7.14 ≈ 0.50).  
- Yanagisawa et al. gloss meta (reported in secondary sources): L1 and L1+L2 glosses ≈ comparable gains; L2-only glosses smallest — relevant when product banishes “English walls” entirely.

**Working picture for ml_teacher:** Sparing, concept-bound images + Spanish form + spoken Spanish is a **high-coherence A1 design**. Default TTS+text is **supported for L2**. Absolute anti-L1-image-only binding is **over-claimed** for true zeros and non-concrete targets. Triple-stack (image + full chat text + continuous TTS) without rate control is the main unaddressed load risk.

---

## 2. Verify / refute table (load-bearing claims in the inlined overview)

| # | Claim (from inlined product text) | Verdict | Evidence / reasoning |
|---|-----------------------------------|---------|----------------------|
| C1 | Association = “Form ↔ meaning (image, context) before English gloss walls” | **PARTIAL — AMEND** | Dual coding supports imageable meaning codes; “before English walls” as *habit* is good. As *first exposure rule for all items*, weak: L1 glosses often win delayed retention for low proficiency; RHM predicts early L1 mediation. |
| C2 | Teach images only for association / comprehension repair / high-visual concrete intro — not every turn | **SUPPORT (strong)** | Coherence principle: extraneous images hurt. Product’s selective policy is closer to CTML than wallpaper CALL. |
| C3 | Images bind **referent ↔ Spanish**, not wallpaper | **SUPPORT intent; PARTIAL execution risk** | Correct pedagogical target (direct concept link). Risk: AI image without Spanish form *on/near* image fails contiguity; ambiguous AI scenes create wrong referents. |
| C4 | Mode `association` for “form ↔ image meaning (English wall or new concrete noun)” | **SUPPORT with scope limit** | English-wall → image repair is coherent. New **concrete** noun: yes. Do not stretch to ser/estar person morphology or abstract affect labels. |
| C5 | Comprehension repair may use images; same idea, re-model, no topic jump | **SUPPORT** | Repair needs a clearer meaning cue; image is one legitimate re-code if the failed item is concrete/visual. |
| C6 | Gemini image gen on cache miss; disk cache thereafter | **ENGINEERING OK; LEARNING CAVEAT** | Cache helps latency (product §19.5). Learning needs **stable identity** of referent across sessions, not only disk path — model prompt drift can still re-render different boats. |
| C7 | First image miss “can take seconds” | **ACCEPT as ops fact** | Latency is extraneous load (frustration) + temporal contiguity risk (image arrives after the Spanish form is gone from WM). |
| C8 | TTS default: Gemini neural TTS; browser fallback | **SUPPORT for A1** | Spoken model of Spanish is core input; dual channel (ear + eye on text) aligns with L2 bimodal / RWL benefits for weak decoders, despite L1 Mayer redundancy. |
| C9 | Speak replies alongside chat text (implicit dual presentation) | **SUPPORT with nuance** | L2 reading-while-listening often helps mapping; not the same as stacking redundant captions on a science animation. Still risk if image + long text + full-rate TTS fire together. |
| C10 | Adult boat/café product, not kids flashcard app | **ORTHOGONAL to modality science** | Dual coding is not “childish”; adult A1 still benefits from sparse concrete visuals. Persona does not license anti-image dogma nor flashcard spam. |
| C11 | Spanish-forward; English is lifeline not dual-subtitle wallpaper | **SUPPORT as UI policy; NOT as total ban on L1 micro-gloss** | Wallpaper dual subtitles = coherence failure. Lifeline L1 on failed mapping = supported by gloss research. |
| C12 | Progress / sheet / modes pipeline owns pedagogy; images are side assets | **SUPPORT** | Images should be mode-triggered (as designed), not decorative chrome. |

### Explicit adjudication of requested product choices

| Choice | Ruling | One-line why |
|--------|--------|--------------|
| **(a)** Images only for association, comprehension repair, high-visual concrete intros — never wallpaper | **COUNTERSIGN** | Coherence principle + selective dual coding. Enforce with hard mode allowlist, not vibe. |
| **(b)** Images bind referent to Spanish directly, avoiding English gloss walls | **AMEND** | Keep Spanish-primary dual code as default for concrete nouns; **do not** forbid minimal L1 when image is non-diagnostic or second repair fails. “Avoid walls” ≠ “never L1.” |
| **(c)** TTS on by default for tutor replies alongside text | **COUNTERSIGN** | A1 needs phonology; bimodal text+speech is generally productive for beginners. Add rate/prosody controls (below). |

---

## 3. What the (inlined) author / product picture MISSED

1. **Redundancy is modality- and task-dependent.** Overview treats “Spanish + image” and “TTS + text” as always good dual coding. CTML redundancy hurts when three redundant *verbal* streams pile up; L2 form learning can still suffer if the picture steals attention from the orthographic/phonological form (Boers-style form-neglect). No product rule for **when to suppress TTS or image during form_focus**.

2. **No speech-rate / prosody policy.** A1 listening is highly rate-sensitive. Default neural TTS at near-native pace can nullify “comprehensible input” even with perfect text. Overview §10 lists voices/models, not **WPM, pause, or slow-first settings**.

3. **No contiguity contract.** “Bind referent to Spanish” requires the Spanish form to be **spatially and temporally** next to the image (label on image, or form highlighted when image lands). Pre-AI image gen that arrives late (post-AI second pass, §7 steps 3 vs 11) risks **temporal contiguity failure**.

4. **Concrete vs abstract not operationalized.** “High-visual concrete intro” is stated; no lexicon flag (imageable? mass noun? proper name? grammar form?) so association mode can still fire on low-imageability items.

5. **L1 gloss evidence is stronger than the rhetoric admits.** Product persona correctly hates English walls; research still favors L1 (or L1+picture) for many beginner form–meaning links on delayed tests. The missed design is **ordered scaffold**: image+Spanish → if fail, short L1 lifeline → not more images or longer Spanish monologue.

6. **AI image quality = referent reliability, not aesthetics.** Ye (2026) supports AI images for *nouns* under controlled multimodal instruction; product has no check for: wrong object, cluttered scene, text-in-image garbage, cultural oddity, or **cross-turn style inconsistency** that breaks the nonverbal code.

7. **Triple-channel load when repair stacks everything.** Comprehension repair that re-models Spanish + shows new image + autoplays TTS + keeps prior chat is a **three-channel burst**. Li et al. (2022) already show “more multimodal” ≠ better delayed retention.

8. **No learning metric on images.** Sheet tracks lexicon confidence; overview does not say image-shown is logged as evidence type or that failed image association escalates scaffold. Images are presentation, not measured dual-code success.

9. **Kids-flashcard allergy can overshoot.** Adult conversational frame is right; it must not become under-use of the only nonverbal code that works for concrete A1 nouns (barco, café, calor-as-scene, etc.).

10. **STT path asymmetry.** TTS is default-on; learner speech recognition quality/rate is a separate bottleneck for closed-loop multimodal practice (say → hear recast). Multimodal section of product is tutor→learner heavy; production loop thinner.

---

## 4. Standing questions (answered from this dimension)

| Question (implied by product) | Answer |
|-------------------------------|--------|
| Should every tutor turn have an image? | **No.** Coherence: only when the open goal is form–meaning for an imageable item or repair needs a referent. |
| Is image better than English gloss at first exposure? | **Depends.** Concrete noun: image (+ Spanish form + audio) strong. Ambiguous/abstract/functional: L1 gloss often better or necessary as backup. Best frequent pattern in research: **picture ± L1**, not picture-as-moral-replacement for L1. |
| Does AI image gen undermine learning? | **Not inherently** (Ye 2026 positive for nouns), but inconsistency, clutter, and latency can. Treat quality gates as pedagogy, not polish. |
| TTS + text + image at once? | **Prefer two primary channels at a time for hard items:** (text+TTS) *or* (image+Spanish label+short TTS), not all three at full intensity without learner control. |
| Prosody / rate? | **Control them.** Beginners need slower rate, clearer boundaries, optional pause-after-model before `<try>`. |

---

## 5. Ranking / critique of product multimodal design

**Strengths (do not regress):**  
- Selective image policy (a) is the right default vs wallpaper CALL.  
- Mode-tied generation (association / repair / concrete) is architecturally aligned with dual coding.  
- Default TTS (c) is correct for Spanish-forward A1.  
- Caching after first miss is the right engineering response to gen latency.

**Weaknesses (contrarian pressure):**  
- (b) is stated as a purity rule (“avoid English gloss walls”) where evidence wants a **fallback ladder**.  
- No rate/prosody layer under “comprehensible input.”  
- Contiguity and consistency of AI images are underspecified relative to how much pedagogical weight images carry.  
- Risk of **form neglect**: pretty referent without forced attention to *el barco / hace calor* as form.

**Overall grade for this dimension:** **B+ policy intent, B− operationalization** — selective dual coding is right; anti-L1 absolutism and missing audio-rate / contiguity / consistency controls are the gaps.

---

## 6. Concrete adjudicable improvement proposals  
**(ranked by impact ÷ cost; each must be falsifiable)**

### R1 — **TTS rate + pause policy for A1** (Impact: High · Cost: Low–Med)

**Change:** Default tutor TTS at reduced rate (product constant, e.g. 0.85–0.90 of provider default, or explicit WPM target if API allows); insert **≥400 ms** gap after `<model>` audio before `<try>` audio when both present; expose “Slower / Normal” toggle.

**Adjudication metric (30-session pilot):**  
- Comprehension-repair rate (mode fires / 100 turns) drops by **≥20% relative** vs baseline, *or*  
- Learner self-report “too fast” ≤ 15% of sessions.  

**Why:** Comprehensible input fails at native-ish rate for zeros; rate is cheaper than more English or more images.  
**Cite family:** L2 listening rate sensitivity (general SLA); CTML segmenting / modality as design cousins — product currently has voice name, not rate policy.

---

### R2 — **Ordered meaning scaffold: image → minimal L1 lifeline** (Impact: High · Cost: Low)

**Change:** Amend (b): On `association` or `comprehension_repair`, prefer image + Spanish form. If **same item** fails again within **3 turns**, allow **one short L1 gloss** (≤6 English words) in `<explain depth="brief">` or a dedicated lifeline part — then re-elicit in Spanish. Never dual-subtitle the whole turn.

**Adjudication:**  
- Second-repair success (correct form or clear comprehension token within 2 turns after lifeline) **≥ first-repair success + 15 absolute pp**.  
- English ratio gate still passes (no `gate:english_wall`).

**Why:** Choi (2016) delayed L1 advantage; Yoshii (2006) L1/L2 gloss multimedia; product already calls English a lifeline — operationalize it after image failure, not as wallpaper.  
**Cite:** Choi et al. 2016; Yoshii 2006; Yanagisawa et al. gloss meta (L1 competitive).

---

### R3 — **Spatial + temporal contiguity for teach images** (Impact: Med–High · Cost: Low)

**Change:**  
1) Always render **Spanish form (and article if taught)** as caption **on or immediately under** the image.  
2) Prefer **pre-AI** image path when mode is association; if only post-AI path fires, **hold TTS of the model phrase until image is visible** (or replay model once image lands).

**Adjudication:**  
- % of teach-image turns with form-on-image caption = **100%** (lint).  
- Latency from model text visible → image visible: p50 **≤ 1.5 s** on cache hit; on miss, replay policy executes **≥ 95%** of times.

**Why:** Mayer spatial/temporal contiguity; late wallpaper images violate dual coding construction.  
**Cite:** Mayer CTML contiguity principles.

---

### R4 — **Referent-stable AI images (identity hash, not only disk cache)** (Impact: Med · Cost: Med)

**Change:** Cache key = normalized lemma + visual template id (e.g. `barco|side_view_simple_boat|style_v1`). Freeze style seed/prompt block so reopening the sheet always shows the **same** boat. Reject/regenerate if vision QA (cheap model) reports multi-object clutter or missing primary object.

**Adjudication:**  
- Same lemma re-shown within 7 days: **pixel or embedding similarity ≥ threshold** (e.g. cosine ≥ 0.90 on embedding) on **≥ 95%** of pairs.  
- Manual audit of 50 images: **≥ 90%** single clear referent.

**Why:** Dual coding needs a stable nonverbal code; style drift = new code every time. Ye (2026) supports AI images for nouns when materials are designed; consistency is the design.  
**Cite:** Ye et al. 2026 (AI images + multimodal nouns); Paivio dual coding (stable imaginal code).

---

### R5 — **Channel budget: no full triple stack on hard breaks** (Impact: Med · Cost: Low)

**Change:** In `form_focus` and hard `association`, default **image XOR long written explain**; keep short Spanish model + TTS. Soften: if image shown, suppress multi-sentence English/Spanish essay in the same bubble.

**Adjudication:**  
- Telemetry: fraction of hard-break turns with (image ∧ TTS ∧ >40 words on-screen) drops to **≤ 10%**.  
- Form production success on next turn **≥ baseline** (non-inferiority δ = 5 pp).

**Why:** Li et al. (2022) delayed multimodal ≤ monomodal; Yeh & Wang-type findings that text+picture can beat text+picture+audio; Boers attention-to-form risk.  
**Cite:** Li et al. 2022; cognitive load / redundancy literature; Boers et al. 2017 (visuals can reduce attention to word form).

---

## 7. Bottom line (append-ready)

- **(a) Selective images — COUNTERSIGN.** Matches coherence; keep strict.  
- **(b) Spanish↔referent only, no English — AMEND.** Dual coding yes; L1 micro-lifeline after failed image/repair is evidence-aligned; anti-wall ≠ anti-L1.  
- **(c) Default TTS + text — COUNTERSIGN.** L2 bimodal support is solid; add rate/pause and avoid obligatory triple-channel overload.

Highest leverage next: **R1 (rate)** + **R2 (L1 after image fail)** + **R3 (contiguity)** before more image generation spend.

---

*End of Grok independent round — MULTIMODAL AND DUAL CODING — 2026-07-26*
