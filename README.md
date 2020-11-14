
`drop.py` is a small script to perform certain operations using the Dropbox API:

- List the contents of certain remote folder. The output is one file per line, and each line lists the file's id, path and server modified time, separated with `\t`.
- Download a file, referenced by it's id. It downloads the file in a local folder, adding a `metadata.json` along with it.
- Upload a file, downloaded beforehand with the `download` option of this script and referenced by it's local path.
- Listing of remote path. Reads `metadata.json` and lists the path of the downloaded file as it's stored in Dropbox.

It needs a token stored in a file. Go to <https://www.dropbox.com/developers/apps> to create an app and then get an access token for it. The app needs the permission "*files.metadata.read*".

All the parameters accepted are listed below:

```
usage: drop.py [-h] [--dropbox_path DROPBOX_PATH] [--command COMMAND]
               [--refresh] [--recursive] [--token_path TOKEN_PATH] [--verbose]
               [rootdir]

Downloads a path in Dropbox to the local file system

positional arguments:
  rootdir               Local directory

optional arguments:
  -h, --help            show this help message and exit
  --dropbox_path DROPBOX_PATH, -p DROPBOX_PATH
                        Path in Dropbox (can be an id)
  --command COMMAND, -c COMMAND
                        Specify the command (download/upload/list/remote-
                        path). "download" needs the file id. "upload" needs
                        the local folder.
  --refresh, -e         Refresh (if needed) local copy of file
  --recursive, -r       When listing files, do it recursively
  --token_path TOKEN_PATH
                        Path where the access token is stored (see
                        https://www.dropbox.com/developers/apps)
  --verbose, -v         Be verbose
```

**Note**: As per the Dropbox api, the root is specified with an empty string.

 The api documentation is at <https://dropbox-sdk-python.readthedocs.io/en/latest/api/dropbox.html>.
 
