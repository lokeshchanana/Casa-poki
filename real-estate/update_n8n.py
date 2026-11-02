import json
import sqlite3

# 1. Read base jsCode from open_house_workflow.json.bak
with open('/tank/n8n/open_house_workflow.json.bak', 'r') as f:
    base_wf = json.load(f)

orig_code = base_wf[0]['nodes'][1]['parameters']['jsCode']

# Define both ntfy (toggleable) and smsgate functions
integration_funcs = """
// ----------------- CONFIGURATION TOGGLES -----------------
const ENABLE_NTFY = false;      // Turned off for now as requested (code preserved)
const ENABLE_SMSGATE = true;    // SMS Gateway active via Android SIM

const SMSGATE_CONFIG = {
  endpoint: 'https://api.sms-gate.app/3rdparty/v1/messages',
  login: 'O8TMSG',
  password: 'b9xdffvtcpvvrn',
  simSlot: 0, // 0 for SIM 1 (ending in 1052)
  sendAsMms: false // Clean standard SMS with direct vCard link (prevents MMS outbox errors)
};

// ----------------- SMS GATEWAY INTEGRATION -----------------
const triggerSmsGate = async (guestPhone, guestName, location, isRepresented) => {
  const digits = String(guestPhone || '').replace(/[^0-9]/g, '');
  if (!guestPhone || digits.length < 10) {
    return { skipped: true, reason: 'No valid phone number provided' };
  }
  if (!SMSGATE_CONFIG.login || SMSGATE_CONFIG.login === 'YOUR_SMSGATE_LOGIN') {
    return { skipped: true, reason: 'Credentials not configured' };
  }
  try {
    const http = require('http');
    const https = require('https');
    const fs = require('fs');
    const url = require('url');

    let draftText = '';
    if (isRepresented) {
      draftText = `Hi ${guestName}, this is Lokesh Chanana (Loki). Thank you for touring the ${location} today!\\n\\n` +
        (SMSGATE_CONFIG.sendAsMms 
          ? `Attached is my direct contact card and property details for your records.\\n\\n` 
          : `Dropping my direct contact card for your records:\\nhttps://lokeshchanana.com/loki.vcf\\n\\n`) +
        `Please feel free to have your agent reach out to me directly if they need disclosure packets or offer guidelines. Enjoy the rest of your tour!`;
    } else {
      draftText = `Hi ${guestName}, this is Lokesh Chanana (Loki). Great meeting you at today's ${location}!\\n\\n` +
        (SMSGATE_CONFIG.sendAsMms 
          ? `Attached is my direct contact card so you have all my info saved in your phone.\\n\\n` 
          : `Dropping my direct contact card so you have all my info saved in your phone:\\nhttps://lokeshchanana.com/loki.vcf\\n\\n`) +
        `Feel free to text or call me anytime if you have questions about this home, neighborhood comps, or other properties in the area!`;
    }

    // Read local vCard file for MMS attachment
    let vcfBase64 = '';
    try {
      const vcfBuffer = fs.readFileSync('/home/node/.n8n/loki.vcf');
      vcfBase64 = vcfBuffer.toString('base64');
    } catch (e) {
      // Fallback if not readable
    }

    const payload = {
      phoneNumbers: [guestPhone]
    };
    if (typeof SMSGATE_CONFIG.simSlot === 'number') {
      payload.simSlot = SMSGATE_CONFIG.simSlot;
    }

    if (SMSGATE_CONFIG.sendAsMms && vcfBase64) {
      // Send as MMS with vCard attachment (no subject line)
      payload.mmsMessage = {
        text: draftText,
        attachments: [
          {
            contentType: 'text/x-vcard',
            name: 'Loki.vcf',
            data: vcfBase64
          }
        ]
      };
    } else {
      // Standard SMS
      payload.textMessage = {
        text: draftText
      };
    }

    const isHttps = SMSGATE_CONFIG.endpoint.startsWith('https');
    const client = isHttps ? https : http;
    const authHeader = 'Basic ' + Buffer.from(SMSGATE_CONFIG.login + ':' + SMSGATE_CONFIG.password).toString('base64');
    const payloadStr = JSON.stringify(payload);
    const parsedUrl = url.parse ? url.parse(SMSGATE_CONFIG.endpoint) : new url.URL(SMSGATE_CONFIG.endpoint);

    return await new Promise((resolve) => {
      const req = client.request({
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || (isHttps ? 443 : 80),
        path: parsedUrl.pathname,
        method: 'POST',
        headers: {
          'Authorization': authHeader,
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payloadStr),
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
      }, (res) => {
        let d = '';
        res.on('data', c => d += c);
        res.on('end', () => {
          try {
            resolve({ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode, data: JSON.parse(d) });
          } catch (e) {
            resolve({ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode, data: d });
          }
        });
      });
      req.on('error', (err) => resolve({ ok: false, error: err.message }));
      req.write(payloadStr);
      req.end();
    });
  } catch (err) {
    return { ok: false, error: err.message };
  }
};

// ----------------- NTFY NOTIFICATION INTEGRATION (TOGGLEABLE) -----------------
const triggerNtfyAlert = async (contactId) => {
  if (!ENABLE_NTFY) return;
  try {
    const https = require('https');
    const firstName = name.split(' ')[0] || name || 'Guest';
    const marketName = (city || 'open house').trim();
    const locationDesc = marketName ? `${marketName} open house` : "today's open house";

    let actionUrl = null;
    let actionLabel = null;

    if (phone) {
      let draftText = '';
      if (workingWithAgent === 'Yes') {
        draftText = `Hi ${name}, this is Lokesh Chanana (Loki). Thank you for touring the ${locationDesc} today!\\n\\n` +
          `Dropping my direct contact card and property details for your records:\\n` +
          `https://lokeshchanana.com/loki.vcf\\n\\n` +
          `Please feel free to have your agent reach out to me directly if they need disclosure packets or offer guidelines. Enjoy the rest of your tour!`;
      } else {
        draftText = `Hi ${name}, this is Lokesh Chanana (Loki). Great meeting you at today's ${locationDesc}!\\n\\n` +
          `Dropping my direct contact card so you have all my info saved in your inbox:\\n` +
          `https://lokeshchanana.com/loki.vcf\\n\\n` +
          `Feel free to text or call me anytime if you have questions about this home, neighborhood comps, or other properties in the area!`;
      }
      actionUrl = `sms:${phone}?body=${encodeURIComponent(draftText)}`;
      actionLabel = `💬 Text ${firstName}`;
    }

    const ntfyPayload = {
      topic: 'loki-re-signins',
      title: `🏡 Open House Sign-In: ${name}`,
      message: `${name} just signed in at ${locationDesc}.\\n` +
        `• Phone: ${rawPhone || phone || 'None'}\\n` +
        `• Email: ${email || 'None'}\\n` +
        `• Market: ${city}\\n` +
        (propertyAddress ? `• Property: ${propertyAddress}\\n` : '') +
        `• Agent: ${workingWithAgent}${agentName ? ' (' + agentName + ')' : ''}\\n` +
        `• Needs: ${needsStr}\\n` +
        (feedback ? `• Feedback: "${feedback}"\\n` : '') +
        (actionUrl ? '\\nTap button below to text contact card!' : ''),
      priority: 4,
      tags: ['house', 'speech_balloon']
    };

    if (actionUrl) {
      ntfyPayload.actions = [
        {
          action: 'view',
          label: actionLabel,
          url: actionUrl
        }
      ];
    }

    const payloadStr = JSON.stringify(ntfyPayload);

    await new Promise((resolve) => {
      const req = https.request({
        hostname: 'ntfy.sh',
        port: 443,
        path: '/',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payloadStr)
        }
      }, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => resolve());
      });
      req.on('error', () => resolve());
      req.write(payloadStr);
      req.end();
    });
  } catch (e) {
    // Graceful fallback: never block lead creation
  }
};
"""

