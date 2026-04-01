# Jira Issue Report Crawler

This project crawls a public Apache Jira issue report page and extracts issue information into a CSV file.

The script was designed for the Apache Jira issue CAMEL-10597, but it is reusable for other public Jira issue URLs that follow the same browse URL format.

## Features

For a given public Jira issue URL, the script collects:

- issue key
- title
- type
- status
- priority
- resolution
- assignee
- reporter
- created date
- created epoch timestamp in milliseconds
- updated date
- resolved date
- description
- comments
- original issue URL

It then writes the extracted data to a CSV file with one row for the issue.

## Installation

### 1. Run project
```bash
python jira_issue_crawler.py https://issues.apache.org/jira/browse/CAMEL-10597
```