import requests, urllib3
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
from urllib3.util.ssl_ import create_urllib3_context
from zeep import Client
from zeep.transports import Transport
from zeep.helpers import serialize_object
import json
import pandas as pd
from pandas import json_normalize 
from datetime import datetime, timedelta, date, timezone
from warnings import warn
from itertools import chain
import csv
import os

__author__ = 'Dan Sleeman'
__copyright__ = 'Copyright 2022, PMC UX Data Source Tools'
__credits__ = ['Dan Sleeman']
__license__ = 'GPL-3'
__version__ = '1.7.4'
__maintainer__ = 'Dan Sleeman'
__email__ = ['sleemand@shapecorp.com', 'dansleeman@gmail.com']
__status__ = 'Production'

ATTR_EXCLUDE = ["__api_id__", "__query_string__", "__refresh_query__", "__call_format__", "_request_body_", "_status_code_", "_transaction_no_", "__input_types__", "url", "apikey", "method", "__template_folder__"]
CALL_FORMATS = [1, 2]
DB_VALUES = ['TEST', 'PROD']
RETRY_COUNT = 10
BACKOFF = 0.5
RETRY_STATUSES = [500, 502, 503, 504]
SOAP_TEST = 'https://testapi.plexonline.com/Datasource/service.asmx'
SOAP_PROD = 'https://api.plexonline.com/Datasource/service.asmx'
class Error(Exception):
    pass
