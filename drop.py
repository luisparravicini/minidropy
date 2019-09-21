#!/usr/bin/env python3

"""Upload the contents of a folder to Dropbox.

Based on the example app for API v2
@ https://github.com/dropbox/dropbox-sdk-python/blob/master/example/updown.py

For python3

api docs: https://dropbox-sdk-python.readthedocs.io/en/latest/api/dropbox.html

@xrm0
"""

from __future__ import print_function

import argparse
import contextlib
import datetime
import os
import sys
import time
import json
import unicodedata
import dropbox
from pathlib import Path

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
                    help='Upload files')
parser.add_argument('--list', '-l', action='store_true',
                    help='List files in dropbox path')
parser.add_argument('--recursive', '-r', action='store_true',
                    help='When listing files, do it recursively')
parser.add_argument('--token', default=TOKEN,
                    help='Access token '
                    '(see https://www.dropbox.com/developers/apps)')
parser.add_argument('--yes', '-y', action='store_true',
                    help='Answer yes to all questions')
parser.add_argument('--no', '-n', action='store_true',
                    help='Answer no to all questions')
parser.add_argument('--default', '-D', action='store_true',
                    help='Take default answer on all questions')
parser.add_argument('--verbose', '-v', action='store_true',
                    help='Be verbose')


def main():
    """Main program.

    Parse command line, then iterate over files and directories under
    rootdir and upload all files.  Skips some temporary files and
    directories, and avoids duplicate uploads by comparing size and
    mtime with the server.
    """
    args = parser.parse_args()
    if sum([bool(b) for b in (args.yes, args.no, args.default)]) > 1:
        print('At most one of --yes, --no, --default is allowed')
        sys.exit(2)
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
            'path': remote_meta.path_lower
        }

        download_path = os.path.join(rootdir, 'data')
        if args.verbose:
            print('Downloading', dropbox_path, 'to', download_path)
        dbx.files_download_to_file(download_path, dropbox_path)

        save_metadata(rootdir, metadata)

        return

    if args.upload:
        if args.verbose:
            print('Fetching metadata from', dropbox_path)

        remote_meta = dbx.files_get_metadata(dropbox_path)
        fname = remote_meta.id

        download_path = os.path.join(rootdir, fname)
        if args.verbose:
            print('Downloading', dropbox_path, 'to', download_path)
        dbx.files_download_to_file(download_path, dropbox_path)
        return




    return 

    for dn, dirs, files in os.walk(rootdir):
        subfolder = dn[len(rootdir):].strip(os.path.sep)
        listing = list_folder(dbx, folder, subfolder)
        if args.verbose:
            print('Descending into', subfolder, '...')

        # First do all the files.
        for name in files:
            fullname = os.path.join(dn, name)
            if not isinstance(name, six.text_type):
                name = name.decode('utf-8')
            nname = unicodedata.normalize('NFC', name)
            if name.startswith('.'):
                print('Skipping dot file:', name)
                continue

            if nname in listing:
              md = listing[nname]
              mtime = os.path.getmtime(fullname)
              mtime_dt = datetime.datetime(*time.gmtime(mtime)[:6])
              size = os.path.getsize(fullname)
              if (isinstance(md, dropbox.files.FileMetadata) and
                      mtime_dt == md.client_modified and size == md.size):
                  print(name, 'is already synced [stats match]')
              else:
                  print(name, 'exists with different stats, downloading')
                  res = download(dbx, folder, subfolder, name)
                  print(res)
                  with open(fullname) as f:
                      data = f.read()
                  if res == data:
                      print(name, 'is already synced [content match]')
                  else:
                      print(name, 'has changed since last sync')
                      if yesno('Refresh %s' % name, False, args):
                          upload(dbx, fullname, folder, subfolder, name,
                                 overwrite=True)
            elif yesno('Upload %s' % name, True, args):
                upload(dbx, fullname, folder, subfolder, name)

        # Then choose which subdirectories to traverse.
        keep = []
        for name in dirs:
            if name.startswith('.'):
                print('Skipping dot directory:', name)
            elif yesno('Descend into %s' % name, True, args):
                print('Keeping directory:', name)
                keep.append(name)
            else:
                print('OK, skipping directory:', name)
        dirs[:] = keep


