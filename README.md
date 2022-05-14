<h1 align="center"> Plex Housekeeping Scripts </h1>
<h3 align="center"> Collection of scripts to manage/cleanup a plex instance </h3>

<hr/>


<h3> Current scripts list </h3>

| Script Name     |          Script Options           |                        Purpose                         |
|:----------------|:---------------------------------:|:------------------------------------------------------:|
| plex-cleanup.py | [Options/Details](#plex-cleanup)  | Removes movie collections based on current movie count |

# Plex Cleanup

```diff
- NOTE: Running the script for the first time will generate a config file you can modify called plex-cleanup-config.json
```

[//]: # (- is red, + is green, ! is orange, # is gray and @@ surround is purple and bold)

<p> </p>

### Configuration

| Setting Name                  | Required | Default    |           Example           | Detail                                                                                                                                                                                                             |
|:------------------------------|----------|------------|:---------------------------:|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| plex_url                      | Required |            | https://192.168.0.50:32400/ | URL pointing to your plex instance, can be public or private                                                                                                                                                       |
| plex_api_key                  | Required |            |    aBCde12F3gh4IJklmno5     | API key from your Plex.TV account, please see [Finding Plex Token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/) for more details                                      |
| movie_libraries               | Optional | ["Movies"] |  ["Movies","4K","Hidden"]   | List of your movie library names, any not included will be skipped                                                                                                                                                 |
| minimum_collection_size       | Optional | 2          |              1              | Number indicating collection size for cleanup, collection cleanup will look at any collections with less movies than the number indicated here, so 2 would mean all collections with 1 or 0 movies will be cleaned |
| delete_undersized_collections | Optional | false      |            true             | Whether to delete collections based on the size indicated, if false then any collections that would be cleaned up will instead be printed to the terminal and logged, if true then collections will be deleted     |

<h3>Installing required dependencies</h3>

```shell
python -m pip install plexapi
```

<h3>Running the script</h3>

```shell
python plex-cleanup.py
```
