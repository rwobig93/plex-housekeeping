<h1 align="center"> Plex Housekeeping Scripts </h1>
<h3 align="center"> Collection of scripts to manage/cleanup a plex instance </h3>

<hr/>

# Clone the repo

```shell
git clone https://github.com/rwobig93/plex-housekeeping.git
```

<h3> Current scripts list </h3>

| Script Name     |          Script Options           |                        Purpose                         |
|:----------------|:---------------------------------:|:------------------------------------------------------:|
| plex-cleanup.py | [Options/Details](#plex-cleanup)  | Removes movie collections based on current movie count |

# Plex Cleanup

### Configuration

<h4>NOTE: Running the script for the first time will generate a config file you can modify called plex-cleanup-config.json</h3>

| Setting Name                  |          Example           | Detail                                                                                                                                                                                                                       |
|:------------------------------|:--------------------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| plex_url                      | https://192.168.1.1:32400/ | Required: URL pointing to your plex instance, can be public or private                                                                                                                                                       |
| plex_api_key                  |    aBCde12F3gh4IJklmno5    | Required: API key from your Plex.TV account, please see [Finding Plex Token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/) for more details                                      |
| movie_libraries               |  ["Movies","4K","Hidden"]  | Optional: List of your movie library names, any not included will be skipped                                                                                                                                                 |
| minimum_collection_size       |             2              | Optional: Number indicating collection size for cleanup, collection cleanup will look at any collections with less movies than the number indicated here, so 2 would mean all collections with 1 or 0 movies will be cleaned |
| delete_undersized_collections |            true            | Optional: Whether to delete collections based on the size indicated, if false then any collections that would be cleaned up will instead be printed to the terminal and logged, if true then collections will be deleted     |

<h3>Installing required dependencies</h3>

```shell
python -m pip install plexapi
```

<h3>Running the script</h3>

```shell
python plex-cleanup.py
```
