import base64
import io
from PIL import Image

# 1. Process logo into crisp 320x320 JPEG on clean white background (universal mobile support)
logo = Image.open('public/lc-logo.png')
logo_thumb = logo.resize((320, 320), Image.Resampling.LANCZOS)

rgb = Image.new('RGB', (320, 320), (255, 255, 255))
if logo_thumb.mode == 'RGBA':
    rgb.paste(logo_thumb, mask=logo_thumb.split()[3])
else:
    rgb.paste(logo_thumb)

buf_jpg = io.BytesIO()
rgb.save(buf_jpg, format='JPEG', quality=92, optimize=True)
logo_b64 = base64.b64encode(buf_jpg.getvalue()).decode('utf-8')

# Fold base64 data to 72 chars per line with standard vCard folding (CRLF + space)
def fold_vcard_line(prefix, value):
    full = prefix + value
    lines = []
    while len(full) > 75:
        lines.append(full[:75])
        full = ' ' + full[75:]
    lines.append(full)
    return '\r\n'.join(lines)

# Clean, comprehensive vCard fields with explicit URLs & social profiles
vcard_lines = [
    "BEGIN:VCARD",
    "VERSION:3.0",
    "N:Chanana;Lokesh;;;",
    "FN:Lokesh Chanana",
    "NICKNAME:Loki",
    "TITLE:Real Estate Broker",
    "ORG:Real Broker LLC",
    "TEL;TYPE=CELL,VOICE,pref:+1-801-860-1052",
    "EMAIL;TYPE=INTERNET,WORK,pref:lokeshchanana@outlook.com",
    "URL;TYPE=Website,WORK,pref:https://lokeshchanana.com",
    "URL;TYPE=Instagram:https://www.instagram.com/lokeshchanana_re",
    "URL;TYPE=Facebook:https://www.facebook.com/share/19qyi21cjW/",
    "URL;TYPE=Zillow:https://www.zillow.com/profile/Lokeshchanana_re",
    "URL;TYPE=Google Reviews:https://share.google/4Ha7jttZI6W7AeiSP",
    "X-SOCIALPROFILE;TYPE=instagram;x-user=lokeshchanana_re:https://www.instagram.com/lokeshchanana_re",
    "X-SOCIALPROFILE;TYPE=facebook:https://www.facebook.com/share/19qyi21cjW/",
    "X-SOCIALPROFILE;TYPE=zillow:https://www.zillow.com/profile/Lokeshchanana_re",
    "NOTE:Greater Seattle Real Estate Broker • Real Broker LLC",
    fold_vcard_line("PHOTO;ENCODING=b;TYPE=JPEG:", logo_b64),
    "END:VCARD"
]

vcf_content = '\r\n'.join(vcard_lines) + '\r\n'

with open('public/loki.vcf', 'wb') as f:
    f.write(vcf_content.encode('utf-8'))

with open('public/Lokesh_Chanana.vcf', 'wb') as f:
    f.write(vcf_content.encode('utf-8'))

# Also update /tank/n8n/loki.vcf if it exists
try:
    with open('/tank/n8n/loki.vcf', 'wb') as f:
        f.write(vcf_content.encode('utf-8'))
    print("Synced to /tank/n8n/loki.vcf")
except Exception as e:
    print("Notice on /tank/n8n/loki.vcf:", e)

print("Generated public/loki.vcf and public/Lokesh_Chanana.vcf successfully!")
print("File size:", len(vcf_content), "bytes")
