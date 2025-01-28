from pmc_automation_tools.api.common import DataSourceInput, DataSourceResponse, DataSource
from pmc_automation_tools.common.exceptions import ClassicConnectionError

import requests
from requests.auth import HTTPBasicAuth

from zeep import Client
from zeep.transports import Transport
from zeep.helpers import serialize_object

from typing import List
from concurrent.futures import ThreadPoolExecutor

SOAP_TEST = 'https://testapi.plexonline.com/Datasource/service.asmx'
SOAP_PROD = 'https://api.plexonline.com/Datasource/service.asmx'
class ClassicDataSourceInput(DataSourceInput):
    """Input object that stores the attributes for building the proper request format."""
    def __init__(self, data_source_key: int, *args, delimeter='|', **kwargs):
        self._delimeter = delimeter
        super().__init__(data_source_key, *args, type='classic', **kwargs)
        self.__api_id__ = int(self.__api_id__)


    def __repr__(self):
        _attrs = [f"{k}='{v}'" for k, v in vars(self).items() if not k.startswith('_')]
        return f"ClassicDataSourceInput(data_source_key={self.__api_id__}, {', '.join(_attrs)})"


    def __str__(self):
        _str = [self._delimeter.join(k, str(v)) for k, v in vars(self).items() if not k.startswith('_')]
        return '\n'.join(_str)


    def _update_input_parameters(self):
        self._parameter_names = self._delimeter.join([k for k, v in vars(self).items() if not k.startswith('_')])
        self._parameter_values = self._delimeter.join([str(v) for k, v in vars(self).items() if not k.startswith('_')])


class ClassicDataSource(DataSource):
    def __init__(self, auth: HTTPBasicAuth|str,
                 wsdl,
                 *args,
                 test_db: bool = True,
                 pcn_config_file: str='resources/pcn_config.json',
                 **kwargs):
        """Data Source object for Classic SOAP web service

        Args:
            auth (HTTPBasicAuth | str): Authentication for web service account
            wsdl (str): path to the SOAP wsdl file
            test_db (bool, optional): Connect to the test api URL. Defaults to True.
            pcn_config_file (str, optional): path to the web service credential file. Defaults to 'resources/pcn_config.json'.
        """
        super().__init__(*args, auth=auth, test_db=test_db, pcn_config_file=pcn_config_file, type='classic', **kwargs)
        self._wsdl = wsdl


    def __repr__(self):
        return f"ClassicDataSource(auth={self.__auth_key__}, wsdl={self._wsdl}, test_db={self._test_db}, pcn_config_file={self._pcn_config_file})"


    def call_data_source(self, query:ClassicDataSourceInput) -> 'ClassicDataSourceResponse':
        """Triggers the data source request.

        Args:
            query (ClassicDataSourceInput): object containing the input details

        Returns:
            ClassicDataSourceResponse: ClassicDataSourceResponse object
        """
        session = requests.Session()
        session.auth = self._auth
        client = Client(wsdl=self._wsdl, transport=Transport(session=session))
        self._connection_address = client.wsdl.services['Service'].ports['ServiceSoap'].binding_options['address']
        if self._test_db and self._connection_address != SOAP_TEST:
            raise ClassicConnectionError('Test database was indicated, but WSDL address does not match expected test address.')
        response = client.service.ExecuteDataSourcePost(dataSourceKey=query.__api_id__, parameterNames=query._parameter_names, parameterValues=query._parameter_values, delimeter=query._delimeter)
        _response = serialize_object(response, dict)
        return ClassicDataSourceResponse(query.__api_id__, **_response)


    def call_data_source_threaded(self, query_list:List['ClassicDataSourceInput']) -> List['ClassicDataSourceResponse']:
        with ThreadPoolExecutor(max_workers=8) as pool:
            response_list = list(pool.map(self.call_data_source, query_list))
        return response_list
    

class ClassicDataSourceResponse(DataSourceResponse):
    def __init__(self, data_source_key, **kwargs):
        super().__init__(data_source_key, **kwargs)
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
    
    def __repr__(self):
        return (f"UXDataSourceResponse("
                f"data_source_key={self.__api_id__}, "
                f"DataSourceName={self.DataSourceName}, "
                f"Message={self.Message}, "
                f"Instance={self.InstanceNo}, "
                f"StatusNo={self.StatusNo}, "
                f"Error={self.Error}, "
                f"ErrorNo={self.ErrorNo})")

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