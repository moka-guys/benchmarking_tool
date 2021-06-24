'''
DNA Nexus Upload agent configuration
'''
#set debug mode
#debug=True
debug=False

#IP address for the server
url="https://genomics.viapath.co.uk"

########################## DNA Nexus setting#############################
#Upload agent path
upload_agent = "/opt/dnanexus-upload-agent-1.5.30-linux/ua"

import os
# read in secret credentials from .env file
from dotenv import load_dotenv
dirname = os.path.dirname(__file__)
env_path = os.path.abspath(os.path.join(dirname + "/.env"))
load_dotenv(env_path)
# load_dotenv("/var/www/django/benchmarking_tool_dev/.env")  # take environment variables from .env.

# SECURITY WARNING: To keep the Nexus_API_Key used in production secret
# it is stored outside version control in .env
Nexus_API_Key = os.environ.get("NEXUS_API_KEY")

# The project containing the app
app_project_id="project-ByfFPz00jy1fk6PjpZ95F27J:"

#The project containing the data
data_project_id="project-FY41yg00bXYjkqP8350F7Ykz:"

# Files for genome build 37
app_truth_vcf_37=" -itruth_vcf='project-ByfFPz00jy1fk6PjpZ95F27J:file-F3V5kgj0jy1b0qFG53k8Ffj4'"     
app_panel_bed_37= " -ipanel_bed='project-ByfFPz00jy1fk6PjpZ95F27J:file-F25VXZj0ybjzxpg0JvppGgQq'"
app_high_conf_bed_37= " -ihigh_conf_bed='project-ByfFPz00jy1fk6PjpZ95F27J:file-F45P6k80jy1jpv6J9G8gG3P0'"
# Files for genome build 38
app_truth_vcf_38=" -itruth_vcf='project-ByfFPz00jy1fk6PjpZ95F27J:file-G2BfBGQ0xkZ2qxf92gGVQq4K'"     
app_panel_bed_38= " -ipanel_bed='project-ByfFPz00jy1fk6PjpZ95F27J:file-G2Gb8F00xkZ7kz646J88gZzK'"
app_high_conf_bed_38= " -ihigh_conf_bed='project-ByfFPz00jy1fk6PjpZ95F27J:file-G2BfBGj0xkZ9V31YPj9xxg1J'"

# App inputs
app_query_vcf=" -iquery_vcf="      
app_prefix=" -iprefix="
app_truth=" -ina12878='false'"

#path to app
app_path="Apps/vcfeval_hap.py/vcfeval_hap.py_v1.4.0"

#hap.py version number
happy_version="v0.3.9"

#Benchmarking tool version
tool_version="v1.6"

################ Emails###############################
# SECURITY WARNING: To keep the credentials used in production secret
# user and password are stored outside version control in .env
user = os.getenv("EMAIL_USER")
pw   = os.getenv("PW")
host = 'email-smtp.eu-west-1.amazonaws.com'
port = 587
# The address that will be spoofed
me   = 'moka.alerts@gstt.nhs.uk'
# Moka guys address which will receive a copy of sent  email
you  = 'gst-tr.mokaguys@nhs.net'

user_error_subject="Benchmarking Tool: An error has occurred "
user_error_message=(
        "An error has occurred when benchmarking your results. "
        "Ensure that the VCF (.vcf) or gzipped VCF (.vcf.gz) file supplied "
        "conforms to the VCF specification, is sorted, and includes genotype information "
        "(using GT tag) in the FORMAT and SAMPLE fields. "
        "If supplying a bed file, please ensure it is sorted and uses zero-based coordinates"
        "Please see error message below and contact gst-tr.mokaguys@nhs.net quoting the timestamp below "
        "if you require any further assistance.\n\n"
    )