def save_metadata(path, metadata):
    metadata_path = os.path.join(path, 'metadata.json')
    with open(metadata_path, 'w') as file:
        file.write(json.dumps(metadata))

def list_folder(dbx, folder, subfolder):
    """List a folder.

    Return a dict mapping unicode filenames to
    FileMetadata|FolderMetadata entries.
    """
    path = '/%s/%s' % (folder, subfolder.replace(os.path.sep, '/'))
    while '//' in path:
        path = path.replace('//', '/')
    path = path.rstrip('/')
    try:
        with stopwatch('list_folder'):
            res = dbx.files_list_folder(path)
    except dropbox.exceptions.ApiError as err:
        print('Folder listing failed for', path, '-- assumed empty:', err)
        return {}
    else:
        rv = {}
        for entry in res.entries:
            rv[entry.name] = entry
        return rv

def download(dbx, folder, subfolder, name):
    """Download a file.

    Return the bytes of the file, or None if it doesn't exist.
    """
    path = '/%s/%s/%s' % (folder, subfolder.replace(os.path.sep, '/'), name)
    while '//' in path:
        path = path.replace('//', '/')
    with stopwatch('download'):
        try:
            md, res = dbx.files_download(path)
        except dropbox.exceptions.HttpError as err:
            print('*** HTTP error', err)
            return None
    data = res.content
    print(len(data), 'bytes; md:', md)
    return data

def upload(dbx, fullname, folder, subfolder, name, overwrite=False):
    """Upload a file.

    Return the request response, or None in case of error.
    """
    path = '/%s/%s/%s' % (folder, subfolder.replace(os.path.sep, '/'), name)
    while '//' in path:
        path = path.replace('//', '/')
    mode = (dropbox.files.WriteMode.overwrite
            if overwrite
            else dropbox.files.WriteMode.add)
    mtime = os.path.getmtime(fullname)
    with open(fullname, 'rb') as f:
        data = f.read()
    with stopwatch('upload %d bytes' % len(data)):
        try:
            res = dbx.files_upload(
                data, path, mode,
                client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                mute=True)
        except dropbox.exceptions.ApiError as err:
            print('*** API error', err)
            return None
    print('uploaded as', res.name.encode('utf8'))
    return res

def yesno(message, default, args):
    """Handy helper function to ask a yes/no question.

    Command line arguments --yes or --no force the answer;
    --default to force the default answer.

    Otherwise a blank line returns the default, and answering
    y/yes or n/no returns True or False.

    Retry on unrecognized answer.

    Special answers:
    - q or quit exits the program
    - p or pdb invokes the debugger
    """
    if args.default:
        print(message + '? [auto]', 'Y' if default else 'N')
        return default
    if args.yes:
        print(message + '? [auto] YES')
        return True
    if args.no:
        print(message + '? [auto] NO')
        return False
    if default:
        message += '? [Y/n] '
    else:
        message += '? [N/y] '
    while True:
        answer = input(message).strip().lower()
        if not answer:
            return default
        if answer in ('y', 'yes'):
            return True
        if answer in ('n', 'no'):
            return False
        if answer in ('q', 'quit'):
            print('Exit')
            raise SystemExit(0)
        if answer in ('p', 'pdb'):
            import pdb
            pdb.set_trace()
        print('Please answer YES or NO.')

def isId(s):
    return s.startswith('id:')

@contextlib.contextmanager
def stopwatch(message):
    """Context manager to print how long a block of code took."""
    t0 = time.time()
    try:
        yield
    finally:
        t1 = time.time()
        print('Total elapsed time for %s: %.3f' % (message, t1 - t0))

if __name__ == '__main__':
    main()
