#!/usr/bin/env python
'''
GlobusArchiver.py helps users archive data to the Campaign Store (and other Globus Endpoints)
'''


import sys    
if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3.5 or later")
if sys.version_info[0] == 3 and sys.version_info[1] < 5:
    raise Exception("Must be using Python 3.5 or later")


######################
# PYTHON LIB IMPORTS
#####################
import subprocess
import shlex
import os
import json
import time
import webbrowser
import ssl
import threading


##################
# GLOBUS IMPORTS
##################
import globus_sdk


#####################
# CONFIG MASTER STUFF
#####################
import logging

# manage externals
sys.path.append('configmaster')
try:
    from ConfigMaster import ConfigMaster
except  ImportError:
    print(f"{os.path.basename(__file__)} needs ConfigMaster to run.")
    print(f"Plase review README.md for details on how to run manage_externals")
    exit(1)

defaultParams = """

# Imports used in the configuration file
import os
import socket
import datetime

#####################################
## GENERAL CONFIGURATION
#####################################

 
## debug ##

# Email Address
emailAddress = ""


# You can define the endpoint directly  
# This default value is the NCAR CampaignStore 
# the value was obtained by running:
# $ globus endpoint search 'NCAR' --filter-owner-id 'ncar@globusid.org' | grep Campaign | cut -f1 -d'      

archiveEndPoint = "6b5ab960-7bbf-11e8-9450-0a6d4e044368"


# The refresh token is what lets you use globus without authenticating every time.  We store it in a local file.
# !!IMPORTANT!!!
# You need to protect your Refresh Tokens. 
# They are an infinite lifetime credential to act as you.
# Like passwords, they should only be stored in secure locations.
# e.g. placed in a directory where only you have read/write access
globusTokenFile = os.path.join(os.path.expanduser("~"),".globus-ral","refresh-tokens.json")


# This is currently being used to add a date/time to the transfer label of each archive item.  
# In the future GlobusArchiver.py will do substitution on paths, labels, etc. using this value.
archiveDateTime = datetime.datetime.now() - datetime.timedelta(days=2)


# TODO: transfer-args are currently ignored
archiveItems = {
"icing-cvs-data":
       {
       "source": "/d1/prestop/backup/test1",
       "destination": "/gpfs/csfs1/ral/nral0003",
       "transfer-args": "--preserve-mtime",
       "transfer-label": f"icing_cvs_data_{archiveDateTime.strftime('%Y%m%d')}"
       },
"icing-cvs-data2":
       {
       "source": "/d1/prestop/backup/test2",
       "destination": "/gpfs/csfs1/ral/nral0003",
       "transfer-args": "--preserve-mtime",
       "transfer-label": f"icing_cvs_data_{archiveDateTime}"
       }
}

#########################
#  GLOBUS CONFIGURATION
#########################

"""
########################################
# Copied from https://github.com/globus/native-app-examples/blob/master/utils.py
import logging
import os
import ssl
import threading

try:
    import http.client as http_client
except ImportError:
    import httplib as http_client

try:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
except ImportError:
    from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    import Queue
except ImportError:
    import queue as Queue

try:
    from urlparse import urlparse, parse_qs
except ImportError:
    from urllib.parse import urlparse, parse_qs


def enable_requests_logging():
    http_client.HTTPConnection.debuglevel = 4

    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger('requests.packages.urllib3')
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def is_remote_session():
    return os.environ.get('SSH_TTY', os.environ.get('SSH_CONNECTION'))


class RedirectHandler(BaseHTTPRequestHandler):

        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'You\'re all set, you can close this window!')

            code = parse_qs(urlparse(self.path).query).get('code', [''])[0]
            self.server.return_code(code)

        def log_message(self, format, *args):
            return


class RedirectHTTPServer(HTTPServer, object):

    def __init__(self, listen, handler_class, https=False):
        super(RedirectHTTPServer, self).__init__(listen, handler_class)

        self._auth_code_queue = Queue.Queue()

        if https:
            self.socket = ssl.wrap_socket(
                self.socket, certfile='./ssl/server.pem', server_side=True)

    def return_code(self, code):
        self._auth_code_queue.put_nowait(code)

    def wait_for_code(self):
        return self._auth_code_queue.get(block=True)


