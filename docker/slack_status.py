#!/usr/bin/python    
import sys, argparse, json, os
import requests
from git import Repo

parser = argparse.ArgumentParser(description='Slack status updater')
parser.add_argument('--webhook', help='Slack webhook URL', required=False)
parser.add_argument('--color', help='Color to set', required=False)
parser.add_argument('--deploy_url', help='Deploy URL', required=False)
parser.add_argument('--deploy_env', help='Deploy environment', required=True)
parser.add_argument('--deploy_status', help='Deploy status', required=True)
parser.add_argument('--org', help='GitHub organization', required=False, default='artshumrc')
parser.add_argument('--repo', help='GitHub repo', required=False, default='giza')
parser.add_argument('--commit_url', help='Commit URL', required=False)
parser.add_argument('--commit_hash', help='Commit hash', required=False)
parser.add_argument('--commit_message', help='Commit message', required=False)
parser.add_argument('--commit_author', help='Commit author', required=False)
parser.add_argument('--branch', help='Branch', required=False)
parser.add_argument('--repo_path', help='Repo path', required=False, default='.')
parser.add_argument('--docker_status', help='Docker status', required=False)

args = vars(parser.parse_args())

if not args['webhook']:
    print('No webhook URL provided, trying environment variable SLACK_WEBHOOK')
    args['webhook'] = os.environ.get('SLACK_WEBHOOK')
    if not args['webhook']:
        print('No webhook URL provided, exiting')
        sys.exit(1)

repo = Repo(args['repo_path'])
latest_commit = repo.head.commit

success_color = '#36a64f'
failure_color = '#ff0000'

payload = {
    "attachments": []
}

attachment = {
    "blocks": []
}
default_color = success_color if 'success' in args['deploy_status'].lower() else failure_color
attachment['color'] = args['color'] if args['color'] else default_color

header_section = {
    "type": "section",
    "text": {
        "type": "mrkdwn",
    }
}
if args['deploy_url']:
    header_section['text']['text'] = f"*{args['deploy_env']}* deployment to {args['deploy_url']}: *{args['deploy_status']}*"
else:
    header_section['text']['text'] = f"*{args['deploy_env']}* deployment: *{args['deploy_status']}*"
attachment['blocks'].append(header_section)

if not args['commit_hash']:
    args['commit_hash'] = latest_commit.hexsha
    commit = latest_commit
else:
    commit = repo.commit(args['commit_hash'])
args['short_sha'] = args['commit_hash'][:7]

if not args['commit_author']:
    args['commit_author'] = commit.author.name
if not args['commit_message']:
    args['commit_message'] = commit.message
if not args['commit_url']:
    args['commit_url'] = f"https://github.com/{args['org']}/{args['repo']}/commit/{args['commit_hash']}"
if not args['branch']:
    args['branch'] = repo.active_branch.name

info_section = {
    "type": "section",
    "text": {
        "type": "mrkdwn",
    }
}
info_section['text']['text'] = f"Commit: <{args['commit_url']}|{args['short_sha']} ({args['branch']})> by {args['commit_author']}\n{args['commit_message']}"
attachment['blocks'].append(info_section)

if args['docker_status']:
    docker_section = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"Docker status: {args['docker_status']}"
        }
    }
    attachment['blocks'].append(docker_section)

payload['attachments'].append(attachment)

print(payload)
r = requests.post(args['webhook'], data=json.dumps(payload))
print(r)