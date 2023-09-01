# Benchmarking Tool Interface v1.8

## What does this app do?
This project contains the code for the Django web interface (https://genomics.viapath.co.uk/benchmark) for the precision medicine hap.py DNAnexus app (https://github.com/moka-guys/dnanexus_happy).  Users can upload a VCF and BED file, then select the appropriate reference build (Genome Reference Consortium Human Build 37 or 38).

## Installation
* install Apache and Apache WSGI module `sudo apt-get install apache2 libapache2-mod-wsgi`
* install pip: `sudo apt-get install python-pip`
* Install Django (Python 2.7): `pip install Django`
* Install django-widget-tweaks: `pip install django-widget-tweaks`
* Install modules to keep credentials in environment variables: `pip install python-dotenv`
* Install modules to keep credentials in environment variables: `pip install django-environ`
* Install DNAnexus SDK and upload agent.
* Clone this repository.
* Some settings files containing sensitive information are stored outside of this repository. Copy the following files and folders from the `170921_Benchmarking_Backup/mokaguys_project/` folder on MokaNAS:
  * .env file
  * media/ (folder and contents)
  * known_issues.txt
  * new_features.txt
  * db.sqlite3
  * .env (file contains sensitive credentials outside version control)
* Update the settings.py and precision_medicine_config.py files as appropriate
* Make sure the `www-data` user (i.e. Apache) has write access to the media folder and subfolders. If necessary this can be added with:
  * `sudo chgrp -R www-data ./media/` Makes www-data group owner
  * `sudo chmod -R g+w ./media/` Grants write access to group
* Update the following Apache config files (See the examples on MokaNAS2 in `170921_Benchmarking_Backup/Apache_conf_files/` and Django docs):
  * /etc/apache2/sites-available/000-default.conf (HTTP)
  * /etc/apache2/sites-available/000-default-le-ssl.conf OR /etc/apache2/sites-available/default-ssl.conf (HTTPS)
* Restart web server `sudo service apache2 restart`

## Development site
* There is a dev site hosted at https://genomics.viapath.co.uk/benchmark-dev. It requires mokaguys login (setup with htpasswd). 

## Additional Information
* The standard structure for a Django application is to have 'apps' (e.g. tools) within a 'project' (e.g. website). In this case **project level** files are found in `benchmarking_tool/mokaguys_project/`, whilst **app level** files are found in `benchmarking_tool/happy_vcfeval/`.
* If there are any known issues that users should be made aware of, these can be added to the `known_issues.txt` file. These will be displayed in a banner at the top of the web page.
* If there are any new features that users should be made aware of, these can be added to the `new_features.txt` file. These will be displayed in a banner at the top of the web page.

## Usage
A user guide is available on the homepage of the app (https://genomics.viapath.co.uk/benchmark)


## Created by
* The app was made by the Viapath Genome Informatics section
