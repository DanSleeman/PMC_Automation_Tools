from pmc_automation_tools import (
    ClassicDataSource,
    ClassicDataSourceInput,
    create_batch_folder,
    setup_logger,
    read_updated,
    save_updated
)
from pmc_automation_tools.common.exceptions import ClassicConnectionError
import csv
import os


batch_folder = create_batch_folder(test=True)
logger = setup_logger('Supplier Cert',log_file='certs_added.log',root_dir=batch_folder)
cert_updates_file = os.path.join(batch_folder,'cert_updates.json')
updated_records = read_updated(cert_updates_file)

input_file = 'cert_reference.csv'
pcn = 'PCN name'

wsdl = os.path.join('resources','Plex_SOAP_prod.wsdl')
pc = ClassicDataSource(auth=pcn,test_db=True,wsdl=wsdl)

with open(input_file,'r',encoding='utf-8-sig') as f:
    c = csv.DictReader(f)
    for r in c:
        try:
            ci = ClassicDataSourceInput(57073)
            supplier_code = r['Delete - Supplier Code'] # just for reference
            cert_name = r['Delete - Certification'] # just for reference
            ci.MP1_Supp_Cert_List_Key = r['Supplier_Cert_List_Key']
            ci.MP1_Begin_Date = r['Begin_Date']
            if not r['Begin_Date']:
                # Some certs possibly had no begin date in classic which is not allowed in the data source.
                logger.warning(f'{pcn} - {supplier_code} - {cert_name} : {r["Note"]} - Missing start date.')
                continue
            ci.MP1_Expiration_Date = r['Expiration_Date']
            ci.MP1_Note = r['Note']
            ci.MP1_Parent = r['Parent']
            ci.MP_Supplier_Cert_Key = r['Supplier_Cert_Key']
            ci.Cert_Supplier_No = r['Cert_Supplier_No']
            log_record = {k:v for k,v in vars(ci).items() if not k.startswith('_')}
            if log_record in updated_records:
                continue
            response = pc.call_data_source(ci)
            logger.info(f'{pcn} - {supplier_code} - {cert_name} - Added')
            updated_records.append(log_record)
        except ClassicConnectionError as e:
            logger.error(f'{pcn} - {supplier_code} - {cert_name} - Failed to be added - {str(e)}')
        finally:
            save_updated(cert_updates_file,updated_records)