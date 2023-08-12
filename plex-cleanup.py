# region Imports


import json
import logging
import os.path
import re

import urllib3
import sys
from enum import Enum
from dataclasses import dataclass, field, asdict
from os.path import exists

import requests
from plexapi.server import PlexServer, Collection, Library
from plexapi.video import Movie


# endregion
# region Classes


@dataclass
class BaseClass:
    def to_dict(self):
        return asdict(self)


class LogContentType(Enum):
    STRING = 'string'
    JSON = 'json'


@dataclass(init=True, repr=True)
class ScriptSettings(BaseClass):
    plex_url: str
    api_key: str
    movie_libraries: list[str] = field(default_factory=lambda: ['Movies'])
    collection_size_minimum: int = 2
    delete_undersized_collections: bool = False
    enforce_movie_names_match_file_names: bool = False
    movie_name_enforce_skip_characters: list['str'] = field(default_factory=lambda: [':', '-', '.', '?'])
    enforce_movie_names_exclude: list['str'] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.plex_url) < 1:
            raise ValueError('URL provided is empty, please provide a valid plex URL')
        if len(self.api_key) < 1:
            raise ValueError('API provided is empty, please provide a valid plex API key')


# endregion
# region Globals


SETTINGS: ScriptSettings
PLEX_INSTANCE: PlexServer
FILE_ENCODING = 'utf-8'


# endregion
# region Functions
# region Script Control


def get_running_script_name() -> str:
    script_path = os.path.abspath(__file__)
    return str(os.path.basename(script_path)).replace('.py', '')


def configure_logging() -> None:
    """ Configure the application logger """
    path_log_file = f"{get_running_script_name()}.log"
    loglevel = logging.INFO

    if exists('./debug'):
        loglevel = logging.DEBUG

    logging.basicConfig(filename=path_log_file, encoding=FILE_ENCODING, level=loglevel, format='%(asctime)s::%(levelname)s:%(message)s')
    logging.info('Logger initialized!')


def stop_running_script(message: str, exception: Exception = None, error_code: int = 1) -> None:
    """ Stop the running script with the provided message, exception and error code """
    if isinstance(exception, Exception):
        full_message = ("Script was stopped due to a critical failure =>"
                        f"\n  {message} =>\n    {exception} =>\n      {exception.with_traceback}")
    else:
        full_message = f"Script was stopped due to a critical failure =>\n  {message}"

    logging.critical(full_message)
    print(full_message)

    script_exit(error_code)


def error_occurred(message: str, exception: Exception = None) -> None:
    """ Convey error occurrence with the provided error message and exception if one is provided """
    if isinstance(exception, Exception):
        full_message = f"{message} =>\n  {exception} =>\n    {exception.with_traceback}"
        logging.error(full_message)
        print(full_message)
    else:
        print(message)


def print_and_log_message(message: object, content_type: LogContentType = LogContentType.STRING) -> None:
    """ Print and log the provided message """
    content = str(message) if content_type == LogContentType.STRING else json.dumps(message, indent=4, default=str)

    logging.info(content)
    print(content)


def create_config_file() -> None:
    """ Creates a default config file for modification """
    path_config_file = f"{get_running_script_name()}.json"

    try:

        if exists(path_config_file):
            os.remove(path_config_file)
            logging.info(f"Deleted existing config file: {path_config_file}")

        logging.debug(f"Attempting to create default config file at: {os.path.abspath(path_config_file)}")

        with open(path_config_file, 'w', encoding=FILE_ENCODING) as config_writer:
            json.dump(
                ScriptSettings('https://plex-ip-or-hostname:32400/', '<insert_api_key_here>').to_dict(), config_writer)

        logging.debug(f"Created default config file at: {os.path.abspath(path_config_file)}")
    except Exception as ex:
        stop_running_script(
            f"Error occurred attempting to create config file at {os.path.abspath(path_config_file)}", ex)


def load_config_file() -> None:
    """ Loads the script config file """
    path_config_file = f"{get_running_script_name()}.json"

    logging.debug(f"Attempting to read config file: {path_config_file}")
    try:
        if exists(path_config_file):
            logging.info(f"Config file exists at {path_config_file}")
        else:
            create_config_file()
            return_message = f"Config file wasn't found, created a new one at: {os.path.abspath(path_config_file)}"
            print(return_message)
            logging.info(return_message)
            exit(0)
        with open(path_config_file, 'r', encoding=FILE_ENCODING) as config_reader:
            loaded_config = json.load(config_reader)
            global SETTINGS
            SETTINGS = ScriptSettings(**loaded_config)
    except Exception as ex:
        stop_running_script(f"Failure occurred attempting to load the config file: {path_config_file}", ex)


def script_startup() -> None:
    configure_logging()
    print_and_log_message("Starting script execution")

    load_config_file()


def script_exit(error_code: int = 0) -> None:
    print_and_log_message('Finished script execution')

    sys.exit(error_code)


# endregion
# region Script Core


def connect_to_plex_instance(plex_url: str, plex_key: str) -> None:
    """ Connect to the specified plex url and auth with the provided api key and return the instance object """
    try:
        logging.info(f"Attempting to connect to plex instance at: {plex_url}")

        session = requests.Session()
        session.verify = False
        urllib3.disable_warnings()

        global PLEX_INSTANCE
        PLEX_INSTANCE = PlexServer(plex_url, plex_key, session=session)

        logging.info(f"Successfully connected to plex instance at: {plex_url}")
    except Exception as ex:
        stop_running_script("Failure occurred attempting to connect to the provided plex url", ex)


