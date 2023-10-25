#!/usr/bin/env python3
import signal
import subprocess
import json
import sys
import os
import logging
import urllib.parse
import urllib.request

import gerrit_tools.config as config
from gerrit_tools import bcolors


cancelled = False


def exec_cmd(cmd: str, warn: bool = True):
    res = None
    try:
        res = subprocess.check_output(cmd, shell=True).decode('UTF-8')
    except subprocess.CalledProcessError as e:
        if warn:
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
            if cancelled:
                return
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
        if cancelled:
            return
        if p in existing_projects:
            print('Branch:', dst, 'already exists in', p)
            continue
        commit = projects[p]['branches'][src]
        print('Creating branch:', dst, 'in', p, 'hash:', commit, end='\t')
        _cmd = '{} create-branch {} {} {}'.format(config.GERRIT_CMD, p, dst, commit)
        if config.noop:
            print('DUMMY: {}'.format(_cmd))
        else:
            create = exec_cmd(_cmd)
            if create is None:
                print('Fail')
            else:
                print('OK')
    if fallback is None:
        return
    fallback_projects = get_projects(branch=fallback)
    for p in fallback_projects:
        if cancelled:
            return
        if p in projects:
            continue
        if p in existing_projects:
            print('Branch', dst, 'already exists in', p)
            continue
        projects[p] = fallback_projects[p]
        commit = projects[p]['branches'][fallback]
        _cmd = '{} create-branch {} {} {}'.format(config.GERRIT_CMD, p, dst, commit)
        if config.noop:
            print('DUMMY: {}'.format(_cmd))
        else:
            print('Creating [fallback] branch:', dst, 'in', p, 'hash:', commit, end='\t')
            create = exec_cmd(_cmd)
            if create is None:
                print('Fail')
            else:
                print('OK')


def delete_branch(branch: str):
    logging.info('Delete branch: {}'.format(branch))
    projects = get_projects(branch=branch)
    for p in projects:
        if cancelled:
            return
        _api_url = '/projects/{}/branches/{}'.format(urllib.parse.quote(p, safe=''),
                                                     urllib.parse.quote(branch, safe=''))
        if config.noop:
            print('DUMMY_API: DELETE {}'.format(_api_url))
        else:
            print('Removing branch:', branch, 'from:', p, end='\t')
            res = exec_api('DELETE', _api_url)
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


def repo_upload(branch: str, force: bool, no_thin: bool, unshallow: bool, create: bool):
    config.verbose and print('repo_upload, branch:', branch)
    if len(config.manifest_projects) == 0:
        logging.error('No projects specified in manifest')
        sys.exit(1)

    git_args = '-o skip-validation'
    if force:
        git_args += ' -f'
    if no_thin:
        git_args += ' --no-thin'
    for p in config.manifest_projects:
        if cancelled:
            return
        path = config.manifest_projects[p]
        config.verbose and print(p, 'in', path)
        if not os.path.isdir(path):
            config.verbose and logging.warning('Skip, no path')
            continue

        url = '{}/{}'.format(config.GERRIT_SSH_URL, p)
        print(bcolors.header("New upload for: {}".format(url)))

        if unshallow and not config.noop and os.path.isfile(os.path.join(path, ".git/shallow")):
            with open(os.path.join(path, ".git/shallow")) as f:
                commit = f.readline().strip()
                print(bcolors.warn('Found shallow commit: {}'.format(commit)))
                _tmp_branch = 'gerrit_tools-unshallow'
                exec_cmd('git -C {} checkout --orphan {} {}'.format(path, _tmp_branch, commit))
                exec_cmd('git -C {} commit -C {}'.format(path, commit))
                exec_cmd('git -C {} replace {} {}'.format(path, commit, _tmp_branch))
                exec_cmd('git -C {} filter-branch -- --all'.format(path))

        if create and not config.noop:
            _cmd = '{} create-project {} -p {}'.format(config.GERRIT_CMD, p, config.GERRIT_MANIFEST_REPO)
            if config.noop:
                print('DUMMY: {}'.format(_cmd))
            else:
                print('Create project:', exec_cmd(_cmd) is None and bcolors.warn("Can't") or bcolors.ok_green('Ok'))

        exec_cmd('git -C {} gc'.format(path, config.GERRIT_REMOTE))
        remote = exec_cmd('git -C {} config remote.{}.url'.format(path, config.GERRIT_REMOTE), False)
        if remote is not None:
            remote = remote.strip()
        if remote != url:
            if remote is not None:
                config.verbose and print('redefine remote:', remote, '=>', url)
                _cmd = 'git -C {} remote remove {}'.format(path, config.GERRIT_REMOTE)
                if config.noop:
                    print('DUMMY: {}'.format(_cmd))
                else:
                    exec_cmd(_cmd)
            _cmd = 'git -C {} remote add {} {}'.format(path, config.GERRIT_REMOTE, url)
            if config.noop:
                print('DUMMY: {}'.format(_cmd))
            else:
                exec_cmd(_cmd)
        _cmd = 'git -C {} push {} {} HEAD:refs/heads/{}'.format(path, git_args, config.GERRIT_REMOTE, branch)
        if config.noop:
            print('DUMMY: {}'.format(_cmd))
        else:
            print('Push to branch: {} project: {} in: {}'.format(bcolors.ok_cyan(branch), bcolors.ok_blue(p), path))
            print('\t', exec_cmd(_cmd) is None and bcolors.fail('Fail') or bcolors.ok_green('Ok'))


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
            repo_upload(args.new_branch_name, args.force, args.no_thin, args.unshallow, args.create)
        else:
            logging.error('Unknown sub-command: {}'.format(args.sub_command))
            sys.exit(1)
    else:
        logging.error('Unknown command: {}'.format(args.command))
        sys.exit(1)


def signal_handler(signum, frame):
    global cancelled
    cancelled = True
    print(bcolors.warn('Cancelled!!!'), signum)
    sys.exit(1)


signal.signal(signal.SIGINT, signal_handler)
if __name__ == "__main__":
    main()
