from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from happy_vcfeval.forms import upload_form
from django.urls import reverse
from django.conf import settings
import os
import re
import threading
import time
#from precision_medicine import *
import precision_medicine

# Upload to nexus and run app
def run_prec_med(email, vcf_filepath, bed_filepath, genome_build):
    # Create upload2Nexus() object
    upload = precision_medicine.upload2Nexus()
    # Pass inputs to object, which will trigger the workflow that runs the DNAnexus app and reports results
    upload.take_inputs(email, vcf_filepath, bed_filepath, genome_build)


# Main upload page
def upload(request):
    # Create list of any issues in known_issues.txt so that they can be displayed on page
    with open(settings.BASE_DIR + '/known_issues.txt', 'r') as f:
        known_issues = [x for x in f if not x.startswith("#")]
    # Create list of any new features in new_features.txt so that they can be displayed on page
    with open(settings.BASE_DIR + '/new_features.txt', 'r') as f:
        new_features = [x for x in f if not x.startswith("#")]
    # If data has been submitted...
    if request.method == 'POST':
        # Pass posted data to form upload_form object for validation
        form = upload_form(request.POST, request.FILES)
        if form.is_valid():  # if submitted data passes validation
            # Capture the posted data
            email = request.POST["email"]
            vcf_file = request.FILES["vcf_file"]
            # Capture genome reference
            genome_build = request.POST["genome_build"]
            # Create timestamp
            timestamp = time.strftime("%y%m%d_%H%M%S")
            # Save the uploaded vcf file with original filename
            fs = FileSystemStorage(settings.MEDIA_ROOT + timestamp, settings.MEDIA_URL + timestamp)
            vcf_filename_orig = fs.save(vcf_file.name, vcf_file)
            vcf_filepath_orig = settings.MEDIA_ROOT + timestamp + "/" + vcf_filename_orig
            # Replace any whitespace/special characters in filename with underscores
            vcf_filename = re.sub('[^0-9a-zA-Z.\-/]+', '_', vcf_filename_orig)
            vcf_filepath = settings.MEDIA_ROOT + timestamp + "/" + vcf_filename
            os.rename(vcf_filepath_orig, vcf_filepath)
            # If user supplied bed file...
            if "bed_file" in request.FILES:
                # Save the uploaded bed file with original file name
                bed_file = request.FILES["bed_file"]
                bed_filename_orig = fs.save(bed_file.name, bed_file)
                bed_filepath_orig = settings.MEDIA_ROOT + timestamp + "/" + bed_filename_orig
                # Replace any whitespace/special characters in filename with underscores
                bed_filename = re.sub('[^0-9a-zA-Z.\-/]+', '_', bed_filename_orig)
                bed_filepath = settings.MEDIA_ROOT + timestamp + "/" + bed_filename
                os.rename(bed_filepath_orig, bed_filepath)
                # Run dna_nexus in background thread. Calls run_prec_med() function and passes email address and filepaths
                t = threading.Thread(target=run_prec_med, kwargs={'email': email, 'vcf_filepath': vcf_filepath,
                                                                  'bed_filepath': bed_filepath, 'genome_build': genome_build})
            # if user did not supply bedfile...
            else:
                # Run dna_nexus in background thread. Calls run_prec_med() and passes email address and filepaths.
                # Passes empty string as bed_filepath
                t = threading.Thread(target=run_prec_med, kwargs={'email': email, 'vcf_filepath': vcf_filepath,
                                                                  'bed_filepath': "", 'genome_build': genome_build})
            t.setDaemon(True)  # Run in background
            t.start()  # Start the thread, which calls run_prec_med() function
            # Redirect to the 'processing' success page.
            # reverse function contructs the URL without having to hardcode it for portablility (see urls.py)
            return redirect(reverse('happy_vcfeval:processing'))
        else:
            # If validation failed, reload the form which will display the error messages from failed validation
            # Error messages are passed as part of the form object
            return render(request, 'happy_vcfeval/upload.html', {'form': form,
                                                                 'tool_version': precision_medicine.config.tool_version,
                                                                 'known_issues': known_issues,
                                                                 'new_features': new_features,
                                                                 'happy_version': precision_medicine.config.happy_version,
                                                                 'na12878_fastq': settings.MEDIA_URL + "FASTQ/NA12878_WES.zip",
                                                                 'our_results': settings.MEDIA_URL + "180511_150443/happy.WES3_Test2_48_136819_PN_WES_3_S2_R1_001.zip"})
    # If data hasn't been submitted, just display the webpage
    else:
        form = upload_form()
        return render(request, 'happy_vcfeval/upload.html', {'form': form,
                                                             'tool_version': precision_medicine.config.tool_version,
                                                             'known_issues': known_issues,
                                                             'new_features': new_features,
                                                             'happy_version': precision_medicine.config.happy_version,
                                                             'na12878_fastq': settings.MEDIA_URL + "FASTQ/NA12878_WES.zip",
                                                             'our_results': settings.MEDIA_URL + "180511_150443/happy.WES3_Test2_48_136819_PN_WES_3_S2_R1_001.zip"})


# page displayed to inform user file is being processed
def processing(request):
    return render(request, 'happy_vcfeval/processing.html', {'tool_version': precision_medicine.config.tool_version})
