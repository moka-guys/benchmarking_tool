import os
import sys
import getopt
import subprocess
import datetime
import time
from email.Message import Message
import smtplib
import re
import shutil
import gzip
from django.conf import settings
from precision_medicine_config import *


class upload2Nexus():
    ''' ''' 
    
    def __init__(self):
        #  variables that are set from  inputs
        self.email=""
        self.vcf_filepath=""
        self.vcf_basename=""
        self.vcf_orig_basename=""
        self.bed_filepath=""
        self.bed_basename=""
        self.app_panel_bed=""
        
        self.vcf_header=os.path.dirname(os.path.realpath(__file__))+"/vcf_header.vcf"

        ################ Working dir ###############################
        # where will the files be downloaded to/from?
        self.working_dir= ""
        

        # log file variables
        self.logfile=""
        self.logfile_name=""

        ################ DNA Nexus###############################
        #path to upload agent
        self.upload_agent = "/home/mokagals/apps/dnanexus-upload-agent-1.5.26-linux/ua"# server
              
        # source command
        self.source_command = "#!/bin/bash\n. /etc/profile.d/dnanexus.environment.sh\n"
        
        # dx run commands and components
        self.auth = " --auth-token "+ Nexus_API_Key # authentication string
        self.nexusprojectstring = "  --project  " # nexus project
        self.dest = " --folder " # nexus folder
        self.nexus_folder="/Tests/" # path to files in project
        self.end_of_upload=" --do-not-compress " # don't compress upload
        self.base_cmd="jobid=$(dx run "+app_project_id+app_path+" -y" # start of dx run command
        self.token = " --brief --auth-token "+Nexus_API_Key+")" # authentication for dx run

        #variable to catch the analysis id of job
        self.analysis_id=""
        
        ################ Emails###############################
        self.you=['gst-tr.mokaguys@nhs.net']
        self.smtp_do_tls = True
        self.email_subject = "" 
        self.email_message = ""
        self.email_priority = 3

        self.generic_error_email=user_error_message
        

    def take_inputs(self, email, vcf_file, bed_file):    
        '''Capture the input arguments'''

        #assign inputs to self variables
        self.email=email
        self.vcf_filepath=vcf_file
        #build path and filename
        self.vcf_basename=os.path.basename(self.vcf_filepath) 
        #The vcf_basename will get updated after the vcf has been stripped, but need to put the original filename in email sent to users, so take a copy of filename
        self.vcf_basename_orig=self.vcf_basename
        self.path=os.path.dirname(self.vcf_filepath)

        if bed_file:
            self.bed_filepath=bed_file
            #build path and filename
            self.bed_basename=os.path.basename(self.bed_filepath)
            self.path=os.path.dirname(self.bed_filepath)            
        
        #capture timestamp
        self.timestamp=self.path.split("/")[-1]

        # add vcf and timestamp to the generic error email message
        self.generic_error_email="vcf = " + self.vcf_basename_orig + "\n\n" + self.generic_error_email + self.timestamp
        
        #update nexus folder so it is Tests/timestamp
        self.nexus_folder=self.nexus_folder+self.path.split("/")[-1]
        
        # use  timestamp to create the logfile name
        self.logfile_name=os.path.join(self.working_dir,self.path,self.timestamp+"_logfile.txt")
        
        #call function to upload to nexus
        self.vcf_strip()

    def vcf_strip(self): 
        #write to logfile
        self.logfile=open(self.logfile_name,'w')
        self.logfile.write("email="+self.email+"\noutput="+self.timestamp+"\nvcf_filepath="+self.vcf_filepath+"\nbed_filepath="+self.bed_filepath+"\n")
        # record in log file steps taken
        self.logfile.write("removing unnecessary fields from VCF\n")
        self.logfile.close()
        # set query vcf
        query_vcf = self.vcf_filepath
        #set vcf header
        vcf_header = self.vcf_header
        # create new file name for modified vcf
        output_vcf =  self.vcf_filepath + '_stripped.vcf.gz'
        
        # check if zipped or not to define settings used to read the file
        if query_vcf.endswith('.gz'):
            open_func = gzip.open
            open_mode = 'rb'
        else:
            open_func = open
            open_mode = 'r'
        try:
            #open vcf header as t and the query vcf with the required settings as q and output file as binary output o
            with open(vcf_header, 'r') as t, open_func(query_vcf, open_mode) as q, gzip.open(output_vcf, 'wb') as o:
                # for each line in q if it's not a header take the first 6 columns of each row, then add two full stops (replacing the filter and info ), then just include the GT field of format and sample columns.
                output = "\n".join(["\t".join(line.rstrip().split('\t')[:6] 
                                   + ['.'] * 2 
                                   + [line.rstrip().split('\t')[8].split(":")[line.rstrip().split('\t')[8].split(":").index("GT")]] 
                                   + [line.rstrip().split('\t')[9].split(":")[line.rstrip().split('\t')[8].split(":").index("GT")]]) 
                                   for line in q if not line.startswith('#')])
                # write output with new header
                o.write(t.read()+"\n"+output)
        
        except Exception,e:
            #send an error email to mokaguys
            self.email_subject = "Benchmarking Tool: stderr reported when running job "
            self.email_priority = 1 # high priority
            self.email_message = "vcf="+self.vcf_basename_orig+"\nemail="+self.email+"\noutput="+self.timestamp+"\nerror="+str(e) # state all inputs and error 
            self.send_an_email()

            #send an error email to user
            self.email_subject = "Benchmarking Tool: Invalid VCF file "
            self.email_priority = 1 # high priority
            self.email_message = ("An error was encountered whilst reading VCF:\n" + self.vcf_basename_orig + "\n\nPlease ensure that the VCF (.vcf) or gzipped VCF (.vcf.gz) file supplied conforms the VCF specification, is sorted, and includes genotype information (using GT tag) in the FORMAT and SAMPLE fields.\n\nIf you continue to experience issues please reply to this email quoting the below code:\n\n" + self.timestamp)
            self.you = [self.email]
            self.send_an_email()

            #write error to log file
            self.logfile=open(self.logfile_name,'a')
            self.logfile.write("Error whilst stripping VCF file:" + str(e) + "\nEXITING")
            self.logfile.close()
            
            #exit 
            sys.exit()
        
        # set the new files asvariables used to upload to nexus etc.
        self.vcf_filepath = output_vcf   
        self.vcf_basename=os.path.basename(self.vcf_filepath)
        
        #call next function to upload to nexus
        self.upload_to_Nexus()

    def upload_to_Nexus(self):
        #write to logfile
        self.logfile=open(self.logfile_name,'a')
        #self.logfile.write("email="+self.email+"\noutput="+self.timestamp+"\nvcf_filepath="+self.vcf_filepath+"\nbed_filepath="+self.bed_filepath+"\n")
        self.logfile.write("uploading to nexus\n")
        self.logfile.close()

        # create bash script name
        upload_bash_script_name=os.path.join(self.working_dir,self.path,self.timestamp+"_upload.sh")
        
        #open bash script
        upload_bash_script=open(upload_bash_script_name,'w')
        
        # upload command 
        #eg path/to/ua  --auth-token abc  --project  projectname --folder /nexus/path --do-not-compress /file/to/upload
        upload_cmd=self.upload_agent+self.auth+ self.nexusprojectstring+data_project_id.replace(":","")+ self.dest + self.nexus_folder+self.end_of_upload + "'{}'".format(self.vcf_filepath)
        if self.bed_filepath:
            upload_cmd+="\n"+self.upload_agent+self.auth+ self.nexusprojectstring+data_project_id.replace(":","")+ self.dest + self.nexus_folder+self.end_of_upload + "'{}'".format(self.bed_filepath)
        
        #write the source and upload cmds
        upload_bash_script.write(self.source_command)
        upload_bash_script.write(upload_cmd)
        
        #close bash script
        upload_bash_script.close()

        # run the command
        proc = subprocess.Popen(["bash "+upload_bash_script_name], stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
            
        # capture the streams (err is redirected to out above)
        (out, err) = proc.communicate()
        # if err:
        #     #send a error email
        #     self.email_subject = "Benchmarking Tool: stderr reported when uploading file "
        #     self.email_priority = 1
        #     self.email_message = "email="+self.email+"\noutput="+self.generic_error_email+"\nerror="+err
        #     self.send_an_email()

        #     #send a error email to user
        #     self.you = [self.email]
        #     self.email_subject = user_error_subject
        #     self.email_message = self.generic_error_email
        #     self.send_an_email()

        self.logfile=open(self.logfile_name,'a')
        self.logfile.write(out+"\n")
        self.logfile.close()
        #call next function
        self.run_app()

        #delete shell script - this will only happend once the script has finished running
        os.remove(upload_bash_script_name)
        self.logfile=open(self.logfile_name,'a')
        self.logfile.write("deleting upload script\nFIN")
        self.logfile.close()

    def run_app(self):
        #write to logfile
        self.logfile=open(self.logfile_name,'a')
        self.logfile.write("running app\n")
        self.logfile.close()
        # create bash script name
        run_bash_script_name=os.path.join(self.working_dir,self.path,self.timestamp+"_run.sh")
        
        #print run_bash_script_name
        
        # open script
        run_bash_script=open(run_bash_script_name,'w')
        
        if self.bed_filepath:
            self.app_panel_bed= " -ipanel_bed="+"'{}'".format(data_project_id+self.nexus_folder +"/"+ self.bed_basename)
        else:
            self.app_panel_bed=app_panel_bed
        # dx run  command
        #eg dxrun_cmd=self.base_cmd+workflow_query_vcf + project+self.nexus_folder +"/"+ self.vcf_basename +workflow_output_name+self.output+self.nexusprojectstring+project_id+self.token+";echo $jobid"
        dxrun_cmd=self.base_cmd+app_query_vcf + "'{}'".format(data_project_id+self.nexus_folder +"/"+ self.vcf_basename) +app_prefix+self.timestamp + app_truth_vcf+self.app_panel_bed+app_high_conf_bed+app_truth+self.dest+self.nexus_folder+self.token
        
        #write source cmd
        run_bash_script.write(self.source_command)
        #can't use dest and project together so inorder to specify dest need to preselect the project
        run_bash_script.write("dx select " + data_project_id.replace(":","") + " " + self.auth+"\n")
        #write dx run cmd
        run_bash_script.write(dxrun_cmd+"\n")
        #echo the job id to use to monitor progress
        run_bash_script.write("echo $jobid")
        #close bash script
        run_bash_script.close()

        # run the command
        proc = subprocess.Popen(["bash "+run_bash_script_name], stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
            
        # capture the streams 
        (out, err) = proc.communicate()
        if err:
                #send a error email
                self.email_subject = "Benchmarking Tool: stderr reported when running job "
                self.email_priority = 1 # high priority
                self.email_message = "vcf="+self.vcf_basename_orig+"\nemail="+self.email+"\noutput="+self.timestamp+"\nerror="+err # state all inputs and error 
                self.send_an_email()
                
                #send a error email to user
                self.you = [self.email]
                self.email_subject = user_error_subject
                self.email_message = self.generic_error_email
                self.send_an_email()

                self.logfile=open(self.logfile_name,'a')
                self.logfile.write(out+"\nEXITING")
                self.logfile.close()
                #exit 
                sys.exit()
        else:
            self.logfile=open(self.logfile_name,'a')
            self.logfile.write(out+"\n")
            self.logfile.close()
            # capture the job id
            self.analysis_id="job"+out.split('job')[-1]
            # call function which monitors progress
            self.monitor_progress()
            #once the script finishes delete the .sh script
            os.remove(run_bash_script_name)
            self.logfile=open(self.logfile_name,'a')
            self.logfile.write("deleting run script\n")
            self.logfile.close()

    def monitor_progress(self):
        #write to logfile
        self.logfile=open(self.logfile_name,'a')
        self.logfile.write("monitoring progress\n")
        self.logfile.close()
        # command which returns a job-id within the project if successfully completed
        status_cmd="dx find jobs --project "+data_project_id+" --id "+self.analysis_id.rstrip()+" --brief --state done"
        
        # create bash script name
        status_bash_script_name=os.path.join(self.working_dir,self.path,self.timestamp+"_status.sh")
        #open script
        status_bash_script=open(status_bash_script_name,'w')
        # write the source cmd
        status_bash_script.write(self.source_command+"\n")
        # write the status command
        status_bash_script.write(status_cmd+"\n")
        #close bash script
        status_bash_script.close() 

        # command which returns a job-id within the project if successfully completed
        fail_status_cmd="dx find jobs --project "+data_project_id+" --id "+self.analysis_id.rstrip()+" --brief --state failed"
        
        # create bash script name
        fail_status_bash_script_name=os.path.join(self.working_dir,self.path,self.timestamp+"_fail_status.sh")
        #open script
        fail_status_bash_script=open(fail_status_bash_script_name,'w')
        # write the source cmd
        fail_status_bash_script.write(self.source_command+"\n")
        # write the status command
        fail_status_bash_script.write(fail_status_cmd+"\n")
        #close bash script
        fail_status_bash_script.close() 
        

        count=0
        # call check status module to execute the script. will only return true when job-id is found
        while not self.check_status(status_bash_script_name):
            # use count to apply a time out limit    
            # if has been running for < 45 mins
            if count < 45:
                
                #write to logfile
                self.logfile=open(self.logfile_name,'a')
                self.logfile.write("job not finished. waited for "+str(count)+ " minutes so far\n")
                self.logfile.close()
                
                print "job not finished. waited for "+str(count)+ " minutes so far"
                
                #increase count
                count+=1
                
                # wait for 1 mins
                time.sleep(60)
                # call the check status function again
                self.check_status(status_bash_script_name)

                # check if it's failed
                if self.check_status(fail_status_bash_script_name):
                    #if failed increase count to stop the loop
                    count+=100
            else:
                # if has been running for 45 mins stop or the job has failed
                # access the error message from the app:
                # command which returns a job-id within the project if successfully completed
                error_cmd="dx watch "+self.analysis_id.rstrip()+"  --no-timestamps --get-stderr -q | tail -n 50"

                # create bash script name
                read_job_error_bash_script_name=os.path.join(self.working_dir,self.path,self.timestamp+"_read_job_error.sh")
                
                #open script
                read_job_error_bash_script=open(read_job_error_bash_script_name,'w')
                # write the source cmd
                read_job_error_bash_script.write(self.source_command+"\n")
                # write the status command
                read_job_error_bash_script.write(error_cmd+"\n")
                #close bash script
                read_job_error_bash_script.close() 
        
                # execute the status script
                proc = subprocess.Popen(["bash "+read_job_error_bash_script_name], stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
                # capture the output
                (out, err) = proc.communicate()
                # only will have stdout if the dx find jobs command terms are met (job finihsed successfully)
                if out:
                    app_std_error=out


                #send a error email
                self.email_subject = "Benchmarking Tool: job has failed or hasn't finished after 45 mins "
                self.email_priority = 1
                self.email_message = "vcf="+self.vcf_basename_orig+"\nemail="+self.email+"\noutput="+self.timestamp+"\nnexus_job_id="+self.analysis_id+"\n\nlast 50 lines of STDERR from app:\n"+app_std_error
                self.send_an_email()

                #send a error email to user
                self.you = [self.email]
                self.email_subject = user_error_subject
                self.email_message = self.generic_error_email
                self.send_an_email()

                self.logfile=open(self.logfile_name,'a')
                self.logfile.write("job has failed or hasn't finished after 45 mins!\nEmail has been sent to:"+self.email+"\nwith error message:"+self.email_message+"\n\nEXITING.\nSTDERR from app = \n"+app_std_error)
                self.logfile.close()

                #remove bash scripts
                os.remove(status_bash_script_name)
                os.remove(read_job_error_bash_script_name)
                os.remove(fail_status_bash_script_name)
                sys.exit()
        else:
            # job has finished. download output files
            self.download_result()
            #once finished remove shell script
            os.remove(status_bash_script_name)
            os.remove(fail_status_bash_script_name)
            self.logfile=open(self.logfile_name,'a')
            self.logfile.write("deleting status scripts\n")
            self.logfile.close()

    def  check_status(self,status_bash_script_name):
        # execute the status script
        proc = subprocess.Popen(["bash "+status_bash_script_name], stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        # capture the output
        (out, err) = proc.communicate()
        # only will have stdout if the dx find jobs command terms are met (job finihsed successfully)
        if out:
            #return true to exit the sleep loop
            return True
        else:
            #return false to continue sleep loop
            return False


    def download_result(self):
        self.logfile=open(self.logfile_name,'a')
        self.logfile.write("Job done, downloading\n")
        self.logfile.close()
        # command to download files. downloads all files that have been output by the app (will have prefix self.output)
        download_cmd="dx download "+data_project_id+self.nexus_folder +"/"+self.timestamp+"*"+self.auth
        # create download script name
        download_bash_script_name=os.path.join(self.working_dir,self.path,self.timestamp+"_download.sh")
        #open script
        download_bash_script=open(download_bash_script_name,'w')
        #write source cmd
        download_bash_script.write(self.source_command)
        #cd to location where files are to be downloaded
        download_bash_script.write("cd "+self.path+"\n")
        #write download cmd
        download_bash_script.write(download_cmd+"\n")
        #close bash script
        download_bash_script.close()

        # run the command
        proc = subprocess.Popen(["bash "+download_bash_script_name], stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
            
        # capture the streams
        (out, err) = proc.communicate()
        self.logfile=open(self.logfile_name,'a')
        self.logfile.write(out+"\n")
        self.logfile.close()
        # if error
        if err:
            self.logfile=open(self.logfile_name,'a')
            self.logfile.write(err+"\nEXITING")
            self.logfile.close()
            
            #send a error email
            self.email_subject = "Benchmarking Tool: cannot download from nexus"
            self.email_priority = 1
            self.email_message = "vcf="+self.vcf_basename_orig+"\nemail="+self.email+"\noutput="+self.timestamp+"\nerr="+err
            self.send_an_email()

            #send a error email to user
            self.you = [self.email]
            self.email_subject = user_error_subject
            self.email_message = self.generic_error_email
            self.send_an_email()
            sys.exit()

        else:    
            # add the user email to the email message
            self.you.append(self.email)
            
            #open the summary file to get recall and precision
            summary_csv=open(os.path.join(self.path,self.timestamp+".summary.csv"),'r')
            # loop through loking for indel result
            for line in summary_csv:
                if line.startswith("SNP,PASS"):
                    # split the line on comma
                    splitline=line.split(",")
                    #capture required columns
                    snp_recall=splitline[9]
                    snp_precision=splitline[10]
                elif line.startswith("INDEL,PASS"):
                    # split the line on comma
                    splitline=line.split(",")
                    #capture required columns
                    indel_recall=splitline[9]
                    indel_precision=splitline[10]
            #close file
            summary_csv.close()


            # send email
            self.email_subject = "Benchmarking Tool: Job Finished"
            self.email_priority = 3

            self.email_message = "Analysis complete for vcf:\n" + self.vcf_basename_orig + "\n\nPlease download your files from:\n"+ip+os.path.join(settings.MEDIA_URL,self.path.split("media/")[1],self.timestamp+".tar.gz")+"\n\nSummary (taken from "+self.timestamp+".summary.csv)\nSNP recall (sensitivity)= "+snp_recall+"\nSNP precision (PPV) = "+snp_precision+"\nINDEL recall (sensitivity)= "+indel_recall+"\nINDEL precision (PPV) = "+indel_precision+"\n\nThanks for using this tool!"
            self.send_an_email()
            self.logfile=open(self.logfile_name,'a')
            self.logfile.write("finished download.\ndeleting download script\n")
            self.logfile.close()
            #delete download bash script 
            os.remove(download_bash_script_name)

    def send_an_email(self):
        '''function to send an email. uses self.email_subject, self.email_message and self.email_priority'''       
        #create message object
        m = Message()
        #set priority
        m['X-Priority'] = str(self.email_priority)
        #set subject
        m['Subject'] = self.email_subject
        #set body
        m.set_payload(self.email_message)
        
        # server details
        server = smtplib.SMTP(host = host, port =port,timeout = 10)
        server.set_debuglevel(1) # verbosity
        server.starttls()
        server.ehlo()
        server.login(user, pw)
        server.sendmail(me, self.you, m.as_string())

if __name__ == '__main__':
    # Create instance of get_list_of_runs
    upload = upload2Nexus()
    # call function
    #upload.take_inputs(sys.argv[1:])
    email="aledjones@nhs.net"
    file='/NA12878_SOPHIA_4_VCF.vcf.gz'
    bed=''
    upload.take_inputs(email,file,bed)
