# Is the hub up?

https://isthehubup.herokuapp.com/

Check if mybinder.org is up or not. The webserver checks if the main website
responds or not. The real monitoring happens with `isthehubup.py` which
executes roughly every ten minutes. It checks several pages and tries to launch
a binder. It reports by email and gitter.
