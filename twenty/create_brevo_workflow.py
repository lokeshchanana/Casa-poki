#!/usr/bin/env python3
import os
import sqlite3
import json
import uuid

TWENTY_TOKEN = os.environ.get('TWENTY_API_KEY', '')
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')

SYNC_CODE = f'''const https = require('https');
const http = require('http');
const urlMod = require('url');

const TWENTY_TOKEN = '{TWENTY_TOKEN}';
const BREVO_KEY = '{BREVO_API_KEY}';

// Helper: HTTP request
const requestJson = (urlStr, options = {{}}, postData = null) => {{
  return new Promise((resolve) => {{
    const parsed = urlMod.parse(urlStr);
    const client = parsed.protocol === 'https:' ? https : http;
    const req = client.request({{
      hostname: parsed.hostname,
      port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
      path: (parsed.pathname || "") + (parsed.search || ""),
      method: options.method || 'GET',
      headers: options.headers || {{}}
    }}, (res) => {{
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {{
        try {{
          resolve({{ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode, data: JSON.parse(data) }});
        }} catch (e) {{
          resolve({{ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode, data: data }});
        }}
      }});
    }});
    req.on('error', err => resolve({{ ok: false, status: 500, error: err.message }}));
    if (postData) {{
      req.write(typeof postData === 'string' ? postData : JSON.stringify(postData));
    }}
    req.end();
  }});
}};

const rawItem = $input.first().json;
const payload = rawItem.body ? rawItem.body : rawItem;

// 1. HANDLE BREVO COMPLIANCE WEBHOOK (Unsubscribe / Hard Bounce)
if (payload.event === 'unsubscribed' || payload.event === 'hard_bounce' || payload.event === 'complaint') {{
  const email = (payload.email || '').trim().toLowerCase();
  if (!email) return [{{ json: {{ success: false, reason: 'No email in Brevo event' }} }}];

  // Lookup person in Twenty CRM
  const findRes = await requestJson(
    `http://192.168.1.240:8085/rest/people?filter=emails.primaryEmail%5Beq%5D:${{encodeURIComponent(email)}}`,
    {{ headers: {{ 'Authorization': `Bearer ${{TWENTY_TOKEN}}`, 'Accept': 'application/json' }} }}
  );

  const people = findRes.data?.data?.people || [];
  if (people.length > 0) {{
    const personId = people[0].id;
    // Set canEmail = false
    await requestJson(
      `http://192.168.1.240:8085/rest/people/${{personId}}`,
      {{ method: 'PATCH', headers: {{ 'Authorization': `Bearer ${{TWENTY_TOKEN}}`, 'Content-Type': 'application/json' }} }},
      {{ canEmail: false }}
    );
    return [{{ json: {{ success: true, event: payload.event, email, action: 'Marked canEmail = false in Twenty CRM' }} }}];
  }}

  return [{{ json: {{ success: true, event: payload.event, email, action: 'Contact not found in Twenty CRM' }} }}];
}}

// 2. HANDLE TWENTY -> BREVO SYNC (Schedule or Manual Trigger)
// A. Fetch existing Brevo lists
const listRes = await requestJson('https://api.brevo.com/v3/contacts/lists?limit=50', {{
  headers: {{ 'api-key': BREVO_KEY, 'Accept': 'application/json' }}
}});

const brevoLists = listRes.data?.lists || [];
const listMap = {{}};
for (const l of brevoLists) {{
  listMap[l.name.toLowerCase()] = l.id;
}}

const defaultListId = listMap['customer'] || 3;

// B. Fetch contacts from Twenty CRM
const twentyRes = await requestJson('http://192.168.1.240:8085/rest/people?limit=500', {{
  headers: {{ 'Authorization': `Bearer ${{TWENTY_TOKEN}}`, 'Accept': 'application/json' }}
}});

const people = twentyRes.data?.data?.people || [];
let syncedCount = 0;
let skippedNoEmail = 0;
let failedCount = 0;

for (const p of people) {{
  const email = (p.emails?.primaryEmail || '').trim().toLowerCase();
  if (!email) {{
    skippedNoEmail++;
    continue;
  }}

  const role = p.contactRole || 'Customer';
  const roleLower = role.toLowerCase();
  let targetListId = listMap[roleLower];

  // If role list does not exist in Brevo yet, create it dynamically
  if (!targetListId) {{
    const createListRes = await requestJson('https://api.brevo.com/v3/contacts/lists', {{
      method: 'POST',
      headers: {{ 'api-key': BREVO_KEY, 'Content-Type': 'application/json', 'Accept': 'application/json' }}
    }}, {{ name: role, folderId: 1 }});
    if (createListRes.ok && createListRes.data?.id) {{
      targetListId = createListRes.data.id;
      listMap[roleLower] = targetListId;
    }} else {{
      targetListId = defaultListId;
    }}
  }}

  let sms = null;
  const rawPhone = p.phones?.primaryPhoneNumber || '';
  const digits = rawPhone.replace(/[^0-9]/g, '');
  if (digits.length === 10) sms = '+1' + digits;
  else if (digits.length === 11 && digits.startsWith('1')) sms = '+' + digits;
  else if (digits.length >= 10 && digits.length <= 15) sms = '+' + digits;

  const attributes = {{
    FIRSTNAME: p.name?.firstName || '',
    LASTNAME: p.name?.lastName || '',
    ROLE: role,
    MARKET: p.market || '',
    LEAD_SOURCE: p.leadSource || '',
    EXT_ID: p.id
  }};
  if (sms) attributes.SMS = sms;

  const brevoPayload = {{
    email: email,
    attributes: attributes,
    listIds: [targetListId],
    updateEnabled: true
  }};

  const syncRes = await requestJson('https://api.brevo.com/v3/contacts', {{
    method: 'POST',
    headers: {{ 'api-key': BREVO_KEY, 'Content-Type': 'application/json', 'Accept': 'application/json' }}
  }}, brevoPayload);

  if (syncRes.ok) {{
    syncedCount++;
  }} else if (syncRes.status === 400 && String(syncRes.data).includes('SMS')) {{
    delete brevoPayload.attributes.SMS;
    const retryRes = await requestJson('https://api.brevo.com/v3/contacts', {{
      method: 'POST',
      headers: {{ 'api-key': BREVO_KEY, 'Content-Type': 'application/json', 'Accept': 'application/json' }}
    }}, brevoPayload);
    if (retryRes.ok) syncedCount++;
    else failedCount++;
  }} else {{
    failedCount++;
  }}
}}

return [{{
  json: {{
    success: true,
    totalTwentyContacts: people.length,
    syncedToBrevo: syncedCount,
    skippedNoEmail: skippedNoEmail,
    failed: failedCount,
    roleLists: listMap
  }}
}}];
'''