class DataSourceException(Error):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.__dict__.update(kwargs)
class ApiError(DataSourceException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.status = kwargs.get('status')
        self.__dict__.update(kwargs)
class ClassicConnectionError(DataSourceException):...
class CustomSslContextHTTPAdapter(HTTPAdapter):
    """"Transport adapter" that allows us to use a custom ssl context object with the requests."""
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = create_urllib3_context()
        ctx.load_default_certs()
        ctx.options |= 0x4  # ssl.OP_LEGACY_SERVER_CONNECT
        self.poolmanager = urllib3.PoolManager(ssl_context=ctx)

class UXResponse():
    def __init__(self, api_id, **kwargs):
        self.__api_id__ = api_id
        self.__dict__.update(kwargs)
        if hasattr(self, 'outputs'):
            self.__dict__.update(**self.outputs)

class plexDateOffset():
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class UXDataSourceInput():
    """
    Class used for calling UX web services.

    Suggested usage is for storing a dictionary of key:value pairs for a web service.
    
    Pass this as an unpacked dictionary to kwargs which will generate a json string that Plex accepts for input.
        This will add attributes for each input.

    Alternatively, store the sample request from Plex as a json file with the API id in the name.
        Pass the template folder to the class, and default values should be set. 
    
    If not using a template, create the input object first, then update the values. 
        Single digit int values will behave incorrectly if passed on initial creation. 
        The templates expect 99999 as the int placeholder and 0/1 as the boolean placehold.
    
    Incorrect:
    >>> c = UXDataSourceInput(123, Quantity=1)
    >>> c.Quantity
    >>> True

    Correct:
    >>> c = UXDataSourceInput(123)
    >>> c.Quantity = 1
    >>> c.Quantity
    >>> 1
    """
    def __init__(self, api_id: str, call_format: int=1, template_folder: str=None, **kwargs):
        self.__input_types__ = {}
        self.__api_id__ = str(api_id)
        self.__call_format__ = call_format
        self.__template_folder__ = template_folder
        self.__dict__.update(kwargs)
        for x in self.__dict__.keys():
            if x in ATTR_EXCLUDE:
                continue
            if len(str(getattr(self, x))) == 1 and type(getattr(self, x)) == int:
                self.__dict__[x] = bool(getattr(self, x))
        if self.__template_folder__:
            template_query = self.query_template_import()
            if template_query:
                self.__dict__.update(**template_query)
        self.update_query_string()
        self.type_create()


    def __setattr__(self, name, value):
        self.__dict__[name] = value
        if not name in ATTR_EXCLUDE:
            self.update_query_string()


    def query_template_import(self):
        for file in os.listdir(self.__template_folder__):
            if self.__api_id__ in file:
                with open(os.path.join(self.__template_folder__, file), 'r', encoding='utf-8') as j:
                    x = json.loads(j.read())
                if 'inputs' in x.keys():
                    return x['inputs']
                else:
                    return x

    def update_query_string(self):
        """
        Recompiles the class __query_string__ attribute for web service calls
        """
        kwargs = {key: value for key, value in self.__dict__.items() if key not in ATTR_EXCLUDE}
        if self.__call_format__ not in CALL_FORMATS:
            raise ValueError(f'{type(self).__name__} `call_format` input must be one of {CALL_FORMATS} . Received {self.__call_format__}')
        if self.__call_format__ == 1:
            self.__query_string__ = {'inputs':kwargs}
        elif self.__call_format__ == 2:
            self.__query_string__ = kwargs


    def pop_inputs(self, *args, **kwargs):
        """
        Will remove attributes from the class that are not needed.

        :param *args: Any specific input name will be removed from the class
        :param **kwargs: Can allow for keeping specific attributes when passed as a list using the "keep" kwarg.
        """
        if kwargs.get('keep'):
            entries_to_remove = [key for key in self.__dict__.keys() if key not in kwargs['keep'] and key not in ATTR_EXCLUDE]
            for attr in entries_to_remove:
                self.__dict__.pop(attr, None)
        for attr in args:
            if attr in ATTR_EXCLUDE:
                continue
            self.__dict__.pop(attr, None)
        self.update_query_string()


    def type_create(self):
        for x in self.__dict__.keys():
            if not getattr(self, x):
                continue
            if x in ATTR_EXCLUDE:
                continue
            else:
                # print(x)
                # print(type(getattr(self, x)))
                if len(str(getattr(self, x))) == 1 and type(getattr(self, x)) == int:
                    self.__input_types__[x] = type(bool(getattr(self, x)))
                else:
                    self.__input_types__[x] = type(getattr(self, x))
                # self.__setattr__(x, getattr(self, x))


    def xstr(self, s):
        if s is None:
            return ''
        return str(s)
    
    def xbool(self, b):
        if b.upper() == 'FALSE':
            return False
        return True

    def type_reconcile(self):
        for x in self.__dict__:
            if x in ATTR_EXCLUDE:
                continue
            if getattr(self, x) == None:
                continue
            if x not in self.__input_types__.keys():
                continue
            else:
                match getattr(self, '__input_types__')[x]:
                    case v if v is int:
                        if type(getattr(self, x)) == str and len(getattr(self, x).strip()) == 0:
                            new_val = None
                        else:
                            new_val = getattr(self, '__input_types__')[x](getattr(self, x))
                    case v if v is str:
                        new_val = self.xstr(getattr(self, x))
                    case v if v is bool:
                        new_val = self.xbool(getattr(self, x))
                    case _:
                        new_val = getattr(self, '__input_types__')[x](getattr(self, x))
                self.__setattr__(x, new_val)


    def get_to_update(self, get_instance):
        for header in vars(get_instance):
            self.__setattr__(header, getattr(get_instance, header))
        for x in self.__input_types__.keys():
            if x not in vars(get_instance):
                self.pop_inputs(x)
        self.type_reconcile()


    def purge_empty(self):
        purge_attrs = []
        for y in vars(self).keys():
            if getattr(self, y) == None or y not in self.__input_types__.keys():
                purge_attrs.append(y)
        for y in purge_attrs:
            self.pop_inputs(y)


class PlexApi(UXDataSourceInput):
    """
    Class used for calling the Plex Dev Portal APIs.
    REF: https://developers.plex.com/
            
    :param **kwargs: used the same as UXDataSourceInput with exception for 'json' keyword. Use this for passing a json object directly to the API call.
            Example: Passing an array which is unnamed in the request body.
                See: https://connect.plex.com/purchasing/v1/release-batch/create
    """
    def __init__(self, method, url, apikey, **kwargs):

        self.__refresh_query__  = True
        self.method = method
        self.url = url
        self.apikey = apikey
        self.__call_format__ = 2
        if kwargs.get('json'):
            self.__refresh_query__ = False
            self.__query_string__ = kwargs['json']
        else:
            self.__dict__.update(kwargs)
            self.update_query_string()

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        if not name in ATTR_EXCLUDE and self.__refresh_query__:
            self.update_query_string()


    def call_api(self, pcn:str|list):
        """
        Returns a list of the json objects as dictionaries from the API response.
        """
        response_list = []
        if type(pcn) == str:
            pcn_list = [pcn]
        for p in pcn_list:
            headers = {'Content-Type': 'application/json',
                'X-Plex-Connect-Api-Key': self.apikey,
                'X-Plex-Connect-Customer-Id': p
            }
            session = requests.Session()
            retry = Retry(total=RETRY_COUNT, connect=RETRY_COUNT, backoff_factor=BACKOFF, status_forcelist=RETRY_STATUSES, raise_on_status=True)
            adapter = CustomSslContextHTTPAdapter(max_retries=retry)
            # adapter = HTTPAdapter(max_retries=retry)
            session.mount('https://', adapter)
            if self.method.upper() in ['POST', 'PUT']:
                response = session.request(self.method, self.url, json=self.__query_string__, headers=headers)
            else:
                response = session.request(self.method, self.url, params=self.__query_string__, headers=headers)
            try:
                response.raise_for_status()
            except HTTPError as e:
                raise ApiError('Error calling API.', **response.json(), status=response.status_code)
            if response.status_code == 200 and response.text !=[]:
                response_list.append(response.json())
            else:
                return response
        if type(response_list[0]) == dict:
            return list(chain(response_list))
        elif type(response_list[0]) == list:
            return list(chain.from_iterable(response_list))

class PlexDataSource(object):


    def __init__(self, pcn: str=None, db: str='TEST', pcn_config_file: str='resources/pcn_config.json'):
        self.pcn = pcn
        if '.' in db:
            warn(f"Period detected in db input. {type(self).__name__} is designed to work without this and has removed it.", SyntaxWarning, stacklevel=2)
            db = db.replace('.', '')
        if not db.upper() in DB_VALUES:
            raise ValueError(f"{type(self).__name__} db input must be one of {DB_VALUES}. Received '{db}'.")
        self.db = db
        self.pcn_config_file = pcn_config_file
        if not self.pcn:
            return
        self.authentication = self.set_auth(pcn, pcn_config_file)


    def set_auth(self, home_pcn: str, pcn_config_file: str='resources/pcn_config.json'):
        """
        Creates a basic authentication string for use with Plex data source calls.
        """
        if not hasattr(self, 'pcn_config_file'):
            self.pcn_config_file = pcn_config_file
        with open(self.pcn_config_file, 'r', encoding='utf-8') as c:
            self.launch_pcn_dict = json.load(c)
        username = self.launch_pcn_dict[home_pcn]['api_user']
        password = self.launch_pcn_dict[home_pcn]['api_pass']
        self.authentication = HTTPBasicAuth(username, password)
        return self.authentication


    def get_week_index(self, input_date: date|datetime|str, week_start_offset: int=0): # TODO - migrate to utils module
        """
        Takes a date and gives the relative week index and start date

        :param input_date: Acceptable formats are ISO date string or datetime object.
        :param week_start_offset: When should the week start? Default Monday=0

        If the Sunday before Monday should be the start, use -1

        Returns:
            plexDateOffset class with various date attributes.
            - formatted_date: ISO formatted string to be used with Plex web service requests
            - week_index: The week index of the date compared to today (0)
            - year_offset: The year offset compared to today (0)
            - group_start_date: The first date of the week acording to the offset defined
        """
        today = datetime.today()
        week_start = today - timedelta(days=today.weekday())
        if isinstance(input_date, (datetime, date)):
            eval_date = input_date
        else:
            try:
                eval_date = datetime.strptime(input_date, '%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                eval_date = datetime.strptime("1990-01-01T00:00:00Z", 
                                            '%Y-%m-%dT%H:%M:%SZ')
        year_offset = date(int(eval_date.strftime("%Y")), 12, 28).isocalendar()[1]
        # Anything less than 0 is considered equally past due
        week_index = max(
                    -1,
                    int(eval_date.strftime("%W")) 
                    - int(week_start.strftime("%W")) 
                    + (
                        (
                            int(eval_date.strftime("%Y")) 
                            - int(week_start.strftime("%Y"))
                        ) 
                        * year_offset
                        )
                )
        group_start_date = week_start + timedelta(weeks=week_index, days=week_start_offset)
        formatted_date = group_start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        return plexDateOffset(formatted_date=formatted_date,
                              week_index=week_index, 
                              year_offset=year_offset, 
                              group_start_date=group_start_date)

    def post_url(self, args: tuple):
        """
        Can  be used to thread web service requests.

        Parameters:
            args: tuple containing the URL, request body, and authentication

        Returns:
            Raw web source response
        
        Example usage for calling prp demand using a list or dictionary of part keys:
            >>> ed = ux.plex_date_formatter(date.today(), date_offset=56)
            >>> api_id  = '15851'
            >>> db = 'test.'
            >>> # Create list of queries for the web service calls
            >>> query_list = []
            >>> for i, (key, item) in enumerate(part_key_dict.items()):
            >>>     query = (
                        ('Part_Key', key),
                        ('From_PRP', True),
                        ('Begin_Date', '2001-10-01T04:00:00.000Z'),
                        ('End_Date', ed)
                    )
            >>>     query_list.append(query)
            >>> with ThreadPoolExecutor(max_workers=100) as executor:
            >>>    url = f'https://{db}cloud.plex.com/api/datasources/{api_id}/execute'
            >>>    list_of_urls = [(url, {'inputs': dict(query)}, authentication) 
                            for query in query_list]
            >>>    futures = [executor.submit(ux.post_url, url_args) for url_args in list_of_urls]
            >>>    for future in as_completed(futures):
            >>>        result = future.result()
            >>>        # work with the result here
        """
        # print("Post URL args:", args)
        session = requests.Session()
        retry = Retry(total=RETRY_COUNT, connect=RETRY_COUNT, backoff_factor=BACKOFF, status_forcelist=RETRY_STATUSES, raise_on_status=True)
        adapter = CustomSslContextHTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        response = session.post(args[0], json=args[1], auth=args[2])
        return response


    def rest_api_query(self, api_id: str, query: str, db: str, authentication: HTTPBasicAuth):
        if not hasattr(self, 'db'):
            self.db = db
        if self.db.upper() == 'TEST':
            # print("Using test database")
            db = 'test.'
        else:
            db = ''
        url = f'https://{db}cloud.plex.com/api/datasources/{api_id}/execute{self.url_call_format}'
        session = requests.Session()
        retry = Retry(total=RETRY_COUNT, connect=RETRY_COUNT, backoff_factor=BACKOFF, status_forcelist=RETRY_STATUSES, raise_on_status=True)
        adapter = CustomSslContextHTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        self.response = session.post(url, json=query, auth=authentication)
        # print(self.response)
        json_data = self.response.json()
        # print(json_data)
        return json_data


    def create_json(self, *args):
        # print(args)
        return {'inputs': dict(args)}


    def data_frame_make(self, json_data):
        df = pd.DataFrame()
        if self.__call_format__ == 1:
            df = json_normalize(json_data['tables'], 'rows')
        elif self.__call_format__ == 2:
            df = pd.DataFrame(json_data['rows'])
        if df.empty:
            return pd.DataFrame()
        if self.__call_format__ == 1:
            df.columns = json_data['tables'][0]['columns']
        df = df.replace('\r\n', '', regex=True)
        return df


    def call_web_service(self, api_id: str, query: UXDataSourceInput| dict | list[tuple] | tuple[tuple] | tuple, pcn: str=None, db: str='TEST', dataframe: bool=False, classlist: bool=False):
        """
        Calls a plex web service to return the values.

        Parameters:
            :param api_id: the UX data source ID
            :param query: The query parameter. It can be one of the following types:
                      - A list of tuples (list[tuple])
                      - A dictionary (dict)
                      - A tuple of tuples (tuple[tuple])
                      - An instance of UXDataSourceInput
            :param pcn: the PCN to which to connect
            :param db: the plex database connection to use
            :param dataframe: return a pandas dataframe
            :param classlist: return a list of UXDataSourceResponse classes
        Returns:
            if dataframe is true, a pandas dataframe
            if classlist is true, a list of UXDataSourceResponse classes
            else a json reponse string from the web service
        """
        self.api_id = api_id
        self.query = query
        if not hasattr(self, 'db'):
            self.db = db
        if pcn:
            self.pcn = pcn
            self.authentication = self.set_auth(self.pcn)
        
        elif not hasattr(self, 'authentication'):
            raise AttributeError(f"{type(self).__name__}.authentication attribute not set. Either provide a pcn input, call the {type(self).__name__}.set_auth function, or set the {type(self).__name__}.attribute first.")
        if hasattr(query, '__call_format__'):
            self.__call_format__ = query.__call_format__
            self.url_call_format = f'?format={query.__call_format__}'
        else:
            self.__call_format__ = 1
            self.url_call_format = ''
        if isinstance(self.query, UXDataSourceInput):
            json_input = self.query.__query_string__
        elif isinstance(self.query, dict):
            json_input = {'inputs': self.query}
        # elif isinstance(self.query, list):
        #     json_input = {'inputs': dict(self.query)}
        elif all(isinstance(key_val, tuple) for key_val in self.query):
            # All items in the input are tuples
            json_input = {'inputs': dict(self.query)}
        elif all(isinstance(key_val, tuple) for key_val in [self.query]):
            # There is a single tuple as input
            json_input = {'inputs': dict([self.query])}

        else:
            raise TypeError("Query input type not supported. Must be a UXDataSourceInput object, a dictionary, or a list/tuple of (key, value) tuples.")
        json_data = self.rest_api_query(self.api_id, json_input, self.db, self.authentication)
        if 'errors' in json_data.keys():
            raise ApiError('Error calling web service.', **json_data, status=self.response.status_code)
        if dataframe:
            df = self.data_frame_make(json_data)
            return df
        elif classlist:
            if self.__call_format__ == 1:
                if 'tables' in json_data.keys():
                    if json_data['tables']:
                        jdt = json_data['tables'][0]
                        transaction_no = json_data['transactionNo']
                        result = [{col: val for col, val in zip(jdt['columns'], row)} for row in jdt['rows']]
                    else:
                        transaction_no = json_data['transactionNo']
                        result = [json_data]
            elif self.__call_format__ == 2:
                jdt = json_data['rows']
                transaction_no = json_data['transactionNo']
                result = [row for row in jdt]
            return [UXResponse(self.api_id, 
                               _transaction_no_ = transaction_no,
                               _request_body_ = self.response.request.body,
                               _status_code_ = self.response.status_code,
                               **r) for r in result]
        else:
            return json_data


    def plex_date_formatter(self, *args: datetime|int, date_offset=0):
        """
        Takes 'normal' date formats and converts them to a Plex web service 
            format (ISO format)
        Can also take a single datetime object.
        2022, 09, 11 -> 2022-09-11T04:00:00Z
        2022, 09, 11, 18, 45 -> 2022-09-11T22:45:00Z
            Next day if hours fall into 20-24 period
        2022, 09, 11, 22 -> 2022-09-12T02:00:00Z
            date_offset arg will add days to the provided time
            Useful when providing just a datetime object to the function
        """
        if isinstance(args[0], (datetime, date)):
            x = args[0]
        else:
            x = datetime(*args).astimezone(datetime.now(timezone.utc).tzinfo)
        # x += timedelta(hours=4)
        x += timedelta(days=date_offset)
        f_date = x.strftime('%Y-%m-%dT%H:%M:%SZ')
        return f_date


    def list_data_source_access(self, pcn=None, all_acc=0, db='TEST'):
        """
        Examples
        ---------
        Get data source access for all accounts
        >>> import ux_data_source_tools as UDST
        >>> ux = UDST.UX_Data_Sources()
        >>> df = ux.list_data_source_access(all_acc=1)
        >>> df.to_csv('account_data_source_access.csv', index=0)

        Get data source access for a single account
        >>> import ux_data_source_tools as UDST
        >>> ux = UDST.UX_Data_Sources('Japan')
        >>> df = ux.list_data_source_access()
        Alternatively:
        >>> import ux_data_source_tools as UDST
        >>> ux = UDST.UX_Data_Sources()
        >>> df = ux.list_data_source_access(pcn='Japan')
        """
        self.all_acc = all_acc
        if not hasattr(self, 'db'):
            self.db = db
        if self.db.upper() == 'TEST':
            print("Using test database")
            db = 'test.'
        else:
            db = ''
        url = f'https://{db}cloud.plex.com/api/datasources/search?name='
        session = requests.Session()
        retry = Retry(total=RETRY_COUNT, connect=RETRY_COUNT, backoff_factor=BACKOFF, status_forcelist=RETRY_STATUSES, raise_on_status=True)
        adapter = CustomSslContextHTTPAdapter(max_retries=retry)
        # adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        if self.all_acc:
            if not self.launch_pcn_dict:
                self.set_auth('Grand Haven')
            df = pd.DataFrame()
            for (key, value) in self.launch_pcn_dict.items():
                
                authentication = self.set_auth(key)

                response = session.get(url, auth=authentication)
                json_data = json.loads(response.text)
                if df.empty:
                    df = json_normalize(json_data)
                    df['PCN'] = key
                    # df.assign(PCN=key)
                else:
                    df_2 = pd.DataFrame()
                    df_2 = json_normalize(json_data)
                    # df_2.assign(PCN=key)
                    df_2['PCN'] = key
                    df = pd.concat([df, df_2])
        else:
            if pcn:
                authentication = self.set_auth(pcn)
            else:
                authentication = self.authentication
            response = session.get(url, auth=authentication)
            json_data = json.loads(response.text)
            df = pd.DataFrame()
            df = json_normalize(json_data)
        if self.all_acc:
            df = df[['id', 'name', 'PCN']]
        else:
            df = df[['id', 'name']]
        return df

        
    def make_csv_dict(self, row):
            """
            I find this is a very useful way to get csv column header references
            Using the names of the columns works even when the position of them
            changes.
            """
            self.row = row
            cd = {}
            for x, i in enumerate(row):
                if i in cd.keys():
                    i = i+'_'+str(x)
                cd[i] = x
            return cd


class ClassicDataSourceInput(UXDataSourceInput):
    def __init__(self, data_source_key: int, delimeter='|', **kwargs):
        self.__data_source_key__ = int(data_source_key)
        self.__dict__.update(kwargs)
        self._delimeter = delimeter
        self._update_params()

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        if not name.startswith('_'):
            self._update_params()
    
    def _update_params(self):
        self._parameter_names = self._delimeter.join([k for k, v in vars(self).items() if not k.startswith('_')])
        self._parameter_values = self._delimeter.join([v for k, v in vars(self).items() if not k.startswith('_')])
    def update_query_string(self):
        return self._update_params()


class PlexClassicDataSource(PlexDataSource):
    def __init__(self, wsdl, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wsdl = wsdl
    

    def call_data_source(self, query:ClassicDataSourceInput):
        session = requests.Session()
        session.auth = self.authentication
        client = Client(wsdl=self._wsdl, transport=Transport(session=session))
        self._connection_address = client.wsdl.services['Service'].ports['ServiceSoap'].binding_options['address']
        if self.db.upper() == 'TEST' and self._connection_address != SOAP_TEST:
            raise
        response = client.service.ExecuteDataSourcePost(dataSourceKey=query.__data_source_key__, parameterNames=query._parameter_names, parameterValues=query._parameter_values, delimeter=query._delimeter)
        _response = serialize_object(response, dict)
        return ClassicResponse(query.__data_source_key__, **_response)


class ClassicResponse():
    def __init__(self, data_source_key, **kwargs):
        self.__data_source_key__ = data_source_key
        self.__dict__.update(kwargs)
        if self.Error:
            raise ClassicConnectionError(self.Message,
                                         data_source_key=self.DataSourceKey,
                                         instance=self.InstanceNo,
                                         status=self.StatusNo,
                                         error_no=self.ErrorNo)
        self._result_set = kwargs.get('ResultSets')
        if self._result_set:
            self._row_count = self._result_set['ResultSet'][0]['RowCount']
            self._result_set = self._result_set['ResultSet'][0]['Rows']['Row']
            self._format_response()
    
    
    def _format_response(self):
        self._transformed_data = []
        if hasattr(self, '_result_set'):
            for row in self._result_set:
                row_data = {}
                columns = row['Columns']['Column']
                for column in columns:
                    name = column['Name']
                    value = column['Value']
                    row_data[name] = value
                self._transformed_data.append(row_data)
        return self._transformed_data
    

    def save_response_csv(self, out_file):
        if not hasattr(self, '_transformed_data'):
            return
        with open(out_file, 'w+', encoding='utf-8') as f:
            c = csv.DictWriter(f, fieldnames=self._transformed_data[0].keys(), lineterminator='\n')
            c.writeheader()
            c.writerows(self._transformed_data)


class UX_Data_Sources(PlexDataSource):...