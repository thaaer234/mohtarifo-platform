import sys, os, random, string
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter

def protect_pdf(input_path: str, output_path: str, password: str):
    reader = PdfReader(input_path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=password, use_128bit=True)
    with open(output_path, 'wb') as f:
        writer.write(f)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python pdf_protect.py <input_pdf> <output_pdf>')
        sys.exit(1)
    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]
    # generate a 6‑digit numeric password
    pwd = ''.join(random.choices(string.digits, k=6))
    protect_pdf(input_pdf, output_pdf, pwd)
    print('Password:', pwd)
    print('Protected PDF saved to', output_pdf)
