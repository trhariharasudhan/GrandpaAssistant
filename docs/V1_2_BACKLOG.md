# Grandpa Assistant v1.2 Backlog (Priority Plan)

Date: 02 April 2026  
Status: Issue-ready backlog

## Priority Scale

- `P0` = must-have for v1.2
- `P1` = strong add-on for v1.2
- `P2` = nice-to-have, move if schedule tight

## Top 10 Features (Issue-Ready)

1. **[P0] Automation Rule Runner Engine**
   - Goal: move from rule storage to real execution (`when` trigger -> `then` action).
   - Acceptance:
     - time-based rules execute in background.
     - rule execution logs (success/fail) are visible in UI/API.
     - disabled rules never execute.

2. **[P0] Habit Reminder + Daily Nudge Integration**
   - Goal: connect habits with reminder system and proactive nudges.
   - Acceptance:
     - per-habit reminder time support.
     - missed check-ins appear in dashboard notifications.
     - habit streak summary appears in planner focus.

3. **[P0] Goals Progress Analytics**
   - Goal: add measurable goal progress view.
   - Acceptance:
     - weekly completion trend for milestones.
     - goal risk indicator (on-track/at-risk).
     - goal summary export in markdown.

4. **[P1] Meeting Capture Upgrade (Transcript + Action Routing)**
   - Goal: improve meeting notes into actionable outputs.
   - Acceptance:
     - richer action extraction with owner/deadline parsing.
     - "convert to tasks/reminders" command.
     - meeting history filter by date/title.

5. **[P1] RAG Library Smart Indexing**
   - Goal: strengthen document retrieval quality.
   - Acceptance:
     - folder/tag-aware ranking.
     - chunk quality score and citation confidence.
     - quick re-index command with progress state.

6. **[P1] Mobile Companion Delivery Channel**
   - Goal: move from queued updates to actual delivery integration.
   - Acceptance:
     - transport adapter interface (push/whatsapp/email).
     - delivery status states: queued/sent/failed/retry.
     - retry strategy with cooldown and max attempts.

7. **[P1] Voice Calibration Wizard**
   - Goal: make voice setup easier for new users.
   - Acceptance:
     - guided calibration flow for wake threshold/timeouts.
     - environment presets auto recommendation.
     - calibration summary saved in settings.

8. **[P1] Multilingual Reply Pipeline**
   - Goal: improve Tamil/English switching accuracy and consistency.
   - Acceptance:
     - auto mode language confidence score.
     - response style preferences per language.
     - fallback rules when mixed-language input arrives.

9. **[P2] Dashboard Custom Widgets**
   - Goal: personalize dashboard blocks.
   - Acceptance:
     - pin/unpin cards.
     - reorder cards.
     - save user-specific dashboard layout.

10. **[P2] Backup/Restore for Local Data**
   - Goal: protect user data and simplify migration.
   - Acceptance:
     - one-command backup zip for `backend/data/`.
     - restore command with safety confirmation.
     - optional scheduled backup rule.

## Suggested Build Order

1. P0 block: #1 -> #2 -> #3  
2. P1 block: #4 -> #5 -> #6 -> #7 -> #8  
3. P2 block: #9 -> #10

## Suggested Milestone Split

- Milestone A (Core reliability): #1, #2, #3
- Milestone B (Intelligence + workflow): #4, #5, #6
- Milestone C (UX + resilience): #7, #8, #9, #10
