#!/usr/bin/env python3
import requests
import json
import time

TWENTY_TOKEN = 'eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjVlNTVhOTVkLTZmMjMtNDg1Ni05YjIxLThkMWFjMDljODcwZCJ9.eyJzdWIiOiIzZDBiOWQ5OC0yMjI2LTQ0NWUtYjYzMS1jNGM1ODAwY2I1OWQiLCJ0eXBlIjoiQVBJX0tFWSIsIndvcmtzcGFjZUlkIjoiM2QwYjlkOTgtMjIyNi00NDVlLWI2MzEtYzRjNTgwMGNiNTlkIiwiaWF0IjoxNzkzMDg0MDgyLCJleHAiOjQ5NDY2ODQwODEsImp0aSI6ImYwOTRjMzJlLTM0YWYtNDk1ZS1hMWUyLWM0YTcyNzE2NTk3MSJ9.LYNFktzyQq7RczVS5lvhTqj7FacH-lCCm5cUK_FgSEQCnU_sjdezIGkzd3TLSS-damzPwctU5oYyfhbENudHNw'
METADATA_URL = 'http://192.168.1.240:8085/metadata'

PERSON_OBJ_ID = 'e18c7a87-cb35-49ce-b0d3-e4e8791200eb'
OPP_OBJ_ID = '0e126f5f-2a44-42bb-8cdc-30d42a73a798'

HEADERS = {
    'Authorization': f'Bearer {TWENTY_TOKEN}',
    'Content-Type': 'application/json'
}

PERSON_FIELDS = [
    {"name": "lifecycleStage", "label": "Lifecycle Stage", "type": "TEXT"},
    {"name": "searchActive", "label": "MLS Search Active", "type": "BOOLEAN"},
    {"name": "portalActive", "label": "Portal Engaged", "type": "BOOLEAN"},
    {"name": "lastPortalActivityAt", "label": "Last Portal Activity", "type": "DATE_TIME"},
    {"name": "bbaSigned", "label": "BBA / Agreement Signed", "type": "BOOLEAN"},
    {"name": "bbaSignedDate", "label": "Agreement Signed Date", "type": "DATE"},
    {"name": "bbaExpirationDate", "label": "Agreement Expiration", "type": "DATE"},
    {"name": "pastClientType", "label": "Past Client Type", "type": "TEXT"},
    {"name": "homeMaintenanceTips", "label": "Home Maintenance Tips", "type": "BOOLEAN"},
    {"name": "partnerName", "label": "Spouse / Co-Client", "type": "TEXT"},
    {"name": "primaryPropertyAddress", "label": "Active / Closed Property", "type": "TEXT"},
]

OPPORTUNITY_FIELDS = [
    {"name": "dealType", "label": "Deal Side", "type": "TEXT"},
    {"name": "dealStage", "label": "Transaction Stage", "type": "TEXT"},
    {"name": "propertyAddress", "label": "Property Address", "type": "TEXT"},
    {"name": "coClients", "label": "Co-Clients / Co-Signers", "type": "TEXT"},
    {"name": "offerDate", "label": "Offer / List Date", "type": "DATE"},
    {"name": "mutualAcceptanceDate", "label": "Mutual Acceptance Date", "type": "DATE"},
    {"name": "inspectionDate", "label": "Inspection Date", "type": "DATE"},
    {"name": "escrowCompany", "label": "Title / Escrow Info", "type": "TEXT"},
]

def create_field(obj_id, field):
    name = field["name"]
    label = field["label"]
    ftype = field["type"]
    query = f'''
    mutation {{
      createOneField(input: {{
        field: {{
          objectMetadataId: "{obj_id}",
          name: "{name}",
          label: "{label}",
          type: {ftype},
          isNullable: true
        }}
      }}) {{
        id
        name
        label
        type
      }}
    }}
    '''
    try:
        r = requests.post(METADATA_URL, headers=HEADERS, json={'query': query}, timeout=15)
        res = r.json()
        if 'errors' in res:
            err = res['errors'][0].get('message', '')
            if 'already exists' in err.lower() or 'duplicate' in err.lower():
                print(f"  [-] Field '{name}' already exists.")
                return True
            print(f"  [!] Error creating '{name}': {err}")
            return False
        else:
            created = res.get('data', {}).get('createOneField', {})
            print(f"  [+] Created '{created.get('name')}' ({created.get('type')}) successfully.")
            return True
    except Exception as e:
        print(f"  [!] Request exception for '{name}': {e}")
        return False

def main():
    print("--- 1. Setting up Custom Fields for Person ---")
    for f in PERSON_FIELDS:
        create_field(PERSON_OBJ_ID, f)
        time.sleep(0.2)

    print("\n--- 2. Setting up Custom Fields for Opportunity ---")
    for f in OPPORTUNITY_FIELDS:
        create_field(OPP_OBJ_ID, f)
        time.sleep(0.2)

    print("\n--- Schema Setup Complete ---")

if __name__ == '__main__':
    main()