target_1 = '// 1. Check if person already exists in CRM'
if target_1 not in orig_code:
    raise ValueError(f"Could not find target_1: {target_1}")
code_with_helper = orig_code.replace(target_1, integration_funcs + '\n' + target_1)
code_with_helper = code_with_helper.replace("if (!foundPerson && name) {", "if (!foundPerson && name && !email && !phone) {")

target_2 = """  // If existing person has no market set, update with current city
  const existingMarket = foundPerson.attributes?.custom_fields?.market;
  if (!existingMarket && city) {
    await requestCrm('/api/v1/people/' + personId, 'PUT', {
      custom_fields: { market: city }
    });
  }

  return [{
    json: {
      success: true,
      status: 'existing_contact_updated',
      personId: personId,
      name: foundPerson.attributes?.name || name,
      market: city,
      lead_source: 'Open House',
      message: `Welcome back, ${name}! Your open house sign-in has been recorded.`
    }
  }];"""

replacement_2 = """  // Update additional information in existing CRM record
  const updatePayload = {
    custom_fields: {}
  };

  const existingName = foundPerson.attributes?.name;
  if (name && (!existingName || existingName === 'Open House Visitor' || existingName === 'Open House Lead' || existingName.toLowerCase().startsWith('guest'))) {
    updatePayload.name = name;
  }

  if (city) {
    updatePayload.custom_fields.market = city;
  }

  updatePayload.custom_fields.role = [roleId];

  const existingPhones = (foundPerson.attributes?.custom_fields?.phone_number || []).map(p => 
    typeof p === 'object' ? (p.label || p.id || '') : String(p)
  ).filter(Boolean);
  if (phone && !existingPhones.includes(phone)) {
    updatePayload.custom_fields.phone_number = [...existingPhones, phone];
  }

  const existingEmails = (foundPerson.attributes?.custom_fields?.emails || []).map(e => 
    typeof e === 'object' ? (e.label || e.id || '') : String(e)
  ).filter(Boolean).map(e => e.toLowerCase());
  if (email && !existingEmails.includes(email)) {
    updatePayload.custom_fields.emails = [...existingEmails, email];
  }

  if (updatePayload.name || Object.keys(updatePayload.custom_fields).length > 0) {
    await requestCrm('/api/v1/people/' + personId, 'PUT', updatePayload);
  }

  const customerName = (name || existingName || 'Friend').trim();

  // Create Follow-Up Task
  await requestCrm('/api/v1/tasks', 'POST', {
    title: `Follow up with ${customerName} (Repeat Open House Visit - ${city})`,
    people_ids: [personId],
    custom_fields: {
      status: '01m35s6hvyb83xwkj01qsnvm2v', // To do
      priority: '01m35s6hwc08qa20pphz7gnncg', // Medium
      description: `Repeat open house visit from ${city}.\\nNeeds: ${needsStr}\\nFeedback: ${feedback || 'None'}\\nPhone: ${phone || (existingPhones[0] || 'N/A')}\\nEmail: ${email || (existingEmails[0] || 'N/A')}`
    }
  });

  // DO NOT send automated text message to existing contacts as requested
  if (ENABLE_NTFY) {
    await triggerNtfyAlert(personId);
  }

  return [{
    json: {
      success: true,
      status: 'existing_contact_updated',
      personId: personId,
      name: customerName,
      market: city,
      lead_source: 'Open House',
      smsGateResult: { skipped: true, reason: 'Existing contact in CRM - text automation skipped' },
      message: `Welcome back, ${customerName}!`
    }
  }];"""

