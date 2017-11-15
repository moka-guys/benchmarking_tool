# Benchmarking Tool Interface v1.1

## What does this app do?
This project contains the code for the Django web interface (https://stickie.be/nch/) for the precision medicine hap.py DNAnexus app (https://github.com/moka-guys/dnanexus_happy)


## Installation
* install pip: `sudo apt-get install python-pip`
* Install Django (Python 2.7): `pip install Django`
* Install django-widget-tweaks: `pip install django-widget-tweaks`
* Install DNAnexus SDK and upload agent.
* Clone this repository into ~/apps.
* Some settings files containing sensitive information are stored outside of this repository. Copy the following files and folders from the `170921_Benchmarking_Backup/mokaguys_project/` folder on MokaNAS:
  * mokaguys_project/settings.py
  * happy_vcfeval/precision_medicine_config.py
  * media/ (folder and contents)
  * known_issues.txt
  * new_features.txt
  * db.sqlite3
* Give the `www-data` user (i.e. Apache) write access to the media folder and subfolders:
  * `sudo chgrp -R www-data ~/apps/mokaguys_project/media/` Adds www-data to group
  * `sudo chmod -R g+w ~/apps/mokaguys_project/media/` Grants write access to group
* Update settings files and file paths in mokaguys_project/happy_vcfeval/precision_medicine.py as required.
* Update the following Apache config files (See the examples on MokaNAS in `170921_Benchmarking_Backup/Apache_conf_files/`):
  * /etc/apache2/sites-available/000-default.conf (HTTP)
  * /etc/apache2/sites-available/000-default-le-ssl.conf (HTTPS)
* Restart web server `sudo service apache2 restart`

## Additional Information
* The standard structure for a Django application is to have 'apps' (e.g. tools) within a 'project' (e.g. website). In this case **project level** files are found in `mokaguys_project/mokaguys_project/`, whilst **app level** files are found in `mokaguys_project/happy_vcfeval/`.
* If there are any known issues that users should be made aware of, these can be added to the `known_issues.txt` file. These will be displayed in a banner at the top of the web page.

## Usage
A user guide is available on the homepage of the app (https://stickie.be/nch/)


## Created by
* The app was made by the Viapath Genome Informatics section
