#!/usr/bin/env python3

import subprocess
import json
import sys
import logging
import urllib.parse
import urllib.request
from urllib.error import HTTPError

import gerrit_tools.config as config


CWD = '.'
GERRIT_URL = config.get_val('GERRIT_URL')
GERRIT_PORT = config.get_val('GERRIT_PORT')
GERRIT_USER = config.get_val('GERRIT_USER')
GERRIT_API_TOKEN = config.get_val('GERRIT_API_TOKEN')
GERRIT_CMD = 'ssh -p {} -l {} {} gerrit'.format(GERRIT_PORT, GERRIT_USER, GERRIT_URL)

skip_projects = []
filter_projects = []


def exec_cmd(cmd: str):
    res = None
    try:
        res = subprocess.check_output(cmd, cwd=CWD, shell=True).decode('UTF-8')
    except subprocess.CalledProcessError as e:
        logging.warning(e)
        return None
    finally:
        return res


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


def get_projects(branch: str):
    projects = exec_cmd('{} ls-projects -b {} --format json_compact'.format(GERRIT_CMD, branch))
    projects = json.loads(projects)
    has_filter = len(filter_projects) > 0
    if has_filter or len(skip_projects) > 0:
        filtered = {}
        for p in projects:
            if p in skip_projects:
                continue
            if has_filter and p not in filter_projects:
                continue
            filtered[p] = projects[p]
        projects = filtered
    if len(projects) == 0:
        logging.info('No projects found for branch: {}'.format(branch))
        sys.exit(1)
    return projects


def copy_branch(src: str, dst: str, fallback: str = None):
    logging.info('Copy branch: {} => {}'.format(src, dst))
    existing_projects = exec_cmd('{} ls-projects -b {} --format json_compact'.format(GERRIT_CMD, dst))
    existing_projects = json.loads(existing_projects).keys()
    projects = get_projects(branch=src)
    for p in projects:
        if p in existing_projects:
            print('Branch:', dst, 'already exists in', p)
            continue
        commit = projects[p]['branches'][src]
        print('Creating branch:', dst, 'in', p, 'hash:', commit, end='\t')
        create = exec_cmd('{} create-branch {} {} {}'.format(GERRIT_CMD, p, dst, commit))
        if create is None:
            print('Fail')
        else:
            print('OK')
    if fallback is None:
        return
    fallback_projects = get_projects(branch=fallback)
    for p in fallback_projects:
        if p in projects:
            continue
        if p in existing_projects:
            print('Branch', dst, 'already exists in', p)
            continue
        projects[p] = fallback_projects[p]
        commit = projects[p]['branches'][fallback]
        print('Creating [fallback] branch:', dst, 'in', p, 'hash:', commit, end='\t')
        create = exec_cmd('{} create-branch {} {} {}'.format(GERRIT_CMD, p, dst, commit))
        if create is None:
            print('Fail')
        else:
            print('OK')


def delete_branch(branch: str):
    logging.info('Delete branch: {}'.format(branch))
    projects = get_projects(branch=branch)
    for p in projects:
        print('Removing branch:', branch, 'from:', p, end='\t')
        res = exec_api('DELETE', '/projects/{}/branches/{}'.format(
            urllib.parse.quote(p, safe=''), urllib.parse.quote(branch, safe='')
        ))
        print('OK')


def main():
    args = config.parse_args()
    global skip_projects
    skip_projects = args.skip
    global filter_projects
    if args.manifest is not None:
        tag = args.manifest_tag
        import xml.etree.ElementTree as ET
        tree = ET.parse(args.manifest)
        root = tree.getroot()
        logging.debug('Manifest tag: {}, Root: {}'.format(tag, root))
        if root.tag == 'manifest':
            for child in root:
                logging.debug('Child: {} -> {}'.format(child.tag, child.attrib))
                if tag == child.tag:
                    filter_projects.append(child.attrib['name'])
        else:
            logging.error('Invalid manifest: {}'.format(args.manifest))
            sys.exit(1)
        logging.debug('Filter projects: {}'.format(filter_projects))
    if args.command in ['branch', 'b']:
        if args.sub_command in ['copy', 'c']:
            copy_branch(args.source, args.destination, args.fallback_source)
        if args.sub_command in ['delete', 'd']:
            delete_branch(args.name)


if __name__ == "__main__":
    main()
