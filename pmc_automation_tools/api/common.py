import csv
import os
import json
from requests.auth import HTTPBasicAuth
from pmc_automation_tools.common.exceptions import PlexResponseError
from typing import Literal, Union
from abc import ABC, abstractmethod
from requests.adapters import HTTPAdapter
from urllib3 import PoolManager
from urllib3.util.ssl_ import create_urllib3_context

"""
Base datasource class
    Shared functions
        set_auth - Done

Base input class
    shared functions
        pop_inputs - done
        update_query_string - Rename to something like update_input_parameters? - done
        purge_empty - done

Base response class
    shared functions
        save_response_csv - will need to update the UX data source to properly format the data
    shared attributes
        data_source_key - Doesn't exist for new API responses


"""
TYPE_VALUES = ['classic', 'ux', 'api']
RETRY_COUNT = 10
BACKOFF = 0.5
RETRY_STATUSES = [500, 502, 503, 504]

class CustomSslContextHTTPAdapter(HTTPAdapter):
    """"Transport adapter" that allows us to use a custom ssl context object with the requests."""
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = create_urllib3_context()
        ctx.load_default_certs()
        ctx.options |= 0x4  # ssl.OP_LEGACY_SERVER_CONNECT
        self.poolmanager = PoolManager(ssl_context=ctx)


class DataSourceInput(ABC):
    """
    """
    def __init__(self, api_id: str, type: Literal['classic', 'ux', 'api'], *args, **kwargs):
        self.__api_id__ = str(api_id)
        self.__refresh_query__ = True

        if not type.lower() in TYPE_VALUES:
            raise ValueError(f"{type(self).__name__} type must be one of {TYPE_VALUES}. Received '{type}'.")
        self.__datasource_type__ = type
        for key, value in kwargs.items():
            setattr(self, key, value)
        if kwargs.get('json'):
            self.__refresh_query__ = False
            self._query_string = kwargs['json']
        else:
            self._update_input_parameters()


    def __setattr__(self, name, value):
        self.__dict__[name] = value
        if not name.startswith('_') and self.__refresh_query__:
            self._update_input_parameters()

    @abstractmethod
    def _update_input_parameters(self):...


    def pop_inputs(self, *args, **kwargs):
        """
        Will remove attributes from the class that are not needed.

        Parameters:
        - *args: Any specific input name will be removed from the class
        - **kwargs: Can allow for keeping specific attributes when passed as a list using the "keep" kwarg.
        """
        if 'keep' in kwargs.keys():
        # if kwargs.get('keep'): # Can't use this method because an empty list is expected and evaluates false here.
            entries_to_remove = [key for key in self.__dict__.keys() if key not in kwargs['keep'] and not key.startswith('_')]
            for attr in entries_to_remove:
                vars(self).pop(attr, None)
        for attr in args:
            if attr.startswith('_'):
                continue
            vars(self).pop(attr, None)
        self._update_input_parameters()


    def purge_empty(self):
        """
        Removes any None type attributes from the object.

        These can cause issues if the input is not nullable.
        """
        purge_attrs = []
        for y in vars(self).keys():
            if getattr(self, y) is None:
                purge_attrs.append(y)
        for y in purge_attrs:
            self.pop_inputs(y)

class DataSource(ABC):
    def __init__(self, auth: HTTPBasicAuth|str,
                       test_db: bool = True,
                       pcn_config_file: str='resources/pcn_config.json',
                       type: Literal['classic', 'ux', 'api']='ux',
                       **kwargs):
        """
        Parameters:

        - auth: HTTPBasicAuth | str
            - HTTPBasicAuth object
            - API Key as a string
            - PCN Reference key for getting the username/password stored in a json config file.
            
        - test_db: bool, optional
            - Use test or production database
        
        - pcn_config_file: str, optional
            - Path to JSON file containing username/password credentials for HTTPBasicAuth connections.
        """
        
        self._test_db = test_db
        self._pcn_config_file = pcn_config_file
        self.__datasource_type__ = type
        self._auth = self.set_auth(kwargs.get('pcn', auth))


    def _check_api_key(self, input_str: str) -> bool:
        return len(input_str)==32 and input_str.isalnum() and self.__datasource_type__ == 'api'
    

    def set_auth(self, key:HTTPBasicAuth|str):
        """
        sets authentication for API calls.

        Parameters:
        - key:
            - HTTPBasicAuth object
            - API Key as a string
            - PCN Reference key for getting the username/password in a json config file.
        
        If not sending an API Key or HTTPBasicAuth object, Expects a JSON file which holds the webservice credentials.
            .. code-block:: json
                {
                    "PCN_REF":{
                        "api_user":"Username@plex.com",
                        "api_pass":"password"
                    },
                    "PCN_2_REF":{
                        "api_user":"Username2@plex.com",
                        "api_pass":"password2"
                    }
                }
        """
        if isinstance(key, HTTPBasicAuth) or self._check_api_key(key):# or key is None:
            return key
        if not os.path.exists(self._pcn_config_file):
            print(f'PCN config file "{self._pcn_config_file}" missing. Create one or enter your credentials now.')
            username = input('Webservice username:')
            password = input('Webservice password:')
        else:
            with open(self._pcn_config_file, 'r', encoding='utf-8') as c:
                self.launch_pcn_dict = json.load(c)
            username = self.launch_pcn_dict[key]['api_user']
            password = self.launch_pcn_dict[key]['api_pass']
        return HTTPBasicAuth(username, password)
    
    @abstractmethod
    def call_data_source(self):...



class DataSourceResponse(ABC):
    def __init__(self, api_id, **kwargs):
        self.__api_id__ = api_id
        for key, value in kwargs.items():
            setattr(self, key, value)


    @abstractmethod
    def _format_response(self):...

    def save_csv(self, out_file):
        """
        Save the response object to a provided CSV file.
        """
        if not getattr(self, '_transformed_data', []):
            raise PlexResponseError(f'{type(self).__name__} has no transformed data to save.')
        with open(out_file, 'w+', encoding='utf-8') as f:
            c = csv.DictWriter(f, fieldnames=self._transformed_data[0].keys(), lineterminator='\n')
            c.writeheader()
            c.writerows(self._transformed_data)
    
    
    def save_json(self, out_file):
        """
        Save the response object to a provided JSON file.
        """
        if not getattr(self, '_transformed_data', []):
            raise PlexResponseError(f'{type(self).__name__} has no transformed data to save.')
        with open(out_file, 'w+', encoding='utf-8') as f:
            f.write(json.dumps(self._transformed_data, indent=4))


    def get_response_attribute(self, attribute:Union[str,tuple[str]], preserve_list=False, **kwargs) -> list | str:
        """
        Extract the attribute from the formatted data in the response.

        Parameters:

        - attribute: attribute name(s) from the response to return
        - preserve_list: Pass true to retain a list of attributes even if a single item is found.
        - kwargs: arbitrary number of attribute=value filters to use when searching for a specific attribute to return.

        Returns:

        - attribute(s) matching the criteria
        """
        if not isinstance(attribute, tuple):
            attribute = (attribute,)
        attr_list = []
        for item in self._transformed_data:
            if not kwargs or all(item.get(k) in v for k, v in kwargs.items()):
                # Extract attributes for each item as a tuple (even for a single attribute)
                values = tuple(item.get(attr) for attr in attribute)
                # If single attribute, unpack the tuple, otherwise append the tuple
                attr_list.append(values[0] if len(values) == 1 else values)
        return attr_list[0] if len(attr_list) == 1 and not preserve_list else attr_list
    get_attribute = get_response_attribute