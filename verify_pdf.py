import sys
from pathlib import Path
from PyPDF2 import PdfReader

pdf_path = Path(r"C:/Users/THAAER/Desktop/pro/protected_ورقة.pdf")
if not pdf_path.exists():
    print('File not found', pdf_path)
    sys.exit(1)

reader = PdfReader(str(pdf_path))
print('encrypted:', reader.is_encrypted)
if reader.is_encrypted:
    # Try decrypting with the password we set
    result = reader.decrypt('123456')
    print('decrypt result code:', result)
    # result 1 = user password, 2 = owner password, 0 = failure
    if result:
        print('decrypt succeeded')
    else:
        print('decrypt failed')
else:
    print('File is not encrypted')
