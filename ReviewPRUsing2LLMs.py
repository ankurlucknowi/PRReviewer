import os
import json
import requests
import vertexai
from vertexai.generative_models import GenerativeModel
import vertexai.preview.generative_models as generative_models
from openai import OpenAI


# Configuration from environment variables
TOKEN = os.getenv('TOKEN', '<Git PAt>')
TOKEN_VERTEX = os.getenv('TOKEN_VERTEX',
                         '<vertex key')
TOKEN_OPENAI = os.getenv('TOKEN_OPENAI', '<openai key>')
REPO_OWNER = os.getenv('REPO_OWNER', 'Rupeek')
REPO_NAME = os.getenv('REPO_NAME', 'RupeekLenderCore')
PR_NUMBER = os.getenv('PR_NUMBER', '607')

# Headers for GitHub API
def get_headers():
    
    return {
        'Authorization': f'token {TOKEN}',
        'Accept': 'Accept: application/vnd.github.v3.diff',
    }


def generate_vertex(text1):
    generation_config = {
        "max_output_tokens": 8192,
        "temperature": 1,
        "top_p": 0.95,
    }

    safety_settings = {
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }

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

client = OpenAI(
    organization='org-8HnXwbIJshIXURi2kHdzNmqI',
    api_key=f'{TOKEN_OPENAI}',

)

def generate_openai(text1):
    openai_response = ''
    stream = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": text1}],
        stream=True,
    )
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            openai_response = openai_response + chunk.choices[0].delta.content
    return openai_response


# Function to get the files changed in a specific pull request
def get_patch_from_pr(pr_number):
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}'
    response = requests.get(url, headers=get_headers())
    return response.text


def review_pull_request_openai():
    pr_number = PR_NUMBER
    patch = get_patch_from_pr(pr_number)

    context = get_context(patch)

    review_vertex = generate_openai(context)
    return review_vertex


def review_pull_request():
    pr_number = PR_NUMBER
    patch = get_patch_from_pr(pr_number)

    context = get_context(patch)

    review_vertex = generate_vertex(context)
    return review_vertex


def get_context(patch):
    context = f"""Analyse the code diff below. Post analysis, print the code review comments in the format given.
  Post review comments only where something needs to be improved.
  Do not give duplicate comments. Do not print the code.
Do not repeat same comments for different lines.
  Print the comments along with Filename and line number.
  Do not comment on missing method descriptions and missing comments.
Check for Backward compatibility of code
Check if there is any need for useful abstractions
Think like an adversary that is trying to break the code.
Check if any of the code re-use. Avoid re-inventing the wheel.
For same comments on multiple lines, make the comment once and mention the line numbers together.

  Response Format: 
  Line 1 - Summary of recommendations
  Leave one line space
  Line 2 onwards -
  File Name - Line number - Review Comment with reason on why the comment is being given- Suggestion on how to fix the comment (with directional code changes).
Leave space after each row of comments.
    {patch}"""
    return context


# Function to post a review comment on a pull request
def post_review_comment(body):
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{PR_NUMBER}/reviews'
    data = {
        "body": body,
        "event": "COMMENT"
    }
    response = requests.post(url, headers=get_headers(), data=json.dumps(data))
    return response.json()


# Function to get the files changed in a specific pull request
def get_pull_request_files(pr_number):
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/files'
    response = requests.get(url, headers=get_headers(), verify=False)
    return response.json()


if __name__ == "__main__":

    files = get_pull_request_files(f'{PR_NUMBER}')
    openai_review_concatenated = ''
    if len(files) >= 10:
        num_batches = len(files) // 10
        batch_size = (len(files) + num_batches - 1) // num_batches
        batches = [files[i:i + batch_size] for i in range(0, len(files), batch_size)]
        for batch in batches:
            concatenated_patch = ''.join(file.get('patch', '') for file in batch)
            openai_review_concatenated = openai_review_concatenated + " \n" + generate_openai(get_context(concatenated_patch))
    else:
        openai_review_concatenated = review_pull_request_openai()
        
    review_vertex = review_pull_request()
    post_review_comment(openai_review_concatenated)
    print(f'Vertex Comment - {review_vertex}')
    print(f'openai Comment - {openai_review_concatenated}')
