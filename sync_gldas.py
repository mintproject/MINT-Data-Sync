from bs4 import BeautifulSoup
import requests 
from requests.auth import HTTPBasicAuth
from requests import Request, Session

import os

import datetime
import pprint
import uuid


earthdata_username = 'read from ENV variable'
earthdata_password = 'read from ENV variable'

mint_data_username = 'read from ENV variable'
mint_data_password = 'read from ENV variable'

def prepare_env():

	if 'earthdata_username' in os.environ:
		global earthdata_username
		earthdata_username = os.environ['earthdata_username']
	else:
		raise Exception(f"'earthdata_username' environment variable is not set")


	if 'earthdata_password' in os.environ:
		global earthdata_password
		earthdata_password = os.environ['earthdata_password']
	else:
		raise Exception(f"'earthdata_password' environment variable is not set")


	if 'mint_data_username' in os.environ:
		global mint_data_username
		mint_data_username = os.environ['mint_data_username']
	else:
		raise Exception(f"'mint_data_username' environment variable is not set")


	if 'mint_data_password' in os.environ:
		global mint_data_password
		mint_data_password = os.environ['mint_data_password']
	else:
		raise Exception(f"'mint_data_password' environment variable is not set")


	# Access to earthdata requires .netrc file
	open(f"{os.environ['HOME']}/.netrc", 'w').write(f"machine urs.earthdata.nasa.gov login {earthdata_username} password {earthdata_password}")



def handle_api_response(response, print_response=False):
    pp = pprint.PrettyPrinter(indent=2)
    parsed_response = response.json()

    if print_response:
        pp.pprint({"API Response": parsed_response})

    if response.status_code == 200:
        return parsed_response
    elif response.status_code == 400:
        raise Exception("Bad request")
    elif response.status_code == 403:
        msg = "Please make sure your request headers include X-Api-Key and that you are using correct url"
        raise Exception(msg)
    else:
        msg = "500 Error"
        raise Exception(msg)


def metadata_from_gldas_filename(filename):
	# e.g., GLDAS_NOAH025_3H.A20191130.0000.021.nc4:
	# date: 2019-11-30
	# time_start = 00:00
	# time_end = time_start + 2:59:59 

	parts = filename.split(".")
	date_str = parts[1][1:]
	date = datetime.datetime.strptime(date_str, "%Y%m%d")

	hhmm_start_str = parts[2]
	hhmm = datetime.datetime.strptime(hhmm_start_str, "%H%M")

	temporal_coverage_start = date.replace(hour=hhmm.hour)
	temporal_coverage_end = temporal_coverage_start + datetime.timedelta(hours=2, minutes=59, seconds=59)

	year = date.strftime("%Y")
	day_of_year = date.strftime("%j")

	return {
		'year': year,
		'day_of_year': day_of_year,
		'temporal_coverage_start': temporal_coverage_start.isoformat().split(".")[0],
		'temporal_coverage_end': temporal_coverage_end.isoformat().split(".")[0]
	}


def generate_list_of_dates_between(start_date, end_date):
	dates = []

	for i in range((end_date - start_date).days):
		date_str = (start_date + datetime.timedelta(days=i+1)).strftime("%Y-%m-%d")
		dates.append(date_str)

	return dates



#################################################################################################################################
#################################### GLDAS ######################################################################################
#################################################################################################################################



def fetch_page(url):
	resp = requests.get(url)
	# print(resp.text)
	return resp.text


def extract_last_available_year(html_doc):
	soup = BeautifulSoup(html_doc, 'html.parser')

	years = set([])

	for link in soup.find_all('a'):
		href = link.get('href')

		if (len(href[0:-1]) > 1 and href[-1] == '/' and href[0:-1].isdigit()):
			years.add(href[0:-1])

	years = list(years)
	years.sort(reverse=True)

	return years[0]


def extract_last_available_day_of_year(html_doc):
	soup = BeautifulSoup(html_doc, 'html.parser')

	days_of_year = set([])

	for link in soup.find_all('a'):
		href = link.get('href')

		if (len(href[0:-1]) > 1 and href[-1] == '/' and href[0:-1].isdigit()):
			days_of_year.add(href[0:-1])

	days_of_year = list(days_of_year)
	days_of_year.sort(reverse=True)

	return days_of_year[0]



def get_last_available_date(last_available_year_str, last_available_day_of_year_str):
	year = int(last_available_year_str)
	day_of_year = int(last_available_day_of_year_str)

	d = datetime.datetime.strptime('{} {}'.format(day_of_year, year),'%j %Y')
	# print(d)
	return d


def list_gldas_files(gldas_url):
	html_doc = fetch_page(gldas_url)
	soup = BeautifulSoup(html_doc, 'html.parser')

	filenames = set([])
	for link in soup.find_all('a'):
		href = link.get('href')
		if len(href) > 4 and href[-3:] == 'nc4':
			filenames.add(href)

	filenames = list(filenames)
	filenames.sort()
	return filenames


