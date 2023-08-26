# region Imports


import json
import logging
import os.path
import re
import time

from ast import literal_eval
import schedule
import urllib3
import sys
from enum import Enum
from dataclasses import dataclass, field, asdict
from os.path import exists

from argparse import ArgumentParser
import requests

from plexapi.server import PlexServer, Collection, Library
from plexapi.video import Movie


# endregion
# region Classes


@dataclass
class BaseClass:
    def to_dict(self):
        return asdict(self)


class ConfigType(Enum):
    FILE = 'file'
    ENVIRONMENT = 'environment'


@dataclass(init=True, repr=True)
class ScriptArgs:
    continuous: bool = False
    interval: int = 300
    config_type: ConfigType = ConfigType.FILE
    log_to_terminal: bool = False


@dataclass(init=True, repr=True)
class ScriptSettings(BaseClass):
    plex_url: str
    api_key: str
    movie_libraries: list[str] = field(default_factory=lambda: ['Movies'])
    collection_size_minimum: int = 2
    delete_undersized_collections: bool = False
    enforce_movie_names_match_file_names: bool = False
    movie_name_enforce_skip_characters: list[str] = field(default_factory=lambda: [':', '-', '.', '?'])
    enforce_movie_names_exclude: list[str] = field(default_factory=lambda: ['Star Wars'])

    def __post_init__(self) -> None:
        if len(self.plex_url) < 1:
            raise ValueError('URL provided is empty, please provide a valid plex URL')
        if len(self.api_key) < 1:
            raise ValueError('API provided is empty, please provide a valid plex API key')


# endregion
# region Globals


FILE_ENCODING = 'utf-8'
SETTINGS: ScriptSettings
PLEX_INSTANCE: PlexServer


# endregion
# region Script Control


def _get_running_script_name() -> str:
    script_path = os.path.abspath(__file__)
    return str(os.path.basename(script_path)).replace('.py', '')


def _configure_logging(log_to_terminal: bool = False) -> None:
    """ Configure the application logger """
    path_log_file = f"{_get_running_script_name()}.log"
    loglevel = logging.INFO

    if exists('./debug') or os.environ.get("LOGGING_DEBUG", None) is not None:
        loglevel = logging.DEBUG

    if log_to_terminal:
        log_handlers = [logging.StreamHandler(), logging.FileHandler(path_log_file)]
    else:
        log_handlers = [logging.FileHandler(path_log_file)]

    logging.basicConfig(encoding=FILE_ENCODING, level=loglevel, format='%(asctime)s::%(levelname)s:%(message)s', handlers=log_handlers)
    logging.info('Logger initialized!')


def _stop_running_script(message: str, exception: Exception = None, error_code: int = 1) -> None:
    """ Stop the running script with the provided message, exception and error code """
    if isinstance(exception, Exception):
        full_message = ("Script was stopped due to a critical failure =>"
                        f"\n  {message} =>\n    {exception} =>\n      {exception.with_traceback}")
    else:
        full_message = f"Script was stopped due to a critical failure =>\n  {message}"

    logging.critical(full_message)

    _script_exit(error_code)


def _error_occurred(message: str, exception: Exception = None) -> None:
    """ Convey error occurrence with the provided error message and exception if one is provided """
    if isinstance(exception, Exception):
        full_message = f"{message} =>\n  {exception} =>\n    {exception.with_traceback}"
        logging.error(full_message)
    else:
        logging.error(message)


def _create_config_file() -> None:
    """ Creates a default config file for modification """
    path_config_file = f"{_get_running_script_name()}.json"

    try:
        if exists(path_config_file):
            os.remove(path_config_file)
            logging.info(f"Deleted existing config file: {path_config_file}")

        logging.debug(f"Attempting to create default config file at: {os.path.abspath(path_config_file)}")

        with open(path_config_file, 'w', encoding=FILE_ENCODING) as config_writer:
            json.dump(
                ScriptSettings('https://plex-ip-or-hostname:32400/', '<insert_api_key_here>').to_dict(), config_writer, indent=4, default=str)

        logging.debug(f"Created default config file at: {os.path.abspath(path_config_file)}")
    except Exception as ex:
        _stop_running_script(
            f"Error occurred attempting to create config file at {os.path.abspath(path_config_file)}", ex)


