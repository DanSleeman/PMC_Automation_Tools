from pmc_automation_tools import UXDataSourceInput, UXDataSource, save_updated, read_updated, setup_logger, create_batch_folder
import csv
in_file = 'plex_sql_report.csv'
ds_id = '2360'
pcn = '123456'
update_file = 'updated_records.json'
batch_folder = create_batch_folder(test=True)
logger = setup_logger('Container Updates',log_file='Container_Updates.log',root_dir=batch_folder,level=10) #level=logging.DEBUG
ux = UXDataSource(pcn, test_db=True)
updates = read_updated(update_file)
with open(in_file,'r',encoding='utf-8-sig') as f: # use utf-8-sig if exporting a CSV from classic SDE
    c = csv.DictReader(f)
    for r in c:
        container_type = r['Container_Type']
        try:
            u = UXDataSourceInput(ds_id, template_folder='templates')
            u.pop_inputs(keep=[])
            for k,v in r.items():
                setattr(u,k,v)
            log_record = {k:v for k,v in vars(u).items() if not k.startswith('_')}
            u.pop_inputs('Container_Type')
            u.type_reconcile()
            u.purge_empty()
            if log_record in updates:
                continue
            r = ux.call_data_source(u)
            updates.append(log_record)
            logger.info(f'{pcn} - Datasource: {ds_id} - Container Type: {container_type} Updated.')
        except:
            logger.error(f'{pcn} - Datasource: {ds_id} - Container Type: {container_type} Failed to update.')
        finally:
            save_updated(update_file, updates)