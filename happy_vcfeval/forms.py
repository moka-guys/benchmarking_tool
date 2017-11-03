from django import forms


class upload_form(forms.Form):
    # Define fields
    email = forms.EmailField(label="Email Address")
    vcf_file = forms.FileField(label="Attach VCF (.vcf) or gzipped VCF (.vcf.gz)")
    bed_file = forms.FileField(label="Attach analysis region BED (.bed) (OPTIONAL)", required=False)

    def clean(self):
        # Validate submitted data
        cleaned_data = super(upload_form, self).clean()
        uploaded_vcf = cleaned_data.get("vcf_file")
        uploaded_bed = cleaned_data.get("bed_file")
        # Check uploaded vcf size does not exceed 200MB
        if uploaded_vcf._size > 200000000:
            raise forms.ValidationError({'vcf_file': "File size cannot be greater than 200MB"})
        # Check uploaded file has .vcf or .vcf.gz extension
        if not uploaded_vcf.name.endswith(".vcf.gz") and not uploaded_vcf.name.endswith(".vcf"):
            raise forms.ValidationError({'vcf_file': "File must be VCF (.vcf) or gzipped VCF ('.vcf.gz')"})
        # If a bed file has been uploaded...
        if uploaded_bed:
            # Check uploaded bed size does not exceed 200MB
            if uploaded_bed._size > 200000000:
                raise forms.ValidationError({'bed_file': "File size cannot be greater than 200MB"})
            # Check uploaded file has .bed extension
            if not uploaded_bed.name.endswith(".bed"):
                raise forms.ValidationError({'bed_file': "File must be BED file with '.bed' extension"})
