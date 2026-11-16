#!/usr/bin/env python3
"""
Update all 13 Buyer Post-Close Brevo Email Templates (IDs 5–17)
to match Lokesh Chanana's Master Brand & Design Guidelines v2.0:
- Warm Ivory (#FAF8F5), Crisp White (#FFFFFF), Architectural Charcoal (#1F2933),
  Charcoal Dark (#151C23), Metallic Silver (#C0C0C0 / #E0E0E0)
- Playfair Display editorial serif headings + Plus Jakarta Sans body & tracked kickers
- Signature 4px solid #1F2933 Charcoal left-accent cards
- Full Light Mode & Dark Mode (@media (prefers-color-scheme: dark)) support
- Classic Maintenance Guide Dark Anchor Agent Banner + Ivory Compliance Footer
- Preserves 100% of the vetted email content and subject lines
"""

import json
import os
import re
import urllib.request

KICKER_BY_TID = {
    5: "DAY 1  •  WELCOME HOME",
    6: "DAY 5  •  HOME MAINTENANCE GUIDE",
    7: "DAY 8  •  HOME SAFETY & SECURITY",
    8: "DAY 14  •  ESTATE & LEGACY PLANNING",
    9: "DAY 21  •  ENERGY EFFICIENCY",
    10: "DAY 45  •  WA PERMITS & CONSTRUCTION",
    11: "DAY 55  •  HIGH-ROI IMPROVEMENTS",
    12: "DAY 90  •  3-MONTH CHECK-IN",
    13: "DAY 280  •  TAX SEASON TIPS",
    14: "DAY 300  •  ANNUAL INSURANCE REVIEW",
    15: "DAY 330  •  ANNUAL HOME VALUE REVIEW",
    16: "DAY 360  •  1-YEAR HOUSIVERSARY",
    17: "NEW CONSTRUCTION  •  11-MONTH WARRANTY",
}


def transform_body_fragment(html_frag: str) -> str:
    # Normalize text colors to Brand Guidelines palette
    frag = html_frag
    frag = frag.replace("color: #334155", "color: #2D3A47")
    frag = frag.replace("color: #475569", "color: #2D3A47")
    frag = frag.replace("color: #64748b", "color: #6B7280")
    frag = frag.replace("color: #0f172a", "color: #1F2933")
    frag = frag.replace("color: #0284c7", "color: #1F2933")

    # Replace old rounded #f1f5f9 cards with signature 4px Charcoal left-accent cards
    frag = frag.replace(
        'class="card-box" style="background-color: #f1f5f9; border-radius: 8px; padding: 18px 20px; margin-bottom: 16px;"',
        'class="card-box editorial-card" style="background-color: #FAF8F5; border: 1px solid #E0E0E0; border-left: 4px solid #1F2933; border-radius: 2px; padding: 18px 20px; margin-bottom: 16px;"',
    )
    # Replace cyan callout boxes (#f0f9ff / #ecfeff) with signature 4px Charcoal left-accent cards
    frag = re.sub(
        r'style="background-color:\s*#(?:f0f9ff|ecfeff);[^"]*"',
        'class="editorial-card" style="background-color: #FAF8F5; border: 1px solid #E0E0E0; border-left: 4px solid #1F2933; border-radius: 2px; padding: 18px 20px; margin-top: 20px; margin-bottom: 16px;"',
        frag,
    )
    # Replace cyan inline badge highlights (#e0f2fe) with Ivory Dark (#E5E1DB)
    frag = frag.replace("background-color: #e0f2fe;", "background-color: #E5E1DB; color: #1F2933;")
    frag = frag.replace("border-top: 1px dashed #cbd5e1;", "border-top: 1px solid #E0E0E0;")

    # Apply Playfair Display serif to card headings (<h3> and <h4>)
    frag = re.sub(
        r"<h3([^>]*)style=\"([^\"]*)\"",
        lambda m: f'<h3{m.group(1)}class="card-heading" style="{m.group(2)} font-family: \'Playfair Display\', \'Palatino Linotype\', Georgia, serif;"',
        frag,
    )
    frag = re.sub(
        r"<h4([^>]*)style=\"([^\"]*)\"",
        lambda m: f'<h4{m.group(1)}class="card-heading" style="{m.group(2)} font-family: \'Playfair Display\', \'Palatino Linotype\', Georgia, serif;"',
        frag,
    )
    return frag


