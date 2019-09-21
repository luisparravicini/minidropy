#!/usr/bin/env python3

"""Upload the contents of a folder to Dropbox.

Based on the example app for API v2
@ https://github.com/dropbox/dropbox-sdk-python/blob/master/example/updown.py

For python3

api docs: https://dropbox-sdk-python.readthedocs.io/en/latest/api/dropbox.html

@xrm0
"""

import argparse
import datetime
import os
import sys
import time
import json
import unicodedata
import dropbox

# OAuth2 access token.  TODO: login etc.
TOKEN = ''

token_path = 'token.txt'

if os.path.exists(token_path):
    with open(token_path) as file:
        TOKEN = file.read()

parser = argparse.ArgumentParser(description='Downloads a path in Dropbox to the local file system')
parser.add_argument('rootdir', nargs='?',
                    help='Local directory')
parser.add_argument('dropbox_path', nargs='?',
                    help='Path in Dropbox (can be an id)')
parser.add_argument('--download', '-d', action='store_true',
                    help='Download file (specify file id)')
parser.add_argument('--upload', '-u', action='store_true',
                    help='Upload file specifying the path where resides the file and the metadata')
parser.add_argument('--list', '-l', action='store_true',
                    help='List files in dropbox path')
parser.add_argument('--recursive', '-r', action='store_true',
                    help='When listing files, do it recursively')
parser.add_argument('--token', default=TOKEN,
                    help='Access token '
                    '(see https://www.dropbox.com/developers/apps)')
parser.add_argument('--verbose', '-v', action='store_true',
                    help='Be verbose')


def main():
    args = parser.parse_args()
    if not args.token:
        print('--token is mandatory')
        sys.exit(2)
    if not args.list and sum([bool(b) for b in (args.download, args.upload)]) != 1:
        print('Needs to specify --download or --upload')
        sys.exit(2)

    rootdir = os.path.expanduser(args.rootdir)
    if args.verbose:
        print('Local directory:', rootdir)
    if not os.path.exists(rootdir):
        print(rootdir, 'does not exist, creating it')
        os.mkdir(rootdir)
    elif not os.path.isdir(rootdir):
        print(rootdir, 'is not a folder on your filesystem')
        sys.exit(1)

    dropbox_path = args.dropbox_path

    dbx = dropbox.Dropbox(args.token)

    if args.list:
        if args.verbose:
            print('Listing files in', dropbox_path)
        res = dbx.files_list_folder(dropbox_path, recursive=args.recursive)
        for entry in res.entries:
            print(f'{entry.id}\t{entry.path_display}')
        return

    if args.download:
        if not isId(dropbox_path):
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

        return

    if args.upload:
        metadata = load_metadata(dropbox_path)

        file_id = metadata['id']
        if args.verbose:
            print('Fetching metadata')
        remote_meta = dbx.files_get_metadata(file_id)

        local_path = os.path.join(rootdir, 'data')
        if args.verbose:
            print('Uploading', local_path, 'to', dropbox_path)

        mtime = os.path.getmtime(local_path)
        mtime = datetime.datetime(*time.gmtime(mtime)[:6])
        with open(local_path, 'rb') as file:
            data = file.read()

        dbx.files_upload(
            data,
            file_id,
            mode=dropbox.files.WriteMode.update(metadata['rev']),
            client_modified=mtime,
        )

        return


METADATA_FNAME = 'metadata.json'


def save_metadata(path, metadata):
    metadata_path = os.path.join(path, METADATA_FNAME)
    with open(metadata_path, 'w') as file:
        json.dump(metadata, file)


def load_metadata(path):
    metadata_path = os.path.join(path, METADATA_FNAME)
    with open(metadata_path) as file:
        return json.load(file)


def isId(s):
    return s.startswith('id:')


if __name__ == '__main__':
    main()
