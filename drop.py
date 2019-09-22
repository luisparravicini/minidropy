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
import sys
import time
import json
import dropbox


METADATA_FNAME = 'metadata.json'

parser = argparse.ArgumentParser(description='Downloads a path in Dropbox to the local file system')
parser.add_argument('rootdir', nargs='?',
                    help='Local directory')
parser.add_argument('--dropbox_path', '-p',
                    help='Path in Dropbox (can be an id)')
parser.add_argument('--download', '-d', action='store_true',
                    help='Download file (specify file id)')
parser.add_argument('--upload', '-u', action='store_true',
                    help='Upload file specifying '
                    'the path where resides the file and the metadata')
parser.add_argument('--list', '-l', action='store_true',
                    help='List files in dropbox path')
parser.add_argument('--remote_path', '-i', action='store_true',
                    help='Show remote path for downloaded file')
parser.add_argument('--recursive', '-r', action='store_true',
                    help='When listing files, do it recursively')
parser.add_argument('--token_path',
                    help='Path where the access token is stored '
                    '(see https://www.dropbox.com/developers/apps)')
parser.add_argument('--verbose', '-v', action='store_true',
                    help='Be verbose')


def main():
    args = parser.parse_args()

    if not args.list and not args.download and not args.upload and not args.remote_path:
        print('Needs to specify one action (list/download/upload/show remote path)')
        sys.exit(2)

    token = setup_token(args)

    rootdir = os.path.expanduser(args.rootdir)
    setup_rootdir(args, rootdir)
    dbx = dropbox.Dropbox(token)

    if args.list:
        list_folder(args, dbx)
    elif args.download:
        download_file(args, dbx, rootdir)
    elif args.upload:
        upload_file(args, dbx, rootdir)
    elif args.remote_path:
        show_remote_path(args, dbx, rootdir)


def setup_rootdir(args, rootdir):
    if args.verbose:
        print('Local directory:', rootdir)
    if not os.path.exists(rootdir):
        print(rootdir, 'does not exist, creating it')
        os.mkdir(rootdir)
    elif not os.path.isdir(rootdir):
        print(rootdir, 'is not a folder on your filesystem')
        sys.exit(1)


def setup_token(args):
    if not args.token_path:
        print('--token is mandatory')
        sys.exit(2)
    if not os.path.exists(args.token_path):
        print('Token path doesn\'t exist')
        sys.exit(2)
    with open(args.token_path) as file:
        return file.read()


def show_remote_path(args, dbx, rootdir):
    metadata = load_metadata(rootdir)
    print(metadata['path'])


def upload_file(args, dbx, rootdir):
    dropbox_path = args.dropbox_path
    if dropbox_path is None:
        if args.verbose:
            print('Dropbox path not supplied, updating file')
        metadata = load_metadata(rootdir)
        file_id = metadata['id']

        if args.verbose:
            print('Fetching metadata')
        remote_meta = dbx.files_get_metadata(file_id)
        mode = dropbox.files.WriteMode.update(metadata['rev'])
    else:
        file_id = dropbox_path
        mode = dropbox.files.WriteMode.overwrite

    local_path = os.path.join(rootdir, 'data')
    if args.verbose:
        if dropbox_path is None:
            print('Uploading', local_path)
        else:
            print('Uploading', local_path, 'to', dropbox_path)

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
    dropbox_path = args.dropbox_path
    if args.dropbox_path is None:
        print('Dropbox path is needed')
        os.sys.exit(1)

    if not is_id(dropbox_path):
        print(f'"{dropbox_path}" is not a Dropbox file id')
        os.sys.exit(1)

    if args.verbose:
        print('Fetching metadata')
    remote_meta = dbx.files_get_metadata(dropbox_path)
    metadata = {
        'id': remote_meta.id,
        'path': remote_meta.path_lower,
        'rev': remote_meta.rev,
        'content_hash': remote_meta.content_hash,
    }

    download_path = os.path.join(rootdir, 'data')
    if args.verbose:
        print('Downloading', dropbox_path, 'to', download_path)
    dbx.files_download_to_file(download_path, dropbox_path)

    save_metadata(rootdir, metadata)


def list_folder(args, dbx):
    dropbox_path = args.dropbox_path
    if dropbox_path is None:
        print('Dropbox path is needed')
        os.sys.exit(1)

    if args.verbose:
        print('Listing files in', dropbox_path)
    res = dbx.files_list_folder(dropbox_path, recursive=args.recursive)
    for entry in res.entries:
        print(f'{entry.id}\t{entry.path_display}')
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


if __name__ == '__main__':
    main()
