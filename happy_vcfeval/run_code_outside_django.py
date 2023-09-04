import precision_medicine
import precision_medicine_config as config # Config file containing variables

with open("/var/www/django/benchmarking_tool_dev/mokaguys_project/.env") as env:
    for line in env.readlines():
        if line.startswith("NEXUS_API_KEY"):
            config.Nexus_API_Key = str(line.split("=")[-1].rstrip())
        if line.startswith("EMAIL_USER"):
            config.EMAIL_USER = str(line.split("=")[-1].rstrip())
        if line.startswith("EMAIL_PASSWORD"):
            config.EMAIL_PASSWORD = str(line.split("=")[-1].rstrip())
config.MEDIA_URL= '/benchmark-dev/files/'

# Upload to nexus and run app
def run_prec_med(email, vcf_filepath, bed_filepath, genome_build):
    # Create upload2Nexus() object
    upload = precision_medicine.upload2Nexus()
    # Pass inputs to object, which will trigger the workflow that runs the DNAnexus app and reports results
    upload.take_inputs(email, vcf_filepath, bed_filepath, genome_build)

email="aledjones@nhs.net"
vcf_filepath="/var/www/django/benchmarking_tool_dev/media/230802_155543/18G002189.markDup.recalibrated.OnTarget.q8.bam.HaplotypeCaller.snp.indel.vcf"
bed_filepath="/var/www/django/benchmarking_tool_dev/media/230802_155543/Bromptome_V5_hg38_100bp_Flanking.bed"
genome_build="GRCh38"
run_prec_med(email, vcf_filepath, bed_filepath, genome_build)