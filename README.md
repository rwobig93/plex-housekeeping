<h1 align="center"> Plex Housekeeping Scripts </h1>
<h3 align="center"> Collection of scripts to manage/cleanup a plex instance </h3>

<hr/>

# Clone the repo

```shell
git clone https://github.com/rwobig93/plex-housekeeping.git
```

<h3 align="center"> Current scripts list </h3>

| Script Name     |          Script Options           |                  Purpose                  |
|:----------------|:---------------------------------:|:-----------------------------------------:|
| plex-cleanup.py | [Options/Details](#plex-cleanup)  | Cleanup collections and movie title names |

# Plex Cleanup

### Configuration

 > NOTE: Running the script for the first time will generate a config file you can modify called `plex-cleanup.json`
 
 > NOTE: All variables below can be used as environment variables by using uppercase using the -e argument on the script

 > NOTE: Using the -c argument for continuous running you can also provide -i <seconds> for the run interval or SCRIPT_INTERVAL as an environment variable

| Setting Name                         |          Example           | Detail                                                                                                                                                                                                                       |
|:-------------------------------------|:--------------------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| plex_url                             | https://192.168.1.1:32400/ | Required: URL pointing to your plex instance, can be public or private                                                                                                                                                       |
| api_key                              |    aBCde12F3gh4IJklmno5    | Required: API key from your Plex.TV account, please see [Finding Plex Token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/) for more details                                      |
| movie_libraries                      |  ["Movies","4K","Hidden"]  | Optional: List of your movie library names, any not included will be skipped                                                                                                                                                 |
| minimum_collection_size              |             2              | Optional: Number indicating collection size for cleanup, collection cleanup will look at any collections with less movies than the number indicated here, so 2 would mean all collections with 1 or 0 movies will be cleaned |
| delete_undersized_collections        |           false            | Optional: Whether to delete collections based on the size indicated, if false then any collections that would be cleaned up will instead be printed to the terminal and logged, if true then collections will be deleted     |
| enforce_movie_names_match_file_names |           false            | Optional: Whether to enforce movie names to match file names after sanitization                                                                                                                                              |
| movie_name_enforce_skip_characters   |    [':', '-', '.', '?']    | Optional: List of characters to ignore when comparing movie title and movie file names for name enforcement                                                                                                                  |
| enforce_movie_names_exclude          |       ['Star Wars']        | Optional: List of movie title names to ignore when enforcing movie title and file names, each entry is case sensitive and checks by doing a 'contains' operation          <br/>                                              |

<h3 align="center">Installing required dependencies</h3>

```shell
pip install -r requirements.txt
```

<h3 align="center">Run the script manually</h3>

```shell
python3 plex-cleanup.py
```

<h3 align="center">Run using docker cli</h3>

### Run in interactive mode
```shell
docker run registry.gitlab.wobigtech.net/public-registry/plex-cleanup:latest -e "PLEX_URL=https://192.168.1.1:32400/" -e "API_KEY=aBCde12F3gh4IJklmno5"
```

### Run in detached mode (non-interactively)
```shell
docker run registry.gitlab.wobigtech.net/public-registry/plex-cleanup:latest -e "PLEX_URL=https://192.168.1.1:32400/" -e "API_KEY=aBCde12F3gh4IJklmno5" -d
```

<h3 align="center">Run using docker-compose</h3>

See [docker-compose.yml](https://gitlab.wobigtech.net/public-registry/plex-cleanup/-/blob/main/example/docker-compose.yml) for a real-world example
