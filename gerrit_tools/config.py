import argparse
import os
import sys
import logging
from pathlib import Path
from gerrit_tools import bcolors

config: dict = {}
_PKG = 'gerrit_tools'
_DEFAULT_SKIP = 'platform/manifest'
_DEFAULT_MANIFEST = '.repo/manifest.xml'
_CONFIG_DIR = str(Path.home()) + os.sep + '.config' + os.sep + _PKG
_CONFIG_FILE = _CONFIG_DIR + os.sep + 'config'
if not os.path.isdir(_CONFIG_DIR):
    os.mkdir(_CONFIG_DIR)
if not os.path.isfile(_CONFIG_FILE):
    descriptor = os.open(
        path=_CONFIG_FILE,
        flags=(
                os.O_WRONLY  # access mode: write only
                | os.O_CREAT  # create if not exists
                | os.O_TRUNC  # truncate the file to zero
        ),
        mode=0o600
    )
    with open(descriptor, 'w+'):
        pass
with open(_CONFIG_FILE, 'r+') as rf:
    for line in rf.readlines():
        (k, v) = line.split('\t')
        config[k.strip()] = v.strip()


def save():
    with open(_CONFIG_FILE, 'w') as wf:
        for key in config:
            wf.write('{}\t{}\n'.format(key, config[key]))


def get_val(key: str):
    if key in config:
        return config[key]
    val = input('Enter value for {}: '.format(key))
    config[key] = val
    save()
    return val


GERRIT_URL = get_val('GERRIT_URL')
GERRIT_PORT = get_val('GERRIT_PORT')
GERRIT_USER = get_val('GERRIT_USER')
GERRIT_API_TOKEN = get_val('GERRIT_API_TOKEN')
GERRIT_CMD = 'ssh -p {} -l {} {} gerrit'.format(GERRIT_PORT, GERRIT_USER, GERRIT_URL)
GERRIT_SSH_URL = 'ssh://{}@{}:{}'.format(GERRIT_USER, GERRIT_URL, GERRIT_PORT)
GERRIT_REMOTE = GERRIT_URL.replace('.', '_')

skip_projects = []
manifest: str
manifest_projects = []
verbose: bool
cwd: str


def add_project_list_limiting_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        '-s', '--skip', nargs='+', default='platform/manifest', help='skip projects, default: ' + _DEFAULT_SKIP)
    parser.add_argument(
        '-m', '--manifest', type=str, required=False, default=_DEFAULT_MANIFEST,
        help='use manifest file to limit project list, default: ' + _DEFAULT_MANIFEST)
    parser.add_argument(
        '-t', '--manifest-tag', choices=['project', 'remove-project'], default='project',
        help='tag, from where project name obtained, default: project')


def parse_args():
    parser = argparse.ArgumentParser(description='CI repo/git tools.')
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='verbose output')
    parser.add_argument(
        '-V', '--version', action='version')
    parser.add_argument(
        '-C', '--cwd', type=str, default=os.getcwd(), help='change working directory')

    # Sub commands:
    subparsers = parser.add_subparsers(dest='command', help='Sub-commands', required=True)

    ##
    # Branch manipulations
    #
    parser_branch = subparsers.add_parser(
        'branch', aliases='b', help='Manipulate branches')
    parser_branch = parser_branch.add_subparsers(dest='sub_command', help='Sub commands', required=True)
    #   Copy
    parser_branch_cmd = parser_branch.add_parser('copy', aliases='c', help='Copy existing branch to a new one')
    parser_branch_cmd.add_argument(
        'source', type=str, help='Source branch name')
    parser_branch_cmd.add_argument(
        'destination', type=str, help='Destination branch name')
    parser_branch_cmd.add_argument(
        '-f', '--fallback-source', type=str, default=None, help='fallback source branch, if <source> does not exist')
    add_project_list_limiting_args(parser_branch_cmd)
    #   Delete
    parser_branch_cmd = parser_branch.add_parser('delete', aliases='d', help='Delete existing branch')
    parser_branch_cmd.add_argument(
        'name', type=str, help='Branch name')
    add_project_list_limiting_args(parser_branch_cmd)
    #   List
    parser_branch_cmd = parser_branch.add_parser('list', aliases='l', help='List projects, containing branch')
    parser_branch_cmd.add_argument(
        'name', type=str, help='Branch name')
    add_project_list_limiting_args(parser_branch_cmd)
    ##

    ##
    # Repo manipulations
    #
    parser_repo = subparsers.add_parser(
        'repo', aliases='r', help='Bulk manipulation based on deployed repo projects')
    parser_repo = parser_repo.add_subparsers(dest='sub_command', help='Sub commands', required=True)
    #   Upload to branch
    parser_repo_cmd = parser_repo.add_parser(
        'upload', aliases='u', help='Upload to new branch, creating remote {} if absent'.format(GERRIT_REMOTE))
    parser_repo_cmd.add_argument(
        'new_branch_name', type=str, help='Branch name, where to upload all repo projects')
    add_project_list_limiting_args(parser_repo_cmd)
    ##

    try:
        args = parser.parse_args()
    except AttributeError:
        import platform
        import pkg_resources
        dist = pkg_resources.get_distribution(_PKG)
        parser.version = '{} (Python {})'.format(bcolors.bold(str(dist)), platform.python_version())
        args = parser.parse_args()

    global verbose
    verbose = args.verbose
    global cwd
    cwd = args.cwd
    global skip_projects
    skip_projects = args.skip
    global manifest_projects
    if args.manifest is not None:
        tag = args.manifest_tag
        global manifest
        if os.path.isfile(args.manifest):
            manifest = args.manifest
        else:
            manifest = cwd.rstrip(os.sep) + os.sep + args.manifest
        if not os.path.isfile(manifest):
            if args.manifest == _DEFAULT_MANIFEST:
                logging.debug('Manifest', args.manifest, 'not found in', cwd)
                verbose and print(bcolors.warn('Manifest {} not found in {}'.format(args.manifest, cwd)))
            else:
                logging.debug('Manifest', args.manifest, 'not found in', cwd)
        else:
            import xml.etree.ElementTree as ET

            def recursive_read_manifest(m_file: str):
                verbose and print('Read tag <{}> in manifest:'.format(tag), m_file)
                tree = ET.parse(m_file)
                root = tree.getroot()
                if root.tag == 'manifest':
                    for child in root:
                        if child.tag == tag:
                            p = child.attrib['name']
                            if p not in manifest_projects:
                                manifest_projects.append(p)
                        elif child.tag == 'include':
                            file = cwd.rstrip(os.sep) + os.sep + '.repo/manifests/' + child.attrib['name']
                            recursive_read_manifest(file)
                else:
                    logging.error('Invalid manifest: {}'.format(args.manifest))
                    sys.exit(1)
            recursive_read_manifest(manifest)
            logging.debug('Filter projects: {}'.format(manifest_projects))
    return args
