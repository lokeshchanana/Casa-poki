#!/usr/bin/env python3
import sqlite3
import json
import os

CRM_TOKEN = os.environ.get('TWENTY_API_KEY', '')
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')

WEBSITE_CONTACT_CODE = f'''const http = require('http');

const CRM_TOKEN = '{CRM_TOKEN}';

const requestCrm = async (endpoint, method = 'GET', body = null) => {{
  return new Promise((resolve) => {{
    const headers = {{
      'Authorization': `Bearer ${{CRM_TOKEN}}`,
      'Accept': 'application/json'
    }};
    if (body) {{
      headers['Content-Type'] = 'application/json';
    }}
    const req = http.request({{
      hostname: '192.168.1.240',
      port: 8085,
      path: endpoint,
      method: method,
      headers: headers
    }}, (res) => {{
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {{
        try {{
          resolve({{
            ok: res.statusCode >= 200 && res.statusCode < 300,
            status: res.statusCode,
            data: JSON.parse(data)
          }});
        }} catch (e) {{
          resolve({{
            ok: res.statusCode >= 200 && res.statusCode < 300,
            status: res.statusCode,
            data: data
          }});
        }}
      }});
    }});
    req.on('error', err => resolve({{ ok: false, status: 500, data: {{ message: err.message }} }}));
    if (body) {{
      req.write(typeof body === 'string' ? body : JSON.stringify(body));
    }}
    req.end();
  }});
}};

function normalizePhone(num) {{
  if (!num) return '';
  let digits = String(num).replace(/[^0-9]/g, '');
  if (digits.length === 10) return '+1' + digits;
  if (digits.length === 11 && digits.startsWith('1')) return '+' + digits;
  if (digits.length >= 10 && digits.length <= 15) return '+' + digits;
  return digits;
}}

const SMSGATE_CONFIG = {{
  endpoint: 'https://api.sms-gate.app/3rdparty/v1/messages',
  login: 'O8TMSG',
  password: 'b9xdffvtcpvvrn',
  simSlot: 0
}};

const triggerSmsGate = async (guestPhone, guestName, purpose) => {{
  const digits = String(guestPhone || '').replace(/[^0-9]/g, '');
  if (!guestPhone || digits.length < 10) {{
    return {{ skipped: true, reason: 'No valid phone number provided' }};
  }}
  if (!SMSGATE_CONFIG.login || SMSGATE_CONFIG.login === 'YOUR_SMSGATE_LOGIN') {{
    return {{ skipped: true, reason: 'Credentials not configured' }};
  }}
  try {{
    const https = require('https');
    const url = require('url');

    const firstName = (guestName || '').split(' ')[0] || guestName || 'there';
    const purposeText = purpose ? purpose.toLowerCase() : 'your inquiry';

    const draftText = `Hi ${{firstName}}, this is Lokesh Chanana (Loki). Thank you for reaching out through my website (lokeshchanana.com)!\\n\\n` +
      `I have received your message regarding ${{purposeText}} and will get back to you shortly.\\n\\n` +
      `In the meantime, feel free to save my direct contact card to your phone:\\nhttps://lokeshchanana.com/loki.vcf`;

    const payload = {{
      phoneNumbers: [guestPhone],
      simSlot: SMSGATE_CONFIG.simSlot,
      textMessage: {{
        text: draftText
      }}
    }};

    const isHttps = SMSGATE_CONFIG.endpoint.startsWith('https');
    const client = isHttps ? https : http;
    const authHeader = 'Basic ' + Buffer.from(SMSGATE_CONFIG.login + ':' + SMSGATE_CONFIG.password).toString('base64');
    const payloadStr = JSON.stringify(payload);
    const parsedUrl = url.parse ? url.parse(SMSGATE_CONFIG.endpoint) : new url.URL(SMSGATE_CONFIG.endpoint);

    return await new Promise((resolve) => {{
      const req = client.request({{
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || (isHttps ? 443 : 80),
        path: parsedUrl.pathname,
        method: 'POST',
        headers: {{
          'Authorization': authHeader,
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payloadStr),
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }}
      }}, (res) => {{
        let d = '';
        res.on('data', c => d += c);
        res.on('end', () => {{
          try {{
            resolve({{ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode, data: JSON.parse(d) }});
          }} catch (e) {{
            resolve({{ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode, data: d }});
          }}
        }});
      }});
      req.on('error', (err) => resolve({{ ok: false, error: err.message }}));
      req.write(payloadStr);
      req.end();
    }});
  }} catch (err) {{
    return {{ ok: false, error: err.message }};
  }}
}};

const triggerBrevoSync = async (guestEmail, guestName, guestPhone, guestRole, guestMarket, guestSource, guestId) => {{
  if (!guestEmail) return {{ skipped: true, reason: 'No email' }};
  try {{
    const https = require('https');
    const listMap = {{ 'customer': 3, 'buyer': 4, 'seller': 5, 'lead': 6, 'real estate agent': 7, 'contractor': 8, 'lender': 9 }};
    const targetListId = listMap[(guestRole || 'customer').toLowerCase()] || 3;
    const digits = String(guestPhone || '').replace(/[^0-9]/g, '');
    let sms = null;
    if (digits.length === 10) sms = '+1' + digits;
    else if (digits.length === 11 && digits.startsWith('1')) sms = '+' + digits;
    else if (digits.length >= 10 && digits.length <= 15) sms = '+' + digits;

    const nameParts = (guestName || '').split(' ');
    const firstName = nameParts[0] || '';
    const lastName = nameParts.slice(1).join(' ') || '';

    const attributes = {{
      FIRSTNAME: firstName,
      LASTNAME: lastName,
      ROLE: guestRole || 'Customer',
      MARKET: guestMarket || '',
      LEAD_SOURCE: guestSource || 'Website',
      EXT_ID: guestId || ''
    }};
    if (sms) attributes.SMS = sms;

    const payload = JSON.stringify({{
      email: guestEmail.trim().toLowerCase(),
      attributes: attributes,
      listIds: [targetListId],
      updateEnabled: true
    }});

    return await new Promise((resolve) => {{
      const req = https.request({{
        hostname: 'api.brevo.com',
        port: 443,
        path: '/v3/contacts',
        method: 'POST',
        headers: {{
          'api-key': f'{BREVO_API_KEY}',
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payload)
        }}
      }}, (res) => {{
        let d = '';
        res.on('data', c => d += c);
        res.on('end', () => resolve({{ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode }}));
      }});
      req.on('error', (err) => resolve({{ ok: false, error: err.message }}));
      req.write(payload);
      req.end();
    }});
  }} catch (e) {{
    return {{ ok: false, error: e.message }};
  }}
}};

const rawItem = $input.first().json;
const payload = rawItem.body ? rawItem.body : rawItem;

const name = (payload.name || payload.Name || '').trim();
const rawPhone = payload.phone || payload.phone_number || payload['Phone'] || '';
const phone = normalizePhone(rawPhone);
const email = (payload.email || payload.Email || '').trim().toLowerCase();
const purpose = (payload.purpose || payload.subject || payload.Purpose || 'General Inquiry').trim();
const message = (payload.message || payload.comments || payload.inquiry || '').trim();

if (!name && !email && !phone) {{
  return [{{
    json: {{
      success: false,
      message: 'Name, email, or phone is required.'
    }}
  }}];
}}

// 1. Search existing person in Twenty CRM
let foundPerson = null;

if (email) {{
  const searchEmail = await requestCrm(`/rest/people?filter=emails.primaryEmail[eq]:${{encodeURIComponent(email)}}`);
  if (searchEmail.ok && searchEmail.data?.data?.people?.length > 0) {{
    foundPerson = searchEmail.data.data.people[0];
  }}
}}

if (!foundPerson && phone) {{
  const digits = phone.replace(/[^0-9]/g, '');
  const searchDigits = digits.length >= 10 ? digits.slice(-10) : digits;
  if (searchDigits) {{
    const searchPhone = await requestCrm(`/rest/people?filter=phones.primaryPhoneNumber[ilike]:%25${{encodeURIComponent(searchDigits)}}%25`);
    if (searchPhone.ok && searchPhone.data?.data?.people?.length > 0) {{
      foundPerson = searchPhone.data.data.people[0];
    }}
  }}
}}

const timestamp = new Date().toLocaleString('en-US', {{ timeZone: 'America/Los_Angeles' }});
let personId = null;

const nameParts = (name || 'Website Visitor').split(' ');
const firstName = nameParts[0] || 'Website';
const lastName = nameParts.slice(1).join(' ');

if (foundPerson) {{
  personId = foundPerson.id;

  const updatePayload = {{
    leadSource: 'Website',
    contactRole: 'Customer'
  }};
  if (name && (!foundPerson.name?.firstName || foundPerson.name.firstName === 'Website')) {{
    updatePayload.name = {{
      firstName: firstName,
      lastName: lastName
    }};
  }}
  if (phone && !foundPerson.phones?.primaryPhoneNumber) {{
    updatePayload.phones = {{ primaryPhoneNumber: phone }};
  }}
  if (email && !foundPerson.emails?.primaryEmail) {{
    updatePayload.emails = {{ primaryEmail: email }};
  }}

  await requestCrm(`/rest/people/${{personId}}`, 'PATCH', updatePayload);
}} else {{
  // Create brand new contact in Twenty CRM
  const newPersonPayload = {{
    name: {{
      firstName: firstName,
      lastName: lastName
    }},
    leadSource: 'Website',
    contactRole: 'Customer',
    canEmail: true
  }};
  if (email) {{
    newPersonPayload.emails = {{ primaryEmail: email }};
  }}
  if (phone) {{
    newPersonPayload.phones = {{ primaryPhoneNumber: phone }};
  }}

  const createPersonRes = await requestCrm('/rest/people', 'POST', newPersonPayload);
  if (!createPersonRes.ok) {{
    return [{{
      json: {{
        success: false,
        error: createPersonRes.data?.message || 'Failed to create person in Twenty CRM',
        details: createPersonRes.data
      }}
    }}];
  }}
  personId = createPersonRes.data?.data?.createPerson?.id;

  // Create Opportunity for new lead
  await requestCrm('/rest/opportunities', 'POST', {{
    name: `[Website Lead] ${{name || 'Inquiry'}}`,
    pointOfContactId: personId,
    stage: 'NEW'
  }});
}}

// 2. Create Note with inquiry details
const noteBody = `Website Contact Inquiry\\n` +
  `-----------------------\\n` +
  `Full Name: ${{name || 'Not provided'}}\\n` +
  `Purpose of Contact: ${{purpose}}\\n` +
  `Phone: ${{phone || rawPhone || 'Not provided'}}\\n` +
  `Email: ${{email || 'Not provided'}}\\n` +
  `Inquiry Details: ${{message || 'None provided'}}\\n` +
  `Timestamp: ${{timestamp}}`;

const noteRes = await requestCrm('/rest/notes', 'POST', {{
  title: `Website Inquiry - ${{purpose}} (${{new Date().toISOString().slice(0, 10)}})`,
  bodyV2: {{ markdown: noteBody }}
}});
const noteId = noteRes.data?.data?.createNote?.id;
if (noteId && personId) {{
  await requestCrm('/rest/noteTargets', 'POST', {{
    noteId: noteId,
    targetPersonId: personId
  }});
}}

// 3. Create Follow-Up Task
const taskRes = await requestCrm('/rest/tasks', 'POST', {{
  title: `Website Inquiry: ${{name || 'New Lead'}} - ${{purpose}}`,
  bodyV2: {{
    markdown: `Website inquiry received from ${{name || 'Lead'}}.\\nPurpose: ${{purpose}}\\nMessage: ${{message || 'None'}}\\nPhone: ${{phone || 'N/A'}}\\nEmail: ${{email || 'N/A'}}`
  }},
  status: 'TODO'
}});
const taskId = taskRes.data?.data?.createTask?.id;
if (taskId && personId) {{
  await requestCrm('/rest/taskTargets', 'POST', {{
    taskId: taskId,
    targetPersonId: personId
  }});
}}

// 4. Send automated SMS
let smsGateResult = null;
const hasValidPhone = Boolean(phone && phone.replace(/[^0-9]/g, '').length >= 10);
if (hasValidPhone) {{
  smsGateResult = await triggerSmsGate(phone, name, purpose);
}}

// 5. Sync to Brevo contact list
if (email) {{
  await triggerBrevoSync(email, name, phone, 'Customer', 'Greater Seattle', 'Website', personId);
}}

return [{{
  json: {{
    success: true,
    personId: personId,
    name: name,
    purpose: purpose,
    lead_source: 'Website',
    smsGateResult: smsGateResult,
    message: `Thank you, ${{name}}! Your inquiry has been received. Loki will get back to you shortly.`
  }}
}}];
'''

