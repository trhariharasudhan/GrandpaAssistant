# Contacts And Calling

GrandpaAssistant supports a local contact manager for reliable `call <name>` behavior.

Contacts are stored only on this machine under:

```text
backend/data/contacts/contacts.json
```

That path is ignored by git.

## Add Contacts

Assistant command:

```text
add contact Riyaa 9876543210
```

API, localhost/admin only:

```text
POST /api/contacts
```

Body:

```json
{"name": "Riyaa", "phone": "9876543210", "labels": ["family"]}
```

## Find And Show Contacts

Assistant commands:

```text
show contacts
find contact Riyaa
```

API routes:

```text
GET /api/contacts
GET /api/contacts/search?q=Riyaa
```

Phone numbers are redacted in summaries except the last four digits.

## Delete Contacts

Assistant command:

```text
delete contact Riyaa
```

Deleting a contact requires confirmation.

API route, localhost/admin only:

```text
DELETE /api/contacts/{name}
```

## Direct Call Behavior

Clear non-emergency call intents start the local call flow directly:

```text
call mom
call 9876543210
riyaa ku call pannu
cll pannu riyaa
```

Resolution order:

1. Local contact manager
2. Existing memory/contact provider
3. Clear phone number

If one exact local contact match is found, GrandpaAssistant opens the local Windows `tel:` handler without asking an extra confirmation. If multiple contacts match, it asks for clarification. If no contact matches, it asks you to add the contact or provide a phone number.

## Phone Link Setup

Calling uses the Windows `tel:` handler. Set up Windows Phone Link or choose a default app for `tel:` links if calls do not open.

Assistant command:

```text
phone link status
```

API route:

```text
GET /api/phone-link/status
```

The readiness check does not place a call.

## Privacy Notes

- Contacts stay local.
- Contact APIs are localhost/admin only.
- Remote unauthenticated requests receive `403`.
- Summaries redact phone numbers.
- The system does not sync these local contacts outside the machine.

## Emergency Call Block

Emergency numbers such as `112` and `911` are not called automatically. Dial emergency services manually.

## Confirmation Rules

Direct clear calls do not ask for an extra confirmation. Risky actions still require confirmation, including:

- delete/move files
- shutdown/restart/sign out
- install/uninstall
- send message/email/payment
- run non-read-only commands
- modify system settings
- delete contacts
