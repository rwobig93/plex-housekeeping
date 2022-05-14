<h1 align="center"> Plex Housekeeping Scripts </h1>
<h3 align="center"> Collection of scripts to manage/cleanup a plex instance </h3>

<hr/>


<h3> Current scripts list </h3>

| Script Name     |          Script Options           |                         Purpose                         |
|:----------------|:---------------------------------:|:-------------------------------------------------------:|
| plex-cleanup.py | [Options/Details](#plex-cleanup)  | Removes movie collections based on current member count |

# Plex Cleanup
```diff
- text in red
+ text in green
! text in orange
# text in gray
@@ text in purple (and bold)@@
```
<p>NOTE: Running the script for the first time will generate a config file you can modify called </p>
<h3>Configuration</h3>

<h3>Installing required dependencies</h3>
```shell
python -m pip install plexapi
```

<h3>Running the script</h3>
```shell
python plex-cleanup.py
```
