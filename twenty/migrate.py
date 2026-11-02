#!/usr/bin/env python3
import os
import subprocess
import json
import urllib.request
import urllib.error
import sys
import time

BASE_URL = "http://localhost:8085"
API_KEY = os.environ.get("TWENTY_API_KEY", "")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def api_request(path, method="GET", payload=None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    retries = 0
    while retries < 15:
        req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
        try:
            with urllib.request.urlopen(req) as response:
                time.sleep(0.08)  # prevent bursting
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            if e.code == 429:
                retries += 1
                wait_sec = 2.0
                try:
                    err_json = json.loads(err_msg)
                    wait_sec = float(err_json.get("retryAfterSeconds", 2.0)) + 0.5
                except Exception:
                    pass
                print(f"Rate limited (429) on {method} {path}, waiting {wait_sec}s (retry {retries})...")
                time.sleep(wait_sec)
                continue
            print(f"HTTPError {e.code} on {method} {path}: {err_msg}")
            return None
        except Exception as e:
            print(f"Error on {method} {path}: {e}")
            return None
    print(f"Max retries reached on {method} {path}")
    return None

def query_pg(sql):
    cmd = ["sudo", "docker", "exec", "-i", "postgres", "psql", "-U", "postgres", "-d", "relaticle", "-t", "-A", "-c", sql]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out = res.stdout.strip()
    if not out:
        return []
    try:
        return json.loads(out)
    except Exception as e:
        print(f"Failed to parse JSON from PG: {e}\nOutput was: {out[:200]}")
        return []

def main():
    print("Fetching Relaticle metadata and records from postgres...")

    # Options mapping
    options_raw = query_pg("SELECT json_agg(o) FROM (SELECT id, name, custom_field_id FROM custom_field_options) o;")
    options_by_id = {o["id"]: o["name"] for o in options_raw}

    # Custom field values mapping: (entity_id, code) -> value
    cf_values_raw = query_pg("""
        SELECT json_agg(v) FROM (
            SELECT cfv.entity_id, cf.code, cfv.text_value, cfv.json_value, cfv.boolean_value, cfv.integer_value, cfv.date_value
            FROM custom_field_values cfv
            JOIN custom_fields cf ON cf.id = cfv.custom_field_id
        ) v;
    """)

    cf_map = {}
    for v in cf_values_raw:
        eid = v["entity_id"]
        code = v["code"]
        val = None
        if v.get("json_value") is not None:
            val = v["json_value"]
        elif v.get("text_value") is not None:
            val = v["text_value"]
        elif v.get("boolean_value") is not None:
            val = v["boolean_value"]
        elif v.get("integer_value") is not None:
            val = v["integer_value"]
        elif v.get("date_value") is not None:
            val = v["date_value"]
        cf_map[(eid, code)] = val

    # 1. COMPANIES
    companies = query_pg("SELECT json_agg(c) FROM (SELECT id, name FROM companies ORDER BY created_at ASC) c;")
    print(f"Migrating {len(companies)} companies...")
    company_id_map = {}
    for c in companies:
        cid = c["id"]
        name = c["name"]
        domains = cf_map.get((cid, "domains"))
        primary_domain = ""
        if isinstance(domains, list) and domains:
            primary_domain = str(domains[0]).strip()
        elif isinstance(domains, str) and domains:
            primary_domain = domains.strip()

        payload = {"name": name}
        if primary_domain:
            clean_dom = primary_domain.replace("https://", "").replace("http://", "").strip()
            payload["domainName"] = {
                "primaryLinkLabel": clean_dom,
                "primaryLinkUrl": clean_dom
            }

        res = api_request("/rest/companies", method="POST", payload=payload)
        if res and "data" in res and "createCompany" in res["data"]:
            new_id = res["data"]["createCompany"]["id"]
            company_id_map[cid] = new_id
            print(f"  + Company '{name}' -> {new_id}")
        else:
            print(f"  ! Failed company '{name}'")

    # 2. PEOPLE
    people = query_pg("SELECT json_agg(p) FROM (SELECT id, name, company_id FROM people ORDER BY created_at ASC) p;")
    print(f"\nMigrating {len(people)} people / contacts...")
    person_id_map = {}
    for p in people:
        pid = p["id"]
        raw_name = (p.get("name") or "").strip()
        parts = raw_name.split() if raw_name else []
        first_name = parts[0] if parts else "Contact"
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        # Emails
        emails_cf = cf_map.get((pid, "emails")) or []
        email_list = []
        if isinstance(emails_cf, list):
            for item in emails_cf:
                if isinstance(item, dict):
                    e = item.get("label") or item.get("id") or ""
                else:
                    e = str(item)
                if e and "@" in e and e not in email_list:
                    email_list.append(e.strip().lower())
        elif isinstance(emails_cf, str) and "@" in emails_cf:
            email_list.append(emails_cf.strip().lower())

        # Phones
        phones_cf = cf_map.get((pid, "phone_number")) or []
        phone_list = []
        if isinstance(phones_cf, list):
            for item in phones_cf:
                if isinstance(item, dict):
                    num = item.get("label") or item.get("id") or ""
                else:
                    num = str(item)
                digits = "".join(ch for ch in num if ch.isdigit() or ch == "+")
                if digits and digits not in phone_list:
                    phone_list.append(digits)
        elif isinstance(phones_cf, str) and phones_cf:
            digits = "".join(ch for ch in phones_cf if ch.isdigit() or ch == "+")
            if digits:
                phone_list.append(digits)

        # Other fields
        lead_source = str(cf_map.get((pid, "lead_source")) or "").strip()
        market = str(cf_map.get((pid, "market")) or "").strip()

        can_email_val = cf_map.get((pid, "can_email_1"))
        can_email = True
        if can_email_val:
            opt_name = options_by_id.get(str(can_email_val), "")
            if opt_name.lower() in ("false", "0", "no"):
                can_email = False

        role_val = cf_map.get((pid, "role"))
        role_name = ""
        if isinstance(role_val, list) and role_val:
            role_name = options_by_id.get(str(role_val[0]), "")
        elif isinstance(role_val, str) and role_val:
            role_name = options_by_id.get(role_val, role_val)

        payload = {
            "name": {
                "firstName": first_name,
                "lastName": last_name
            },
            "emails": {
                "primaryEmail": email_list[0] if email_list else "",
                "additionalEmails": email_list[1:] if len(email_list) > 1 else []
            },
            "phones": {
                "primaryPhoneNumber": phone_list[0] if phone_list else "",
                "additionalPhones": [{"number": ph} for ph in phone_list[1:]] if len(phone_list) > 1 else []
            },
            "canEmail": can_email
        }
        if lead_source:
            payload["leadSource"] = lead_source
        if market:
            payload["market"] = market
        if role_name:
            payload["contactRole"] = role_name
        if p.get("company_id") and p["company_id"] in company_id_map:
            payload["companyId"] = company_id_map[p["company_id"]]

        res = api_request("/rest/people", method="POST", payload=payload)
        if res and "data" in res and "createPerson" in res["data"]:
            new_id = res["data"]["createPerson"]["id"]
            person_id_map[pid] = new_id
            print(f"  + Person '{raw_name}' ({email_list[0] if email_list else 'no email'}) -> {new_id}")
        else:
            print(f"  ! Failed person '{raw_name}': {res}")

    # 3. OPPORTUNITIES
    opps = query_pg("SELECT json_agg(o) FROM (SELECT id, name, contact_id FROM opportunities ORDER BY created_at ASC) o;")
    print(f"\nMigrating {len(opps)} opportunities / deals...")
    opp_id_map = {}
    for o in opps:
        oid = o["id"]
        name = o["name"]
        contact_id = o.get("contact_id")
        poc_id = person_id_map.get(contact_id)

        # Stage mapping
        stage_opt_id = cf_map.get((oid, "stage"))
        stage_name = options_by_id.get(str(stage_opt_id), "")
        stage_mapping = {
            "Prospecting": "NEW",
            "Qualification": "SCREENING",
            "Needs Analysis": "MEETING",
            "Value Proposition": "MEETING",
            "Id. Decision Makers": "MEETING",
            "Perception Analysis": "MEETING",
            "Proposal/Price Quote": "PROPOSAL",
            "Negotiation/Review": "PROPOSAL",
            "Closed Won": "CUSTOMER",
            "Closed Lost": "NEW"
        }
        stage = stage_mapping.get(stage_name, "NEW")

        amount_val = cf_map.get((oid, "amount"))
        close_date_val = cf_map.get((oid, "close_date"))

        payload = {
            "name": name,
            "stage": stage
        }
        if poc_id:
            payload["pointOfContactId"] = poc_id
        if amount_val:
            try:
                amt = float(amount_val)
                payload["amount"] = {
                    "amountMicros": int(amt * 1000000),
                    "currencyCode": "USD"
                }
            except Exception:
                pass
        if close_date_val:
            payload["closeDate"] = f"{str(close_date_val).strip()[:10]}T00:00:00.000Z"

        res = api_request("/rest/opportunities", method="POST", payload=payload)
        if res and "data" in res and "createOpportunity" in res["data"]:
            new_id = res["data"]["createOpportunity"]["id"]
            opp_id_map[oid] = new_id
            print(f"  + Opportunity '{name}' -> {new_id}")
        else:
            print(f"  ! Failed opportunity '{name}': {res}")

    # 4. TASKS
    tasks = query_pg("SELECT json_agg(t) FROM (SELECT id, title FROM tasks ORDER BY created_at ASC) t;")
    taskables = query_pg("SELECT json_agg(ta) FROM (SELECT task_id, taskable_type, taskable_id FROM taskables) ta;")
    taskables_map = {}
    for ta in taskables:
        taskables_map.setdefault(ta["task_id"], []).append(ta)

    print(f"\nMigrating {len(tasks)} tasks...")
    for t in tasks:
        tid = t["id"]
        title = t["title"]
        desc = cf_map.get((tid, "description")) or ""
        status_opt_id = cf_map.get((tid, "status"))
        status = "TODO"
        if status_opt_id == "01m35s6hw2ppnebfbpet18n12z":  # Done
            status = "DONE"
        elif status_opt_id == "01m35s6hw094d9sd38ew4kwzsm":  # In progress
            status = "IN_PROGRESS"

        due_date_val = cf_map.get((tid, "due_date"))

        payload = {
            "title": title,
            "bodyV2": {"markdown": str(desc)},
            "status": status
        }
        if due_date_val:
            try:
                payload["dueAt"] = f"{str(due_date_val).strip()[:10]}T12:00:00.000Z"
            except Exception:
                pass

        res = api_request("/rest/tasks", method="POST", payload=payload)
        if res and "data" in res and "createTask" in res["data"]:
            new_task_id = res["data"]["createTask"]["id"]
            print(f"  + Task '{title}' -> {new_task_id}")

            # Link targets
            links = taskables_map.get(tid, [])
            for link in links:
                ttype = link["taskable_type"]
                target_id = link["taskable_id"]
                target_payload = {"taskId": new_task_id}
                if ttype in ("people", "App\\Models\\Person") and target_id in person_id_map:
                    target_payload["targetPersonId"] = person_id_map[target_id]
                elif ttype in ("company", "companies", "App\\Models\\Company") and target_id in company_id_map:
                    target_payload["targetCompanyId"] = company_id_map[target_id]
                else:
                    continue

                api_request("/rest/taskTargets", method="POST", payload=target_payload)
        else:
            print(f"  ! Failed task '{title}': {res}")

    # 5. NOTES
    notes = query_pg("SELECT json_agg(n) FROM (SELECT id, title FROM notes ORDER BY created_at ASC) n;")
    noteables = query_pg("SELECT json_agg(na) FROM (SELECT note_id, noteable_type, noteable_id FROM noteables) na;")
    noteables_map = {}
    for na in noteables:
        noteables_map.setdefault(na["note_id"], []).append(na)

    print(f"\nMigrating {len(notes)} notes...")
    for n in notes:
        nid = n["id"]
        title = n["title"]
        body = cf_map.get((nid, "body")) or ""

        payload = {
            "title": title,
            "bodyV2": {"markdown": str(body)}
        }
        res = api_request("/rest/notes", method="POST", payload=payload)
        if res and "data" in res and "createNote" in res["data"]:
            new_note_id = res["data"]["createNote"]["id"]
            print(f"  + Note '{title}' -> {new_note_id}")

            # Link targets
            links = noteables_map.get(nid, [])
            for link in links:
                ntype = link["noteable_type"]
                target_id = link["noteable_id"]
                target_payload = {"noteId": new_note_id}
                if ntype in ("people", "App\\Models\\Person") and target_id in person_id_map:
                    target_payload["targetPersonId"] = person_id_map[target_id]
                elif ntype in ("company", "companies", "App\\Models\\Company") and target_id in company_id_map:
                    target_payload["targetCompanyId"] = company_id_map[target_id]
                else:
                    continue

                api_request("/rest/noteTargets", method="POST", payload=target_payload)
        else:
            print(f"  ! Failed note '{title}': {res}")

    print("\n--- MIGRATION SUMMARY ---")
    print(f"Companies migrated: {len(company_id_map)} / {len(companies)}")
    print(f"People migrated:    {len(person_id_map)} / {len(people)}")
    print(f"Opportunities:      {len(opp_id_map)} / {len(opps)}")
    print("Done!")

if __name__ == "__main__":
    main()
