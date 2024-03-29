# GlobusArchiver
Python utility to archive local data via Globus (originally designed for the Campaign Store), but could be used with
any globus endpoint.  GlobusArchiver.py is in the [Alpha phase](https://en.wikipedia.org/wiki/Software_release_life_cycle#Alpha), and is ready for experimentation by early-adopters. A beta release is planned for the end of June.

## Requires
* Python 3
* ConfigMaster  (installed via manage_externals -- see instructions below)
* A personal globus account


# Creating a Globus Account
You can find [instructions for creating a personal globus account on the CISL website](https://www2.cisl.ucar.edu/resources/storage-and-file-systems/globus-file-transfers).  

# Installing

## Installing the Globus CLI and globusconnectpersonal

You will need these installed to start your own local endpoint.  I had SNAT install them in:
* /opt/globusconnectpersonal-2.3.6/globusconnectpersonal
* /opt/bin/globus

The instructions that follow assume these two programs are in your path.  A "quickstart guide" to using Globus Connect Personal is given below, but you can also find more [information about Globus Connect Personal online](https://www.globus.org/globus-connect-personal).

## Installing the Globus Python SDK
To run GlobusArchiver.py, you will need the Globus Python SDK installed.

As long as you have write permissions in your python3 environment, you can install it yourself using pip.  Instructions online are straightforward:
https://globus-sdk-python.readthedocs.io/en/stable/installation/


## Installing GlobusArchiver

After you have cloned the GlobusArchiver repository, you can run checkout_externals to get any external dependencies:

To get the required dependencies, run the following:
./manage_externals/checkout_externals


# Using the GlobusArchiver

## Configure your local accesible directories

You will need to edit ~/.globusonline/lta/config-paths to configure which local directories are accessible via your personal endpoint.  [Details are online.](https://docs.globus.org/faq/globus-connect-endpoints/#how_do_i_configure_accessible_directories_on_globus_connect_personal_for_linux)

## Create your local endpoint
You only need to do this once.  Once you have your local endpoint created it persists.  You can check to see if you have a global endpoint already using the globus endpoint search:
```
globus endpoint search --filter-scope my-endpoints
```

You need to "create", "setup" and then "start" your endpoint:
```
# set this to whatever you want - I am using the name of the machine I am on.
export LOCAL_EP_NAME=$(uname -n)

globus login --no-local-server

# storing this output in a log file for ease of grepping later
globus endpoint create --personal $LOCAL_EP_NAME > local_endpoint.log

# get local setup ID, and local endpoint ID
export LOCAL_SETUP_ID=$(grep Setup local_endpoint.log | rev | cut -f1 -d' ' | rev)
export LOCAL_EP_ID=$(globus endpoint search $LOCAL_EP_NAME | grep $LOCAL_EP_NAME | cut -f1 -d' ')

# setup local personal endpoint
globusconnectpersonal  -setup $LOCAL_SETUP_ID
 
# start the GCP server
globusconnectpersonal -start &
```

You can check that your local endpoint is working:
```
globus ls ${LOCAL_EP_ID}:/path/to/local/files
```

## Running GlobusArchiver.py
First you will want to use the "print_params" argument to create a default configuration file for GlobusArchiver.py

```
GlobusArchiver.py --print_params > GlobusArchiver_my_project.py
```

Now edit your configuration file.  You will likely need to edit the archive-items dictionary.

Finally run GlobusArchiver.py with your configuration file.  The first time you run GlobusArchiver.py, I recommmend you run interactively from the command line, and redirect the log to a file.  This will help keep debug and status message from obscuring prompts for authentication.

```
GlobusArchiver.py -c GlobusArchiver_my_project.py -l MyArchive.log -d DEBUG
```

You will probably get prompted to both authenticate your globus account and activate with the Campaign Store endpoint.  Once you do this the first time, you should not need to do it for 6 months.

# Troubleshooting

# TODO / Wishlist
Note, that not all of these will necessarily get done.

* Move these TODO's to github issues
* Test with directories, instead of files & recursive directories, and add examples to the default param file.
* Add summary emails
* email user if globus authentication/activation fails
* Check expected num files / expected file size?
* Add relative path to transfers
* Add ability to tar and/or zip prior to transfer
* Add staging area in case files don't want to get TAR'd zipped in place.
* Add ability to put multiple different targets into the same tar file.
* Add database of meta-data?
* Add setting of mode of files upon transfer
* Add tar TOC creation/transfer?
* Add force overwrite, or don't overwrite?  (what does it do now?)
