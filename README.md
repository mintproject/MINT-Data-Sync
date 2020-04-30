# MINT-Data-Sync
Scripts to download new datasets as it becomes available and register them in MINT Data Catalog

## Instructions

### 1. Clone this repo 

```git clone https://github.com/mintproject/MINT-Data-Sync.git```

### 2. Go into the directory

```cd MINT-Data-Sync```

### 3. Build Docker image

```docker build -t mint-data-sync```

### 4. Run it 

```docker run -e "earthdata_username=REPLACE_ME" -e "earthdata_password=REPLACE_ME" -e "mint_data_username=REPLACE_ME" -e "mint_data_password=REPLACE_ME" -it --rm mint-data-sync:latest```

By default, the above container will start a cron process that will trigger `sync.py` script every day at 01:00 (am). That logic can be modified
by editing `cronjobs` file and rebuilding the Docker image


