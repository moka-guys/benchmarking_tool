
import os
import smtplib
import subprocess
import sys
import zipfile
import time

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
        self.user_email = ""
        self.vcf_filepath = ""
        self.vcf_basename = ""
        self.vcf_basename_orig = ""
        self.bed_filepath = ""
        self.bed_basename = ""
        self.app_panel_bed = ""
        self.genome_build  = ""

        ################ Working dir ###############################
        # where will the files be downloaded to/from?
        self.directory = ""
        self.timestamp = ""

        # log file variables
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
        self.genome_build_cmd = " -igenome_reference='"
        self.nexus_folder = "/Tests/"  # path to files in project
        self.end_of_upload = " --do-not-compress "  # don't compress upload
        self.base_cmd = "jobid=$(dx run " + config.app_project_id + config.app_path + " -y --instance-type mem1_ssd1_v2_x2"  # start of dx run command
        self.token = " --brief --auth-token " + config.Nexus_API_Key + ")"  # authentication for dx run

        # variable to catch the id of job
        self.jobid = ""

    def take_inputs(self, email, vcf_file, bed_file, genome_build):
        """Captures the input arguments (email, vcf_file, bed_file)"""

        # assign inputs to self variables
        self.user_email = email
        self.vcf_filepath = vcf_file
        self.genome_build = genome_build
        # build path and filename
        self.vcf_basename = os.path.basename(self.vcf_filepath)
        # The vcf_basename will get updated after the vcf has been stripped
        # store the original filename so it can be included in results
        self.vcf_basename_orig = self.vcf_basename
        self.directory = os.path.dirname(self.vcf_filepath)

        # Select correct files from the config file for the selected genome build
        if self.genome_build == "GRCh37":
            self.app_truth_vcf = config.app_truth_vcf_37
            self. app_high_conf_bed = config.app_high_conf_bed_37
        elif self.genome_build == "GRCh38":
            self.app_truth_vcf = config.app_truth_vcf_38 
            self.app_high_conf_bed = config. app_high_conf_bed_38
        else:
            # write error to log file
            with open(self.logfile_name, 'a') as logfile:
                logfile.write("Benchmarking Tool: Selected genome build not recognised: " + self.genome_build)

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
        self.user_error_message = "vcf = %s\n%s\ntimestamp=%s" % (self.vcf_basename_orig , config.user_error_message, self.timestamp)

        # update nexus folder so it is Tests/timestamp
        self.nexus_folder = self.nexus_folder + self.directory.split("/")[-1]

        # use  timestamp to create the logfile name
        self.logfile_name = os.path.join(self.directory, self.timestamp + "_logfile.txt")

        # call function to upload to nexus
        self.upload_to_Nexus()

    def upload_to_Nexus(self):
        """Uploads vcf/bed files to Nexus"""
        with open(self.logfile_name, 'a') as logfile:
            logfile.write("uploading to nexus\n")
        
        # create bash script name
        upload_bash_script_name = os.path.join(self.directory, self.timestamp + "_upload.sh")

        # because bedfile is optional need to handle it possibly being absent, whilst also escaping any spaces etc
        if self.bed_filepath:
            bed_upload_string="'%s'" % self.bed_filepath
        else:
            bed_upload_string=""

        # upload command
        # eg path/to/ua  --auth-token abc  --project  projectname --folder /nexus/path --do-not-compress /file/to/upload
        # .format() method used to enclose vcf and bed filepaths in quotes incase there's any characters in filenames
        # that could break the command (although all special characters should have been removed in an earlier step)
        upload_cmd = (config.upload_agent + self.auth + self.nexusprojectstring + config.data_project_id.replace(":", "")
                      + self.dest + self.nexus_folder + self.end_of_upload + "'%s' %s") % (self.vcf_filepath,bed_upload_string)
        
        # open bash script
        with open(upload_bash_script_name, 'w') as upload_script:
            # write the source and upload cmds
            upload_script.write(self.source_command)
            upload_script.write(upload_cmd)

        # run the command
        proc = subprocess.Popen(["bash " + upload_bash_script_name], stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)

        # capture the streams (err is redirected to out above)
        (out, err) = proc.communicate()
        with open(self.logfile_name, 'a') as logfile:
            logfile.write(out + "\n")

        # call next function
        self.run_app()

        # delete shell script - this will only happend once the script has finished running
        os.remove(upload_bash_script_name)
        with open(self.logfile_name, 'a') as logfile:
            logfile.write("deleting upload script\nFIN")
        

    def run_app(self):
        """Runs DNANexus hap.py workflow"""
        # write to logfile
        with open(self.logfile_name, 'a') as logfile:
            logfile.write("running app\n")
        
        # create bash script name
        run_bash_script_name = os.path.join(self.directory, self.timestamp + "_run.sh")

        # the dnanexus app requires a panel bedfile. This is used along with the hig confidence region bedfile to restrict regions assessed.
        # If no bedfile is provided the high confidence region bedfile is provided (set in config)
        if self.bed_filepath:
            self.app_panel_bed = " -ipanel_bed=" + "'{}'".format(
                config.data_project_id + self.nexus_folder + "/" + self.bed_basename)
        else:
            if self.genome_build == "GRCh37":
                self.app_panel_bed = config.app_panel_bed_37
            elif self.genome_build == "GRCh38": 
                self.app_panel_bed = config.app_panel_bed_38

        # dx run command
        # Construct the dx run command to submit hap.py job and capture returned job id.
        dxrun_cmd = (self.base_cmd + config.app_query_vcf + "'{}'".format(config.data_project_id + self.nexus_folder + "/"
                     + self.vcf_basename) + config.app_prefix + "happy." + self.vcf_basename_orig.split(".vcf")[0]
                     + self.app_truth_vcf + self.app_panel_bed + self.app_high_conf_bed + config.app_truth + self.dest
                     + self.nexus_folder + self.genome_build_cmd + self.genome_build + "'" + self.token)
        with open(run_bash_script_name, 'w') as run_bash_script:
            # write source cmd
            run_bash_script.write("%s\ndx select %s %s\n%s\necho $jobid" %(self.source_command,config.data_project_id.replace(":", ""),self.auth,dxrun_cmd))
        
        # run the bash script containing dx run command
        proc = subprocess.Popen(["bash " + run_bash_script_name], stderr=subprocess.PIPE, stdout=subprocess.PIPE,shell=True)

        # capture the streams 
        (out, err) = proc.communicate()
        if err:
            # send an error email to mokaguys
            email_subject = "Benchmarking Tool: stderr reported when running job "
            email_message = "vcf=%s\nemail=%s\noutput=%s\nerror=%s" %(self.vcf_basename_orig, self.user_email, self.timestamp, err)  # state all inputs and error
            self.send_an_email(config.failed_email_priority,email_subject,email_message,[config.mokaguys_email])

            # send a error email to user
            # Change self.you to the user's email address rather than mokaguys
            email_subject = config.user_error_subject
            email_message = self.user_error_message + "\n\nError message = \n" + err
            self.send_an_email(config.default_email_priority,email_subject,email_message,[self.user_email])

            with open(self.logfile_name, 'a') as logfile:
                logfile.write("stderr:\n%s\n\nEXITING" % err)
            
            # exit
            sys.exit()
        else:
            with open(self.logfile_name, 'a') as logfile:
                logfile.write(out + "\n")
            
            # capture the job id
            self.jobid = "job" + out.split('job')[-1].rstrip()
            # call function which monitors progress
            job_state = str(self.monitor_progress())
            with open(self.logfile_name, 'a') as logfile:
                logfile.write("outside of moniitor progress. job_state=%s\n" % job_state)
            # job state can be done, failed or something else (timeout)
            if "done" in job_state:
                self.download_result()
            elif "fail" in job_state:
                with open(self.logfile_name, 'a') as logfile:
                    logfile.write("fail in job_state")
                # get dnanexus job log
                stderr = self.get_job_log(self.jobid)
                #email to mokaguys
                email_subject = "Benchmarking Tool: job has failed "
                email_message = "vcf=%s\nemail=%s\noutput_folder=%s\nnexus_job_id=%s\n\nlast 50 lines of log:\n%s" % (self.vcf_basename_orig, self.user_email, self.timestamp, self.jobid, stderr)
                self.send_an_email(config.failed_email_priority,email_subject,email_message,[config.mokaguys_email])
                # send a error email to user
                email_message = self.user_error_message + "\n\nlast 50 lines of STDERR from app:\n" + stderr
                self.send_an_email(config.default_email_priority,config.user_error_subject,email_message, self.user_email)
                # write to logfile
                with open (self.logfile_name, 'a') as logfile:
                    logfile.write("Job has failed. Email has been sent to %s with error message %s" % (self.user_email, email_message)) # email message includes app stderr
            # if job didn't finish in 200 mins
            else:
                with open(self.logfile_name, 'a') as logfile:
                    logfile.write("fail or done not in job_state")
                email_subject = "Benchmarking Tool: job is not done or failed after %s mins " % config.max_wait_time
                email_message = "vcf=%s\nemail=%s\noutput_folder=%s\nnexus_job_id=%s" % (self.vcf_basename_orig, self.user_email, self.timestamp, self.jobid)
                self.send_an_email(config.failed_email_priority,email_subject,email_message,[config.mokaguys_email])
                with open (self.logfile_name, 'a') as logfile:
                    logfile.write("Unable to determine job state after 200 mins")
                              
            # once the script finishes delete the .sh script
            os.remove(run_bash_script_name)
            with open(self.logfile_name, 'a') as logfile:
                logfile.write("deleting run script (%s)\n" % run_bash_script_name)

    def monitor_progress(self):
        """Monitors the job and alerts if it has failed"""
        job_state=False
        time_counter=0
        while time_counter < config.max_wait_time:
            job_state = str(self.check_status(self.jobid).rstrip())
            with open(self.logfile_name, 'a') as logfile:
                logfile.write("job state = %s after %s mins\n" % (job_state,time_counter))
            if "done" in job_state or "fail" in job_state:
                break
            else:
                # wait for 1 mins
                time.sleep(60)
                time_counter+=1
        return job_state

                
    def get_job_log(self, jobid):
        log_message="dx watch %s --no-timestamps --get-stderr -q %s | tail -n 50" % (jobid, self.auth)
        joblog_script_name = os.path.join(self.directory, self.timestamp + "_joblog.sh")
        with open(self.logfile_name, 'a') as logfile:
            logfile.write("job log cmd %s\njoblog_script=%s" % (log_message,joblog_script_name))
        # open script
        with open(joblog_script_name, 'w') as joblog_script:
            # write source cmd
            joblog_script.write("%s\n%s" % (self.source_command,log_message))
        
        proc = subprocess.Popen(["bash %s" % joblog_script_name ], stderr=subprocess.PIPE,stdout=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()
        return out
        
    def format_result_5dp(self, result_string):
        """If provided string can be converted to float, will round to 5dp and return as string. Otherwise will just return the string provided"""
        try:
            return str(round(float(result_string), 5))
        except ValueError:
            return result_string

    def check_status(self, jobid):
        """Used by monitor_progress() method to check status of job"""
        status_cmd="dx describe %s --json  %s | jq '.state'" % ( jobid, self.auth)
        status_script_name = os.path.join(self.directory, self.timestamp + "_status.sh")
        # open script
        with open(status_script_name, 'w') as status_script:
            # write source cmd
            status_script.write("%s\ncd %s\n%s" % (self.source_command,self.directory,status_cmd))
        
        proc = subprocess.Popen(["bash %s" % status_script_name], stderr=subprocess.PIPE, stdout=subprocess.PIPE,shell=True)
        (out, err) = proc.communicate()
        if out:
            return out.rstrip()
        else:
            return False

    def download_result(self):
        """Downloads hap.py results and sends results email"""
        with open(self.logfile_name, 'a') as logfile:
            logfile.write("Job done, downloading\n")

        # command to download files. downloads all files that have been output by the app (will have prefix self.output)
        download_cmd = ("dx download %s/happy.%s* %s " % (config.data_project_id + self.nexus_folder, self.vcf_basename_orig.split(".vcf")[0] ,self.auth))
        # create download script name
        download_bash_script_name = os.path.join(self.directory, self.timestamp + "_download.sh")
        # open script
        with open(download_bash_script_name, 'w') as download_bash_script:
            # write source cmd
            download_bash_script.write("%s\ncd %s\n%s" % (self.source_command,self.directory,download_cmd))
        
        # run the command
        proc = subprocess.Popen(["bash %s" % download_bash_script_name], stderr=subprocess.PIPE, stdout=subprocess.PIPE,shell=True)

        # capture the streams
        (out, err) = proc.communicate()
        # with open(self.logfile_name, 'a') as logfile:
        #     logfile.write("cmd:%s\nstdout:\n%s\nstderr:\n%s\n" % ("bash %s" % download_bash_script_name,out,err))
        
        # if error
        if err:
            with open(self.logfile_name, 'a') as logfile:
                logfile.write("stderr:%s\nEXITING" % err)
            
            # send a error email
            email_subject = "Benchmarking Tool: cannot download from nexus"
            email_message = "vcf=%s\nemail=%s\noutput=%s\nerr=%s" % (self.vcf_basename_orig, self.user_email, self.timestamp, err)
            self.send_an_email(config.failed_email_priority,email_subject,email_message,[config.mokaguys_email])

            # send a error email to user
            email_message = config.user_error_message + "\n\nError message = \n" + err
            self.send_an_email(config.default_email_priority,config.user_error_subject,email_message,[self.user_email])
            sys.exit()

        else:
            with open(self.logfile_name, 'a') as logfile:
                logfile.write("opening summary.csv")
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
            print snp_recall,snp_recall_lowerCI, snp_recall_upperCI, snp_precision,snp_precision_lowerCI,snp_precision_upperCI
            print indel_recall, indel_recall_lowerCI, indel_recall_upperCI, indel_precision, indel_precision_lowerCI, indel_precision_upperCI 
            # send email
            email_subject = "Benchmarking Tool: Job Finished"
            
            # Create the email body
            # Include:
            # Names of supplied VCF and BED files to identify the results
            # Name of file from which summary is taken
            email_message = "Analysis complete for vcf: %s\nbed (if supplied): %s\nreference build selected: %s\nSummary (taken from happy.%s.extended.csv):\n" % (self.vcf_basename_orig, self.bed_basename,self.genome_build,self.vcf_basename_orig.split(".vcf")[0])
            print "386 %s" % email_message
            # If SNP results are present in the extended summary file, include the recall, precision and confidence intervals in the email
            if snps_found:
                email_message += "\nSNP recall (sensitivity)={recall} (95% CI: {recall_lower}-{recall_upper})\nSNP precision (PPV) = {precision} (95% CI: {precision_lower}-{precision_upper})".format(recall = snp_recall, recall_lower = snp_recall_lowerCI, recall_upper = snp_recall_upperCI, precision = snp_precision,precision_lower = snp_precision_lowerCI,precision_upper = snp_precision_upperCI)
                print "390: %s" %  email_message
            # If INDEL results are present in the extended summary file, include the recall, precision and confidence intervals in the email
            if indels_found:
                email_message += "\nINDEL recall (sensitivity)={recall} (95% CI: {recall_lower}-{recall_upper})\nINDEL precision (PPV) = {precision} (95% CI: {precision_lower}-{precision_upper})".format(recall = indel_recall, recall_lower =indel_recall_lowerCI, recall_upper = indel_recall_upperCI, precision = indel_precision,precision_lower = indel_precision_lowerCI,precision_upper = indel_precision_upperCI)
                print "395: %s " % email_message
            # A link to view the detailed summary html report
            # A link to download the full output .zip archive
            # Version numbers of hap.py and the DNAnexus app that were used to produce the results
            email_message += "\n\nA detailed summary report is available here:\n%s\nFull results are available here:\n%s\n\nThanks for using this tool!\n\nResults generated using Illumina hap.py %s (https://github.com/Illumina/hap.py) implemented in Synnovis Genome Informatics DNAnexus app: %s" % (os.path.join(config.url,config.MEDIA_URL, self.directory.split("media/")[1], "happy.%s.summary_report.html" % (self.vcf_basename_orig.split(".vcf")[0])),os.path.join(config.url,config.MEDIA_URL, self.directory.split("media/")[1], "happy.%s.zip" % (self.vcf_basename_orig.split(".vcf")[0])),config.happy_version,os.path.basename(config.app_path))
            print "400: %s" % email_message
            with open(self.logfile_name, 'a') as logfile:
                logfile.write("email message: %s" % email_message)
            self.send_an_email(config.default_email_priority,email_subject,email_message,[config.mokaguys_email,self.user_email])
            with open(self.logfile_name, 'a') as logfile:
                logfile.write("finished download.\ndeleting download script\n")
            # delete download bash script
            os.remove(download_bash_script_name)

    def send_an_email(self, priority,subject,message,recipient_list):
        """function to send an email. uses self.email_subject, self.email_message and self.email_priority"""
        # create message object
        m = Message()
        # set priority
        m['X-Priority'] = priority
        # set subject
        m['Subject'] = subject
        # set body
        m.set_payload(message)
        # server details
        server = smtplib.SMTP(host=config.host, port=config.port, timeout=10)
        server.set_debuglevel(1)  # verbosity
        server.starttls()
        server.ehlo()
        server.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
        server.sendmail(config.me, recipient_list, m.as_string())