OPEN_HOUSE_CODE = f'''const http = require('http');

const CRM_TOKEN = '{CRM_TOKEN}';

const requestCrm = async (endpoint, method = 'GET', body = null) => {{
  return new Promise((resolve) => {{
    const headers = {{
      'Authorization': `Bearer ${{CRM_TOKEN}}`,
      'Accept': 'application/json'
    }};
    if (body) {{
      headers['Content-Type'] = 'application/json';
    }}
    const req = http.request({{
      hostname: '192.168.1.240',
      port: 8085,
      path: endpoint,
      method: method,
      headers: headers
    }}, (res) => {{
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {{
        try {{
          resolve({{
            ok: res.statusCode >= 200 && res.statusCode < 300,
            status: res.statusCode,
            data: JSON.parse(data)
          }});
        }} catch (e) {{
          resolve({{
            ok: res.statusCode >= 200 && res.statusCode < 300,
            status: res.statusCode,
            data: data
          }});
        }}
      }});
    }});
    req.on('error', err => resolve({{ ok: false, status: 500, data: {{ message: err.message }} }}));
    if (body) {{
      req.write(typeof body === 'string' ? body : JSON.stringify(body));
    }}
    req.end();
  }});
}};

function normalizePhone(num) {{
  if (!num) return '';
  let digits = String(num).replace(/[^0-9+]/g, '');
  if (digits.startsWith('+')) return digits;
  if (digits.length === 10) return '+1' + digits;
  if (digits.length === 11 && digits.startsWith('1')) return '+' + digits;
  return digits ? '+' + digits : '';
}}

const rawItem = $input.first().json;
const payload = rawItem.body ? rawItem.body : rawItem;

const name = (payload.name || payload.Name || '').trim();
const rawPhone = payload.phone || payload.phone_number || payload['Phone #'] || payload['Phone Number'] || '';
const phone = normalizePhone(rawPhone);
const email = (payload.email || payload.Email || '').trim().toLowerCase();
const feedback = (payload.feedback || payload.Feedback || '').trim();
const workingWithAgent = (payload.working_with_agent || payload.agent || payload['Are you working with an agent?'] || 'No').trim();
const agentName = (payload.agent_name || payload.agentName || '').trim();
const propertyAddress = (payload.property_address || payload.property || payload.propertyAddress || '').trim();
const city = (payload.city || payload.market || payload.City || payload.Market || 'Greater Seattle').trim();

let needs = payload.current_needs || payload.needs || payload['CURRENT NEEDS?'] || [];
if (typeof needs === 'string') {{
  try {{ needs = JSON.parse(needs); }} catch (e) {{ needs = [needs]; }}
}}
if (!Array.isArray(needs)) needs = [String(needs)];
needs = needs.filter(Boolean);
const needsStr = needs.join(', ') || 'Not specified';

if (!name && !email && !phone) {{
  return [{{
    json: {{
      success: false,
      message: 'Name, email, or phone is required.'
    }}
  }}];
}}

// ----------------- CONFIGURATION TOGGLES -----------------
const ENABLE_NTFY = false;
const ENABLE_SMSGATE = true;

const SMSGATE_CONFIG = {{
  endpoint: 'https://api.sms-gate.app/3rdparty/v1/messages',
  login: 'O8TMSG',
  password: 'b9xdffvtcpvvrn',
  simSlot: 0,
  sendAsMms: false
}};

const triggerSmsGate = async (guestPhone, guestName, location, isRepresented) => {{
  const digits = String(guestPhone || '').replace(/[^0-9]/g, '');
  if (!guestPhone || digits.length < 10) {{
    return {{ skipped: true, reason: 'No valid phone number provided' }};
  }}
  if (!SMSGATE_CONFIG.login || SMSGATE_CONFIG.login === 'YOUR_SMSGATE_LOGIN') {{
    return {{ skipped: true, reason: 'Credentials not configured' }};
  }}
  try {{
    const https = require('https');
    const url = require('url');

    let draftText = '';
    if (isRepresented) {{
      draftText = `Hi ${{guestName}}, this is Lokesh Chanana (Loki). Thank you for touring the ${{location}} today!\\n\\n` +
        `Dropping my direct contact card for your records:\\nhttps://lokeshchanana.com/loki.vcf\\n\\n` +
        `Please feel free to have your agent reach out to me directly if they need disclosure packets or offer guidelines. Have a great day!`;
    }} else {{
      draftText = `Hi ${{guestName}}, this is Lokesh Chanana (Loki). Thank you for visiting the ${{location}} open house today!\\n\\n` +
        `Dropping my direct contact card so you have it saved:\\nhttps://lokeshchanana.com/loki.vcf\\n\\n` +
        `Feel free to text or call if you have any questions about this property or anything in the area. Have a wonderful weekend!`;
    }}

    const payload = {{
      phoneNumbers: [guestPhone],
      simSlot: SMSGATE_CONFIG.simSlot,
      textMessage: {{
        text: draftText
      }}
    }};

    const isHttps = SMSGATE_CONFIG.endpoint.startsWith('https');
    const client = isHttps ? https : http;
    const authHeader = 'Basic ' + Buffer.from(SMSGATE_CONFIG.login + ':' + SMSGATE_CONFIG.password).toString('base64');
    const payloadStr = JSON.stringify(payload);
    const parsedUrl = url.parse ? url.parse(SMSGATE_CONFIG.endpoint) : new url.URL(SMSGATE_CONFIG.endpoint);

    return await new Promise((resolve) => {{
      const req = client.request({{
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || (isHttps ? 443 : 80),
        path: parsedUrl.pathname,
        method: 'POST',
        headers: {{
          'Authorization': authHeader,
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payloadStr),
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }}
      }}, (res) => {{
        let d = '';
        res.on('data', c => d += c);
        res.on('end', () => {{
          try {{
            resolve({{ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode, data: JSON.parse(d) }});
          }} catch (e) {{
            resolve({{ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode, data: d }});
          }}
        }});
      }});
      req.on('error', (err) => resolve({{ ok: false, error: err.message }}));
      req.write(payloadStr);
      req.end();
    }});
  }} catch (err) {{
    return {{ ok: false, error: err.message }};
  }}
}};

const triggerBrevoSync = async (guestEmail, guestName, guestPhone, guestRole, guestMarket, guestSource, guestId) => {{
  if (!guestEmail) return {{ skipped: true, reason: 'No email' }};
  try {{
    const https = require('https');
    const listMap = {{ 'customer': 3, 'buyer': 4, 'seller': 5, 'lead': 6, 'real estate agent': 7, 'contractor': 8, 'lender': 9 }};
    const targetListId = listMap[(guestRole || 'customer').toLowerCase()] || 3;
    const digits = String(guestPhone || '').replace(/[^0-9]/g, '');
    let sms = null;
    if (digits.length === 10) sms = '+1' + digits;
    else if (digits.length === 11 && digits.startsWith('1')) sms = '+' + digits;
    else if (digits.length >= 10 && digits.length <= 15) sms = '+' + digits;

    const nameParts = (guestName || '').split(' ');
    const firstName = nameParts[0] || '';
    const lastName = nameParts.slice(1).join(' ') || '';

    const attributes = {{
      FIRSTNAME: firstName,
      LASTNAME: lastName,
      ROLE: guestRole || 'Customer',
      MARKET: guestMarket || '',
      LEAD_SOURCE: guestSource || 'Website',
      EXT_ID: guestId || ''
    }};
    if (sms) attributes.SMS = sms;

    const payload = JSON.stringify({{
      email: guestEmail.trim().toLowerCase(),
      attributes: attributes,
      listIds: [targetListId],
      updateEnabled: true
    }});

    return await new Promise((resolve) => {{
      const req = https.request({{
        hostname: 'api.brevo.com',
        port: 443,
        path: '/v3/contacts',
        method: 'POST',
        headers: {{
          'api-key': f'{BREVO_API_KEY}',
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payload)
        }}
      }}, (res) => {{
        let d = '';
        res.on('data', c => d += c);
        res.on('end', () => resolve({{ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode }}));
      }});
      req.on('error', (err) => resolve({{ ok: false, error: err.message }}));
      req.write(payload);
      req.end();
    }});
  }} catch (e) {{
    return {{ ok: false, error: e.message }};
  }}
}};

// 1. Search existing person in Twenty CRM
let foundPerson = null;

if (email) {{
  const searchEmail = await requestCrm(`/rest/people?filter=emails.primaryEmail[eq]:${{encodeURIComponent(email)}}`);
  if (searchEmail.ok && searchEmail.data?.data?.people?.length > 0) {{
    foundPerson = searchEmail.data.data.people[0];
  }}
}}

if (!foundPerson && phone) {{
  const digits = phone.replace(/[^0-9]/g, '');
  const searchDigits = digits.length >= 10 ? digits.slice(-10) : digits;
  if (searchDigits) {{
    const searchPhone = await requestCrm(`/rest/people?filter=phones.primaryPhoneNumber[ilike]:%25${{encodeURIComponent(searchDigits)}}%25`);
    if (searchPhone.ok && searchPhone.data?.data?.people?.length > 0) {{
      foundPerson = searchPhone.data.data.people[0];
    }}
  }}
}}

const timestamp = new Date().toLocaleString('en-US', {{ timeZone: 'America/Los_Angeles' }});
let personId = null;

const nameParts = (name || 'Open House Visitor').split(' ');
const firstName = nameParts[0] || 'Visitor';
const lastName = nameParts.slice(1).join(' ');

if (foundPerson) {{
  personId = foundPerson.id;

  const updatePayload = {{
    leadSource: 'Open House',
    market: city || foundPerson.market,
    contactRole: 'Customer'
  }};
  if (name && (!foundPerson.name?.firstName || foundPerson.name.firstName.toLowerCase().startsWith('guest'))) {{
    updatePayload.name = {{
      firstName: firstName,
      lastName: lastName
    }};
  }}
  if (phone && !foundPerson.phones?.primaryPhoneNumber) {{
    updatePayload.phones = {{ primaryPhoneNumber: phone }};
  }}
  if (email && !foundPerson.emails?.primaryEmail) {{
    updatePayload.emails = {{ primaryEmail: email }};
  }}

  await requestCrm(`/rest/people/${{personId}}`, 'PATCH', updatePayload);

  const customerName = name || (foundPerson.name?.firstName ? `${{foundPerson.name.firstName}} ${{foundPerson.name.lastName || ''}}`.trim() : 'Friend');

  // Create Follow-Up Task
  const taskRes = await requestCrm('/rest/tasks', 'POST', {{
    title: `Follow up with ${{customerName}} (Repeat Open House Visit - ${{city}})`,
    bodyV2: {{
      markdown: `Repeat open house visit from ${{city}}.\\nNeeds: ${{needsStr}}\\nFeedback: ${{feedback || 'None'}}\\nPhone: ${{phone || 'N/A'}}\\nEmail: ${{email || 'N/A'}}`
    }},
    status: 'TODO'
  }});
  const taskId = taskRes.data?.data?.createTask?.id;
  if (taskId && personId) {{
    await requestCrm('/rest/taskTargets', 'POST', {{
      taskId: taskId,
      targetPersonId: personId
    }});
  }}

  const syncEmail = email || foundPerson.emails?.primaryEmail;
  if (syncEmail) {{
    await triggerBrevoSync(syncEmail, customerName, phone || foundPerson.phones?.primaryPhoneNumber, 'Customer', city, 'Open House', personId);
  }}

  return [{{
    json: {{
      success: true,
      status: 'existing_contact_updated',
      personId: personId,
      name: customerName,
      market: city,
      lead_source: 'Open House',
      smsGateResult: {{ skipped: true, reason: 'Existing contact in CRM - text automation skipped' }},
      message: `Welcome back, ${{customerName}}!`
    }}
  }}];
}}

// 2. Create brand new contact in Twenty CRM
const newPersonPayload = {{
  name: {{
    firstName: firstName,
    lastName: lastName
  }},
  leadSource: 'Open House',
  market: city,
  canEmail: true,
  contactRole: 'Customer'
}};
if (phone) newPersonPayload.phones = {{ primaryPhoneNumber: phone }};
if (email) newPersonPayload.emails = {{ primaryEmail: email }};

const createPersonRes = await requestCrm('/rest/people', 'POST', newPersonPayload);
if (!createPersonRes.ok) {{
  return [{{
    json: {{
      success: false,
      error: createPersonRes.data?.message || 'Failed to create person in Twenty CRM',
      details: createPersonRes.data
    }}
  }}];
}}

const newPersonId = createPersonRes.data?.data?.createPerson?.id;

// 3. Create Note
const noteBody = `Open House Sign-In Details\\n` +
  `--------------------------\\n` +
  `Full Name: ${{name}}\\n` +
  `Phone: ${{phone || 'Not provided'}}\\n` +
  `Email: ${{email || 'Not provided'}}\\n` +
  `Market / City: ${{city}}\\n` +
  `Property: ${{propertyAddress || 'Open House'}}\\n` +
  `Working with Agent: ${{workingWithAgent}}${{agentName ? ' (' + agentName + ')' : ''}}\\n` +
  `Current Needs: ${{needsStr}}\\n` +
  `Feedback: ${{feedback || 'None provided'}}\\n` +
  `Timestamp: ${{timestamp}}`;

const noteRes = await requestCrm('/rest/notes', 'POST', {{
  title: `Open House Sign-In - ${{city}}`,
  bodyV2: {{ markdown: noteBody }}
}});
const noteId = noteRes.data?.data?.createNote?.id;
if (noteId && newPersonId) {{
  await requestCrm('/rest/noteTargets', 'POST', {{
    noteId: noteId,
    targetPersonId: newPersonId
  }});
}}

// 4. Create Opportunity
await requestCrm('/rest/opportunities', 'POST', {{
  name: `[Customer] ${{name}}`,
  pointOfContactId: newPersonId,
  stage: 'NEW'
}});

// 5. Create Follow-Up Task
const taskRes = await requestCrm('/rest/tasks', 'POST', {{
  title: `Follow up with ${{name}} (Open House Lead - ${{city}})`,
  bodyV2: {{
    markdown: `Follow up with open house lead from ${{city}}.\\nNeeds: ${{needsStr}}\\nFeedback: ${{feedback || 'None'}}\\nPhone: ${{phone || 'N/A'}}\\nEmail: ${{email || 'N/A'}}`
  }},
  status: 'TODO'
}});
const taskId = taskRes.data?.data?.createTask?.id;
if (taskId && newPersonId) {{
  await requestCrm('/rest/taskTargets', 'POST', {{
    taskId: taskId,
    targetPersonId: newPersonId
  }});
}}

const marketDesc = city ? (city + ' open house') : "today's open house";
let smsGateResult = null;
const hasValidPhone = Boolean(phone && phone.replace(/[^0-9]/g, '').length >= 10);
if (ENABLE_SMSGATE && hasValidPhone) {{
  smsGateResult = await triggerSmsGate(phone, name, marketDesc, workingWithAgent === 'Yes');
}}

// Sync to Brevo contact list
if (email) {{
  await triggerBrevoSync(email, name, phone, 'Customer', city, 'Open House', newPersonId);
}}

return [{{
  json: {{
    success: true,
    status: 'created',
    personId: newPersonId,
    name: name,
    market: city,
    lead_source: 'Open House',
    smsGateResult: smsGateResult,
    message: `Welcome, ${{name}}! Your sign-in has been received.`
  }}
}}];
'''

