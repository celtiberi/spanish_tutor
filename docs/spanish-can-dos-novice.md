# Spanish can-dos (Novice) — product curriculum map

**Status:** v0.1 — operational list for character sheet + conversational tutor  
**Date:** 2026-07-23  
**Basis:** NCSSFL-ACTFL Can-Do / proficiency orientation (Novice Low–Mid band),  
mapped to our A1 pack inventory. We **do not invent** method; we implement can-dos.  
**Methods:** CLT + TBLT + comprehensible input + focus on form (see  
`docs/conversational-spanish-and-learner-model.md` §2).

---

## 1. How to read this

| Field | Meaning |
|-------|---------|
| **id** | Stable key on the character sheet (`skills` / can-dos) |
| **mode** | ACTFL communication mode: interpersonal / interpretive / presentational |
| **band** | Target band for this product slice: NL = Novice Low, NM = Novice Mid |
| **I can…** | Learner-facing performance statement |
| **Evidence** | What counts as “they did it” in chat |
| **Form hooks** | Grammar/lexicon that often support this can-do (not the goal itself) |
| **Stretch after known** | Where a good tutor goes next |

**Progression rule:** prefer the **lowest-confidence interpersonal can-do** that fits the chat, not “finish all greeting variants.”

---

## 2. Interpersonal (priority for live chat)

### IP-01 — Greet and respond informally  
**Band:** NL–NM · **I can** greet a peer and respond to a simple greeting.  
**Evidence:** *Hola*, *buenos días/tardes/noches*, reciprocal *¿cómo estás?* / *bien*.  
**Form hooks:** fixed greetings; present *estar* in formula.  
**Stretch after known:** IP-03 introduce self; IP-04 small talk beyond “fine.”

### IP-02 — Greet formally (when the situation needs it)  
**Band:** NM · **I can** greet and ask how someone is in a formal situation.  
**Evidence:** *usted* forms with appropriate addressee (*señor/a*, teacher, stranger).  
**Form hooks:** *¿Cómo está usted?*, *se llama*.  
**Stretch after known:** stop grinding; use only when the *role* is formal.

### IP-03 — Introduce myself and ask someone’s name  
**Band:** NL–NM · **I can** say my name and ask another person’s name.  
**Evidence:** *Me llamo…*, *¿Cómo te llamas? / ¿Cómo se llama?*  
**Form hooks:** fixed intro formulas (not full reflexive grammar).  
**Stretch after known:** IP-05 leave-taking; simple *mucho gusto*.

### IP-04 — Say how I am / ask how you are  
**Band:** NL–NM · **I can** answer and ask about wellbeing with practiced phrases.  
**Evidence:** *Estoy bien / más o menos / cansado/a*; reciprocal question.  
**Form hooks:** *estar* person agreement (conceptual if *esta bien* for self).  
**Stretch after known:** reason/state (*porque…*, *un poco…*) lightly; IP-06 preferences.

### IP-05 — Take leave  
**Band:** NL · **I can** end a short exchange politely.  
**Evidence:** *Adiós*, *hasta luego*, *hasta mañana*, *nos vemos*.  
**Form hooks:** fixed closings.  
**Stretch after known:** full micro-exchange open→close (task).

### IP-06 — Express simple preferences  
**Band:** NM · **I can** say what I like / prefer on familiar topics.  
**Evidence:** *Me gusta…*, *prefiero…* (as formulas if full *gustar* grammar out of scope).  
**Form hooks:** pack-limited preference frames.  
**Stretch after known:** food, free time, plans (in-scope vocab).

### IP-07 — Ask and answer simple personal questions  
**Band:** NM · **I can** handle a few personal Qs (where from, work/study—within pack).  
**Evidence:** short Q↔A using practiced patterns.  
**Form hooks:** *ser* (*soy de…*), *tener*, question words when in pack.  
**Stretch after known:** longer interpersonal strings (Novice High direction).

### IP-08 — Complete a short transactional / social task  
**Band:** NM · **I can** get through a 4–8 turn role task (meet stranger, order idea, etc.).  
**Evidence:** maintains register, opens/closes, exchanges required info.  
**Form hooks:** whatever the task needs from the palette.  
**Stretch after known:** freer chat; new domains (numbers, food) if never touched.

---

## 3. Interpretive (listening / reading in chat)

### IT-01 — Understand a short practiced dialogue  
**Band:** NL–NM · **I can** get the gist of a short, familiar-topic dialogue.  
**Evidence:** answers a meaning question about who/when/relationship.  
**Teaching move:** input first + one comprehension check (CLT/CI).

### IT-02 — Recognize high-frequency words and phrases  
**Band:** NL · **I can** pick out known words in speech/text.  
**Evidence:** identifies a word/line from input.  
**Teaching move:** seed dialogues; point to forms in context.

---

## 4. Presentational (light, in chat)

### PR-01 — Produce short practiced self-info  
**Band:** NL–NM · **I can** say a few practiced sentences about myself.  
**Evidence:** name, greeting, origin, one preference — not a monologue test.  
**Teaching move:** after interpersonal success, invite a 2–3 sentence “about me.”

---

## 5. Supporting form inventory (not can-dos)

Track on sheet under `grammar` — support can-dos; never become the only activity.

| id | Supports | Conceptual error example |
|----|----------|---------------------------|
| `present_estar_person` | IP-04 | *esta bien* for “I am fine” |
| `register_tu_usted` | IP-02, IP-08 | *¿cómo estás?* to a boss |
| `present_ser` | IP-07, PR-01 | *estar* for identity |
| `gender_articles` | later can-dos | *buenos tardes* |
| `present_regular_ar_er_ir` | IP-06–08 | wrong person ending |
| `numbers_0_20` | age, quantity tasks | — |
| `tener_age_possession` | IP-07 | age with *ser* |

**Focus on form:** one recast / one-beat notice inside interpersonal use — not a forms unit.

---

## 6. Mapping from old sheet keys → can-do ids

| Old skill key | Can-do id |
|---------------|-----------|
| `greet_informal` | `IP-01` |
| `greet_formal` | `IP-02` |
| `introduce_self` | `IP-03` |
| `small_talk_how_are_you` | `IP-04` |
| `take_leave` | `IP-05` |
| `simple_preferences` | `IP-06` |
| `ask_name` | `IP-03` (ask side) |
| *(new)* | `IP-07`, `IP-08` |
| `can_follow_short_dialogue` | `IT-01` |

---

## 7. Selection policy for `next_best`

1. If affect = boredom / meta complaint → change task (IP-08 or new domain), never more of the same drill.  
2. Else pick interpersonal can-do with **lowest confidence among those with priority**, preferring:
   - never-touched high-value can-dos after basics emerge  
   - IP-03 / IP-05 / IP-06 once IP-01 is *emerging+*  
3. Do **not** select IP-01/IP-02 if status is *known* unless learner asks.  
4. Pair stretch with a **CLT activity type**: chat, roleplay, preference share, story question — not “produce formal greeting variant #N.”

---

## 8. References (starting points)

- NCSSFL-ACTFL Can-Do Statements (Novice continuum)  
- ACTFL proficiency levels (Novice Low / Mid / High descriptions)  
- CLT / TBLT / focus-on-form literature (summary in conversational direction doc §2)

This file is the **curriculum contract** for the character sheet skills block.
