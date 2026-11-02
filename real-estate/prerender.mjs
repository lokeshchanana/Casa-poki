import fs from 'node:fs';
import path from 'node:path';
import { SEO_ROUTES, buildRouteJsonLd } from './src/data/seoRoutes.js';
import { CITY_PAGES_DATA } from './src/data/cityPagesData.js';

const DIST_DIR = path.resolve('dist');
const BASE_HTML_PATH = path.join(DIST_DIR, 'index.html');

const ROUTE_STATIC_CONTENT = {
  '/': {
    h1: 'Lokesh Chanana (Loki) — Dedicated, Personalized Real Estate Service in Greater Seattle',
    lead:
      'Lokesh "Loki" Chanana is a licensed Washington State Real Estate Broker (#26006634) with REAL Broker LLC and the Lakhani Team Real Estate, serving buyers, sellers, and investors across Kent, Bellevue, Seattle, Redmond, Kirkland, Renton, Tacoma, and Puget Sound.',
    sections: [
      {
        h2: 'Data-Driven Real Estate Analytics & Micro-Market Intelligence',
        body: 'Leveraging 15+ years in IT and Systems Analytics, Loki transitions real estate from an emotional transaction into a structured, quantitative process using predictive pricing models, NWMLS absorption rate tracking, and rigorous due diligence.'
      },
      {
        h2: 'Strategic Greater Seattle Micro-Markets',
        body: 'Coverage spans the Eastside Tech Core (Bellevue, Kirkland, Redmond, Sammamish, Issaquah, Woodinville — Avg Target $1.4M+, 10 Days DOM), Seattle Urban Core (Seattle, Shoreline, Lake Forest Park — Avg Target $880K+, 14 Days DOM), North Sound Corridor (Bothell, Lynnwood, Edmonds, Everett — Avg Target $740K+, 18 Days DOM), South Sound Hub (Kent, Renton, Auburn, Tacoma, Gig Harbor, Puyallup — Avg Target $560K+, 20 Days DOM), and Capital & Exurban Fringe (Olympia, Lacey, Tumwater, Yelm — Avg Target $510K+, 22 Days DOM).'
      }
    ]
  },
  '/about': {
    h1: 'About Lokesh Chanana (Loki) — Real Estate Broker',
    lead:
      'With over 15 years of experience in IT and Systems Analytics, Lokesh "Loki" Chanana brings data, precision, and process engineering to Greater Seattle real estate in partnership with REAL Broker LLC and the Lakhani Team Real Estate.',
    sections: [
      {
        h2: 'White-Glove Service Backed by Analytical Rigor',
        body: 'Operating across King, Snohomish, Pierce, and Thurston counties, Loki leverages deep micro-market intelligence, private video walkthroughs, and structured negotiation to help buyers uncover hidden value and sellers maximize return on investment.'
      }
    ]
  },
  '/buyers': {
    h1: 'Buying a Home in Seattle, Bellevue & King County',
    lead:
      'Navigating the Greater Seattle housing market requires strategic precision, deep micro-market intelligence, and an agent who fiercely protects your interests.',
    sections: [
      {
        h2: '1. Initial Consultation & Market Analytics',
        body: 'Aligning lifestyle goals, financial parameters, macro-economic trends in King and Snohomish counties, and neighborhood-specific appreciation rates.'
      },
      {
        h2: '2. Pre-Approval, Financial Strategy & WA Mortgage Calculator',
        body: 'Working with reputable local lenders fluent in jumbo loans, tech RSU compensation schedules, and bridge financing so your offer stands out to listing agents.'
      },
      {
        h2: '3. Targeted Property Search, Video Walkthroughs & Offer Engineering',
        body: 'Leveraging NWMLS RESO data, off-market networks, structural/mechanical tour analysis, intelligent escalation clauses, earnest money structuring, and pre-inspection strategies.'
      }
    ]
  },
  '/sellers': {
    h1: 'Selling Your Seattle or King County Home',
    lead:
      'Maximizing your real estate asset return through data-driven pricing, strategic high-ROI preparation, and omnichannel digital marketing.',
    sections: [
      {
        h2: '1. Analytical Pricing Strategy & Absorption Modeling',
        body: 'Evaluating active inventory absorption rates, interest rate macro-trends, and micro-market Days on Market (DOM) velocity to generate multiple-offer momentum.'
      },
      {
        h2: '2. High-ROI Asset Preparation & Omnichannel Marketing',
        body: 'Auditing pre-listing improvements (paint, flooring, professional staging, pre-inspections) combined with twilight photography, 3D Matterport tours, drone video, and geofenced digital campaigns.'
      }
    ]
  },
  '/investors': {
    h1: 'Real Estate Investment in Seattle & Puget Sound',
    lead:
      'Calculating After Repair Value (ARV), Cap Rates, Cash-on-Cash returns, CapEx, and DADU/AADU zoning potential across the Pacific Northwest.',
    sections: [
      {
        h2: 'Sourcing Value, ARV Modeling & CapEx Audits',
        body: 'Identifying off-market opportunities, BRRRR acquisitions, DADU/AADU infill lots, and cash-flowing multi-family rentals across King, Snohomish, and Pierce counties.'
      }
    ]
  },
  '/commercial': {
    h1: 'Commercial Real Estate Acquisitions & 1031 Exchanges',
    lead:
      'Navigating retail, industrial, and multi-family site selection, municipal zoning, Phase I/II feasibility, lease-vs-buy modeling, and 1031 tax-deferred exchanges in Washington State.',
    sections: [
      {
        h2: 'Feasibility, Lease vs. Buy & 1031 Exchange Coordination',
        body: 'Rigorous due diligence on zoning, parking, environmental constraints, depreciation modeling, and strict 45-day identification / 180-day closing coordination for 1031 exchanges.'
      }
    ]
  },
  '/markets/eastside-core': {
    h1: 'Eastside Tech Core Real Estate Market Profile',
    lead:
      'Cities: Bellevue, Kirkland, Redmond, Sammamish, Issaquah, Woodinville • Avg Target Price: $1.4M+ • Avg Days on Market: 10 Days.',
    sections: [
      {
        h2: 'High-Basis Innovation Corridor Analysis',
        body: 'Anchored by Microsoft, Amazon, Meta, and Google campuses, the Eastside Tech Core combines top-ranked school districts, Lake Washington waterfront living, and resilient luxury appreciation.'
      }
    ]
  },
  '/markets/seattle-core': {
    h1: 'Seattle Urban Core Real Estate Market Profile',
    lead:
      'Cities: Seattle, Shoreline, Lake Forest Park • Avg Target Price: $880K+ • Avg Days on Market: 14 Days.',
    sections: [
      {
        h2: 'Transit, Density & Split-Asset Market Analysis',
        body: 'From historic Craftsman and Tudor residences in Queen Anne, Capitol Hill, and Ballard to South Lake Union condominiums and Sound Transit Link Light Rail upzoned corridors in Shoreline.'
      }
    ]
  },
  '/markets/north-sound': {
    h1: 'North Sound Corridor Real Estate Market Profile',
    lead:
      'Cities: Lynnwood, Edmonds, Bothell, Everett, Marysville • Avg Target Price: $740K+ • Avg Days on Market: 18 Days.',
    sections: [
      {
        h2: 'Snohomish County Growth & Light Rail Expansion',
        body: 'Anchored by Bothell biotech, Everett aerospace, Edmonds waterfront charm, and expanding Link Light Rail connectivity.'
      }
    ]
  },
  '/markets/south-sound': {
    h1: 'South Sound Hub & South King County Real Estate Market Profile',
    lead:
      'Cities: Kent, Renton, Auburn, Tacoma, Gig Harbor, Puyallup, Lakewood, Spanaway • Avg Target Price: $560K+ • Avg Days on Market: 20 Days.',
    sections: [
      {
        h2: 'Kent Valley, Pierce County & JBLM Value Corridor',
        body: 'Strong residential value baseline and high-yield rental market supported by Kent Valley logistics, Tacoma revitalization, Gig Harbor waterfront, and Joint Base Lewis-McChord (JBLM) demand.'
      }
    ]
  },
  '/markets/thurston-belt': {
    h1: 'Capital & Exurban Fringe (Thurston Belt) Real Estate Market Profile',
    lead:
      'Cities: Olympia, Lacey, Tumwater, Yelm • Avg Target Price: $510K+ • Avg Days on Market: 22 Days.',
    sections: [
      {
        h2: 'State Government Stability & Acreage Value',
        body: 'Stabilized by the Washington State government in Olympia, master-planned communities in Lacey and Tumwater, and expansive acreage in Yelm.'
      }
    ]
  }
};

