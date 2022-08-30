#!/usr/bin/env python3

import subprocess
import argparse
import json
import sys
import logging
import urllib.parse
import urllib.request
import config

parser = argparse.ArgumentParser(description='CI repo/git tools.')
parser.add_argument('--skip', nargs='+', default='platform/manifest',
                    help='Skip projects, default: platform/manifest')

# Sub commands:
subparsers = parser.add_subparsers(dest='command', help='Sub-commands', required=True)
# Branch manipulation
parser_branch = subparsers.add_parser('branch', aliases='b', help='Manipulate branches')
parser_branch = parser_branch.add_subparsers(dest='sub_command', help='Sub commands', required=True)
# Copy
parser_branch_copy = parser_branch.add_parser('copy', aliases='c', help='Copy existing branch to a new one')
parser_branch_copy.add_argument('source', type=str, help='Source branch name')
parser_branch_copy.add_argument('destination', type=str, help='Destination branch name')
# Delete
parser_branch_copy = parser_branch.add_parser('delete', aliases='d', help='Delete existing branch')
parser_branch_copy.add_argument('name', type=str, help='Branch name')

parser_d = subparsers.add_parser('dummy', help='Dummy help')
parser_d.add_argument('--foo', choices=['one', 'two'], help='foo help')
args = parser.parse_args()

CWD = '.'
GERRIT_URL = config.get_val('GERRIT_URL')
GERRIT_PORT = config.get_val('GERRIT_PORT')
GERRIT_USER = config.get_val('GERRIT_USER')
GERRIT_API_TOKEN = config.get_val('GERRIT_API_TOKEN')
GERRIT_CMD = 'ssh -p {} -l {} {} gerrit'.format(GERRIT_PORT, GERRIT_USER, GERRIT_URL)


def exec_cmd(cmd: str):
    return subprocess.check_output(cmd, cwd=CWD, shell=True).decode('UTF-8')


def exec_api(method: str, url: str, data: [] = None):
    url = 'https://{}/a/{}'.format(GERRIT_URL, url.lstrip('/'))
    if data is not None:
        data = urllib.parse.urlencode(data).encode()
    passwd = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    passwd.add_password(None, url, GERRIT_USER, GERRIT_API_TOKEN)
    auth_handler = urllib.request.HTTPBasicAuthHandler(passwd)
    opener = urllib.request.build_opener(auth_handler)
    urllib.request.install_opener(opener)
    logging.info('API [{}]: {}'.format(method, url))
    request = urllib.request.Request(url, method=method, data=data)
    with opener.open(request) as f:
        return f.read().decode()


if args.command in ['branch', 'b']:
    if args.sub_command in ['copy', 'c']:
        src = args.source
        dst = args.destination
        logging.info('Copy branch: {} => {}'.format(src, dst))
        projects = exec_cmd('{} ls-projects -b {} --format json_compact'.format(GERRIT_CMD, src))
        projects = json.loads(projects)
        if len(projects) == 0:
            logging.warning('No source branch found: {}'.format(src))
            sys.exit(1)
        for p in projects:
            if p in args.skip:
                continue
            commit = projects[p]['branches'][src]
            create = exec_cmd('{} create-branch {} {} {}'.format(GERRIT_CMD, p, dst, commit))
            print('Branch', dst, 'created in', p, 'hash:', commit, 'OK')
    if args.sub_command in ['delete', 'd']:
        branch = args.name
        logging.info('Delete branch: {}'.format(branch))
        projects = exec_cmd('{} ls-projects -b {} --format json_compact'.format(GERRIT_CMD, branch))
        projects = json.loads(projects)
        if len(projects) == 0:
            logging.warning('No branch found: {}'.format(branch))
            sys.exit(1)
        for p in projects:
            if p in args.skip:
                continue
            res = exec_api('DELETE', '/projects/{}/branches/{}'.format(
                urllib.parse.quote(p, safe=''), urllib.parse.quote(branch, safe='')
            ))
            print('Removed branch:', branch, 'from:', p)
logging.info('DONE')