def main():
    db_path = '/tank/n8n/database.sqlite'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    wf_id = 'twentyBrevoSyncWf01'
    name = 'Twenty CRM ↔ Brevo Contact Sync'
    version_id = str(uuid.uuid4())

    nodes = [
        {
            "parameters": {
                "httpMethod": "POST",
                "path": "twenty-brevo-sync",
                "responseMode": "lastNode",
                "options": {}
            },
            "id": "node-sync-webhook",
            "name": "Sync On-Demand Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [200, 200],
            "webhookId": "twenty-brevo-sync"
        },
        {
            "parameters": {
                "httpMethod": "POST",
                "path": "brevo-event-webhook",
                "responseMode": "lastNode",
                "options": {}
            },
            "id": "node-brevo-webhook",
            "name": "Brevo Unsubscribe/Bounce Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [200, 380],
            "webhookId": "brevo-event-webhook"
        },
        {
            "parameters": {
                "rule": {
                    "interval": [
                        {
                            "field": "hours",
                            "hoursInterval": 6
                        }
                    ]
                }
            },
            "id": "node-schedule",
            "name": "Schedule Trigger (Every 6h)",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [200, 560]
        },
        {
            "parameters": {
                "jsCode": SYNC_CODE
            },
            "id": "node-sync-processor",
            "name": "Process Twenty ↔ Brevo Sync",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [500, 380]
        }
    ]

    connections = {
        "Sync On-Demand Webhook": {
            "main": [[{"node": "Process Twenty ↔ Brevo Sync", "type": "main", "index": 0}]]
        },
        "Brevo Unsubscribe/Bounce Webhook": {
            "main": [[{"node": "Process Twenty ↔ Brevo Sync", "type": "main", "index": 0}]]
        },
        "Schedule Trigger (Every 6h)": {
            "main": [[{"node": "Process Twenty ↔ Brevo Sync", "type": "main", "index": 0}]]
        }
    }

    # 1. workflow_entity
    cur.execute("""
    INSERT OR REPLACE INTO workflow_entity (id, name, active, nodes, connections, versionId, activeVersionId, settings, staticData, pinData, createdAt, updatedAt)
    VALUES (?, ?, 1, ?, ?, ?, ?, "{}", "{}", "{}", datetime("now"), datetime("now"))
    """, (wf_id, name, json.dumps(nodes), json.dumps(connections), version_id, version_id))

    # 2. shared_workflow
    cur.execute("""
    INSERT OR REPLACE INTO shared_workflow (workflowId, projectId, role)
    VALUES (?, "dsceMxUAlkx7KphM", "workflow:owner")
    """, (wf_id,))

    # 3. workflow_history
    cur.execute("""
    INSERT OR REPLACE INTO workflow_history (versionId, workflowId, authors, nodes, connections, name, autosaved, nodeGroups)
    VALUES (?, ?, "system", ?, ?, ?, 0, "[]")
    """, (version_id, wf_id, json.dumps(nodes), json.dumps(connections), name))

    # 4. workflow_published_version
    cur.execute("""
    INSERT OR REPLACE INTO workflow_published_version (workflowId, publishedVersionId)
    VALUES (?, ?)
    """, (wf_id, version_id))

    # 5. webhook_entity
    cur.execute("""
    INSERT OR REPLACE INTO webhook_entity (workflowId, webhookPath, method, node, pathLength)
    VALUES (?, "twenty-brevo-sync", "POST", "Sync On-Demand Webhook", 1)
    """, (wf_id,))

    cur.execute("""
    INSERT OR REPLACE INTO webhook_entity (workflowId, webhookPath, method, node, pathLength)
    VALUES (?, "brevo-event-webhook", "POST", "Brevo Unsubscribe/Bounce Webhook", 1)
    """, (wf_id,))

    conn.commit()
    conn.close()
    print(f"Created workflow '{name}' ({wf_id}) successfully!")

if __name__ == '__main__':
    main()
