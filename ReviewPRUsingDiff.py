from cryptography.hazmat.primitives import serialization
import os
import json
import requests
import vertexai
from vertexai.generative_models import GenerativeModel
import vertexai.preview.generative_models as generative_models

# Configuration from environment variables
TOKEN = os.getenv('TOKEN')
REPO_OWNER = os.getenv('REPO_OWNER', 'Rupeek')
REPO_NAME = os.getenv('REPO_NAME', 'rupeek-web')
PR_NUMBER = os.getenv('PR_NUMBER', '1805')

# Headers for GitHub API
def get_headers():
    return {
        'Authorization': f'token {TOKEN}',
        'Accept': 'Accept: application/vnd.github.v3.diff',
    }

# Function to get the files changed in a specific pull request
def get_patch_from_pr(pr_number):
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}'
    response = requests.get(url, headers=get_headers())
    return response.text

generation_config = {
    "max_output_tokens": 8192,
    "temperature": 0.4,
    "top_p": 0.95,
}

safety_settings = {
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

def generate(text1):
    vertexai.init(project="langflowtest-420416", location="us-central1")
    model = GenerativeModel(
        "gemini-1.5-pro-001",
        system_instruction=[
            "you are a code reviewer. Do not provide review comments on non-mandatory things like missing descriptions of variables, fields, and methods. Also allow commented code. Ignore comments on variable naming."]
    )
    responses = model.generate_content(
        [text1],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    review_output = ''
    for response in responses:
        review_output += response.text

    return review_output


def review_pull_request():
    pr_number = PR_NUMBER
    patch = get_patch_from_pr(pr_number)

    context = f"""review the code diff below. Post analysis print the review in the format given.
    Post review comments only where something needs to be improved.
    Do not give duplicate comments. Do not print the code.
    Print the comments along with Filename and line number.
    Do not comment on missing method descriptions and missing comments.
    Format: 
    Line 1 - Summary of recommendations
    Leave one line space
    Line 2 onwards -
    File Name - Line number - Comment - Suggestion to improve. Leave space between each row.
    
    The diff of each file is as follows:
    {patch}"""

    review = generate(context)
    return review

# Function to post a review comment on a pull request
def post_review_comment(body):
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{PR_NUMBER}/reviews'
    data = {
        "body": body,
        "event": "COMMENT"
    }
    response = requests.post(url, headers=get_headers(), data=json.dumps(data))
    return response.json()

if __name__ == "__main__":
    pr_comment = review_pull_request()
    post_review_comment(pr_comment)
    print(f'comment posted successfully - {pr_comment}')
