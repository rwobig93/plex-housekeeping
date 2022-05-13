# region Imports
import json
import logging
import os.path
from dataclasses import dataclass
from os.path import exists
from plexapi.server import PlexServer

# endregion
# region Classes


@dataclass(init=False, repr=True, eq=True, order=True)
class ScriptSettings:
    plex_url: str
    api_key: str
    movie_libraries: list[str]
    collection_size_minimum: int
    delete_undersized_collections: bool

    def __init__(self, url, api, movie_library_names=None, delete_collections=False, size=-1) -> None:
        if movie_library_names is None:
            movie_library_names = list('Movies')
        self.plex_url = url
        self.api_key = api
        self.movie_libraries = movie_library_names
        self.collection_size_minimum = int(size)
        self.delete_undersized_collections = delete_collections
        if len(url) < 1:
            raise ValueError('URL provided is empty, please provide a valid plex URL')
        if len(api) < 1:
            raise ValueError('API provided is empty, please provide a valid plex API key')


# endregion
# region Globals


global_settings: ScriptSettings
plex_instance: PlexServer
file_encoding = 'utf-8'
path_config_file = './plex-cleanup-config.json'


# endregion
# region Functions

# region Script Control


def configure_logging(logfile_name='script_log'):
    """ Configure the application logger """
    loglevel = logging.INFO
    if exists('./debug'):
        loglevel = logging.DEBUG
    logging.basicConfig(filename='%s.log' % logfile_name, encoding=file_encoding, level=loglevel, format='%(asctime)s::%(levelname)s:%(message)s')
    logging.info('Logger initialized!')


def stop_running_script(message, exception=None, error_code=1):
    """ Stop the running script with the provided message, exception and error code """
    if isinstance(exception, Exception):
        full_message = 'Script was stopped due to a critical failure =>\n  %s =>\n    %s =>\n      %s' % (message, exception, exception.with_traceback)
    else:
        full_message = 'Script was stopped due to a critical failure =>\n  %s' % message
    logging.critical(full_message)
    print(full_message)
    exit(error_code)


def error_occurred(message, exception=None):
    """ Convey error occurrence with the provided error message and exception if one is provided """
    if isinstance(exception, Exception):
        full_message = '%s =>\n  %s =>\n    %s' % (message, exception, exception.with_traceback)
        logging.error(full_message)
        print(full_message)
    else:
        print(message)


def print_and_log_message(message):
    """ Print and log the provided message """
    logging.info(message)
    print(message)


# endregion
# region Configuration Handling


def create_config_file():
    """ Creates a default config file for modification """
    try:
        default_config_file = {
            "plex_url": "",
            "plex_api_key": "",
            "movie_libraries": ['Movies'],
            "minimum_collection_size": 2,
            "delete_undersized_collections": False
        }

        if exists(path_config_file):
            os.remove(path_config_file)
            logging.info('Deleted existing config file: %s' % path_config_file)
        logging.debug('Attempting to create default config file at: %s' % os.path.abspath(path_config_file))
        with open(path_config_file, 'w', encoding=file_encoding) as config_writer:
            json.dump(default_config_file, config_writer)
        logging.debug('Created default config file at: %s' % os.path.abspath(path_config_file))
    except Exception as ex:
        stop_running_script('Error occurred attempting to create config file at %s' % os.path.abspath(path_config_file), ex)


def load_config_file():
    """ Loads the script config file """
    logging.debug('Attempting to read config file: %s' % path_config_file)
    try:
        if exists(path_config_file):
            logging.info('Config file exists at %s' % path_config_file)
        else:
            create_config_file()
            return_message = 'Config file wasn\'t found, created a new one at: %s' % os.path.abspath(path_config_file)
            print(return_message)
            logging.info(return_message)
            exit(0)
        with open(path_config_file, 'r', encoding=file_encoding) as config_reader:
            loaded_config = json.load(config_reader)
            global global_settings
            global_settings = ScriptSettings(loaded_config['plex_url'], loaded_config['plex_api_key'], loaded_config['movie_libraries'], loaded_config['minimum_collection_size'],
                                             loaded_config['delete_undersized_collections'])
    except Exception as ex:
        stop_running_script('Failure occurred attempting to load the config file: %s' % path_config_file, ex)


# endregion
# region Plex API Handling


def connect_to_plex_instance():
    """ Connect to the specified plex url and auth with the provided api key and return the instance object """
    try:
        logging.info('Attempting to connect to plex instance at: %s' % global_settings.plex_url)
        global plex_instance
        plex_instance = PlexServer(global_settings.plex_url, global_settings.api_key)
        logging.info('Successfully connected to plex instance at: %s' % global_settings.plex_url)
    except Exception as ex:
        stop_running_script('Failure occurred attempting to connect to the provided plex url', ex)


def get_movie_collections():
    """ Return all movie collections from the connected plex instance, filters collections based on the minimum collection size provided in the config file """
    collection_count_total = 0
    collection_filtered_list = []
    collection_size_min = global_settings.collection_size_minimum
    for movie_library in global_settings.movie_libraries:
        try:
            logging.debug('Attempting to load collections from movie library: %s' % movie_library)
            collections = plex_instance.library.section(movie_library).search(libtype='collection')
            print_and_log_message('Library [%s] has a collection count of [%s]' % (movie_library, len(collections)))
            logging.debug('Successfully grabbed movie library [%s], attempting to enumerate [%s] collections' % (movie_library, len(collections)))
            for collection in collections:
                logging.debug('Enumerating collection, validating size: [collection_name]%s [collection_members]%s [member_minimum]%s'
                              % (collection.title, collection.childCount, collection_size_min))
                collection_count_total += 1
                if collection_size_min > -1 and collection.childCount < collection_size_min:
                    logging.debug('Found movie collection matching provided criteria, appending to master list: %s' % collection.title)
                    collection_filtered_list.append(collection)
        except Exception as ex:
            error_occurred('Failure occurred attempting to parse move library', ex)
    print_and_log_message('Total filtered collections: %s' % len(collection_filtered_list))
    print_and_log_message('Total collection count enumerated: %s from %s libraries' % (collection_count_total, len(global_settings.movie_libraries)))
    return collection_filtered_list


def delete_movie_collection(collection):
    """ Delete the provided movie collection from the connected plex instance """
    try:
        collection_name = collection.title
        logging.debug('Attempting to delete moving collection: %s' % collection_name)
        collection.delete()
        logging.info('Deleted movie collection: %s' % collection_name)
    except Exception as ex:
        error_occurred('Failure occurred attempting to delete the provided collection: %s' % collection.title, ex)


def take_action_on_movie_collections(collections):
    """ Deletes or conveys the provided movie collections list """
    for collection in collections:
        if global_settings.delete_undersized_collections:
            delete_movie_collection(collection)
        else:
            print_and_log_message('We would delete this movie collection: %s' % collection.title)


# endregion


# endregion


def main():
    """ Main script execution point """
    configure_logging('Plex-Cleanup-Script')
    logging.info('Starting script execution')
    load_config_file()

    connect_to_plex_instance()
    movie_collections = get_movie_collections()
    take_action_on_movie_collections(movie_collections)

    logging.info('Finished script execution')


if __name__ == '__main__':
    main()