def last_available_gldas_date():
	gldas_url_base = 'https://hydro1.gesdisc.eosdis.nasa.gov'


	request_path = gldas_url_base + '/data/GLDAS/GLDAS_NOAH025_3H.2.1/'
	list_of_years_html_doc = fetch_page(request_path)

	
	last_year = extract_last_available_year(list_of_years_html_doc)

	list_of_day_of_year_html_doc = fetch_page(request_path + last_year + "/")
	# print(list_of_day_of_year_html_doc)

	last_day_of_year = extract_last_available_day_of_year(list_of_day_of_year_html_doc)

	last_date = get_last_available_date(last_year, last_day_of_year)

	return last_date



def download_gldas_file(url_prefix, filename):
	# authentication is happening through ~/.netrc file
	resp = requests.get(url_prefix + filename, allow_redirects=True)

	open(filename, 'wb').write(resp.content)

	# if file size > 1000 bytes, it probably contains the data we want
	if os.stat(filename).st_size > 1000:
		return os.path.abspath(filename)
	else:
		return False



#################################################################################################################################
##################################### OWNCLOUD ##################################################################################
#################################################################################################################################


host = "https://files.mint.isi.edu/remote.php/webdav/"


src_root = "/data/storage/mint/data-catalog/production/raw-data/GLDAS"
s = Session()

def does_object_exist(rel_path):
	req_xml = '''
    <propfind xmlns="DAV:">
        <prop>
          <resourcetype />
        </prop>
    </propfind>
	'''

	path = os.path.join(host, rel_path)
	#print("Testing " + path)
	
	req = Request('PROPFIND', path, auth=(mint_data_username, mint_data_password), data=req_xml)
	prepped = req.prepare()

	prepped.headers['Content-Type'] = 'text/xml'
	prepped.headers['Depth'] = 1


	# print(prepped.headers)

	resp = s.send(prepped)
	# print(resp.status_code)
	# print(resp.text)

	if resp.status_code == 404:
		return False
	elif resp.status_code == 207:
		return True
	else:
		raise Exception("ERROR: " + resp.status_code + " -----\n " + resp.text)

def create_folder_recursive(path):
	req = Request('MKCOL', host + path, auth=(mint_data_username, mint_data_password))
	prepped = req.prepare()
	resp = s.send(prepped)

	if resp.status_code == 409:
		print("Parent node of " + path + " does not exist. Attempting to create parent folder...")
    # 409 - Parent node does not exist
		if path[-1] == "/":
			parent_path = "/".join(path.split("/")[0:-2])
		else:
			parent_path = "/".join(path.split("/")[0:-1])

		success = create_folder_recursive(parent_path)

		if success:
			create_folder_recursive(path)
		else:
			raise Exception("Could not create " + parent_path)

	elif resp.status_code == 201:
  	# 201 - success
		print("Sucessfully created " + path)
		return True
	elif resp.status_code == 405:
		# 405 - The resource you tried to create already exists
		print("The resource " + path + " already exists. Ignoring")
		return True
	else:
		return False


def list_files(root):
	result = []

	for path, subdirs, files in os.walk(root):
		for name in files:
			if ".nc4" in name:
				rel_dir = path.replace(root, '')
				if len(rel_dir) > 0 and rel_dir[0] == '/':
					# remove '/' so that rel_dir isn't interpreted as absolute path
					rel_dir = rel_dir[1:]

				filepath = os.path.join(path, name)
				result.append({
					'filename': name,
					'dirname': rel_dir,
					'filepath': filepath
				})

	return result

def upload_file(source, filename):
	data = open(source, 'rb').read()

	metadata = metadata_from_gldas_filename(filename)

	target_dir = os.path.join("GLDAS", metadata['year'], metadata['day_of_year']) + "/"
	upload_target = os.path.join(target_dir, filename)


	folder_exists = does_object_exist(target_dir)
	print(target_dir + " exists? " + str(folder_exists))

	if not folder_exists:
		print("Folder " + target_dir + " does not exist. Attempting to create...")
		create_folder_recursive(target_dir)

	if not does_object_exist(upload_target):
		print("Uploading to " + upload_target)

		req = Request('PUT', os.path.join(host, upload_target), auth=(mint_data_username, mint_data_password), data=data)
		prepped = req.prepare()
		prepped.headers['Content-Type'] = 'application/octet-stream'
		t = datetime.datetime.now()
		resp = s.send(prepped)

		# 201 - success
		# 404 - likely the directory (or directories) does not exist
		if resp.status_code == 201:
			print("Successfully uploaded " + filename + " to " + upload_target + " in " + str((datetime.datetime.now() - t)))
			return upload_target
		else:
			print(resp.status_code)
			print(resp.text)
			raise Exception("Could not upload " + filename + " to " + upload_target)
	else:
		print("File " + upload_target + " already exists. Skipping")
		return upload_target



