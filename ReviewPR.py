import os
import requests
import json


# Configuration from environment variables
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_OWNER = os.getenv('REPO_OWNER')
REPO_NAME = os.getenv('REPO_NAME')
PR_NUMBER = os.getenv('PR_NUMBER')

# Headers for GitHub API
headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
}

# Function to get the details of a specific pull request
def get_pull_request(pr_number):
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}'
    response = requests.get(url, headers=headers,verify=False)
    return response.json()

# Function to post a review comment on a pull request
def post_review_comment(pr_number, body):
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/reviews'
    data = {
        "body": body,
        "event": "COMMENT"
    }
    response = requests.post(url, headers=headers, data=json.dumps(data), verify=False)
    return response.json()

# Main function to review the specific PR
def review_pull_request(pr_number):
    pr = get_pull_request(pr_number)
    pr_title = pr['title']
    pr_body = pr['body']

    # Custom review logic
    review_comment = f"Reviewing PR #{pr_number}: {pr_title}\n\n{pr_body}\n\n"

    # Get the changed files
    files = get_pull_request_files(pr_number)
    for file in files:
        filename = file['filename']
        patch = file.get('patch', '')
        if patch:
            line_numbers = extract_line_numbers(patch)
            review_comment += f"File: {filename}\nChanged lines: {line_numbers}\n\n"

    print(review_comment);
    # Post the review comment
  #  post_review_comment(pr_number, review_comment)

# Function to get the files changed in a specific pull request
def get_pull_request_files(pr_number):
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/files'
    response = requests.get(url, headers=headers, verify=False)
    return response.json()

# Function to extract line numbers from the patch data
def extract_line_numbers(patch):
    line_numbers = []
    lines = patch.split('\n')
    for line in lines:
        if line.startswith('@@'):
            parts = line.split(' ')
            for part in parts:
                if part.startswith('+') and ',' in part:
                    start, count = map(int, part[1:].split(','))
                    line_numbers.extend(range(start, start + count))
                elif part.startswith('+'):
                    line_numbers.append(int(part[1:]))
    return line_numbers


if __name__ == "__main__":
    review_pull_request(PR_NUMBER)
