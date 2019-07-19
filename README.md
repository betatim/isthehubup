# Is the hub up?

https://isthehubup.herokuapp.com/

Check if mybinder.org is up or not. The webserver checks if the main website
responds. More extensive monitoring happens with `isthehubup.py` which
executes roughly every ten minutes. It checks several pages and tries to launch
a binder on each cluster. It reports by email and gitter.