#################################################################################################################################
##################################### DCAT ######################################################################################
#################################################################################################################################

dcat_url = "https://api.mint-data-catalog.org"
dcat_request_headers = {'Content-Type': "application/json"}

gldas_dataset_id = '5babae3f-c468-4e01-862e-8b201468e3b5'
		
def last_dcat_gldas_date():
	url = "https://api.mint-data-catalog.org/datasets/get_dataset_temporal_coverage"

	request_headers = {'Content-Type': "application/json"}

	payload = {"dataset_id": gldas_dataset_id}

	resp = requests.post(url, headers=request_headers, json=payload)

	parsed_response = handle_api_response(resp)

	# print(parsed_response)

	dataset_info = parsed_response['dataset']

	start_date = None
	end_date = None

	if dataset_info is not None and 'temporal_coverage_end' in dataset_info:
		end_date = datetime.datetime.strptime(dataset_info['temporal_coverage_end'], '%Y-%m-%d %H:%M:%S')

	return end_date



def get_dataset_variable_ids():
	resp = requests.post(f"{dcat_url}/datasets/dataset_variables", headers=dcat_request_headers, json={"dataset_id": gldas_dataset_id})

	resp_json = handle_api_response(resp)
	variable_ids = [r['variable_id'] for r in resp_json["dataset"]["variables"]]
	return variable_ids


def generate_resources_definitions(sync_state):
	resource_definitions = []

	provenance_id = "7abe6e06-6f12-47b5-8844-3ad3f659e64c"

	resource_spatial_coverage = {
        "type": "BoundingBox",
        "value": {
            "xmin": -180.0,
            "ymin": -60.0,
            "xmax": 180.0,
            "ymax": 90.0
        }
    }

	variable_ids = get_dataset_variable_ids()

	resource_type = "NetCDF"

	for filename, state in sync_state.items():
		metadata = metadata_from_gldas_filename(filename)
		resource_url = state['data_url']

		resource_definition = {
            "dataset_id": gldas_dataset_id,
            "provenance_id": provenance_id,
            "record_id": str(uuid.uuid4()),
            "variable_ids": variable_ids,
            "name": filename,
            "resource_type": resource_type,
            "data_url": resource_url,
            "metadata": {
                "spatial_coverage": resource_spatial_coverage,
                "temporal_coverage": {
                    "start_time": metadata['temporal_coverage_start'],
                    "end_time": metadata['temporal_coverage_end'],
                    "resolution": {
                        "value": 3,
                        "units": "hours"
                    }
                }
            }
        }

		resource_definitions.append(resource_definition)

	return resource_definitions


def register_resource_batch(resource_definition_batch):
    resp = requests.post(f"{dcat_url}/datasets/register_resources",
                         headers=dcat_request_headers,
                         json={"resources": resource_definition_batch})

    handle_api_response(resp, print_response=True) 



##################################################################################################################################
##################################################################################################################################
##################################################################################################################################

def sync_date(date_str):
	t = datetime.datetime.now()
	print(f"\n\nStarting syncing {date_str}\n\n")
	date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
	year = date.strftime("%Y")
	day_of_year = date.strftime("%j")

	gldas_data_page = f"https://hydro1.gesdisc.eosdis.nasa.gov/data/GLDAS/GLDAS_NOAH025_3H.2.1/{year}/{day_of_year}/"
	filenames = list_gldas_files(gldas_data_page)

	sync_state = {}

	# download locally
	for filename in filenames:
		downloaded_to = download_gldas_file(gldas_data_page, filename)
		if downloaded_to:
			print(f"Downloaded {filename} to {downloaded_to}")
			sync_state[filename] = {'local_path': downloaded_to}
		else:
			raise Exception(f"Did not download {filename}")


	# upload to owncloud
	for filename in filenames:
		upload_target = upload_file(sync_state[filename]['local_path'], filename)
		upload_target_parts = upload_target.split("/")
		
		upload_year = upload_target_parts[1]
		upload_doy = upload_target_parts[2]
		upload_filename = upload_target_parts[3]

		prefix = "https://files.mint.isi.edu/s/OHUdhphbirUoJ8o/download?path="

		data_url = prefix + "/" + upload_year + "/" + upload_doy + "&files=" + upload_filename

		sync_state[filename]['data_url'] = data_url



	resource_definitions = generate_resources_definitions(sync_state)
	print(resource_definitions)

	register_resource_batch(resource_definitions)

	for filename in filenames:
		os.remove(filename)

	print(f"\n\nFinished syncing {date_str} in {datetime.datetime.now() - t}\n\n -----------------------------------------------------------------------------")



def main():
	prepare_env()

	last_gldas_date = last_available_gldas_date()
	last_dcat_date = last_dcat_gldas_date()
	missing_dates = generate_list_of_dates_between(last_dcat_date, last_gldas_date)


	for date_str in missing_dates:
		sync_date(date_str)

	# download_gldas(last_dcat_date)


if __name__ == '__main__':
    main()