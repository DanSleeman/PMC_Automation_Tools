import pmc_automation_tools as pa

in_file = 'popup_errors.json'
out_file = 'popup_errors.csv'
obj = pa.read_updated(in_file)
pa.save_updated(out_file, obj)