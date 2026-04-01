import csv
import html
import re
import sys
from datetime import datetime
from typing import Dict, List
from xml.etree import ElementTree as ET

import requests

HEADERS = {
    "User-Agent": "jira-issue-crawler/1.0"
}

# Normalize whitespace in text by collapsing repeated spaces
def clean_text(text: str) -> str:
    """Collapse repeated whitespace and trim the result."""
    return re.sub(r"\s+", " ", text).strip() if text else ""

# Convert Jira date formats to epoch milliseconds
def to_epoch_millis(date_str: str) -> str:
    """
    Convert Jira date strings into epoch milliseconds.
    Supports both:
    - 2016-12-14T14:42:08+0000
    - Wed, 14 Dec 2016 14:42:08 +0000
    """
    if not date_str:
        return ""

    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%a, %d %b %Y %H:%M:%S %z",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return str(int(dt.timestamp() * 1000))
        except ValueError:
            continue

    return ""

# Extract the issue key from a Jira browse URL using regex
def extract_issue_key(url: str) -> str:
    """Extract the issue key from a Jira browse URL."""
    match = re.search(r"/browse/([A-Z0-9\-]+)", url)
    return match.group(1) if match else ""

# Construct the URL for fetching issue XML from Apache Jira
def build_xml_url(issue_key: str) -> str:
    """Build the public Jira XML export URL for the issue."""
    return f"https://issues.apache.org/jira/si/jira.issueviews:issue-xml/{issue_key}/{issue_key}.xml"

# Fetch and parse XML content from the given URL
def get_xml_root(url: str) -> ET.Element:
    """Download the XML and parse it into an ElementTree root."""
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return ET.fromstring(response.content)

# Retrieve cleaned text content from a specific child element
def get_child_text(parent: ET.Element, tag_name: str) -> str:
    """Return cleaned text for the first direct child tag, or empty string."""
    child = parent.find(tag_name)
    if child is None:
        return ""
    return clean_text("".join(child.itertext()))

# Download issue from public Jira and extract key metadata fields
def crawl_issue(browse_url: str) -> Dict[str, str]:
    """
    Crawl one public Jira issue and return the required fields.
    This uses the public XML export, not the Jira REST API.
    """
    issue_key = extract_issue_key(browse_url)
    if not issue_key:
        raise ValueError("Could not extract issue key from URL.")

    xml_url = build_xml_url(issue_key)
    root = get_xml_root(xml_url)

    channel = root.find("channel")
    if channel is None:
        raise ValueError("Invalid XML: missing <channel> element.")

    item = channel.find("item")
    if item is None:
        raise ValueError("Invalid XML: missing <item> element.")

    created = get_child_text(item, "created")
    updated = get_child_text(item, "updated")
    resolved = get_child_text(item, "resolved")
    description = strip_html(get_child_text(item, "description"))

    row = {
        "Issue Key": issue_key,
        "Title": get_child_text(item, "summary"),
        "Type": get_child_text(item, "type"),
        "Status": get_child_text(item, "status"),
        "Priority": get_child_text(item, "priority"),
        "Resolution": get_child_text(item, "resolution"),
        "Assignee": get_child_text(item, "assignee"),
        "Reporter": get_child_text(item, "reporter"),
        "Created": created,
        "Created Epoch": to_epoch_millis(created),
        "Updated": updated,
        "Resolved": resolved,
        "Description": description,
        "Comments": parse_comments(item),
        "URL": browse_url,
    }

    return row

# Write crawled issue data to a CSV file with proper formatting
def write_csv(row: Dict[str, str], output_file: str) -> None:
    """Write one crawled issue row to a CSV file."""
    fieldnames = [
        "Issue Key",
        "Title",
        "Type",
        "Status",
        "Priority",
        "Resolution",
        "Assignee",
        "Reporter",
        "Created",
        "Created Epoch",
        "Updated",
        "Resolved",
        "Description",
        "Comments",
        "URL",
    ]

    with open(output_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)

# Main entry point that orchestrates crawling and saving issue data
def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python jira_issue_crawler.py <jira_issue_url> [output.csv]")
        sys.exit(1)

    browse_url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "jira_issue.csv"

    row = crawl_issue(browse_url)
    write_csv(row, output_file)

    print(f"Saved issue data to {output_file}")

# Remove HTML tags and entities from text while preserving newlines
def strip_html(text: str) -> str:
    """Remove HTML tags and unescape HTML entities."""
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return clean_text(text)

# Extract and format all comments from the XML element into a delimited string
def parse_comments(item: ET.Element) -> str:
    """
    Extract all comments from the XML.
    Each comment is joined into one field separated by ' || '.
    """
    comments: List[str] = []

    comments_parent = item.find("comments")
    if comments_parent is None:
        return ""

    for comment in comments_parent.findall("comment"):
        author = clean_text(comment.attrib.get("author", ""))
        created = clean_text(comment.attrib.get("created", ""))
        body = strip_html("".join(comment.itertext()))

        parts = []
        if author:
            parts.append(author)
        if created:
            parts.append(created)
        if body:
            parts.append(body)

        comment_text = ": ".join(parts)
        if comment_text:
            comments.append(comment_text)

    return " || ".join(comments)

if __name__ == "__main__":
    main()