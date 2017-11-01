from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from happy_vcfeval.forms import upload_form
from django.urls import reverse
from django.conf import settings
import os
import re
import threading
import time
from precision_medicine import *

# upload to nexus and run app
def run_prec_med(email, vcf_filepath, bed_filepath):
    upload=upload2Nexus()
    upload.take_inputs(email, vcf_filepath, bed_filepath)

# main upload page
def upload(request):
    with open(settings.BASE_DIR + '/known_issues.txt', 'r') as f:
        known_issues = [x for x in f if not x.startswith("#")]
    if request.method == 'POST':
        form = upload_form(request.POST, request.FILES) #Pass posted data to form object for validation
        if form.is_valid(): # if submitted data passes validation
            email = request.POST["email"]
            vcf_file = request.FILES["vcf_file"]
            timestamp = time.strftime("%y%m%d_%H%M%S")
            # Save the uploaded file(s), and remove any illegal characters or whitespace from filename
            fs = FileSystemStorage(settings.MEDIA_ROOT + timestamp, settings.MEDIA_URL + timestamp)
            vcf_filename_orig = fs.save(vcf_file.name, vcf_file)
            vcf_filepath_orig = settings.MEDIA_ROOT + timestamp + "/" + vcf_filename_orig
            #Replace any whitespace/special characters in filename with underscores
            vcf_filename = re.sub('[^0-9a-zA-Z.\-/]+', '_', vcf_filename_orig)
            vcf_filepath = settings.MEDIA_ROOT + timestamp + "/" + vcf_filename
            os.rename(vcf_filepath_orig, vcf_filepath)
            # if user supplied bed file...           
            if "bed_file" in request.FILES:
                bed_file = request.FILES["bed_file"]
                bed_filename_orig = fs.save(bed_file.name, bed_file)
                bed_filepath_orig = settings.MEDIA_ROOT + timestamp + "/" + bed_filename_orig
                #Replace any whitespace/special characters in filename with underscores
                bed_filename = re.sub('[^0-9a-zA-Z.\-/]+', '_', bed_filename_orig)
                bed_filepath = settings.MEDIA_ROOT + timestamp + "/" + bed_filename
                os.rename(bed_filepath_orig, bed_filepath)
                # run dna_nexus in background thread
                t = threading.Thread(target=run_prec_med, kwargs={'email': email, 'vcf_filepath': vcf_filepath, 'bed_filepath': bed_filepath})
            else: # no user supplied bedfile...
                t = threading.Thread(target=run_prec_med, kwargs={'email': email, 'vcf_filepath': vcf_filepath, 'bed_filepath': ""})
            t.setDaemon(True)
            t.start()
            return redirect(reverse('happy_vcfeval:processing'))
        else:
            # If validation failed, reload the form which will display the error messages from failed validation
            return render(request, 'happy_vcfeval/upload.html', {'form': form, 
                                                                 'known_issues': known_issues, 
                                                                 'na12878_fastq': settings.MEDIA_URL + "FASTQ/NA12878_WES.zip",
                                                                 'our_results': settings.MEDIA_URL + "170624_184727/170624_184727.tar.gz"})
    else:
    	form = upload_form()
    	return render(request, 'happy_vcfeval/upload.html', {'form': form, 
                                                             'known_issues': known_issues, 
                                                             'na12878_fastq': settings.MEDIA_URL + "FASTQ/NA12878_WES.zip",
                                                             'our_results': settings.MEDIA_URL + "170624_184727/170624_184727.tar.gz"})

# page displayed to inform user file is being processed
def processing(request):
	return render(request, 'happy_vcfeval/processing.html')