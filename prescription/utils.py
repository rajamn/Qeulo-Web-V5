# prescription/utils.py
import os
from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML
# prescription/utils.py
def flatten_multiselect_input(values):
    """Converts ['A', 'B'] to 'A\nB'"""
    return "\n".join([v.strip() for v in values if v.strip()])


def save_prescription_pdf(master):
    """
    Renders the given PrescriptionMaster to PDF and writes it under MEDIA_ROOT/prescriptions/.
    Updates master.pdf to the relative path and saves that field.
    """
    # 1) Render HTML from a dedicated template
    html_string = render_to_string('prescription/pdf_template.html', {
        'master':  master,
        'details': master.details.all(),
        'hospital': master.hospital,
        'doctor':   master.doctor,
    })

    # 2) Generate PDF
    pdf_bytes = HTML(string=html_string).write_pdf()

    # 3) Build output path
    out_dir = os.path.join(settings.MEDIA_ROOT, 'prescriptions')
    os.makedirs(out_dir, exist_ok=True)
    filename = f'prescription_{master.pk}.pdf'
    path = os.path.join(out_dir, filename)

    # 4) Write file
    with open(path, 'wb') as f:
        f.write(pdf_bytes)

    # 5) Update the model
    master.pdf = os.path.join('prescriptions', filename)
    master.save(update_fields=['pdf'])