def start_local_server(listen=('', 4443)):
    server = RedirectHTTPServer(listen, RedirectHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    return server

#####################################
# ConfigMaster 
#####################################
p = ConfigMaster()
p.setDefaultParams(defaultParams)
p.init(__doc__)

########################################################
# global constants
########################################################
CLIENT_ID = "f70debeb-31cc-40c0-8d65-d747641428b4"
REDIRECT_URI = 'https://auth.globus.org/v2/web/auth-code'
SCOPES = ('openid email profile '
          'urn:globus:auth:scope:transfer.api.globus.org:all')

########################################################
# Function definitions
########################################################
def safe_mkdirs(d):
    logging.info(f"making dir: {d}")
    if not os.path.exists(d):
        try:
            os.makedirs(d, 0o700)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            
def run_cmd(cmd):
    '''
    runs a command with blocking

    returns a CompletedProcess instance 
        - you can get to stdout with .stdout.decode('UTF-8').strip('\n') 
    '''
    logging.debug(f"running command: {cmd}")
    
    # I know you shouldn't use shell=True, but splitting up a piped cmd into
    # multiple separate commands is too much work right now.
    # TODO: https://stackoverflow.com/questions/13332268/how-to-use-subprocess-command-with-pipes
    # https://stackoverflow.com/questions/295459/how-do-i-use-subprocess-popen-to-connect-multiple-processes-by-pipes
    if '|' in cmd:
        return subprocess.run(cmd, check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        splitcmd = shlex.split(cmd)
        return subprocess.run(splitcmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # not used.
def handle_configuration():
    if p.opt["archiveEndPoint"] == "":
        #comp_proc = run_cmd(p.opt["archiveEndPointShellCmd"])
        #print(comp_proc)
        # stdout comes back as a series of octets, so decode to a normal string and strip endline
        #EP = comp_proc.stdout.decode('UTF-8').strip('\n')
        #logging.debug(f"Got EndPoint via archiveEndPointShellCmd: {EP}")
        #p.opt["archiveEndPoint"] = EP
        logging.debug("")


def load_tokens_from_file(filepath):
    """Load a set of saved tokens."""
    logging.info(f"Attempting load of tokens from {filepath}")
    with open(filepath, 'r') as f:
        tokens = json.load(f)

    return tokens


def save_tokens_to_file(filepath, tokens):
    """Save a set of tokens for later use."""
    safe_mkdirs(os.path.dirname(filepath))
    logging.info(f"Attempting save of tokens to {filepath}")
    with open(filepath, 'w') as f:
        json.dump(tokens, f)
    # TODO: make sure mode is set restrictively on this file


def update_tokens_file_on_refresh(token_response):
    """
    Callback function passed into the RefreshTokenAuthorizer.
    Will be invoked any time a new access token is fetched.
    """
    save_tokens_to_file(p.opt["globusTokenFile"], token_response.by_resource_server)


def do_native_app_authentication(client_id, redirect_uri,
                                 requested_scopes=None):
    """
    Does a Native App authentication flow and returns a
    dict of tokens keyed by service name.
    """
    client = globus_sdk.NativeAppAuthClient(client_id=client_id)
    # pass refresh_tokens=True to request refresh tokens
    client.oauth2_start_flow(requested_scopes=requested_scopes,
                             redirect_uri=redirect_uri,
                             refresh_tokens=True)

    url = client.oauth2_get_authorize_url()

    print(f'\n\nAuthorization needed.  Please visit this URL:\n{url}\n')

    if not is_remote_session():
        webbrowser.open(url, new=1)

    auth_code = input('Enter the auth code: ').strip()

    token_response = client.oauth2_exchange_code_for_tokens(auth_code)

    # return a set of tokens, organized by resource server name
    return token_response.by_resource_server



# TODO - transfer and everything is happening in here.  Refactor to separate functionality into different methods.
def getTokens():

    tokens = None
    try:
        # if we already have tokens, load and use them
        tokens = load_tokens_from_file(p.opt["globusTokenFile"])
    except:
        pass

    if not tokens:
        # if we need to get tokens, start the Native App authentication process
        tokens = do_native_app_authentication(CLIENT_ID, REDIRECT_URI, SCOPES)

        try:
            save_tokens_to_file(p.opt["globusTokenFile"], tokens)
        except:
            pass

    transfer_tokens = tokens['transfer.api.globus.org']

    auth_client = globus_sdk.NativeAppAuthClient(client_id=CLIENT_ID)

    authorizer = globus_sdk.RefreshTokenAuthorizer(
        transfer_tokens['refresh_token'],
        auth_client,
        access_token=transfer_tokens['access_token'],
        expires_at=transfer_tokens['expires_at_seconds'],
        on_refresh=update_tokens_file_on_refresh)

    transfer = globus_sdk.TransferClient(authorizer=authorizer)

    myproxy_lifetime=720 #in hours.  What's the maximum?
    try:
        r = transfer.endpoint_autoactivate(p.opt["archiveEndPoint"], if_expires_in=3600)
        while (r["code"] == "AutoActivationFailed"):
            print("Endpoint requires manual activation, please use your UCAS name/password for this activation. "
                "You can activate via the command line or via web browser:\n"
                "WEB BROWSER -- Open the following URL in a browser to activate the "
                "endpoint:")
            print(f"https://app.globus.org/file-manager?origin_id={p.opt['archiveEndPoint']}")
            print("CMD LINE -- run this from your shell: ")
            print(f"globus endpoint activate --myproxy --myproxy-lifetime {myproxy_lifetime} {p.opt['archiveEndPoint']}")
            input("Press ENTER after activating the endpoint:")
            r = tc.endpoint_autoactivate(ep_id, if_expires_in=3600)
        
    except globus_sdk.exc.GlobusAPIError as ex:
        print("endpoint_autoactivation failed.")
        print(ex)
        if ex.http_status == 401:
            sys.exit('Refresh token has expired. '
                     'Please delete refresh-tokens.json and try again.')
        else:
            raise ex

    # print out a directory listing from an endpoint
    #print("Looking at archive end point")
    #for entry in transfer.operation_ls(p.opt["archiveEndPoint"], path='/~/'):
    #    print(entry['name'] + ('/' if entry['type'] == 'dir' else ''))

    # revoke the access token that was just used to make requests against
    # the Transfer API to demonstrate that the RefreshTokenAuthorizer will
    # automatically get a new one
    #auth_client.oauth2_revoke_token(authorizer.access_token)
    # Allow a little bit of time for the token revocation to settle
    #time.sleep(1)
    # Verify that the access token is no longer valid
    #token_status = auth_client.oauth2_validate_token(
    #    transfer_tokens['access_token'])
    #assert token_status['active'] is False, 'Token was expected to be invalid.'

    #print('\nDoing a second directory listing with a new access token:')
    #for entry in transfer.operation_ls(p.opt["archiveEndPoint"], path='/~/'):
    #    print(entry['name'] + ('/' if entry['type'] == 'dir' else ''))
    
    local_ep = globus_sdk.LocalGlobusConnectPersonal()
    local_ep_id = local_ep.endpoint_id

    #print("Looking at local end point")
    #for entry in transfer.operation_ls(local_ep_id):
    #    print(f"Local file: {entry['name']}")


    logging.info("BEGINNING PROCESSING OF archiveItems")
    for item,item_info in p.opt["archiveItems"].items():
        logging.info(f"Transferring {item}")
        if not item_info["source"].startswith('/'):
            logging.error(f"{item} source: {item_info['source']} must be absolute.  SKIPPING!")
            continue
        if not item_info["destination"].startswith('/'):
            logging.error(f"{item} source: {item_info['destination']} must be absolute.  SKIPPING!")
            continue
        try:
            transfer.operation_ls(p.opt["archiveEndPoint"], path=item_info["destination"])
        except globus_sdk.exc.TransferAPIError as e:
            logging.fatal(f"Destination path ({item_info['destination']}) does not exist on archiveEndPoint.")
            logging.fatal(e)
            sys.exit(1)

        # get leaf dir from source, and add it to destination
        dirname, leaf = os.path.split(item_info['source'])
        if leaf == '':
            _, leaf = os.path.split(dirname)
        destination_directory = os.path.join(item_info['destination'], leaf) + '/'

        # Check if destination_dir already exists, and skip if so
        # TODO: add support to overwrite?
        try:
            transfer.operation_ls(p.opt["archiveEndPoint"], path=destination_directory)
            logging.error(f"Destination {destination_directory} already exists on archiveEndPoint.  SKIPPING!")
            continue
        except globus_sdk.exc.TransferAPIError as e:
            if e.code != u'ClientError.NotFound':
                logging.fatal(f"Can't ls {p.opt['archiveEndPoint']} : {destination_directory}")
                logging.fatal(e)
                sys.exit(1)
                
        # create destination directory
        try:
            logging.info(f"Creating destination directory {destination_directory}")
            transfer.operation_mkdir(p.opt["archiveEndPoint"], destination_directory)
        except globus_sdk.exc.TransferAPIError as e:
            logging.fatal(f"Can't mkdir {p.opt['archiveEndPoint']} : {destination_directory}")
            logging.fatal(e)
            sys.exit(1)

        # TODO: set permissions for users to read dir
        #       look at https://github.com/globus/automation-examples/blob/master/share_data.py

        #tdata = globus_sdk.TransferData(transfer, local_ep_id, p.opt["archiveEndPoint"], label=item_info["transfer-label"])
        tdata = globus_sdk.TransferData(transfer, local_ep_id, p.opt["archiveEndPoint"])
        tdata.add_item(item_info["source"], destination_directory, recursive=True)
        try:
            logging.info(f"Submitting transfer task - {item_info['transfer-label']}")
            task = transfer.submit_transfer(tdata)
        except globus_sdk.exc.TransferAPIError as e:
            logging.fatal("Transfer task submission failed")
            logging.fatal(e)
            sys.exit(1)
        logging.info(f"Task ID: {task['task_id']}")
        logging.info(f"This task can be monitored via the Web UI: https://app.globus.org/activity/{task['task_id']}")


def main():

    print(f"Starting {os.path.basename(__file__)}")

    logging.info(f"Using this configuration:")
    for line in p.getParamsString().splitlines():
        logging.info(f"\t{line}")
 
    #handle_configuration()

    
    #for item,item_info in p.opt["archiveItems"].items():
    #    print(item)
    #    print (item_info)
        
    #logging.info(f"Using archiveEndPoint: {p.opt['archiveEndPoint']}")

    
    
    getTokens()

    # connect to globus
    #client = globus_sdk.NativeAppAuthClient(CLIENT_ID)
    
    #getGlobusAuthorizer(p, client)
    


   

if __name__ == "__main__":
    main()