def build_branded_email(tid: int, title_text: str, body_html: str, support_html: str) -> str:
    kicker = KICKER_BY_TID.get(tid, "CLIENT CARE  •  HOMEOWNER SERIES")
    clean_body = transform_body_fragment(body_html)
    clean_support = transform_body_fragment(support_html)

    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="x-apple-disable-message-reformatting">
  <meta name="format-detection" content="telephone=no,address=no,email=no,date=no,url=no">
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <title>{title_text} — Lokesh Chanana (Loki)</title>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,700;1,400&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style type="text/css">
    :root {{
      color-scheme: light dark;
      supported-color-schemes: light dark;
    }}
    body, table, td, p, a, li {{
      -webkit-text-size-adjust: 100%;
      -ms-text-size-adjust: 100%;
    }}
    table, td {{
      mso-table-lspace: 0pt;
      mso-table-rspace: 0pt;
    }}
    img {{
      -ms-interpolation-mode: bicubic;
      border: 0;
      height: auto;
      line-height: 100%;
      outline: none;
      text-decoration: none;
    }}
    body {{
      margin: 0 !important;
      padding: 0 !important;
      width: 100% !important;
      min-width: 100% !important;
      background-color: #FAF8F5;
    }}
    @media (prefers-color-scheme: dark) {{
      body, .email-wrapper {{
        background-color: #151C23 !important;
        color: #C0C0C0 !important;
      }}
      .email-container {{
        background-color: #1F2933 !important;
        border-color: #2D3A47 !important;
      }}
      .cobrand-bar, .compliance-footer {{
        background-color: #151C23 !important;
        border-color: #2D3A47 !important;
      }}
      .kicker-pill {{
        background-color: #151C23 !important;
        border-color: #2D3A47 !important;
        color: #C0C0C0 !important;
      }}
      .header-title, .card-heading, .greeting-text {{
        color: #FAF8F5 !important;
      }}
      .body-text, .list-item {{
        color: #C0C0C0 !important;
      }}
      .editorial-card, .support-card {{
        background-color: #151C23 !important;
        border-color: #2D3A47 !important;
        border-left: 4px solid #C0C0C0 !important;
      }}
      .dark-invert-logo {{
        filter: invert(1) brightness(1.8) !important;
      }}
      .muted-copy {{
        color: #A0A0A0 !important;
      }}
    }}
    @media only screen and (max-width: 600px) {{
      .email-wrapper {{
        padding: 0 !important;
      }}
      .email-container {{
        width: 100% !important;
        max-width: 100% !important;
        border-radius: 0 !important;
        border-left: none !important;
        border-right: none !important;
      }}
      .mobile-padding {{
        padding: 22px 18px !important;
      }}
      .mobile-header-padding {{
        padding: 18px 18px !important;
      }}
      .header-title {{
        font-size: 21px !important;
        line-height: 1.22 !important;
      }}
      .body-text {{
        font-size: 15px !important;
        line-height: 1.55 !important;
      }}
      .list-item {{
        font-size: 14px !important;
        line-height: 1.5 !important;
        margin-bottom: 8px !important;
      }}
      .card-box, .editorial-card {{
        padding: 16px 14px !important;
        margin-bottom: 14px !important;
      }}
      .agent-stack-col {{
        display: block !important;
        width: 100% !important;
        text-align: left !important;
        padding-bottom: 12px !important;
      }}
    }}
  </style>
