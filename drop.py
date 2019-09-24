#!/usr/bin/env python3

"""Download / upload the contents of a file and list files in a folder.

Based on the example app for API v2
@ https://github.com/dropbox/dropbox-sdk-python/blob/master/example/updown.py

For python3

api docs: https://dropbox-sdk-python.readthedocs.io/en/latest/api/dropbox.html

"""

import argparse
import datetime
import os
import time
import json
import dropbox


METADATA_FNAME = 'metadata.json'
verbose = False


def main():
    global verbose

    commands = {
        'download': download_file,
        'upload': upload_file,
        'list': list_folder,
        'remote-path': show_remote_path,
    }

    parser = setup_parser(commands)

    args = parser.parse_args()
    verbose = args.verbose

    cmd = args.command
    if cmd not in commands:
        error('Unrecognized command')

    token = setup_token(args)

    rootdir = os.path.expanduser(args.rootdir)
    setup_rootdir(rootdir)
    dbx = dropbox.Dropbox(token)

    commands[cmd](args, dbx, rootdir)


def setup_parser(commands):
    command_list = '/'.join(commands.keys())

    parser = argparse.ArgumentParser(
        description='Downloads a path in Dropbox to the '
        'local file system')
    parser.add_argument('rootdir', nargs='?',
                        help='Local directory')
    parser.add_argument('--dropbox_path', '-p',
                        help='Path in Dropbox (can be an id)')
    parser.add_argument('--command', '-c',
                        help='Specify the command '
                        f'({command_list}). '
                        '"download" needs the file id. '
                        '"upload" needs the local folder. ')
    parser.add_argument('--refresh', '-e', action='store_true',
                        help='Refresh (if needed) local copy of file')
    parser.add_argument('--recursive', '-r', action='store_true',
                        help='When listing files, do it recursively')
    parser.add_argument('--token_path',
                        help='Path where the access token is stored '
                        '(see https://www.dropbox.com/developers/apps)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Be verbose')

    return parser


def setup_rootdir(rootdir):
    log('Local directory:', rootdir)
    if not os.path.exists(rootdir):
        print(rootdir, 'does not exist, creating it')
        os.mkdir(rootdir)
    elif not os.path.isdir(rootdir):
        error(rootdir, 'is not a folder on your filesystem')


def setup_token(args):
    if not args.token_path:
        error('--token_path is mandatory')
    if not os.path.exists(args.token_path):
        error('Token path doesn\'t exist')
    with open(args.token_path) as file:
        return file.read()


def show_remote_path(args, dbx, rootdir):
    metadata = load_metadata(rootdir)
    print(metadata['path'])


def upload_file(args, dbx, rootdir):
    dropbox_path = args.dropbox_path
    if dropbox_path is None:
        log('Dropbox path not supplied, updating file')
        metadata = load_metadata(rootdir)
        file_id = metadata['id']

        log('Fetching metadata')
        remote_meta = dbx.files_get_metadata(file_id)
        mode = dropbox.files.WriteMode.update(metadata['rev'])
    else:
        file_id = dropbox_path
        mode = dropbox.files.WriteMode.overwrite

    local_path = os.path.join(rootdir, 'data')
    if dropbox_path is None:
        log('Uploading', local_path)
    else:
        log('Uploading', local_path, 'to', dropbox_path)

    mtime = os.path.getmtime(local_path)
    mtime = datetime.datetime(*time.gmtime(mtime)[:6])
    with open(local_path, 'rb') as file:
        data = file.read()

    dbx.files_upload(
        data,
        file_id,
        mode=mode,
        client_modified=mtime,
    )


def download_file(args, dbx, rootdir):
    refresh = args.refresh
    if refresh:
        metadata = load_metadata(rootdir)
        cur_rev = metadata['rev']
        log('Fetching metadata')
        dropbox_path = metadata['id']
        remote_meta = dbx.files_get_metadata(dropbox_path)
        if cur_rev == remote_meta.rev:
            log('Same revision, not updating')
            return
        else:
            log('Remote has newer version, updating')
    else:
        dropbox_path = args.dropbox_path
        check_has_path(dropbox_path)

        if not is_id(dropbox_path):
            error(f'"{dropbox_path}" is not a Dropbox file id')

        log('Fetching metadata')
        remote_meta = dbx.files_get_metadata(dropbox_path)

    metadata = {
        'id': remote_meta.id,
        'path': remote_meta.path_lower,
        'rev': remote_meta.rev,
        'content_hash': remote_meta.content_hash,
    }

    download_path = os.path.join(rootdir, 'data')
    log('Downloading', dropbox_path, 'to', download_path)
    dbx.files_download_to_file(download_path, dropbox_path)

    save_metadata(rootdir, metadata)


def list_folder(args, dbx, rootdir):
    dropbox_path = args.dropbox_path
    check_has_path(dropbox_path)

    log('Listing files in', dropbox_path)
    res = dbx.files_list_folder(dropbox_path, recursive=args.recursive)
    for entry in res.entries:
        try:
            mtime = entry.server_modified
        except AttributeError:
            continue

        datum = [entry.id, entry.path_display, mtime.isoformat()]
        print("\t".join(datum))
    return


def save_metadata(path, metadata):
    metadata_path = os.path.join(path, METADATA_FNAME)
    with open(metadata_path, 'w') as file:
        json.dump(metadata, file)


def load_metadata(path):
    metadata_path = os.path.join(path, METADATA_FNAME)
    with open(metadata_path) as file:
        return json.load(file)


def is_id(s):
    return s.startswith('id:')


def error(s):
    print(s)
    os.sys.exit(1)


def log(*args):
    global verbose

    if verbose:
        print(*args)


def check_has_path(path):
    if path is None:
        error('Dropbox path is needed')


if __name__ == '__main__':
    main()
