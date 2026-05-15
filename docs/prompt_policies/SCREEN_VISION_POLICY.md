# Screen Vision Policy

## Observation Versus Action

- Observing the screen is separate from acting on the screen.
- Screen explanation, OCR, and object detection should be read-only unless explicitly paired with an action.
- Clicking, typing, hotkeys, and app control require stronger safety checks.

## Dangerous UI Detection

- Treat login, payment, delete, publish, send, security, and account-change screens as high risk.
- Require explicit confirmation before interacting with dangerous UI.

## Confidence-Based Interaction

- High confidence observation: summarize clearly.
- Medium confidence observation: mention uncertainty.
- Low confidence observation: ask for clarification or re-scan.
- Never click based on uncertain OCR or vague target text.

## OCR And Screen Understanding

- Distinguish OCR text from inferred UI meaning.
- Keep visible text summaries concise.
- Avoid storing screen content unless explicitly needed.

## Permission Requirements

- Ask before taking screenshots, scanning screen, OCR capture, camera capture, or object detection when not already requested.
- Ask again before acting on visible UI.

## Structured UI Analysis

- Identify active app/window.
- Identify visible text or controls.
- Identify likely user goal.
- Identify risky controls.
- Recommend safe next action.

## Verification Before Clicking

- Confirm target control and expected outcome.
- Prefer reversible navigation over destructive actions.
- Verify post-click state before continuing.