def get_movie_collections(movie_libraries: list[str], collection_size_minimum: int) -> list[Collection]:
    """ Return all movie collections from the connected plex instance, filters collections based on the minimum collection size provided in the config file """
    collection_count_total = 0
    collection_filtered_list: list[Collection] = []
    collection_size_min = collection_size_minimum
    for movie_library in movie_libraries:
        try:
            logging.debug(f"Attempting to load collections from movie library: {movie_library}")

            collections = PLEX_INSTANCE.library.section(movie_library).search(libtype='collection')
            print_and_log_message(f"Library [{movie_library}] has a collection count of [{len(collections)}]")

            logging.debug(f"Successfully grabbed movie library [{movie_library}], attempting to enumerate [{len(collections)}] collections")

            for collection in collections:
                logging.debug(f"Enumerating collection, validating size: [collection_name]{collection.title}"
                              f" [collection_members]{collection.childCount} [member_minimum]{collection_size_min}")

                collection_count_total += 1

                if collection_size_min > -1 and collection.childCount < collection_size_min:
                    logging.debug(f"Found movie collection matching provided criteria, appending to master list: {collection.title}")
                    collection_filtered_list.append(collection)
        except Exception as ex:
            error_occurred("Failure occurred attempting to parse move library", ex)

    print_and_log_message(f"Total filtered collections: {len(collection_filtered_list)}")
    print_and_log_message(f"Total collection count enumerated: {collection_count_total} from {len(movie_libraries)} libraries")
    return collection_filtered_list


def _delete_movie_collection(collection: Collection) -> None:
    """ Delete the provided movie collection from the connected plex instance """
    try:
        collection_name = collection.title
        logging.debug(f"Attempting to delete moving collection: {collection_name}")
        collection.delete()
        logging.info(f"Deleted movie collection: {collection_name}")
    except Exception as ex:
        error_occurred(f"Failure occurred attempting to delete the provided collection: {collection.title}", ex)


def take_action_on_movie_collections(collections: list[Collection], delete_undersized_collections: bool = False) -> None:
    """ Deletes or conveys the provided movie collections list """
    for collection in collections:
        if delete_undersized_collections:
            _delete_movie_collection(collection)
        else:
            print_and_log_message(f"We would delete this undersized movie collection: {collection.title}")


def get_all_movies(movie_libraries: list[str]) -> list[Movie]:
    all_movies = []

    for library in movie_libraries:
        try:
            movie_library: Library = PLEX_INSTANCE.library.section(library)
            library_movies: list[Movie] = movie_library.search(libtype='movie')

            all_movies.extend(library_movies)
            logging.debug(f"Gathered {len(library_movies)} movies from the {library} library")
        except Exception as ex:
            logging.error(f"Error occurred attempting to parse {library} movies: {ex}")

    logging.info(f"Found a total of {len(all_movies)} movies from targeted libraries")
    return all_movies


def _sanitize_movie_name_for_file_match(movie_title: str, sanitize_pattern: str):
    return re.sub(sanitize_pattern, "", movie_title).strip()


def ensure_movie_name_matches_file(movies: list[Movie], make_changes: bool, characters_to_skip_for_match: list[str]) -> None:
    logging.debug("Starting movie file and name match enforcement")
    fixed_movie_count = 0
    movie_title_sanitize_pattern = "|".join(map(re.escape, characters_to_skip_for_match))

    for movie in movies:
        # Verify provided exclude filters, if any are inside teh title of the movie we'll skip it
        if any(exclude_name in movie.title for exclude_name in SETTINGS.enforce_movie_names_exclude):
            logging.debug(f"Skipping matching movie in provided exclude list: {movie.title}")
            continue

        # Get the file name and discard the file extension of the movie
        file_name, _ = os.path.splitext(os.path.basename(movie.media[0].parts[0].file))

        # Extract and trim movie name | Movies have the year in the name following this format: movie name (movie_year).extension
        file_movie_name = str(file_name).split('(')[0].strip()

        logging.debug(f"Movie: {movie.title} | File: {file_movie_name}")
        sanitized_title_name = _sanitize_movie_name_for_file_match(movie.title, movie_title_sanitize_pattern)
        sanitized_file_name = _sanitize_movie_name_for_file_match(file_movie_name, movie_title_sanitize_pattern)

        # Sanitized movie and file names match, so we'll move on
        if sanitized_title_name == sanitized_file_name:
            continue

        logging.debug(f"Sanitized movie name doesn't match file name: {movie.title} != {file_movie_name}")

        if make_changes:
            movie.edit(**{"title.value": sanitized_file_name, "titleSort.value": sanitized_file_name})
            fixed_movie_count += 1
            logging.info(f"Updated Movie Title & Sort Title: {movie.title} => {sanitized_file_name}")

    print_and_log_message(f"Finished movie name enforcement, fixed {fixed_movie_count} movies")

# endregion
# endregion


def main():
    """ Main script execution point """
    script_startup()

    connect_to_plex_instance(SETTINGS.plex_url, SETTINGS.api_key)

    movie_collections = get_movie_collections(SETTINGS.movie_libraries, SETTINGS.collection_size_minimum)
    take_action_on_movie_collections(movie_collections, SETTINGS.delete_undersized_collections)

    all_movies = get_all_movies(SETTINGS.movie_libraries)
    ensure_movie_name_matches_file(all_movies, SETTINGS.enforce_movie_names_match_file_names, SETTINGS.movie_name_enforce_skip_characters)

    script_exit()


if __name__ == '__main__':
    try:
        main()
    except Exception as root_exception:
        stop_running_script("Global script failure occurred", root_exception, 1)
