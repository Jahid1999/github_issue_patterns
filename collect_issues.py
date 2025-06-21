import requests
import pandas as pd
import os
import json

# GitHub API base URL
GITHUB_API_URL = "https://api.github.com"

# Your GitHub Personal Access Token (replace with your token)
# It's recommended to use environment variables for sensitive information
GITHUB_TOKEN = "token_was_here"

# Headers for authenticated requests
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_issues(owner, repo, state="all", labels=None):
    issues = []
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues"
    
    # Initial parameters for pagination
    params = {
        "state": state,
        "per_page": 100  # Max per page
    }
    if labels:
        params["labels"] = ",".join(labels)

    while url:
        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code == 200:
            data = response.json()
            if not data:
                break  # No more issues
            issues.extend(data)
            
            # Check for next page in Link header (cursor-based pagination)
            if 'link' in response.headers:
                links = response.headers['link'].split(', ')
                next_page_url = None
                for link in links:
                    if 'rel="next"' in link:
                        next_page_url = link.split(';')[0].strip('<>')
                        break
                url = next_page_url
                params = {} # Clear params as URL already contains them
            else:
                url = None # No more pages
        else:
            print(f"Error fetching issues for {owner}/{repo}: {response.status_code} - {response.text}")
            break
    return issues

def main():
    projects_df = pd.read_csv("projects.csv")
    all_issues_data = []

    for index, row in projects_df.iterrows():
        project_name = row["project_name"]
        github_url = row["github_url"]
        framework = row["framework"]

        # Extract owner and repo from GitHub URL
        parts = github_url.split("/")
        owner = parts[-2]
        repo = parts[-1]

        print(f"Collecting issues for {owner}/{repo}...")

        # Define labels to filter by
        target_labels = ["bug", "security", "performance"]

        # Get issues for each label (or all if no specific label is found)
        issues = get_issues(owner, repo, state="all") # Fetch all issues first

        project_issues_data = []
        for issue in issues:
            issue_labels = [label["name"] for label in issue["labels"]]
            
            # Filter issues by target labels
            if not any(label in issue_labels for label in target_labels):
                continue

            # Extract relevant data
            issue_type = "N/A"
            if "bug" in issue_labels: issue_type = "bug"
            elif "security" in issue_labels: issue_type = "security"
            elif "performance" in issue_labels: issue_type = "performance"
            else: issue_type = "other"

            created_at = issue["created_at"]
            closed_at = issue["closed_at"]
            
            # Calculate time to close if closed
            time_to_close = None
            if created_at and closed_at:
                from datetime import datetime
                created_dt = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
                closed_dt = datetime.strptime(closed_at, "%Y-%m-%dT%H:%M:%SZ")
                time_to_close = (closed_dt - created_dt).total_seconds() / (60*60*24) # in days

            issue_data = {
                "project_name": project_name,
                "framework": framework,
                "issue_id": issue["number"],
                "issue_title": issue["title"],
                "issue_type": issue_type,
                "state": issue["state"],
                "created_at": created_at,
                "closed_at": closed_at,
                "time_to_close_days": time_to_close,
                "labels": ", ".join(issue_labels),
                "comments": issue["comments"],
                "url": issue["html_url"]
            }
            all_issues_data.append(issue_data)
            project_issues_data.append(issue_data)
        # Write this project's issues to a CSV after each iteration
        if project_issues_data:
            project_issues_df = pd.DataFrame(project_issues_data)
            safe_project_name = project_name.replace("/", "_").replace(" ", "_")
            project_issues_df.to_csv(f"{safe_project_name}.csv", index=False)

    issues_df = pd.DataFrame(all_issues_data)
    issues_df.to_csv("github_issues1.csv", index=False)
    print("Issue collection complete. Data saved to github_issues.csv")

if __name__ == "__main__":
    main()