def _load_config_file() -> None:
    """ Loads the script config file """
    path_config_file = f"{_get_running_script_name()}.json"

    logging.debug(f"Attempting to read config file: {path_config_file}")
    try:
        if exists(path_config_file):
            logging.info(f"Config file exists at {path_config_file}")
        else:
            _create_config_file()
            return_message = f"Config file wasn't found, created a new one at: {os.path.abspath(path_config_file)}"
            logging.info(return_message)
            exit(0)
        with open(path_config_file, 'r', encoding=FILE_ENCODING) as config_reader:
            loaded_config = json.load(config_reader)
            global SETTINGS
            SETTINGS = ScriptSettings(**loaded_config)
    except Exception as ex:
        _stop_running_script(f"Failure occurred attempting to load the config file: {path_config_file}", ex)


def _load_environment_variables():
    """ Loads script configuration from environment variables """
    logging.debug("Attempting to read script configuration from environment variables")
    global SETTINGS
    SETTINGS = ScriptSettings('example.com', 'default_token')

    for class_property in dir(SETTINGS):
        if callable(getattr(SETTINGS, class_property)) or class_property.startswith('_'):
            continue

        environment_value = os.environ.get(class_property.upper(), None)
        if environment_value is None:
            continue

        logging.debug(f"Setting script config from environment: {class_property} => {environment_value}")
        setattr(SETTINGS, class_property, environment_value)


def _script_startup(config_type: ConfigType, log_to_terminal: bool) -> None:
    _configure_logging(log_to_terminal)
    logging.info("Starting script execution")

    if config_type == ConfigType.FILE:
        _load_config_file()
    elif config_type == ConfigType.ENVIRONMENT:
        _load_environment_variables()


def _script_exit(error_code: int = 0) -> None:
    logging.info('Finished script execution')

    sys.exit(error_code)


# endregion
# region Script Core


def _parse_script_arguments() -> ScriptArgs:
    parser = ArgumentParser(description='Plex Cleanup Script For Housekeeping / Maintenance',
                            usage="python3 plex-cleanup.py  # Will generate a config file on first run to fill out, then run normally once config file is filled\n"
                                  "python3 plex-cleanup.py -environment  # Will pull from environment variables (API_KEY for example) instead of the config file\n"
                                  "python3 plex-cleanup.py -c -e -i 600  # Will run continuously every hour using environment variables")

    parser.add_argument('-c', '--continuous', action='store_true', help='Continue executing on an interval/schedule, standard run is one time')
    parser.add_argument('-i', '--interval', type=int, default=300, help='Used in conjunction with -c, Interval in seconds between runs, default is 300')
    parser.add_argument('-e', '--environment', action='store_true', help='Execute with environment variables instead of config file')
    parser.add_argument('-lt', '--logterminal', action='store_true', help='Adds logging to terminal output as well as log file')

    parsed_args = parser.parse_args()

    converted_args = ScriptArgs()
    converted_args.continuous = getattr(parsed_args, 'continuous', converted_args.continuous)
    converted_args.interval = os.environ.get("SCRIPT_INTERVAL", converted_args.interval)
    converted_args.interval = getattr(parsed_args, 'interval', converted_args.interval)
    converted_args.config_type = ConfigType.ENVIRONMENT if bool(getattr(parsed_args, 'environment', False)) else ConfigType.FILE
    converted_args.log_to_terminal = getattr(parsed_args, 'logterminal', converted_args.log_to_terminal)

    return converted_args


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
        _stop_running_script("Failure occurred attempting to connect to the provided plex url", ex)