// Populate static content for all 8 city routes dynamically from CITY_PAGES_DATA
for (const [slug, cityData] of Object.entries(CITY_PAGES_DATA)) {
  ROUTE_STATIC_CONTENT[`/cities/${slug}`] = {
    h1: `${cityData.city}, WA Real Estate — Lokesh "Loki" Chanana`,
    lead: `${cityData.regionTag} • Avg Target Price: ${cityData.avgPrice} • Avg Days on Market: ${cityData.avgDom}. Key Neighborhoods: ${cityData.neighborhoods.join(', ')}.`,
    sections: [
      {
        h2: `${cityData.city} Housing Market Intelligence`,
        body: cityData.overview.join(' ')
      },
      {
        h2: `Transit, Commute & Economic Anchors in ${cityData.city}`,
        body: cityData.commuteHighlights
      }
    ]
  };
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function buildSemanticRootHtml(routePath, seo) {
  const content = ROUTE_STATIC_CONTENT[routePath] || ROUTE_STATIC_CONTENT['/'];
  const faqs = seo.faqs || [];

  const sectionsHtml = (content.sections || [])
    .map(
      (s) =>
        `<section><h2>${escapeHtml(s.h2)}</h2><p>${escapeHtml(s.body)}</p></section>`
    )
    .join('\n');

  const faqsHtml =
    faqs.length > 0
      ? `<section><h2>Frequently Asked Questions</h2>${faqs
          .map(
            (f) =>
              `<article><h3>${escapeHtml(f.question)}</h3><p>${escapeHtml(
                f.answer
              )}</p></article>`
          )
          .join('\n')}</section>`
      : '';

  return `<main class="max-w-5xl mx-auto px-4 py-16">
    <header>
      <p>Lokesh Chanana (Loki) • Licensed Real Estate Broker (#26006634) • REAL Broker LLC &amp; Lakhani Team</p>
      <h1>${escapeHtml(content.h1)}</h1>
      <p>${escapeHtml(content.lead)}</p>
    </header>
    ${sectionsHtml}
    ${faqsHtml}
    <footer>
      <p>Contact Lokesh "Loki" Chanana: <a href="tel:+18018601052">(801) 860-1052</a> | <a href="mailto:lokeshchanana@outlook.com">lokeshchanana@outlook.com</a> | <a href="https://share.google/4Ha7jttZI6W7AeiSP">Google Business Profile &amp; Reviews</a> | <a href="https://www.zillow.com/profile/Lokeshchanana_re">Zillow Profile</a></p>
      <nav aria-label="Site Directory">
        <a href="/">Home</a> |
        <a href="/about">About Loki</a> |
        <a href="/buyers">Buyer's Guide</a> |
        <a href="/sellers">Seller's Guide</a> |
        <a href="/investors">Investor's Guide</a> |
        <a href="/commercial">Commercial &amp; 1031</a> |
        <a href="/markets/eastside-core">Eastside Tech Core</a> |
        <a href="/markets/seattle-core">Seattle Urban Core</a> |
        <a href="/markets/north-sound">North Sound Corridor</a> |
        <a href="/markets/south-sound">South Sound Hub</a> |
        <a href="/markets/thurston-belt">Capital &amp; Thurston Belt</a> |
        <a href="/cities/kent">Kent, WA</a> |
        <a href="/cities/bellevue">Bellevue, WA</a> |
        <a href="/cities/seattle">Seattle, WA</a> |
        <a href="/cities/redmond">Redmond, WA</a> |
        <a href="/cities/kirkland">Kirkland, WA</a> |
        <a href="/cities/renton">Renton, WA</a> |
        <a href="/cities/auburn">Auburn, WA</a> |
        <a href="/cities/tacoma">Tacoma, WA</a>
      </nav>
    </footer>
  </main>`;
}

const baseHtml = fs.readFileSync(BASE_HTML_PATH, 'utf-8');

// Generate dedicated checkin.html for checkin.lokeshchanana.com (no public SEO indexing)
const checkinHtml = baseHtml
  .replace(
    /<title>[\s\S]*?<\/title>/,
    '<title>Open House Guest Check-In | Lokesh Chanana (Loki)</title>'
  )
  .replace(
    /<meta name="robots" content="[^"]*"\s*\/>/,
    '<meta name="robots" content="noindex, nofollow, noarchive" />'
  )
  .replace(
    /<link rel="canonical" href="[^"]*"\s*\/>/,
    '<link rel="canonical" href="https://checkin.lokeshchanana.com/" />'
  );
