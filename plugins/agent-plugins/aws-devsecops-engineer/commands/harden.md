---
description: Audit and harden IaC templates (Terraform, CDK, CloudFormation, Dockerfiles), network perimeters (VPC, WAFv2), S3, KMS, and Secrets Manager
argument-hint: "[path/to/iac or service domain]"
---

Invoke the **hardening-iac-and-perimeter** skill (and **threat-modeling-with-aws-security-agent** when evaluating architecture specs) to audit local Infrastructure-as-Code templates and live AWS perimeters against the AWS Well-Architected Security Pillar, enforce S3 Block Public Access, KMS key rotation, Secrets Manager secret injection, WAFv2 protection, and least-privilege Security Groups, and patch local IaC files directly.

Target path or scope: $ARGUMENTS