def get_movie_collections(movie_libraries: list[str], collection_size_minimum: int) -> list[Collection]:
    """ Return all movie collections from the connected plex instance, filters collections based on the minimum collection size provided in the config file """
    collection_count_total = 0
    collection_filtered_list: list[Collection] = []
    collection_size_min = int(collection_size_minimum)
    for movie_library in movie_libraries:
        try:
            logging.debug(f"Attempting to load collections from movie library: {movie_library}")

            collections = PLEX_INSTANCE.library.section(movie_library).search(libtype='collection')
            logging.info(f"Library [{movie_library}] has a collection count of [{len(collections)}]")

            logging.debug(f"Successfully grabbed movie library [{movie_library}], attempting to enumerate [{len(collections)}] collections")

            for collection in collections:
                logging.debug(f"Enumerating collection, validating size: [collection_name]{collection.title}"
                              f" [collection_members]{collection.childCount} [member_minimum]{collection_size_min}")

                collection_count_total += 1

                if collection_size_min > -1 and collection.childCount < collection_size_min:
                    logging.debug(f"Found movie collection matching provided criteria, appending to master list: {collection.title}")
                    collection_filtered_list.append(collection)
        except Exception as ex:
            _error_occurred("Failure occurred attempting to parse movie library", ex)

    logging.info(f"Total filtered collections: {len(collection_filtered_list)}")
    logging.info(f"Total collection count enumerated: {collection_count_total} from {len(movie_libraries)} libraries")
    return collection_filtered_list


def _delete_movie_collection(collection: Collection) -> None:
    """ Delete the provided movie collection from the connected plex instance """
    try:
        collection_name = collection.title
        logging.debug(f"Attempting to delete moving collection: {collection_name}")
        collection.delete()
        logging.info(f"Deleted movie collection: {collection_name}")
    except Exception as ex:
        _error_occurred(f"Failure occurred attempting to delete the provided collection: {collection.title}", ex)


def take_action_on_movie_collections(collections: list[Collection], delete_undersized_collections: bool = False) -> None:
    """ Deletes or conveys the provided movie collections list """
    for collection in collections:
        if delete_undersized_collections:
            _delete_movie_collection(collection)
        else:
            logging.info(f"We would delete this undersized movie collection: {collection.title}")


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

    logging.info(f"Finished movie name enforcement, fixed {fixed_movie_count} movies")


def _convert_environment_variable_types() -> None:
    """ Converts the provided environment variable values to their respective values """
    logging.debug("Attempting to convert environment variables to their respective types")

    SETTINGS.movie_libraries = literal_eval(str(SETTINGS.movie_libraries))
    SETTINGS.movie_name_enforce_skip_characters = literal_eval(str(SETTINGS.movie_name_enforce_skip_characters))
    SETTINGS.enforce_movie_names_exclude = literal_eval(str(SETTINGS.enforce_movie_names_exclude))

    logging.debug("Finished converting environment variables to their respective types")


# endregion
# region Script Execution


def main_continuous(script_args: ScriptArgs):
    """ Main script execution point for continuous execution """
    schedule.every(script_args.interval).seconds.do(main(script_args))

    while True:
        schedule.run_pending()
        time.sleep(1)


def main(script_args: ScriptArgs):
    """ Main script execution point """
    _script_startup(script_args.config_type, script_args.log_to_terminal)
    if script_args.config_type == ConfigType.ENVIRONMENT:
        _convert_environment_variable_types()

    connect_to_plex_instance(SETTINGS.plex_url, SETTINGS.api_key)

    movie_collections = get_movie_collections(SETTINGS.movie_libraries, SETTINGS.collection_size_minimum)
    take_action_on_movie_collections(movie_collections, SETTINGS.delete_undersized_collections)

    all_movies = get_all_movies(SETTINGS.movie_libraries)
    ensure_movie_name_matches_file(all_movies, SETTINGS.enforce_movie_names_match_file_names, SETTINGS.movie_name_enforce_skip_characters)


# endregion


if __name__ == '__main__':
    script_arguments = _parse_script_arguments()

    try:
        if bool(script_arguments.continuous):
            main_continuous(script_arguments)
        else:
            main(script_arguments)
            _script_exit()
    except Exception as root_exception:
        _stop_running_script("Global script failure occurred", root_exception, 1)
