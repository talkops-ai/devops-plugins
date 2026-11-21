---
source_url: https://aws.amazon.com/startups/build/zero-etl
title: "Build zero-ETL Integrations"
---

## Build zero-ETL Integrations

- **Summary:** Examples illustrating how to build zero-ETL integrations
- **AWS Services Used:** Amazon RDS, Amazon Redshift
- **Deployment Method:** Implementation guide
- **Estimated Time:** 1 hour 50 minutes
- **Cost Calculator:** https://calculator.aws/
- **Get Started:** https://docs.aws.amazon.com/redshift/latest/mgmt/zero-etl-using.html

## Overview

Zero-ETL integration is a fully managed solution that makes transactional and operational data available in Amazon Redshift from multiple operational and transactional sources. With this solution, you can configure an integration from your source to an Amazon Redshift data warehouse. You don't need to maintain an extract, transform, and load (ETL) pipeline. We take care of the ETL for you by automating the creation and management of data replication from the data source to the Amazon Redshift cluster or Redshift Serverless namespace. You can continue to update and query your source data while simultaneously using Amazon Redshift for analytic workloads, such as reporting and dashboards.

This demo architecture shows cdk scripts and sample code to create an Amazon RDS zero-ETL integration with Amazon Redshift Serverless. An Amazon RDS zero-ETL integration with Amazon Redshift enables near real-time analytics and machine learning (ML) using Amazon Redshift on petabytes of transactional data from RDS.