if target_2 not in code_with_helper:
    raise ValueError("Could not find target_2")
code_with_call1 = code_with_helper.replace(target_2, replacement_2)

target_3 = """// 5. Create Follow-Up Task
await requestCrm('/api/v1/tasks', 'POST', {
  title: `Follow up with ${name} (Open House Lead - ${city})`,
  people_ids: [newPersonId],
  custom_fields: {
    status: '01m35s6hvyb83xwkj01qsnvm2v', // To do
    priority: '01m35s6hwc08qa20pphz7gnncg', // Medium
    description: `Follow up with open house lead from ${city}.\\nNeeds: ${needsStr}\\nFeedback: ${feedback || 'None'}\\nPhone: ${phone || 'N/A'}\\nEmail: ${email || 'N/A'}`
  }
});

return [{
  json: {
    success: true,
    status: 'created',
    personId: newPersonId,
    name: name,
    market: city,
    lead_source: 'Open House',
    message: `Thank you for signing in, ${name}! Your details have been added to the CRM.`
  }
}];"""

replacement_3 = """// 5. Create Follow-Up Task
await requestCrm('/api/v1/tasks', 'POST', {
  title: `Follow up with ${name} (Open House Lead - ${city})`,
  people_ids: [newPersonId],
  custom_fields: {
    status: '01m35s6hvyb83xwkj01qsnvm2v', // To do
    priority: '01m35s6hwc08qa20pphz7gnncg', // Medium
    description: `Follow up with open house lead from ${city}.\\nNeeds: ${needsStr}\\nFeedback: ${feedback || 'None'}\\nPhone: ${phone || 'N/A'}\\nEmail: ${email || 'N/A'}`
  }
});

const marketDesc = city ? (city + ' open house') : "today's open house";
let smsGateResult = null;
const hasValidPhone = Boolean(phone && phone.replace(/[^0-9]/g, '').length >= 10);
if (ENABLE_SMSGATE && hasValidPhone) {
  smsGateResult = await triggerSmsGate(phone, name, marketDesc, workingWithAgent === 'Yes');
}
if (ENABLE_NTFY) {
  await triggerNtfyAlert(newPersonId);
}

return [{
  json: {
    success: true,
    status: 'created',
    personId: newPersonId,
    name: name,
    market: city,
    lead_source: 'Open House',
    smsGateResult: smsGateResult,
    message: `Welcome, ${name}! Your sign-in has been received.`
  }
}];"""