GATEWAY_CODE = f'''const http = require('http');

const CRM_TOKEN = '{CRM_TOKEN}';

const requestCrm = async (endpoint, method = 'GET', body = null) => {{
  return new Promise((resolve) => {{
    const headers = {{
      'Authorization': `Bearer ${{CRM_TOKEN}}`,
      'Accept': 'application/json'
    }};
    if (body) {{
      headers['Content-Type'] = 'application/json';
    }}
    const req = http.request({{
      hostname: '192.168.1.240',
      port: 8085,
      path: endpoint,
      method: method,
      headers: headers
    }}, (res) => {{
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {{
        try {{
          resolve({{
            ok: res.statusCode >= 200 && res.statusCode < 300,
            status: res.statusCode,
            data: JSON.parse(data)
          }});
        }} catch (e) {{
          resolve({{
            ok: res.statusCode >= 200 && res.statusCode < 300,
            status: res.statusCode,
            data: data
          }});
        }}
      }});
    }});
    req.on('error', err => resolve({{ ok: false, status: 500, data: {{ message: err.message }} }}));
    if (body) {{
      req.write(typeof body === 'string' ? body : JSON.stringify(body));
    }}
    req.end();
  }});
}};

const rawItem = $input.first().json;
const params = rawItem.body ? rawItem.body : rawItem;
const tool = (params.tool || 'search_contacts').toLowerCase();
const action = (params.action || 'list').toLowerCase();

// 1. SEARCH CONTACTS
if (tool === 'search_contacts') {{
  let url = '/rest/people?limit=150&order=createdAt:desc';
  const res = await requestCrm(url);
  if (!res.ok) {{
    return [{{ json: {{ ok: false, tool, error: res.data?.message || 'Failed to search contacts' }} }}];
  }}

  const rawList = res.data?.data?.people || [];
  let items = rawList.map(p => {{
    const firstName = p.name?.firstName || '';
    const lastName = p.name?.lastName || '';
    const fullName = `${{firstName}} ${{lastName}}`.trim() || 'Contact';
    const email = p.emails?.primaryEmail || '';
    const phone = p.phones?.primaryPhoneNumber || '';
    const createdAt = p.createdAt || '';

    return {{
      id: p.id,
      name: fullName,
      company_id: p.companyId || null,
      phone: phone,
      email: email,
      role: p.contactRole || 'Customer',
      can_email: p.canEmail ? 'True' : 'False',
      lead_source: p.leadSource || '',
      market: p.market || '',
      created_at: createdAt,
      created_date: createdAt.slice(0, 10)
    }};
  }});

  if (params.query && typeof params.query === 'string') {{
    const qLower = params.query.trim().toLowerCase();
    if (!['all', 'contacts', 'users', 'list', 'show all'].includes(qLower)) {{
      items = items.filter(c => 
        c.name.toLowerCase().includes(qLower) ||
        c.email.toLowerCase().includes(qLower) ||
        c.phone.includes(qLower) ||
        c.market.toLowerCase().includes(qLower) ||
        c.lead_source.toLowerCase().includes(qLower)
      );
    }}
  }}

  const limit = params.limit ? parseInt(params.limit, 10) : 50;
  items = items.slice(0, limit);

  return [{{
    json: {{
      ok: true,
      tool,
      total_found: items.length,
      contacts: items
    }}
  }}];
}}

// 2. CREATE CONTACT
if (tool === 'create_contact') {{
  if (!params.name && !params.email && !params.phone) {{
    return [{{ json: {{ ok: false, tool, error: 'Name, email or phone is required.' }} }}];
  }}
  const nameParts = (params.name || 'New Lead').split(' ');
  const payload = {{
    name: {{
      firstName: nameParts[0] || 'New',
      lastName: nameParts.slice(1).join(' ') || 'Lead'
    }},
    leadSource: params.lead_source || 'AI Agent',
    market: params.market || '',
    contactRole: params.role || 'Customer',
    canEmail: true
  }};
  if (params.email) payload.emails = {{ primaryEmail: params.email.trim() }};
  if (params.phone) payload.phones = {{ primaryPhoneNumber: params.phone.trim() }};
  if (params.company_id) payload.companyId = params.company_id;

  const res = await requestCrm('/rest/people', 'POST', payload);
  if (!res.ok) return [{{ json: {{ ok: false, tool, error: res.data?.message || 'Create contact failed' }} }}];
  const newPerson = res.data?.data?.createPerson;
  return [{{ json: {{ ok: true, tool, id: newPerson?.id, contact: newPerson, message: 'Contact created successfully.' }} }}];
}}

// 3. UPDATE CONTACT
if (tool === 'update_contact') {{
  if (!params.id) return [{{ json: {{ ok: false, tool, error: 'Contact ID is required.' }} }}];
  const payload = {{}};
  if (params.name) {{
    const parts = params.name.split(' ');
    payload.name = {{ firstName: parts[0], lastName: parts.slice(1).join(' ') }};
  }}
  if (params.email) payload.emails = {{ primaryEmail: params.email.trim() }};
  if (params.phone) payload.phones = {{ primaryPhoneNumber: params.phone.trim() }};
  if (params.market) payload.market = params.market;
  if (params.lead_source) payload.leadSource = params.lead_source;
  if (params.role) payload.contactRole = params.role;

  const res = await requestCrm(`/rest/people/${{params.id}}`, 'PATCH', payload);
  if (!res.ok) return [{{ json: {{ ok: false, tool, error: res.data?.message || 'Update contact failed' }} }}];
  return [{{ json: {{ ok: true, tool, id: params.id, message: 'Contact updated successfully.' }} }}];
}}

// 4. DELETE CONTACT
if (tool === 'delete_contact') {{
  if (!params.id) return [{{ json: {{ ok: false, tool, error: 'Contact ID is required.' }} }}];
  const res = await requestCrm(`/rest/people/${{params.id}}`, 'DELETE');
  if (!res.ok) return [{{ json: {{ ok: false, tool, error: res.data?.message || 'Delete contact failed' }} }}];
  return [{{ json: {{ ok: true, tool, deleted_id: params.id, message: 'Contact deleted successfully.' }} }}];
}}

// 5. MANAGE COMPANIES
if (tool === 'manage_companies') {{
  if (action === 'create') {{
    if (!params.name) return [{{ json: {{ ok: false, tool, error: 'Company name is required.' }} }}];
    const payload = {{ name: params.name }};
    if (params.domain) {{
      const dom = params.domain.replace('https://', '').replace('http://', '');
      payload.domainName = {{ primaryLinkLabel: dom, primaryLinkUrl: dom }};
    }}
    const res = await requestCrm('/rest/companies', 'POST', payload);
    if (!res.ok) return [{{ json: {{ ok: false, tool, error: res.data?.message || 'Create company failed' }} }}];
    return [{{ json: {{ ok: true, tool, id: res.data?.data?.createCompany?.id, message: 'Company created successfully.' }} }}];
  }}
  const res = await requestCrm('/rest/companies?limit=50');
  if (!res.ok) return [{{ json: {{ ok: false, tool, error: res.data?.message || 'List companies failed' }} }}];
  const comps = (res.data?.data?.companies || []).map(c => ({{
    id: c.id,
    name: c.name,
    domain: c.domainName?.primaryLinkUrl || null
  }}));
  return [{{ json: {{ ok: true, tool, total: comps.length, companies: comps }} }}];
}}

// 6. MANAGE TASKS
if (tool === 'manage_tasks') {{
  if (action === 'create') {{
    if (!params.title) return [{{ json: {{ ok: false, tool, error: 'Task title is required.' }} }}];
    const payload = {{
      title: params.title,
      bodyV2: {{ markdown: params.description || '' }},
      status: 'TODO'
    }};
    if (params.status && params.status.toUpperCase() === 'DONE') payload.status = 'DONE';
    if (params.due_date) payload.dueAt = `${{params.due_date.slice(0, 10)}}T12:00:00.000Z`;

    const res = await requestCrm('/rest/tasks', 'POST', payload);
    if (!res.ok) return [{{ json: {{ ok: false, tool, error: res.data?.message || 'Create task failed' }} }}];
    const taskId = res.data?.data?.createTask?.id;
    if (taskId && params.contact_id) {{
      await requestCrm('/rest/taskTargets', 'POST', {{ taskId, targetPersonId: params.contact_id }});
    }}
    return [{{ json: {{ ok: true, tool, id: taskId, title: params.title, message: 'Task created successfully.' }} }}];
  }}
  if (action === 'delete') {{
    if (!params.id) return [{{ json: {{ ok: false, tool, error: 'Task ID is required.' }} }}];
    const res = await requestCrm(`/rest/tasks/${{params.id}}`, 'DELETE');
    if (!res.ok) return [{{ json: {{ ok: false, tool, error: res.data?.message || 'Delete task failed' }} }}];
    return [{{ json: {{ ok: true, tool, deleted_id: params.id, message: 'Task deleted successfully.' }} }}];
  }}
  const res = await requestCrm('/rest/tasks?limit=50');
  if (!res.ok) return [{{ json: {{ ok: false, tool, error: res.data?.message || 'List tasks failed' }} }}];
  const tasks = (res.data?.data?.tasks || []).map(t => ({{
    id: t.id,
    title: t.title,
    status: t.status,
    description: t.bodyV2?.markdown || null,
    due_date: t.dueAt || null
  }}));
  return [{{ json: {{ ok: true, tool, total: tasks.length, tasks }} }}];
}}

// 7. MANAGE NOTES
if (tool === 'manage_notes') {{
  if (action === 'create') {{
    if (!params.title) return [{{ json: {{ ok: false, tool, error: 'Note title is required.' }} }}];
    const payload = {{
      title: params.title,
      bodyV2: {{ markdown: params.body || '' }}
    }};
    const res = await requestCrm('/rest/notes', 'POST', payload);
    if (!res.ok) return [{{ json: {{ ok: false, tool, error: res.data?.message || 'Create note failed' }} }}];
    const noteId = res.data?.data?.createNote?.id;
    if (noteId && params.contact_id) {{
      await requestCrm('/rest/noteTargets', 'POST', {{ noteId, targetPersonId: params.contact_id }});
    }}
    return [{{ json: {{ ok: true, tool, id: noteId, title: params.title, message: 'Note created successfully.' }} }}];
  }}
  const res = await requestCrm('/rest/notes?limit=50');
  if (!res.ok) return [{{ json: {{ ok: false, tool, error: res.data?.message || 'List notes failed' }} }}];
  const notes = (res.data?.data?.notes || []).map(n => ({{
    id: n.id,
    title: n.title,
    body: n.bodyV2?.markdown || null,
    created_at: n.createdAt
  }}));
  return [{{ json: {{ ok: true, tool, total: notes.length, notes }} }}];
}}

// 8. MANAGE OPPORTUNITIES
if (tool === 'manage_opportunities') {{
  const res = await requestCrm('/rest/opportunities?limit=50');
  if (!res.ok) return [{{ json: {{ ok: false, tool, error: res.data?.message || 'List opportunities failed' }} }}];
  const opps = (res.data?.data?.opportunities || []).map(o => ({{
    id: o.id,
    name: o.name,
    contact_id: o.pointOfContactId,
    company_id: o.companyId,
    amount: o.amount?.amountMicros ? (o.amount.amountMicros / 1000000) : null,
    stage: o.stage,
    close_date: o.closeDate
  }}));
  return [{{ json: {{ ok: true, tool, total: opps.length, opportunities: opps }} }}];
}}

// 9. MANAGE CUSTOM FIELDS
if (tool === 'manage_custom_fields') {{
  return [{{ json: {{
    ok: true,
    tool,
    custom_fields: [
      {{ name: 'Lead Source', code: 'leadSource', entity_type: 'person', type: 'text' }},
      {{ name: 'Market', code: 'market', entity_type: 'person', type: 'text' }},
      {{ name: 'Can Email', code: 'canEmail', entity_type: 'person', type: 'boolean' }},
      {{ name: 'Role', code: 'contactRole', entity_type: 'person', type: 'text' }}
    ]
  }} }}];
}}

return [{{ json: {{ ok: false, error: 'Unsupported CRM tool: ' + tool }} }}];
'''

