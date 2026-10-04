---
description: Build a golden AMI or container image pipeline with EC2 Image Builder
argument-hint: "<base OS and hardening requirements>"
---

Design an EC2 Image Builder pipeline for `$ARGUMENTS` using the `amazon-ec2-image-builder` skill.

1. Choose the base image, components (hardening, agents, application), tests, and distribution (accounts/regions, launch template updates).
2. Produce the recipe, infrastructure configuration, distribution configuration, and schedule as IaC.
3. Call out patching cadence, image lifecycle/cleanup, and the IAM roles required.

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
