#!/usr/bin/env python3
import requests
import json
import time
import subprocess
import sqlite3

def get_brevo_api_key():
    conn = sqlite3.connect('/tank/n8n/database.sqlite')
    c = conn.cursor()
    c.execute('SELECT data FROM credentials_entity WHERE id = "wdXqAoATqKkISRe1"')
    enc = c.fetchone()[0]
    conn.close()

    js = f'''
    const crypto = require("crypto");
    function getKeyAndIv(salt, key) {{
      const password = Buffer.concat([Buffer.from(key, "binary"), salt]);
      const hash1 = crypto.createHash("md5").update(password).digest();
      const hash2 = crypto.createHash("md5").update(Buffer.concat([hash1, password])).digest();
      const iv = crypto.createHash("md5").update(Buffer.concat([hash2, password])).digest();
      return [Buffer.concat([hash1, hash2]), iv];
    }}
    function decrypt(data, key) {{
      const input = Buffer.from(data, "base64");
      const salt = input.subarray(8, 16);
      const [derivedKey, iv] = getKeyAndIv(salt, key);
      const decipher = crypto.createDecipheriv("aes-256-cbc", derivedKey, iv);
      return Buffer.concat([decipher.update(input.subarray(16)), decipher.final()]).toString("utf-8");
    }}
    const key = process.env.N8N_ENCRYPTION_KEY || "";
    const creds = JSON.parse(decrypt("{enc}", key));
    console.log(creds.apiKey);
    '''
    return subprocess.run(['sudo', 'docker', 'exec', 'n8n', 'node', '-e', js], capture_output=True, text=True).stdout.strip()

def get_twenty_token():
    return os.environ.get('TWENTY_API_KEY', '')

def format_sms(phone):
    if not phone:
        return None
    digits = ''.join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        return '+1' + digits
    if len(digits) == 11 and digits.startswith('1'):
        return '+' + digits
    if len(digits) >= 10 and len(digits) <= 15:
        return '+' + digits
    return None

def main():
    brevo_key = get_brevo_api_key()
    twenty_token = get_twenty_token()

    session = requests.Session()
    session.headers.update({
        'api-key': brevo_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    })

    # 1. Fetch Brevo lists
    r = session.get('https://api.brevo.com/v3/contacts/lists?limit=50', timeout=10)
    brevo_lists = r.json().get('lists', [])
    list_map = {l['name'].lower(): l['id'] for l in brevo_lists}
    default_list_id = list_map.get('customer', 3)
    print("Brevo List Mapping:", list_map)

    # 2. Fetch Twenty CRM People
    t_res = requests.get(
        'http://192.168.1.240:8085/rest/people?limit=500',
        headers={'Authorization': f'Bearer {twenty_token}', 'Accept': 'application/json'},
        timeout=10
    )
    people = t_res.json().get('data', {}).get('people', [])
    print(f"Total Twenty CRM people: {len(people)}")

    synced_count = 0
    skipped_no_email = 0
    failed_count = 0

    for p in people:
        email = (p.get('emails', {}).get('primaryEmail') or '').strip().lower()
        if not email:
            skipped_no_email += 1
            continue

        first_name = (p.get('name', {}).get('firstName') or '').strip()
        last_name = (p.get('name', {}).get('lastName') or '').strip()
        role = p.get('contactRole') or 'Customer'
        market = p.get('market') or ''
        lead_source = p.get('leadSource') or ''
        raw_phone = p.get('phones', {}).get('primaryPhoneNumber') or ''
        sms = format_sms(raw_phone)

        target_list_id = list_map.get(role.lower(), default_list_id)

        attributes = {
            'FIRSTNAME': first_name,
            'LASTNAME': last_name,
            'ROLE': role,
            'MARKET': market,
            'LEAD_SOURCE': lead_source,
            'EXT_ID': p['id']
        }
        if sms:
            attributes['SMS'] = sms

        payload = {
            'email': email,
            'attributes': attributes,
            'listIds': [target_list_id],
            'updateEnabled': True
        }

        try:
            resp = session.post('https://api.brevo.com/v3/contacts', json=payload, timeout=8)
            if resp.status_code in [200, 201, 204]:
                synced_count += 1
            elif resp.status_code == 400 and 'SMS' in resp.text:
                # Retry without SMS if Brevo considers the number invalid
                del payload['attributes']['SMS']
                resp2 = session.post('https://api.brevo.com/v3/contacts', json=payload, timeout=8)
                if resp2.status_code in [200, 201, 204]:
                    synced_count += 1
                else:
                    print(f"Failed {email} without SMS: {resp2.status_code} - {resp2.text}")
                    failed_count += 1
            else:
                print(f"Failed {email}: {resp.status_code} - {resp.text}")
                failed_count += 1
        except Exception as e:
            print(f"Timeout/Error syncing {email}: {e}")
            failed_count += 1

        if synced_count % 10 == 0 and synced_count > 0:
            print(f"Progress: {synced_count} contacts synced to Brevo...")

        time.sleep(0.05)

    print("\n--- Final Sync Summary ---")
    print(f"Successfully Synced to Brevo: {synced_count}")
    print(f"Skipped (No Email Address): {skipped_no_email}")
    print(f"Failed: {failed_count}")

if __name__ == '__main__':
    main()