fs.writeFileSync(path.join(DIST_DIR, 'checkin.html'), checkinHtml, 'utf-8');

for (const [routePath, seo] of Object.entries(SEO_ROUTES)) {
  let html = baseHtml;

  html = html.replace(
    /<title>[\s\S]*?<\/title>/,
    `<title>${escapeHtml(seo.title)}</title>`
  );

  html = html.replace(
    /<meta name="description" content="[^"]*"\s*\/>/,
    `<meta name="description" content="${escapeHtml(seo.description)}" />`
  );

  const robotsValue = seo.noindex
    ? 'noindex, nofollow'
    : 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1';
  html = html.replace(
    /<meta name="robots" content="[^"]*"\s*\/>/,
    `<meta name="robots" content="${robotsValue}" />`
  );

  html = html.replace(
    /<link rel="canonical" href="[^"]*"\s*\/>/,
    `<link rel="canonical" href="${escapeHtml(seo.canonical)}" />`
  );

  html = html.replace(
    /<meta property="og:url" content="[^"]*"\s*\/>/,
    `<meta property="og:url" content="${escapeHtml(seo.canonical)}" />`
  );
  html = html.replace(
    /<meta property="og:title" content="[^"]*"\s*\/>/,
    `<meta property="og:title" content="${escapeHtml(seo.title)}" />`
  );
  html = html.replace(
    /<meta property="og:description" content="[^"]*"\s*\/>/,
    `<meta property="og:description" content="${escapeHtml(seo.description)}" />`
  );
  html = html.replace(
    /<meta property="og:image" content="[^"]*"\s*\/>/,
    `<meta property="og:image" content="${escapeHtml(seo.ogImage)}" />`
  );

  html = html.replace(
    /<meta name="twitter:url" content="[^"]*"\s*\/>/,
    `<meta name="twitter:url" content="${escapeHtml(seo.canonical)}" />`
  );
  html = html.replace(
    /<meta name="twitter:title" content="[^"]*"\s*\/>/,
    `<meta name="twitter:title" content="${escapeHtml(seo.title)}" />`
  );
  html = html.replace(
    /<meta name="twitter:description" content="[^"]*"\s*\/>/,
    `<meta name="twitter:description" content="${escapeHtml(seo.description)}" />`
  );
  html = html.replace(
    /<meta name="twitter:image" content="[^"]*"\s*\/>/,
    `<meta name="twitter:image" content="${escapeHtml(seo.ogImage)}" />`
  );

  const schemas = buildRouteJsonLd(routePath);
  if (schemas.length > 0) {
    const scriptsHtml = schemas
      .map(
        (schema) =>
          `  <script data-route-jsonld="true" type="application/ld+json">${JSON.stringify(
            schema
          )}</script>`
      )
      .join('\n');
    html = html.replace('</head>', `${scriptsHtml}\n  </head>`);
  }

  const rootContent = buildSemanticRootHtml(routePath, seo);
  html = html.replace(
    '<div id="root"></div>',
    `<div id="root">${rootContent}</div>`
  );

  if (routePath === '/') {
    fs.writeFileSync(BASE_HTML_PATH, html, 'utf-8');
  } else {
    const outDir = path.join(DIST_DIR, routePath.slice(1));
    fs.mkdirSync(outDir, { recursive: true });
    fs.writeFileSync(path.join(outDir, 'index.html'), html, 'utf-8');
  }
}

console.log(`Prerendered ${Object.keys(SEO_ROUTES).length} static routes in dist/`);
