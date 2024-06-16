import os
import subprocess
import requests
import json
import javalang
import networkx as nx
import pydot


# Configuration from environment variables
#GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
#REPO_OWNER = os.getenv('REPO_OWNER')
#REPO_NAME = os.getenv('REPO_NAME')
#PR_NUMBER = os.getenv('PR_NUMBER')

GITHUB_TOKEN = '<personal access token>'
REPO_OWNER = 'ankurlucknowi'
REPO_NAME = 'planner'
PR_NUMBER = '18'
# Headers for GitHub API
headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
}

# Function to get the details of a specific pull request
def get_pull_request(pr_number):
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}'
    response = requests.get(url, headers=headers , verify=False)
    return response.json()

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

# Function to clone the repo and checkout the PR branch
#def clone_repo_and_checkout_pr(pr_number):
    #subprocess.run(['git', 'clone', f'https://github.com/{REPO_OWNER}/{REPO_NAME}.git'])
    #os.chdir(REPO_NAME)
    #subprocess.run(['git', 'fetch', 'origin', f'pull/{pr_number}/head:pr-branch'])
    #subprocess.run(['git', 'checkout', 'pr-branch'])

# Function to find the functions affected by the changed lines using javalang
def find_changed_functions(file_path, line_numbers):
    with open(file_path, 'r') as file:
        content = file.read()
    tree = javalang.parse.parse(content)
    changed_functions = set()

    for path, node in tree:
        if isinstance(node, javalang.tree.MethodDeclaration):
            start_line = node.position.line
            end_line = start_line + len(node.body) if node.body else start_line
            for line in line_numbers:
                if start_line <= line <= end_line:
                    changed_functions.add(path[2].name + "." + node.name)
                    break
    return changed_functions

# Function to build a call graph for Java code
def build_call_graph(repo_path):
    call_graph = nx.DiGraph()

    def add_method_invocations(tree, current_class, current_method):
        for path, node in tree:
            if isinstance(node, javalang.tree.MethodInvocation):
                invoked_method = node.member
                call_graph.add_edge(f"{current_class}.{current_method}", f"{current_class}.{invoked_method}")
            # Recursively traverse the tree to find nested method invocations
            for child in node.children:
                if isinstance(child, list):
                    for item in child:
                        if isinstance(item, javalang.tree.Node):
                            add_method_invocations([(path, item)], current_class, current_method)
                elif isinstance(child, javalang.tree.Node):
                    add_method_invocations([(path, child)], current_class, current_method)

    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    content = f.read()
                tree = javalang.parse.parse(content)
                current_class = None
                for path, node in tree:
                    if isinstance(node, javalang.tree.ClassDeclaration):
                        current_class = node.name
                    elif isinstance(node, javalang.tree.MethodDeclaration):
                        method_name = node.name
                        call_graph.add_node(f"{current_class}.{method_name}")
                        add_method_invocations([(path, node)], current_class, method_name)

    return call_graph

# Function to find upstream and downstream dependencies in the call graph
def find_dependencies(nx_graph, changed_functions):
    upstream_dependencies = set()
    downstream_dependencies = set()

    for func in changed_functions:
        if func in nx_graph:
            # Upstream dependencies (functions that call the changed function)
            upstream_dependencies.update(nx.ancestors(nx_graph, func))

            # Downstream dependencies (functions called by the changed function)
            downstream_dependencies.update(nx.descendants(nx_graph, func))

    return upstream_dependencies, downstream_dependencies

if __name__ == "__main__":
    pr_number = PR_NUMBER

    # Step 1: Fetch changed files and line numbers
    files = get_pull_request_files(pr_number)
    changed_functions = set()

   # clone_repo_and_checkout_pr(pr_number)

    for file in files:
        filename = file['filename']
        patch = file.get('patch', '')
        if patch and filename.endswith('.java'):
            line_numbers = extract_line_numbers(patch)
            changed_functions.update(find_changed_functions(filename, line_numbers))

    # Step 2: Build call graph
    #repo_path = os.getcwd()
    repo_path="/Users/ankur.srivastava/source/planner-master/backend/src/main/java"
    call_graph = build_call_graph(repo_path)

    # Step 3: Find upstream and downstream dependencies
    upstream, downstream = find_dependencies(call_graph, changed_functions)
    print("Upstream dependencies:", upstream)
    print("Downstream dependencies:", downstream)
