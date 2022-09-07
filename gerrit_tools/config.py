import argparse
import os
from pathlib import Path

config: dict = {}
_CONFIG_DIR = str(Path.home()) + os.sep + '.config' + os.sep + 'gerrit_tools'
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


def add_project_list_limiting_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        '--skip', nargs='+', default='platform/manifest', help='Skip projects, default: platform/manifest')
    parser.add_argument(
        '--manifest', type=str, help='Use manifest to limit project list')
    parser.add_argument(
        '--manifest-tag', choices=['project', 'remove-project'], default='project',
        help='Tag, from where project name obtained, default: project')


def parse_args():
    parser = argparse.ArgumentParser(description='CI repo/git tools.')

    # Sub commands:
    subparsers = parser.add_subparsers(dest='command', help='Sub-commands', required=True)

    ##
    # Branch manipulations
    #
    parser_branch = subparsers.add_parser(
        'branch', aliases='b', help='Manipulate branches')
    parser_branch = parser_branch.add_subparsers(
        dest='sub_command', help='Sub commands', required=True)
    #   Copy
    parser_branch_copy = parser_branch.add_parser('copy', aliases='c', help='Copy existing branch to a new one')
    parser_branch_copy.add_argument(
        'source', type=str, help='Source branch name')
    parser_branch_copy.add_argument(
        'destination', type=str, help='Destination branch name')
    parser_branch_copy.add_argument(
        '--fallback-source', type=str, default=None, help='Fallback source branch, if <source> does not exist')
    add_project_list_limiting_args(parser_branch_copy)
    #   Delete
    parser_branch_copy = parser_branch.add_parser('delete', aliases='d', help='Delete existing branch')
    parser_branch_copy.add_argument(
        'name', type=str, help='Branch name')
    add_project_list_limiting_args(parser_branch_copy)
    ##

    ##
    # Dummy?
    #
    parser_d = subparsers.add_parser('dummy', help='Dummy help')
    parser_d.add_argument('--foo', choices=['one', 'two'], help='foo help')
    ##

    return parser.parse_args()