def update_workflow(wf_id, new_js_code):
    db_path = '/tank/n8n/database.sqlite'
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    row = cur.execute('SELECT name, nodes, connections, versionId, activeVersionId FROM workflow_entity WHERE id = ?', (wf_id,)).fetchone()
    if not row:
        print(f"Workflow {wf_id} not found in database!")
        con.close()
        return
    name, nodes_json, connections_json, version_id, active_version_id = row
    nodes = json.loads(nodes_json)
    updated = False
    for n in nodes:
        if n.get('type') == 'n8n-nodes-base.code':
            n['parameters']['jsCode'] = new_js_code
            updated = True
            print(f"Updated node '{n.get('name')}' in workflow '{name}' ({wf_id})")
    
    if updated:
        # 1. Update workflow_entity
        cur.execute('UPDATE workflow_entity SET nodes = ?, updatedAt = datetime("now") WHERE id = ?', (json.dumps(nodes), wf_id))
        
        # 2. Update workflow_history for activeVersionId
        target_version = active_version_id or version_id
        if target_version:
            cur.execute('''
            INSERT OR REPLACE INTO workflow_history (versionId, workflowId, authors, nodes, connections, name, autosaved, nodeGroups)
            VALUES (?, ?, 'system', ?, ?, ?, 0, '[]')
            ''', (target_version, wf_id, json.dumps(nodes), connections_json, name))

            # 3. Update workflow_published_version
            cur.execute('''
            INSERT OR REPLACE INTO workflow_published_version (workflowId, publishedVersionId)
            VALUES (?, ?)
            ''', (wf_id, target_version))

        con.commit()
        print(f"Committed changes and synced published version for '{name}' ({wf_id}) to database.sqlite")
    con.close()

