#!/usr/bin/env python3

import subprocess
import json
import sys
import logging
import urllib.parse
import urllib.request
import gerrit_tools.config as config


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


def copy_branch(src: str, dst: str, skip: list):
    logging.info('Copy branch: {} => {}'.format(src, dst))
    projects = exec_cmd('{} ls-projects -b {} --format json_compact'.format(GERRIT_CMD, src))
    projects = json.loads(projects)
    if len(projects) == 0:
        logging.warning('No source branch found: {}'.format(src))
        sys.exit(1)
    for p in projects:
        if p in skip:
            continue
        commit = projects[p]['branches'][src]
        create = exec_cmd('{} create-branch {} {} {}'.format(GERRIT_CMD, p, dst, commit))
        print('Branch', dst, 'created in', p, 'hash:', commit, 'OK')


def delete_branch(branch: str, skip: list):
    logging.info('Delete branch: {}'.format(branch))
    projects = exec_cmd('{} ls-projects -b {} --format json_compact'.format(GERRIT_CMD, branch))
    projects = json.loads(projects)
    if len(projects) == 0:
        logging.warning('No branch found: {}'.format(branch))
        sys.exit(1)
    for p in projects:
        if p in skip:
            continue
        res = exec_api('DELETE', '/projects/{}/branches/{}'.format(
            urllib.parse.quote(p, safe=''), urllib.parse.quote(branch, safe='')
        ))
        print('Removed branch:', branch, 'from:', p)


def main():
    args = config.parse_args()
    if args.command in ['branch', 'b']:
        if args.sub_command in ['copy', 'c']:
            copy_branch(args.source, args.destination, args.skip)
        if args.sub_command in ['delete', 'd']:
            delete_branch(args.name, args.skip)


if __name__ == "__main__":
    main()
