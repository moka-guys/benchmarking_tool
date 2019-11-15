import gzip
import os
import smtplib
import subprocess
import sys
import zipfile
import time

from django.conf import settings
from email.Message import Message
import precision_medicine_config as config # Config file containing variables


class upload2Nexus(object):
    """
    Submits jobs to dnanexus_happy app from web interface, and returns results via email.
    Takes an email address, vcf filepath and optional bed filepath as inputs (via take_inputs() method)
    (The filepaths are the full filepaths to the uploaded files on the server)
    """

    def __init__(self):
        #  variables that are set from  inputs
        self.email = ""
        self.vcf_filepath = ""
        self.vcf_basename = ""
        self.vcf_basename_orig = ""
        self.bed_filepath = ""
        self.bed_basename = ""
        self.app_panel_bed = ""

        self.vcf_header = os.path.dirname(os.path.realpath(__file__)) + "/vcf_header.vcf"

        ################ Working dir ###############################
        # where will the files be downloaded to/from?
        self.directory = ""
        self.timestamp = ""

        # log file variables
        self.logfile = ""
        self.logfile_name = ""

        ################ DNA Nexus###############################
        # path to upload agent
        self.upload_agent = config.upload_agent

        # source command
        self.source_command = "#!/bin/bash\n. /etc/profile.d/dnanexus.environment.sh\n"

        # dx run commands and components
        self.auth = " --auth-token " + config.Nexus_API_Key  # authentication string
        self.nexusprojectstring = "  --project  "  # nexus project
        self.dest = " --folder "  # nexus folder
        self.nexus_folder = "/Tests/"  # path to files in project
        self.end_of_upload = " --do-not-compress "  # don't compress upload
        self.base_cmd = "jobid=$(dx run " + config.app_project_id + config.app_path + " -y"  # start of dx run command
        self.token = " --brief --auth-token " + config.Nexus_API_Key + ")"  # authentication for dx run

        # variable to catch the analysis id of job
        self.analysis_id = ""

        ################ Emails###############################
        self.you = [config.you]
        self.smtp_do_tls = True
        self.email_subject = ""
        self.email_message = ""
        self.email_priority = 3

        self.generic_error_email = config.user_error_message

    def take_inputs(self, email, vcf_file, bed_file):
        """Captures the input arguments (email, vcf_file, bed_file)"""

        # assign inputs to self variables
        self.email = email
        self.vcf_filepath = vcf_file
        # build path and filename
        self.vcf_basename = os.path.basename(self.vcf_filepath)
        # The vcf_basename will get updated after the vcf has been stripped
        # store the original filename so it can be included in results
        self.vcf_basename_orig = self.vcf_basename
        self.directory = os.path.dirname(self.vcf_filepath)

        # if a bed file has been supplied...
        if bed_file:
            self.bed_filepath = bed_file
            # build path and filename. os.path.basename() extracts the filename from a path.
            self.bed_basename = os.path.basename(self.bed_filepath)

        # Capture timestamp.
        # When the files are uploaded a timestamp is generated, and the files are uploaded to a folder called .../<timestamp>
        # self.directory is the full directory path for the uploaded files
        # e.g. /home/mokagals/mokaguys_project/media/171115_171920
        # Timestamp is extracted by splitting on '/' and capturing the last element
        self.timestamp = self.directory.split("/")[-1]

        # add vcf and timestamp to the generic error email message
        self.generic_error_email = "vcf = " + self.vcf_basename_orig + "\n\n" + self.generic_error_email + self.timestamp

        # update nexus folder so it is Tests/timestamp
        self.nexus_folder = self.nexus_folder + self.directory.split("/")[-1]

        # use  timestamp to create the logfile name
        self.logfile_name = os.path.join(self.directory, self.timestamp + "_logfile.txt")

        ##### SKIP VCF STRIP FUNCTION, SEE https://github.com/moka-guys/benchmarking_tool/issues/36 #####
        #self.vcf_strip()

        # call function to upload to nexus
        self.upload_to_Nexus()

    def vcf_strip(self):
        """
        Removes the header from vcf and replaces with a stock header and removes unnecessary fields.
        This is to avoid errors when processing
        """
        # write to logfile
        self.logfile = open(self.logfile_name, 'w')
        self.logfile.write("email=" + self.email + "\noutput=" + self.timestamp + "\nvcf_filepath=" + self.vcf_filepath
                           + "\nbed_filepath=" + self.bed_filepath + "\n")
        # record in log file steps taken
        self.logfile.write("removing unnecessary fields from VCF\n")
        self.logfile.close()
        # create new file name for modified vcf
        output_vcf = self.vcf_filepath + '_stripped.vcf.gz'

        # check if zipped or not to define settings used to read the file
        if self.vcf_filepath.endswith('.gz'):
            open_func = gzip.open
            open_mode = 'rb'
        else:
            open_func = open
            open_mode = 'r'
        try:
            # open vcf header as t and the query vcf with the required settings as q and output file as binary output o
            with open(self.vcf_header, 'r') as t, open_func(self.vcf_filepath, open_mode) as q, gzip.open(output_vcf, 'wb') as o:
                # for each line in q if it's not a header take the first 6 columns of each row, then add two full stops
                # (replacing the filter and info ). Then remove everything except the GT field of format and sample
                # fields. These fields are delimited by colon (:) so split on colon, then use .index() list method to
                # get index of GT field so it can be retained.
                output = "\n".join(["\t".join(line.rstrip().split('\t')[:6]
                                              + ['.'] * 2
                                              + [line.rstrip().split('\t')[8].split(":")[
                                                     line.rstrip().split('\t')[8].split(":").index("GT")]]
                                              + [line.rstrip().split('\t')[9].split(":")[
                                                     line.rstrip().split('\t')[8].split(":").index("GT")]])
                                    for line in q if not line.startswith('#')])
                # write output with new header
                o.write(t.read() + "\n" + output)

        except Exception, e:
            # send an error email to mokaguys
            self.email_subject = "Benchmarking Tool: stderr reported when running job "
            self.email_priority = 1  # high priority
            self.email_message = ("vcf=" + self.vcf_basename_orig + "\nemail=" + self.email + "\noutput="
                                  + self.timestamp + "\nerror=" + str(e))  # state all inputs and error
            self.send_an_email()

            # send an error email to user
            self.email_subject = "Benchmarking Tool: Invalid VCF file "
            self.email_priority = 1  # high priority
            self.email_message = ("An error was encountered whilst reading VCF:\n" + self.vcf_basename_orig
                                  + "\n\nPlease ensure that the VCF (.vcf) or gzipped VCF (.vcf.gz) file supplied "
                                    "conforms to the VCF specification, is sorted, and includes genotype information "
                                    "(using GT tag) in the FORMAT and SAMPLE fields.\n\nIf you continue to experience "
                                    "issues please reply to this email quoting the below code:\n\n" + self.timestamp)
            self.you = [self.email]
            self.send_an_email()

            # write error to log file
            self.logfile = open(self.logfile_name, 'a')
            self.logfile.write("Error whilst stripping VCF file:" + str(e) + "\nEXITING")
            self.logfile.close()

            # exit the script because an error was encountered.
            sys.exit()

        # set the new files asvariables used to upload to nexus etc.
        self.vcf_filepath = output_vcf
        self.vcf_basename = os.path.basename(self.vcf_filepath)

        # call next function to upload to nexus
        self.upload_to_Nexus()

    def upload_to_Nexus(self):
        """Uploads vcf/bed files to Nexus"""
        # write to logfile
        self.logfile = open(self.logfile_name, 'a')
        self.logfile.write("uploading to nexus\n")
        self.logfile.close()

        # create bash script name
        upload_bash_script_name = os.path.join(self.directory, self.timestamp + "_upload.sh")

        # open bash script
        upload_bash_script = open(upload_bash_script_name, 'w')

        # upload command
        # eg path/to/ua  --auth-token abc  --project  projectname --folder /nexus/path --do-not-compress /file/to/upload
        # .format() method used to enclose vcf and bed filepaths in quotes incase there's any characters in filenames
        # that could break the command (although all special characters should have been removed in an earlier step)
        upload_cmd = (self.upload_agent + self.auth + self.nexusprojectstring + config.data_project_id.replace(":", "")
                      + self.dest + self.nexus_folder + self.end_of_upload + "'{}'".format(self.vcf_filepath))
        if self.bed_filepath:
            upload_cmd += ("\n" + self.upload_agent + self.auth + self.nexusprojectstring
                           + config.data_project_id.replace(":", "") + self.dest + self.nexus_folder + self.end_of_upload
                           + "'{}'".format(self.bed_filepath))

        # write the source and upload cmds
        upload_bash_script.write(self.source_command)
        upload_bash_script.write(upload_cmd)

        # close bash script
        upload_bash_script.close()

        # run the command
        proc = subprocess.Popen(["bash " + upload_bash_script_name], stderr=subprocess.STDOUT, stdout=subprocess.PIPE
                                , shell=True)

        # capture the streams (err is redirected to out above)
        (out, err) = proc.communicate()
        self.logfile = open(self.logfile_name, 'a')
        self.logfile.write(out + "\n")
        self.logfile.close()
        # call next function
        self.run_app()

        # delete shell script - this will only happend once the script has finished running
        os.remove(upload_bash_script_name)
        self.logfile = open(self.logfile_name, 'a')
        self.logfile.write("deleting upload script\nFIN")
        self.logfile.close()

    def run_app(self):
        """Runs DNANexus hap.py workflow"""
        # write to logfile
        self.logfile = open(self.logfile_name, 'a')
        self.logfile.write("running app\n")
        self.logfile.close()
        # create bash script name
        run_bash_script_name = os.path.join(self.directory, self.timestamp + "_run.sh")

        # print run_bash_script_name

        # open script
        run_bash_script = open(run_bash_script_name, 'w')

        # If a bedfile has been submitted, update the -ipanel_bed argument to use the users bed file rather than the
        # default WES capture kit bedfile specified in the config file (config.app_panel_bed). Need to construct path to bedfile in DNANexus
        # project
        if self.bed_filepath:
            self.app_panel_bed = " -ipanel_bed=" + "'{}'".format(
                config.data_project_id + self.nexus_folder + "/" + self.bed_basename)
        else:
            self.app_panel_bed = config.app_panel_bed
        # dx run command
        # Construct the dx run command to submit hap.py job and capture returned job id.
        dxrun_cmd = (self.base_cmd + config.app_query_vcf + "'{}'".format(config.data_project_id + self.nexus_folder + "/"
                     + self.vcf_basename) + config.app_prefix + "happy." + self.vcf_basename_orig.split(".vcf")[0]
                     + config.app_truth_vcf + self.app_panel_bed + config.app_high_conf_bed + config.app_truth + self.dest
                     + self.nexus_folder + self.token)

        # write source cmd
        run_bash_script.write(self.source_command)
        # can't use dest and project together so inorder to specify dest need to preselect the project
        run_bash_script.write("dx select " + config.data_project_id.replace(":", "") + " " + self.auth + "\n")
        # write dx run cmd
        run_bash_script.write(dxrun_cmd + "\n")
        # echo the job id to use to monitor progress
        run_bash_script.write("echo $jobid")
        # close bash script
        run_bash_script.close()

        # run the bash script containing dx run command
        proc = subprocess.Popen(["bash " + run_bash_script_name], stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                shell=True)

        # capture the streams 
        (out, err) = proc.communicate()
        if err:
            # send an error email to mokaguys
            self.email_subject = "Benchmarking Tool: stderr reported when running job "
            self.email_priority = 1  # high priority
            self.email_message = ("vcf=" + self.vcf_basename_orig + "\nemail=" + self.email + "\noutput="
                                  + self.timestamp + "\nerror=" + err)  # state all inputs and error
            self.send_an_email()

            # send a error email to user
            # Change self.you to the user's email address rather than mokaguys
            self.you = [self.email]
            self.email_subject = config.user_error_subject
            self.email_message = self.generic_error_email
            self.send_an_email()

            self.logfile = open(self.logfile_name, 'a')
            self.logfile.write(out + "\nEXITING")
            self.logfile.close()
            # exit
            sys.exit()
        else:
            self.logfile = open(self.logfile_name, 'a')
            self.logfile.write(out + "\n")
            self.logfile.close()
            # capture the job id
            self.analysis_id = "job" + out.split('job')[-1]
            # call function which monitors progress
            self.monitor_progress()
            # once the script finishes delete the .sh script
            os.remove(run_bash_script_name)
            self.logfile = open(self.logfile_name, 'a')
            self.logfile.write("deleting run script\n")
            self.logfile.close()

    def monitor_progress(self):
        """Monitors the job and alerts if it has failed"""
        # write to logfile
        self.logfile = open(self.logfile_name, 'a')
        self.logfile.write("monitoring progress\n")
        self.logfile.close()
        # command which returns a job-id within the project if successfully completed
        status_cmd = ("dx find jobs --project " + config.data_project_id + " --id " + self.analysis_id.rstrip()
                      + " --brief --state done")

        # create bash script name
        status_bash_script_name = os.path.join(self.directory, self.timestamp + "_status.sh")
        # open script
        status_bash_script = open(status_bash_script_name, 'w')
        # write the source cmd
        status_bash_script.write(self.source_command + "\n")
        # write the status command
        status_bash_script.write(status_cmd + "\n")
        # close bash script
        status_bash_script.close()

        # command which returns a job-id within the project if successfully completed
        fail_status_cmd = ("dx find jobs --project " + config.data_project_id + " --id " + self.analysis_id.rstrip()
                           + " --brief --state failed")

        # create bash script name
        fail_status_bash_script_name = os.path.join(self.directory, self.timestamp + "_fail_status.sh")
        # open script
        fail_status_bash_script = open(fail_status_bash_script_name, 'w')
        # write the source cmd
        fail_status_bash_script.write(self.source_command + "\n")
        # write the status command
        fail_status_bash_script.write(fail_status_cmd + "\n")
        # close bash script
        fail_status_bash_script.close()

        # initialise count variable, used to count how long app has been running for
        count = 0
        # call check status module to execute the script. will only return true when job-id is found
        while not self.check_status(status_bash_script_name):
            # use count to apply a time out limit    
            # if has been running for < 45 mins
            if count < 45:

                # write to logfile
                self.logfile = open(self.logfile_name, 'a')
                self.logfile.write("job not finished. waited for " + str(count) + " minutes so far\n")
                self.logfile.close()

                # increase count
                count += 1

                # wait for 1 mins
                time.sleep(60)

                # check if it's failed
                if self.check_status(fail_status_bash_script_name):
                    # if failed increase count to stop the loop
                    count += 100
            else:
                # if has been running for 45 mins stop or the job has failed
                # access the error message from the app:
                # command which returns stderr from job
                error_cmd = "dx watch " + self.analysis_id.rstrip() + "  --no-timestamps --get-stderr -q | tail -n 50"

                # create bash script name
                read_job_error_bash_script_name = (os.path.join(self.directory, self.timestamp
                                                                + "_read_job_error.sh"))

                # open script
                read_job_error_bash_script = open(read_job_error_bash_script_name, 'w')
                # write the source cmd
                read_job_error_bash_script.write(self.source_command + "\n")
                # write the status command
                read_job_error_bash_script.write(error_cmd + "\n")
                # close bash script
                read_job_error_bash_script.close()

                # execute the status script
                proc = subprocess.Popen(["bash " + read_job_error_bash_script_name], stderr=subprocess.PIPE,
                                        stdout=subprocess.PIPE, shell=True)
                # capture the output
                (out, err) = proc.communicate()
                # only will have stdout if the dx find jobs command terms are met (job finihsed successfully)
                if out:
                    app_std_error = out

                # send a error email
                self.email_subject = "Benchmarking Tool: job has failed or hasn't finished after 45 mins "
                self.email_priority = 1
                self.email_message = ("vcf=" + self.vcf_basename_orig + "\nemail=" + self.email + "\noutput="
                                      + self.timestamp + "\nnexus_job_id=" + self.analysis_id
                                      + "\n\nlast 50 lines of STDERR from app:\n" + app_std_error)
                self.send_an_email()

                # send a error email to user
                self.you = [self.email]
                self.email_subject = config.user_error_subject
                self.email_message = self.generic_error_email
                self.send_an_email()

                self.logfile = open(self.logfile_name, 'a')
                self.logfile.write("job has failed or hasn't finished after 45 mins!\nEmail has been sent to:"
                                   + self.email + "\nwith error message:" + self.email_message
                                   + "\n\nEXITING.\nSTDERR from app = \n" + app_std_error)
                self.logfile.close()

                # remove bash scripts
                os.remove(status_bash_script_name)
                os.remove(read_job_error_bash_script_name)
                os.remove(fail_status_bash_script_name)
                sys.exit()
        else:
            # job has finished. download output files
            self.download_result()
            # once finished remove shell script
            os.remove(status_bash_script_name)
            os.remove(fail_status_bash_script_name)
            self.logfile = open(self.logfile_name, 'a')
            self.logfile.write("deleting status scripts\n")
            self.logfile.close()

    def format_result_5dp(self, result_string):
        """If provided string can be converted to float, will round to 5dp and return as string. Otherwise will just return the string provided"""
        try:
            return str(round(float(result_string), 5))
        except ValueError:
            return result_string

    def check_status(self, status_bash_script_name):
        """Used by monitor_progress() method to check status of job"""
        # execute the status script
        proc = subprocess.Popen(["bash " + status_bash_script_name], stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                shell=True)
        # capture the output
        (out, err) = proc.communicate()
        # only will have stdout if the dx find jobs command terms are met (job finihsed successfully)
        if out:
            # return true to exit the sleep loop
            return True
        else:
            # return false to continue sleep loop
            return False

    def download_result(self):
        """Downloads hap.py results and sends results email"""
        self.logfile = open(self.logfile_name, 'a')
        self.logfile.write("Job done, downloading\n")
        self.logfile.close()

        # command to download files. downloads all files that have been output by the app (will have prefix self.output)
        download_cmd = ("dx download " + config.data_project_id + self.nexus_folder + "/happy."
                        + self.vcf_basename_orig.split(".vcf")[0] + "*" + self.auth)
        # create download script name
        download_bash_script_name = os.path.join(self.directory, self.timestamp + "_download.sh")
        # open script
        download_bash_script = open(download_bash_script_name, 'w')
        # write source cmd
        download_bash_script.write(self.source_command)
        # cd to location where files are to be downloaded
        download_bash_script.write("cd " + self.directory + "\n")
        # write download cmd
        download_bash_script.write(download_cmd + "\n")
        # close bash script
        download_bash_script.close()

        # run the command
        proc = subprocess.Popen(["bash " + download_bash_script_name], stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                shell=True)

        # capture the streams
        (out, err) = proc.communicate()
        self.logfile = open(self.logfile_name, 'a')
        self.logfile.write(out + "\n")
        self.logfile.close()
        # if error
        if err:
            self.logfile = open(self.logfile_name, 'a')
            self.logfile.write(err + "\nEXITING")
            self.logfile.close()

            # send a error email
            self.email_subject = "Benchmarking Tool: cannot download from nexus"
            self.email_priority = 1
            self.email_message = (
                "vcf=" + self.vcf_basename_orig + "\nemail=" + self.email + "\noutput=" + self.timestamp
                + "\nerr=" + err)
            self.send_an_email()

            # send a error email to user
            self.you = [self.email]
            self.email_subject = config.user_error_subject
            self.email_message = self.generic_error_email
            self.send_an_email()
            sys.exit()

        else:
            # add the user email to the email message
            self.you.append(self.email)

            # Need to parse the extended summary file to get recall and precision with confidence intervals (the normal summary file doesn't have confidence intervals)
            # This file is contained in the zip archive, so need to use zipfile module to read the file contents 
            summary_csv = (zipfile.ZipFile(os.path.join(self.directory, "happy." + self.vcf_basename_orig.split(".vcf")[0]
                           + ".zip"), 'r').open("happy." + self.vcf_basename_orig.split(".vcf")[0]
                           + '.extended.csv', 'r'))
            # loop through file and pull out results for SNPs and/or INDELs if present
            # If there are e.g. no indels in results, there will be no indel lines in the summary CSV file, so use snps_found and indels_found flags to determine what 
            # results need to be included in email 
            snps_found = False
            indels_found = False
            for line in summary_csv:
                if line.startswith("SNP,*,*,PASS"):
                    snps_found = True
                    # split the line on comma
                    splitline = line.split(",")
                    # capture required columns
                    snp_recall = self.format_result_5dp(splitline[7])
                    snp_recall_lowerCI = self.format_result_5dp(splitline[65])
                    snp_recall_upperCI = self.format_result_5dp(splitline[66])
                    snp_precision = self.format_result_5dp(splitline[8])
                    snp_precision_lowerCI = self.format_result_5dp(splitline[67])
                    snp_precision_upperCI = self.format_result_5dp(splitline[68])
                elif line.startswith("INDEL,*,*,PASS"):
                    indels_found = True
                    # split the line on comma
                    splitline = line.split(",")
                    # capture required columns
                    indel_recall = self.format_result_5dp(splitline[7])
                    indel_recall_lowerCI = self.format_result_5dp(splitline[65])
                    indel_recall_upperCI = self.format_result_5dp(splitline[66])
                    indel_precision = self.format_result_5dp(splitline[8])
                    indel_precision_lowerCI = self.format_result_5dp(splitline[67])
                    indel_precision_upperCI = self.format_result_5dp(splitline[68])
            # close file
            summary_csv.close()

            # send email
            self.email_subject = "Benchmarking Tool: Job Finished"
            self.email_priority = 3
            # Create the email body
            # Include:
            # Names of supplied VCF and BED files to identify the results
            # Name of file from which summary is taken
            self.email_message = ("Analysis complete for vcf:\n" + self.vcf_basename_orig
                                  + "\nbed (if supplied):\n" + self.bed_basename
                                  + "\n\nSummary (taken from "
                                  + "happy." + self.vcf_basename_orig.split(".vcf")[0]
                                  + ".extended.csv):\n")
            # If SNP results are present in the extended summary file, include the recall, precision and confidence intervals in the email
            if snps_found:
                self.email_message += ("\nSNP recall (sensitivity)= " + snp_recall
                                       + " (95% CI: " + snp_recall_lowerCI + " - "
                                       + snp_recall_upperCI + ")\nSNP precision (PPV) = "
                                       + snp_precision + " (95% CI: " + snp_precision_lowerCI
                                       + " - " + snp_precision_upperCI + ")")
            # If INDEL results are present in the extended summary file, include the recall, precision and confidence intervals in the email
            if indels_found:
                self.email_message += ("\nINDEL recall (sensitivity)= " + indel_recall 
                                       + " (95% CI: " + indel_recall_lowerCI + " - "
                                       + indel_recall_upperCI + ")\nINDEL precision (PPV) = "
                                       + indel_precision + " (95% CI: " + indel_precision_lowerCI 
                                       + " - " + indel_precision_upperCI + ")")
            # A link to view the detailed summary html report
            # A link to download the full output .zip archive
            # Version numbers of hap.py and the DNAnexus app that were used to produce the results
            self.email_message += ("\n\nA detailed summary report is available here:\n" + config.url
                                  + os.path.join(settings.MEDIA_URL, self.directory.split("media/")[1], "happy."
                                  + self.vcf_basename_orig.split(".vcf")[0] + ".summary_report.html")
                                  + "\n\nFull results are available here:\n" + config.url
                                  + os.path.join(settings.MEDIA_URL, self.directory.split("media/")[1], "happy."
                                  + self.vcf_basename_orig.split(".vcf")[0] + ".zip")
                                  + "\n\nThanks for using this tool!\n\nResults generated using Illumina hap.py "
                                  + config.happy_version + " (https://github.com/Illumina/hap.py) implemented in "
                                  + "Viapath Genome Informatics DNAnexus app: " + os.path.basename(config.app_path))
            self.send_an_email()
            self.logfile = open(self.logfile_name, 'a')
            self.logfile.write("finished download.\ndeleting download script\n")
            self.logfile.close()
            # delete download bash script
            os.remove(download_bash_script_name)

    def send_an_email(self):
        """function to send an email. uses self.email_subject, self.email_message and self.email_priority"""
        # create message object
        m = Message()
        # set priority
        m['X-Priority'] = str(self.email_priority)
        # set subject
        m['Subject'] = self.email_subject
        # set body
        m.set_payload(self.email_message)

        # server details
        server = smtplib.SMTP(host=config.host, port=config.port, timeout=10)
        server.set_debuglevel(1)  # verbosity
        server.starttls()
        server.ehlo()
        server.login(config.user, config.pw)
        server.sendmail(config.me, self.you, m.as_string())