</head>
<body style="margin: 0; padding: 0; background-color: #FAF8F5; font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #2D3A47; line-height: 1.6;">
  <table role="presentation" class="email-wrapper" width="100%" cellspacing="0" cellpadding="0" style="background-color: #FAF8F5; margin: 0; padding: 24px 0;">
    <tr>
      <td align="center" style="padding: 0;">
        <table role="presentation" class="email-container" width="100%" cellspacing="0" cellpadding="0" style="max-width: 620px; background-color: #FFFFFF; border: 1px solid #E0E0E0; overflow: hidden;">

          <!-- 1. Top Architectural Crown Bar (6px Solid Charcoal) -->
          <tr>
            <td style="background-color: #1F2933; height: 6px; font-size: 0; line-height: 0;">&nbsp;</td>
          </tr>

          <!-- 2. Co-Branded Ivory Header Bar (LC Monogram + Real Broker) -->
          <tr>
            <td class="cobrand-bar mobile-header-padding" style="background-color: #FAF8F5; padding: 14px 28px; border-bottom: 1px solid #E0E0E0;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td valign="middle" align="left">
                    <table role="presentation" cellspacing="0" cellpadding="0">
                      <tr>
                        <td valign="middle" style="padding-right: 10px;">
                          <img src="https://lokeshchanana.com/lc-logo.png" alt="LC" width="40" style="width: 40px; height: auto; display: block;" />
                        </td>
                        <td valign="middle">
                          <div style="font-family: 'Playfair Display', Georgia, serif; font-size: 13px; font-weight: 700; color: #1F2933; letter-spacing: 0.5px; line-height: 1.2;">LOKESH CHANANA</div>
                          <div class="muted-copy" style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: 9px; font-weight: 600; color: #6B7280; letter-spacing: 1.2px; text-transform: uppercase; margin-top: 2px;">REALTOR<sup>&reg;</sup> &bull; GREATER SEATTLE</div>
                        </td>
                      </tr>
                    </table>
                  </td>
                  <td valign="middle" align="right">
                    <img class="dark-invert-logo" src="https://lokeshchanana.com/real-logo.png" alt="Real Broker LLC" height="24" style="height: 24px; width: auto; display: inline-block; mix-blend-mode: multiply;" />
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- 3. Editorial Kicker Pill & Playfair Display Headline -->
          <tr>
            <td class="mobile-padding" style="padding: 26px 28px 18px 28px; border-bottom: 1px solid #E0E0E0;">
              <span class="kicker-pill" style="display: inline-block; background-color: #FAF8F5; border: 1px solid #E0E0E0; padding: 4px 10px; font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: 10px; font-weight: 700; letter-spacing: 1.6px; text-transform: uppercase; color: #1F2933; margin-bottom: 12px;">
                {kicker}
              </span>
              <h1 class="header-title" style="font-family: 'Playfair Display', 'Palatino Linotype', Georgia, serif; color: #1F2933; font-size: 24px; margin: 0; font-weight: 700; line-height: 1.24;">
                {title_text}
              </h1>
            </td>
          </tr>

          <!-- 4. Main Body Content -->
          <tr>
            <td class="mobile-padding" style="padding: 26px 28px 22px 28px;">
              <p class="greeting-text" style="font-size: 16px; font-weight: 600; margin: 0 0 16px 0; color: #1F2933;">Hi {{{{ contact.FIRSTNAME | default: "there" }}}},</p>

              <!-- Body Content -->
              {clean_body}

              <!-- Support & Referral Section -->
              <div class="support-card editorial-card" style="background-color: #FAF8F5; border: 1px solid #E0E0E0; border-left: 4px solid #1F2933; border-radius: 2px; padding: 18px 20px; margin-top: 22px; margin-bottom: 8px;">
                {clean_support}
              </div>
            </td>
          </tr>

          <!-- 5. Signature Dark Charcoal Agent Banner (Classic Maintenance Guide Style) -->
          <tr>
            <td class="mobile-padding" style="background-color: #1F2933; border-top: 3px solid #C0C0C0; padding: 22px 28px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td class="agent-stack-col" width="80" valign="middle" style="padding-right: 16px; width: 80px;">
                    <img src="https://lokeshchanana.com/loki-profile.jpg" alt="Lokesh Chanana (Loki)" width="72" height="72" style="width: 72px; height: 72px; object-fit: cover; border: 2px solid #C0C0C0; display: block; border-radius: 2px;" />
                  </td>
                  <td class="agent-stack-col" valign="middle">
                    <div style="font-family: 'Playfair Display', Georgia, serif; font-size: 18px; font-weight: 700; color: #FAF8F5; line-height: 1.2;">Lokesh Chanana (Loki)</div>
                    <div style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: 10px; font-weight: 600; color: #C0C0C0; letter-spacing: 1.1px; text-transform: uppercase; margin: 4px 0 8px 0;">REALTOR<sup>&reg;</sup> &bull; REAL BROKER LLC &bull; WA LIC #26006634</div>
                    <div style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: 12.5px; color: #FAF8F5; line-height: 1.5;">
                      <a href="tel:8018601052" style="color: #FAF8F5; text-decoration: none; font-weight: 600;">(801) 860-1052</a> &bull;
                      <a href="mailto:lokesh@lokeshchanana.com" style="color: #FAF8F5; text-decoration: none;">lokesh@lokeshchanana.com</a>
                    </div>
                    <div style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: 12px; margin-top: 4px;">
                      <a href="https://lokeshchanana.com" target="_blank" style="color: #C0C0C0; text-decoration: underline;">lokeshchanana.com</a> &bull;
                      <a href="https://lokeshchanana.com/loki.vcf" target="_blank" style="color: #C0C0C0; text-decoration: underline;">Save Contact Card (vCard)</a>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- 6. Clean Ivory Legal & Compliance Footer -->
          <tr>
            <td class="compliance-footer mobile-padding" style="background-color: #FAF8F5; padding: 18px 28px; text-align: center; border-top: 1px solid #E0E0E0; color: #6B7280; font-size: 11px;">
              <p class="muted-copy" style="margin: 0 0 6px 0; font-weight: 600; color: #2D3A47;">Real Broker LLC &bull; Greater Seattle, King, Pierce &amp; Snohomish Counties</p>
              <p class="muted-copy" style="margin: 0 0 8px 0; font-size: 10px; line-height: 1.4;">Equal Housing Opportunity. Information deemed reliable but not guaranteed. All real estate advertising is subject to the Federal Fair Housing Act.</p>
              <p class="muted-copy" style="margin: 0; font-size: 10px;">If you prefer not to receive homeowner updates, you can <a href="{{{{ unsubscribe }}}}" style="color: #2D3A47; text-decoration: underline;">unsubscribe here</a>.</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def main():
    env = {}
    with open("/tank/agents/.env") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v.strip().strip('"').strip("'")

    headers = {
        "api-key": env["BREVO_API_KEY"],
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }

    os.makedirs("/tmp/brevo_post_close_v2", exist_ok=True)

    for tid in range(5, 18):
        tpl = json.load(open(f"/tmp/brevo_post_close/tpl_{tid}.json"))
        old_html = tpl["htmlContent"]
        h1_m = re.search(r"<h1[^>]*>(.*?)</h1>", old_html, re.S)
        body_m = re.search(r"<!-- Body Content -->(.*?)<!-- Support & Referral Section -->", old_html, re.S)
        sup_m = re.search(r"<!-- Support & Referral Section -->(.*?)<!-- Custom Responsive Signature Block -->", old_html, re.S)

        if not (h1_m and body_m and sup_m):
            raise RuntimeError(f"Missing markers in template {tid}")

        title_text = h1_m.group(1).strip()
        body_inner = body_m.group(1).strip()
        sup_inner = sup_m.group(1).strip()
        # Strip outer support wrapper div so our branded .support-card wraps it cleanly
        sup_inner = re.sub(r'^\s*<div style="background-color:\s*#f8fafc;[^"]*">\s*', "", sup_inner)
        sup_inner = re.sub(r"\s*</div>\s*$", "", sup_inner)

        new_html = build_branded_email(tid, title_text, body_inner, sup_inner)
        with open(f"/tmp/brevo_post_close_v2/tpl_{tid}.html", "w") as f:
            f.write(new_html)

        payload = {
            "templateName": tpl["name"],
            "subject": tpl["subject"],
            "htmlContent": new_html,
            "isActive": True,
        }
        req = urllib.request.Request(
            f"https://api.brevo.com/v3/smtp/templates/{tid}",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="PUT",
        )
        resp = urllib.request.urlopen(req, timeout=20)
        print(f"Updated TPL {tid:2d} ({tpl['name']}) -> HTTP {resp.status}")


if __name__ == "__main__":
    main()