def main():
    print("Updating n8n workflows in SQLite database...")
    update_workflow('websiteContactWf01', WEBSITE_CONTACT_CODE)
    update_workflow('wGB3XfRGWgbbvOGP', OPEN_HOUSE_CODE)
    update_workflow('crmRelaticleAssistant', GATEWAY_CODE)

    # Also update backup files on disk
    print("\nUpdating JSON files on disk...")
    # 1. website_contact_workflow.json
    wc_file = '/tank/n8n/website_contact_workflow.json'
    if os.path.exists(wc_file):
        with open(wc_file, 'r') as f:
            data = json.load(f)
        target = data[0] if isinstance(data, list) else data
        for n in target.get('nodes', []):
            if n.get('type') == 'n8n-nodes-base.code':
                n['parameters']['jsCode'] = WEBSITE_CONTACT_CODE
        with open(wc_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Updated {wc_file}")

    # 2. open_house_workflow.json
    oh_file = '/tank/n8n/open_house_workflow.json'
    if os.path.exists(oh_file):
        with open(oh_file, 'r') as f:
            data = json.load(f)
        target = data[0] if isinstance(data, list) else data
        for n in target.get('nodes', []):
            if n.get('type') == 'n8n-nodes-base.code':
                n['parameters']['jsCode'] = OPEN_HOUSE_CODE
        with open(oh_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Updated {oh_file}")

    print("\nDone updating workflows!")

if __name__ == '__main__':
    main()
