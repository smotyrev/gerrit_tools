#!/usr/bin/env python3

import subprocess
import json
import sys
import os
import logging
import urllib.parse
import urllib.request

import gerrit_tools.config as config
from gerrit_tools import bcolors


def exec_cmd(cmd: str):
    res = None
    try:
        res = subprocess.check_output(cmd, cwd=config.cwd, shell=True).decode('UTF-8')
    except subprocess.CalledProcessError as e:
        logging.warning(e)
        return None
    finally:
        return res


def exec_api(method: str, url: str, data: [] = None):
    url = 'https://{}/a/{}'.format(config.GERRIT_URL, url.lstrip('/'))
    if data is not None:
        data = urllib.parse.urlencode(data).encode()
    passwd = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    passwd.add_password(None, url, config.GERRIT_USER, config.GERRIT_API_TOKEN)
    auth_handler = urllib.request.HTTPBasicAuthHandler(passwd)
    opener = urllib.request.build_opener(auth_handler)
    urllib.request.install_opener(opener)
    logging.info('API [{}]: {}'.format(method, url))
    request = urllib.request.Request(url, method=method, data=data)
    with opener.open(request) as f:
        return f.read().decode()


def get_projects(branch: str):
    projects = exec_cmd('{} ls-projects -b {} --format json_compact'.format(config.GERRIT_CMD, branch))
    projects = json.loads(projects)
    has_filter = len(config.manifest_projects) > 0
    if has_filter or len(config.skip_projects) > 0:
        filtered = {}
        for p in projects:
            if p in config.skip_projects:
                continue
            if has_filter and p not in config.manifest_projects:
                continue
            filtered[p] = projects[p]
        projects = filtered
    if len(projects) == 0:
        logging.info('No projects found for branch: {}'.format(branch))
        sys.exit(1)
    return projects


def copy_branch(src: str, dst: str, fallback: str = None):
    logging.info('Copy branch: {} => {}'.format(src, dst))
    existing_projects = exec_cmd('{} ls-projects -b {} --format json_compact'.format(config.GERRIT_CMD, dst))
    existing_projects = json.loads(existing_projects).keys()
    projects = get_projects(branch=src)
    for p in projects:
        if p in existing_projects:
            print('Branch:', dst, 'already exists in', p)
            continue
        commit = projects[p]['branches'][src]
        print('Creating branch:', dst, 'in', p, 'hash:', commit, end='\t')
        create = exec_cmd('{} create-branch {} {} {}'.format(config.GERRIT_CMD, p, dst, commit))
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
        create = exec_cmd('{} create-branch {} {} {}'.format(config.GERRIT_CMD, p, dst, commit))
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


def list_branch(branch: str):
    logging.info('List branch: {}'.format(branch))
    projects = get_projects(branch=branch)
    if config.verbose:
        from gerrit_tools import bcolors
        for p in projects:
            proj = projects[p]
            links = []
            for link in proj['web_links']:
                links.append('https://{}{}'.format(config.GERRIT_URL, link['url']))
            state = proj['state']
            if state == 'ACTIVE':
                state = bcolors.ok_green(state)
            else:
                state = bcolors.warn(state)
            print(state, proj['branches'][branch], bcolors.bold(bcolors.underline(p)), ' '.join(links))
    else:
        print('\n'.join(projects.keys()))


def repo_upload(branch: str):
    config.verbose and print('repo_upload, branch:', branch)
    if len(config.manifest_projects) == 0:
        logging.error('No projects specified in manifest')
        sys.exit(1)
    manifest_paths = {}
    import xml.etree.ElementTree as ET

    def recursive_read_manifest(m_file: str):
        tree = ET.parse(m_file)
        root = tree.getroot()
        if root.tag == 'manifest':
            for child in root:
                if child.tag == 'project':
                    p = child.attrib['name']
                    if p not in config.manifest_projects:
                        config.verbose and print(bcolors.ok_cyan("Skip project: {}".format(p)))
                        continue
                    if p not in manifest_paths:
                        manifest_paths[p] = child.attrib['path']
                    else:
                        logging.warning('Project: {} already exists'.format(p))
                        continue
                elif child.tag == 'remove-project':
                    p = child.attrib['name']
                    if p in manifest_paths:
                        rp = manifest_paths.pop(p, None)
                        config.verbose and logging.warning('Removing project: {} => {}'.format(p, rp))
                elif child.tag == 'include':
                    file = config.cwd.rstrip(os.sep) + os.sep + '.repo/manifests/' + child.attrib['name']
                    recursive_read_manifest(file)
        else:
            logging.error('Invalid manifest: {}'.format(config.manifest))
            sys.exit(1)
    recursive_read_manifest(config.manifest)
    for p in manifest_paths:
        path = manifest_paths[p]
        config.verbose and print(p, 'in', path)
        if not os.path.isdir(path):
            config.verbose and logging.warning('Skip, no path')
            continue
        rmt = exec_cmd('git -C {} config remote.{}.url'.format(path, config.GERRIT_REMOTE))
        if rmt is None:
            rmt = ''
        rmt = rmt.strip()
        url = '{}/{}'.format(config.GERRIT_SSH_URL, p)
        if rmt != url:
            config.verbose and print('remote:', rmt, '=>', url)
            if rmt != url:
                exec_cmd('git -C {} remote remove {}'.format(path, config.GERRIT_REMOTE))
            exec_cmd('git -C {} remote add {} {}'.format(path, config.GERRIT_REMOTE, url))
        print('Push to branch:', branch, 'project:', p, 'in:', path)
        create = exec_cmd('git -C {} push -f {} HEAD:refs/heads/{}'.format(path, config.GERRIT_REMOTE, branch))
        print('\tOK', create)


def main():
    args = config.parse_args()
    if args.command in ['branch', 'b']:
        if args.sub_command in ['copy', 'c']:
            copy_branch(args.source, args.destination, args.fallback_source)
        elif args.sub_command in ['delete', 'd']:
            delete_branch(args.name)
        elif args.sub_command in ['list', 'l']:
            list_branch(args.name)
        else:
            logging.error('Unknown sub-command: {}'.format(args.sub_command))
            sys.exit(1)
    elif args.command in ['repo', 'r']:
        if args.sub_command in ['upload', 'u']:
            repo_upload(args.new_branch_name)
        else:
            logging.error('Unknown sub-command: {}'.format(args.sub_command))
            sys.exit(1)
    else:
        logging.error('Unknown command: {}'.format(args.command))
        sys.exit(1)


if __name__ == "__main__":
    main()