if target_3 not in code_with_call1:
    raise ValueError("Could not find target_3")
final_code = code_with_call1.replace(target_3, replacement_3)

# Verify $input is intact
if '$input.first().json' not in final_code:
    raise ValueError("Verification failed: $input.first().json not found in final_code!")

# 2. Update sqlite database
conn = sqlite3.connect('/tank/n8n/database.sqlite')
cursor = conn.cursor()

cursor.execute('SELECT nodes FROM workflow_entity WHERE id="wGB3XfRGWgbbvOGP";')
nodes = json.loads(cursor.fetchone()[0])
for n in nodes:
    if n['name'] == 'Process Open House Intake':
        n['parameters']['jsCode'] = final_code

nodes_json = json.dumps(nodes)
cursor.execute('UPDATE workflow_entity SET nodes = ? WHERE id="wGB3XfRGWgbbvOGP";', (nodes_json,))
print("Updated workflow_entity rows:", cursor.rowcount)

cursor.execute('UPDATE workflow_history SET nodes = ? WHERE workflowId="wGB3XfRGWgbbvOGP";', (nodes_json,))
print("Updated workflow_history rows:", cursor.rowcount)

conn.commit()
conn.close()

# 3. Update /tank/n8n/open_house_workflow.json
with open('/tank/n8n/open_house_workflow.json', 'r') as f:
    wf_file = json.load(f)

for n in wf_file[0]['nodes']:
    if n['name'] == 'Process Open House Intake':
        n['parameters']['jsCode'] = final_code

with open('/tank/n8n/open_house_workflow.json', 'w') as f:
    json.dump(wf_file, f, indent=2)

print("Updated /tank/n8n/open_house_workflow.json successfully!")
