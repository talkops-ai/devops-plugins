---
description: Set up Amazon SES for sending email
argument-hint: "<domain> [region]"
---

Use the `amazon-ses` skill to make `$ARGUMENTS` ready to send email.

1. Verify the domain identity with Easy DKIM, set a custom MAIL FROM domain, and publish SPF/DMARC records.
2. Check sandbox status and prepare the production-access request; set up configuration sets, bounce/complaint handling, and suppression lists.
3. Provide the DNS records to add and a test send plan.

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
