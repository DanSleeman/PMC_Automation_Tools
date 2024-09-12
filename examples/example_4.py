from pmc_automation_tools import ApiDataSource, ApiDataSourceInput
from datetime import datetime, timedelta
import base64

test = True
today = datetime.now()
tomorrow = today + timedelta(days=1)
yesterday = today - timedelta(days=1)
pcn = '123456'
api_key = 'API_KEY_HERE'

a = ApiDataSource(auth=api_key, test_db=test)

# Get customer ID
url = 'https://connect.plex.com/mdm/v1/customers'
method = 'get'
ai = ApiDataSourceInput(url, method)
ai.name = 'Customer Name Here'
r = a.call_data_source(pcn, ai)
cust_id = r.get_response_attribute('id') # Should only return 1 item.

# Get EDI log entries
url = 'https://connect.plex.com/edi/v1/logs'
method = 'get'
ai = ApiDataSourceInput(url, method)
ai.customerId = cust_id
ai.action = 'Receive'
ai.mailboxActive = True
ai.logDateBegin = log_start_date = yesterday.strftime('%Y-%m-%dT04:00:00Z')
# This will return a list of all received documents
r = a.call_data_source(pcn, ai)
# Filter out 830s and 862s. This isn't possible directly from the API call.
edi_messages = r.get_response_attribute('id', preserve_list=True, documentName='830')
edi_862 = r.get_response_attribute('id', preserve_list=True, documentName='862')
edi_messages.extend(edi_862)

# Get the actual EDI documents
method = 'get'
for edi_id in edi_messages:
    url = f'https://connect.plex.com/edi/v1/documents/{edi_id}'
    ai = ApiDataSourceInput(url, method)
    r = a.call_data_source(pcn, ai)
    edi_raw = r.get_response_attribute('rawDocument')
    # You'll need to decode this from base64 string and save it to a file
    edi_str = str(base64.b64decode(edi_raw).decode('utf-8'))
    with open(f'{edi_id}_edi_file.txt', 'w+', encoding='utf-8') as out_file:
        out_file.write(edi_str)