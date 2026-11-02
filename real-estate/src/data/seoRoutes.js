// Centralized route SEO metadata, Breadcrumb schema, VideoObject schema, and FAQ schema for all pages
// Strict length limits enforced for Bing Webmaster Tools & Google Search Console:
// - Title: 45–56 chars (strictly <= 60)
// - Meta Description: 130–155 chars (strictly <= 158)

export const SITE_URL = 'https://lokeshchanana.com';
export const DEFAULT_OG_IMAGE = 'https://lokeshchanana.com/loki-profile.jpg';

export const PROPERTY_TOUR_VIDEOS = [
  {
    id: 'DefBayDkggh',
    name: 'Move-In Ready Single-Level Home Tour — Fife, WA',
    description: 'Walkthrough of 6304 Sheffield Ln E, Fife, WA 98424 (3 Beds, 2 Baths, 1,614 Sq Ft) in a gated 55+ community with Lokesh "Loki" Chanana.',
    embedUrl: 'https://www.instagram.com/reel/DefBayDkggh/embed/',
    contentUrl: 'https://www.instagram.com/reel/DefBayDkggh/',
    thumbnailUrl: 'https://lokeshchanana.com/hero_south.jpg',
    uploadDate: '2026-10-01T12:00:00-07:00'
  },
  {
    id: 'DeNfft0EdO0',
    name: 'Haller Lake Modern Retreat Home Tour — North Seattle, WA',
    description: 'Property walkthrough of a 4 Bed, 2.5 Bath, 2,751 Sq Ft modern residence near Haller Lake in North Seattle with Lokesh "Loki" Chanana.',
    embedUrl: 'https://www.instagram.com/reel/DeNfft0EdO0/embed/',
    contentUrl: 'https://www.instagram.com/reel/DeNfft0EdO0/',
    thumbnailUrl: 'https://lokeshchanana.com/hero_seattle.jpg',
    uploadDate: '2026-10-05T12:00:00-07:00'
  },
  {
    id: 'DdxZw6Ozj4t',
    name: 'Turnkey Multi-Gen Seattle Residence Walkthrough — Seattle, WA',
    description: 'Full tour of 10036 1st Ave S, Seattle, WA 98168 (4 Beds, 2 Baths, 1,760 Sq Ft) by Greater Seattle Real Estate Broker Lokesh Chanana.',
    embedUrl: 'https://www.instagram.com/reel/DdxZw6Ozj4t/embed/',
    contentUrl: 'https://www.instagram.com/reel/DdxZw6Ozj4t/',
    thumbnailUrl: 'https://lokeshchanana.com/hero_seattle.jpg',
    uploadDate: '2026-10-10T12:00:00-07:00'
  }
];

export const SEO_ROUTES = {
  '/': {
    title: 'Lokesh Chanana (Loki) | Seattle & Bellevue Realtor',
    description:
      'Lokesh "Loki" Chanana is a data-driven Greater Seattle Real Estate Broker (#26006634) with REAL Broker LLC serving Kent, Bellevue, Seattle & King County.',
    canonical: 'https://lokeshchanana.com/',
    ogImage: DEFAULT_OG_IMAGE,
    includeVideos: true,
    breadcrumbs: [{ name: 'Home', path: '/' }],
    faqs: [
      {
        question: 'Who is Lokesh Chanana (Loki) and what areas does he serve?',
        answer:
          'Lokesh "Loki" Chanana is a licensed Washington State Real Estate Broker (License #26006634) with REAL Broker LLC and the Lakhani Team Real Estate. Leveraging 15+ years in IT and Systems Analytics, he serves buyers, sellers, and investors across 80+ cities in King, Snohomish, Pierce, and Thurston counties—including Kent, Bellevue, Seattle, Redmond, Kirkland, Renton, and Tacoma.'
      },
      {
        question: 'What makes Loki’s analytical approach to Greater Seattle real estate different?',
        answer:
          'Rather than relying on guesswork, Loki applies predictive pricing models, NWMLS absorption rate tracking, Days on Market (DOM) velocity analysis, and structured inspection/risk-mitigation protocols so buyers avoid overpaying and sellers maximize net proceeds.'
      },
      {
        question: 'Do you offer remote video walkthroughs for out-of-state or tech relocation buyers?',
        answer:
          'Yes. Loki regularly conducts detailed, unedited private video tours and field walkthroughs for relocating tech professionals and out-of-state buyers—evaluating foundation, roof/HVAC age, street noise, natural light, and micro-market commute dynamics.'
      },
      {
        question: 'How can I contact Lokesh Chanana for a home valuation or buyer consultation?',
        answer:
          'You can call or text Loki directly at (801) 860-1052, email lokeshchanana@outlook.com, or submit a request through the contact form at lokeshchanana.com.'
      }
    ]
  },
  '/about': {
    title: 'About Lokesh "Loki" Chanana | Seattle Real Estate',
    description:
      'Meet Lokesh Chanana (Loki), former 15-year IT & Systems Analytics leader turned Greater Seattle Real Estate Broker with REAL Broker LLC & Lakhani Team.',
    canonical: 'https://lokeshchanana.com/about',
    ogImage: DEFAULT_OG_IMAGE,
    includeVideos: true,
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'About Loki', path: '/about' }
    ],
    faqs: [
      {
        question: 'What is Lokesh Chanana’s professional background before real estate?',
        answer:
          'Prior to real estate, Lokesh Chanana spent more than 15 years in IT and Systems Analytics. He brings rigorous quantitative analysis, process engineering, and structured negotiation to residential and commercial transactions across Greater Seattle.'
      },
      {
        question: 'Which brokerage and team is Lokesh Chanana affiliated with?',
        answer:
          'Lokesh is a licensed Washington Real Estate Broker (#26006634) partnered with REAL Broker LLC and the Lakhani Team Real Estate.'
      },
      {
        question: 'What languages does Lokesh Chanana speak?',
        answer: 'Lokesh is fluent in both English and Hindi.'
      }
    ]
  },
  '/buyers': {
    title: 'Buying a Home in Seattle & Bellevue | Loki Chanana',
    description:
      'Strategic guide to buying a home in Seattle, Bellevue & King County: local jumbo/RSU lenders, NWMLS off-market search, pre-inspections & offer strategy.',
    canonical: 'https://lokeshchanana.com/buyers',
    ogImage: DEFAULT_OG_IMAGE,
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'Buyer’s Guide', path: '/buyers' }
    ],
    faqs: [
      {
        question: 'Why does using a local lender matter when buying a home in Seattle or Bellevue?',
        answer:
          'In multiple-offer situations in King and Snohomish counties, listing agents strongly favor local lenders who understand tech RSU income schedules, jumbo underwriting, and fast appraisal turnarounds, giving your offer a higher probability of acceptance.'
      },
      {
        question: 'How do escalation clauses and pre-inspections work in the Seattle housing market?',
        answer:
          'An escalation clause automatically increments your offer above competing bona fide offers up to a data-backed price cap so you win without blindly overpaying. Conducting a pre-offer inspection allows you to evaluate structural and mechanical systems upfront before waiving inspection contingencies.'
      },
      {
        question: 'Can Loki help first-time home buyers as well as luxury tech relocation buyers?',
        answer:
          'Yes. Loki guides first-time buyers through financing, neighborhood trade-offs, and inspection protection, while also advising tech professionals and move-up buyers across Bellevue, Redmond, Kirkland, Seattle, and Kent.'
      }
    ]
  },
  '/sellers': {
    title: 'Selling Your Seattle Home | Lokesh "Loki" Chanana',
    description:
      'Maximize your Seattle, Bellevue, or Kent home sale with predictive CMA pricing, high-ROI prep, 3D Matterport/drone media, and multi-offer negotiation.',
    canonical: 'https://lokeshchanana.com/sellers',
    ogImage: DEFAULT_OG_IMAGE,
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'Seller’s Guide', path: '/sellers' }
    ],
    faqs: [
      {
        question: 'How do you determine the optimal listing price for a home in King County?',
        answer:
          'Instead of looking only at lagging 60-day sold comps, Loki models current active inventory absorption rates, micro-market Days on Market (DOM) velocity, and buyer search price brackets to generate maximum first-week showing velocity and multiple-offer leverage.'
      },
      {
        question: 'Which pre-listing home improvements yield the highest ROI in Greater Seattle?',
        answer:
          'Fresh neutral interior paint, refinished or updated flooring, landscaping curb appeal, professional staging, and a clean seller pre-inspection report consistently deliver the highest return on investment and reduce buyer contingencies.'
      },
      {
        question: 'How do you evaluate multiple offers beyond just the highest price?',
        answer:
          'Every offer is scored in an analytical matrix comparing net proceeds, lender reputation, down payment strength, earnest money non-refundability, appraisal gap coverage, and closing timeline certainty.'
      }
    ]
  },
  '/investors': {
    title: 'Seattle Real Estate Investing Guide | Loki Chanana',
    description:
      'Data-driven real estate investment advisory in Puget Sound: ARV comps, Cap Rate & Cash-on-Cash modeling, BRRRR strategy, CapEx & DADU/AADU zoning.',
    canonical: 'https://lokeshchanana.com/investors',
    ogImage: DEFAULT_OG_IMAGE,
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'Investor’s Guide', path: '/investors' }
    ],
    faqs: [
      {
        question: 'Where do real estate investors find positive cash flow vs. appreciation in Puget Sound?',
        answer:
          'The Eastside (Bellevue, Redmond, Kirkland) and Seattle Core primarily drive long-term appreciation and DADU/AADU infill equity, whereas South King County (Kent, Auburn, Renton, Federal Way) and Pierce County (Tacoma, Puyallup, Lakewood near JBLM) offer stronger cap rates and cash-on-cash rental yields.'
      },
      {
        question: 'How does Washington’s DADU / AADU zoning create value for investors?',
        answer:
          'Municipalities like Seattle, Shoreline, and cities across King County allow Detached Accessory Dwelling Units (DADUs) and Attached ADUs on qualifying residential lots, enabling investors and homeowners to add rental units or condo-ize backyard cottages for forced appreciation.'
      }
    ]
  },
  '/commercial': {
    title: 'Commercial Real Estate & 1031 Exchanges | Seattle',
    description:
      'Commercial real estate acquisitions, retail/industrial site selection, zoning feasibility, lease-vs-buy modeling & 1031 exchanges in Greater Seattle.',
    canonical: 'https://lokeshchanana.com/commercial',
    ogImage: DEFAULT_OG_IMAGE,
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'Commercial Real Estate', path: '/commercial' }
    ],
    faqs: [
      {
        question: 'What are the timeline rules for a 1031 tax-deferred exchange in Washington?',
        answer:
          'In an IRS Section 1031 exchange, investors must identify replacement investment or commercial property within 45 calendar days of closing the relinquished asset and complete the acquisition within 180 calendar days using a Qualified Intermediary.'
      },
      {
        question: 'What commercial property types does Lokesh Chanana advise on?',
        answer:
          'Loki assists owner-users and investors with multi-family apartment buildings, retail storefronts, light industrial/warehouse facilities in the Kent Valley and Puget Sound logistics corridor, mixed-use properties, and lease-vs-buy financial analysis.'
      }
    ]
  },
  '/markets/eastside-core': {
    title: 'Eastside Real Estate | Bellevue, Redmond & Kirkland',
    description:
      'Eastside Tech Core real estate market analysis for Bellevue, Kirkland, Redmond, Sammamish, Issaquah & Woodinville with Lokesh "Loki" Chanana.',
    canonical: 'https://lokeshchanana.com/markets/eastside-core',
    ogImage: 'https://lokeshchanana.com/hero_eastside.jpg',
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'Eastside Tech Core', path: '/markets/eastside-core' }
    ],
    faqs: [
      {
        question: 'What cities make up the Eastside Tech Core real estate market?',
        answer:
          'The Eastside Tech Core encompasses Bellevue, Kirkland, Redmond, Sammamish, Issaquah, Woodinville, Mercer Island, and Newcastle on the eastern shore of Lake Washington.'
      },
      {
        question: 'Why is the Eastside real estate market so competitive?',
        answer:
          'Anchored by Microsoft headquarters in Redmond and major Amazon, Meta, and Google campuses in Bellevue and Kirkland, the Eastside combines high-compensation tech employment, top-ranked Lake Washington and Bellevue school districts, and constrained single-family land supply.'
      }
    ]
  },
  '/markets/seattle-core': {
    title: 'Seattle Urban Core Real Estate | Shoreline & Seattle',
    description:
      'Seattle Urban Core real estate analytics covering Queen Anne, Capitol Hill, Ballard, South Lake Union, Shoreline & Lake Forest Park with Loki Chanana.',
    canonical: 'https://lokeshchanana.com/markets/seattle-core',
    ogImage: 'https://lokeshchanana.com/hero_seattle.jpg',
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'Seattle Urban Core', path: '/markets/seattle-core' }
    ],
    faqs: [
      {
        question: 'How is Sound Transit Link Light Rail impacting Seattle and Shoreline real estate?',
        answer:
          'Light rail expansion northward through Northgate, Shoreline, and Mountlake Terrace has catalyzed transit-oriented upzoning, making properties near stations highly attractive for townhome infill, DADU additions, and commuter resale value.'
      },
      {
        question: 'What is the difference between buying a Craftsman home vs. a townhome or condo in Seattle?',
        answer:
          'Historic single-family Craftsman and Tudor homes in Queen Anne, Ballard, and Capitol Hill offer land appreciation and DADU potential, while modern townhomes provide fee-simple ownership without HOA dues, and downtown/South Lake Union condos offer turnkey urban walkability.'
      }
    ]
  },
  '/markets/north-sound': {
    title: 'North Sound Real Estate | Bothell, Lynnwood & Everett',
    description:
      'North Sound & Snohomish County real estate guide for Bothell, Lynnwood, Edmonds, Everett & Marysville: pricing, DOM velocity & Light Rail growth.',
    canonical: 'https://lokeshchanana.com/markets/north-sound',
    ogImage: 'https://lokeshchanana.com/hero_north.jpg',
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'North Sound Corridor', path: '/markets/north-sound' }
    ],
    faqs: [
      {
        question: 'Why are buyers moving to the North Sound Corridor in Snohomish County?',
        answer:
          'Cities like Bothell, Lynnwood, Edmonds, Mill Creek, and Everett offer larger lot sizes, newer suburban developments, and lower price-per-square-foot than Seattle and Bellevue while maintaining direct I-5, I-405, and Link Light Rail access.'
      }
    ]
  },
  '/markets/south-sound': {
    title: 'South Sound Real Estate | Kent, Renton & Tacoma WA',
    description:
      'South King & Pierce County real estate market guide for Kent, Renton, Auburn, Tacoma, Gig Harbor & Puyallup with broker Lokesh "Loki" Chanana.',
    canonical: 'https://lokeshchanana.com/markets/south-sound',
    ogImage: 'https://lokeshchanana.com/hero_south.jpg',
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'South Sound Hub', path: '/markets/south-sound' }
    ],
    faqs: [
      {
        question: 'Why are Kent, Renton, Auburn, and Tacoma popular with both homebuyers and investors?',
        answer:
          'South King County (Kent, Renton, Auburn, Covington, Maple Valley) and Pierce County (Tacoma, Puyallup, Gig Harbor, Lakewood) provide strong value per square foot, convenient access to both Seattle/Eastside tech jobs and Joint Base Lewis-McChord (JBLM), and some of the strongest rental yields in Puget Sound.'
      }
    ]
  },
  '/markets/thurston-belt': {
    title: 'Thurston County Real Estate | Olympia, Lacey & Yelm',
    description:
      'Capital & Thurston County real estate market guide for Olympia, Lacey, Tumwater & Yelm: master-planned homes, acreage & market trends with Loki Chanana.',
    canonical: 'https://lokeshchanana.com/markets/thurston-belt',
    ogImage: 'https://lokeshchanana.com/hero_thurston.jpg',
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'Capital & Exurban Fringe', path: '/markets/thurston-belt' }
    ],
    faqs: [
      {
        question: 'What attracts buyers to Olympia, Lacey, Tumwater, and Yelm?',
        answer:
          'Thurston County offers recession-resistant stability anchored by the Washington State government in Olympia, master-planned golf and commuter communities in Lacey and Tumwater, and spacious acreage in Yelm at roughly half the price per square foot of core King County.'
      }
    ]
  },
  '/cities/kent': {
    title: 'Kent, WA Real Estate Agent | Lokesh "Loki" Chanana',
    description:
      'Buy or sell a home in Kent, WA (East Hill, Lake Meridian, Scenic Hill & Kent Valley) with data-driven Real Estate Broker Lokesh "Loki" Chanana.',
    canonical: 'https://lokeshchanana.com/cities/kent',
    ogImage: 'https://lokeshchanana.com/hero_south.jpg',
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'South Sound Hub', path: '/markets/south-sound' },
      { name: 'Kent, WA Real Estate', path: '/cities/kent' }
    ],
    faqs: [
      {
        question: 'What are the most popular neighborhoods to buy a home in Kent, WA?',
        answer:
          'Kent’s East Hill, Lake Meridian, Panther Lake, Scenic Hill, and West Hill are top residential choices offering spacious lots, parks, and quick access to SR-167, I-5, and the Sounder commuter train to Downtown Seattle.'
      },
      {
        question: 'How fast do homes sell in Kent, Washington?',
        answer:
          'Well-priced single-family homes in Kent average around 16 Days on Market (DOM) with an average target price near $625K+, making pre-approval and strategic offer engineering essential.'
      }
    ]
  },
  '/cities/bellevue': {
    title: 'Bellevue, WA Real Estate Broker | Lokesh Chanana',
    description:
      'Luxury & tech relocation real estate broker in Bellevue, WA (West Bellevue, Somerset, Clyde Hill, Bridle Trails & Downtown) — Lokesh "Loki" Chanana.',
    canonical: 'https://lokeshchanana.com/cities/bellevue',
    ogImage: 'https://lokeshchanana.com/hero_eastside.jpg',
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'Eastside Tech Core', path: '/markets/eastside-core' },
      { name: 'Bellevue, WA Real Estate', path: '/cities/bellevue' }
    ],
    faqs: [
      {
        question: 'What makes Bellevue, WA real estate a top choice for tech relocation buyers?',
        answer:
          'Bellevue combines major Amazon, Microsoft, and Meta employment hubs, nationally ranked Bellevue School District schools, Lake Washington waterfront living, and Sound Transit 2 Line Light Rail connectivity.'
      }
    ]
  },
  '/cities/seattle': {
    title: 'Seattle, WA Real Estate Agent | Lokesh "Loki" Chanana',
    description:
      'Data-driven real estate broker in Seattle, WA covering Queen Anne, Ballard, Capitol Hill, Green Lake, Magnolia & West Seattle — Lokesh "Loki" Chanana.',
    canonical: 'https://lokeshchanana.com/cities/seattle',
    ogImage: 'https://lokeshchanana.com/hero_seattle.jpg',
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'Seattle Urban Core', path: '/markets/seattle-core' },
      { name: 'Seattle, WA Real Estate', path: '/cities/seattle' }
    ],
    faqs: [
      {
        question: 'Which Seattle neighborhoods have the strongest long-term appreciation and DADU potential?',
        answer:
          'Queen Anne, Ballard, Green Lake, Capitol Hill, Phinney Ridge, and West Seattle combine strong historic single-family demand with progressive DADU/AADU accessory dwelling unit zoning.'
      }
    ]
  },
  '/cities/redmond': {
    title: 'Redmond, WA Real Estate Broker | Lokesh Chanana',
    description:
      'Redmond, WA real estate specialist for Education Hill, Overlake, Redmond Ridge & Downtown Redmond tech relocations — Broker Lokesh "Loki" Chanana.',
    canonical: 'https://lokeshchanana.com/cities/redmond',
    ogImage: 'https://lokeshchanana.com/hero_eastside.jpg',
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'Eastside Tech Core', path: '/markets/eastside-core' },
      { name: 'Redmond, WA Real Estate', path: '/cities/redmond' }
    ],
    faqs: [
      {
        question: 'Why are Education Hill and Overlake in Redmond so competitive?',
        answer:
          'Minutes from Microsoft’s global campus and the new Sound Transit Light Rail stations, Education Hill and Overlake offer top-rated Lake Washington schools and high resale liquidity.'
      }
    ]
  },
  '/cities/kirkland': {
    title: 'Kirkland, WA Real Estate Agent | Lokesh Chanana',
    description:
      'Buy or sell in Kirkland, WA (Moss Bay, Houghton, West of Market, Juanita & Totem Lake) with analytical Real Estate Broker Lokesh "Loki" Chanana.',
    canonical: 'https://lokeshchanana.com/cities/kirkland',
    ogImage: 'https://lokeshchanana.com/hero_eastside.jpg',
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'Eastside Tech Core', path: '/markets/eastside-core' },
      { name: 'Kirkland, WA Real Estate', path: '/cities/kirkland' }
    ],
    faqs: [
      {
        question: 'What are the premier waterfront and view neighborhoods in Kirkland, WA?',
        answer:
          'West of Market, Moss Bay, Houghton, and Juanita offer walkable Lake Washington waterfront parks, panoramic Olympic Mountain views, and immediate access to Google’s Kirkland Urban campus.'
      }
    ]
  },
  '/cities/renton': {
    title: 'Renton, WA Real Estate Agent | Lokesh "Loki" Chanana',
    description:
      'Renton, WA real estate guide for Renton Highlands, Kennydale, Fairwood & Talbot Hill: pricing, CMA valuations, and home buying with Loki Chanana.',
    canonical: 'https://lokeshchanana.com/cities/renton',
    ogImage: 'https://lokeshchanana.com/hero_south.jpg',
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'South Sound Hub', path: '/markets/south-sound' },
      { name: 'Renton, WA Real Estate', path: '/cities/renton' }
    ],
    faqs: [
      {
        question: 'Why do Eastside and Seattle buyers target Kennydale and the Renton Highlands?',
        answer:
          'Located immediately south of Bellevue along I-405 and Lake Washington, Kennydale and the East Renton Highlands offer newer homes and larger lots just 10–15 minutes from Downtown Bellevue.'
      }
    ]
  },
  '/cities/auburn': {
    title: 'Auburn, WA Real Estate Agent | Lokesh "Loki" Chanana',
    description:
      'Buy or sell a home in Auburn, WA (Lakeland Hills, Lea Hill & West Hill) with data-driven Greater Seattle Real Estate Broker Lokesh "Loki" Chanana.',
    canonical: 'https://lokeshchanana.com/cities/auburn',
    ogImage: 'https://lokeshchanana.com/hero_south.jpg',
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'South Sound Hub', path: '/markets/south-sound' },
      { name: 'Auburn, WA Real Estate', path: '/cities/auburn' }
    ],
    faqs: [
      {
        question: 'What makes Lakeland Hills and Lea Hill in Auburn popular with homebuyers?',
        answer:
          'Lakeland Hills and Lea Hill offer master-planned parks, walkable town centers, attainable single-family pricing ($565K+ avg target), and easy access to the Auburn Sounder commuter train.'
      }
    ]
  },
  '/cities/tacoma': {
    title: 'Tacoma, WA Real Estate Agent | Lokesh "Loki" Chanana',
    description:
      'Tacoma & Pierce County real estate broker for North End, Proctor, Stadium District, Point Ruston & JBLM investment properties — Lokesh "Loki" Chanana.',
    canonical: 'https://lokeshchanana.com/cities/tacoma',
    ogImage: 'https://lokeshchanana.com/hero_south.jpg',
    breadcrumbs: [
      { name: 'Home', path: '/' },
      { name: 'South Sound Hub', path: '/markets/south-sound' },
      { name: 'Tacoma, WA Real Estate', path: '/cities/tacoma' }
    ],
    faqs: [
      {
        question: 'Which Tacoma neighborhoods are best for residential buyers vs. cash-flow investors?',
        answer:
          'North End, Proctor, Old Town, Stadium District, and Point Ruston lead for residential lifestyle and waterfront walkability, while Central/South Tacoma, University Place, and Lakewood near JBLM offer strong multi-family and rental cash flow.'
      }
    ]
  }
};

export function buildRouteJsonLd(pathname) {
  const route = SEO_ROUTES[pathname] || SEO_ROUTES['/'];
  const items = [];

  if (route.breadcrumbs && route.breadcrumbs.length > 0) {
    items.push({
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      '@id': `${route.canonical}#breadcrumb`,
      itemListElement: route.breadcrumbs.map((crumb, idx) => ({
        '@type': 'ListItem',
        position: idx + 1,
        name: crumb.name,
        item: `${SITE_URL}${crumb.path === '/' ? '/' : crumb.path}`
      }))
    });
  }

  if (route.faqs && route.faqs.length > 0) {
    items.push({
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      '@id': `${route.canonical}#faq`,
      mainEntity: route.faqs.map((faq) => ({
        '@type': 'Question',
        name: faq.question,
        acceptedAnswer: {
          '@type': 'Answer',
          text: faq.answer
        }
      }))
    });
  }

  if (route.includeVideos) {
    for (const vid of PROPERTY_TOUR_VIDEOS) {
      items.push({
        '@context': 'https://schema.org',
        '@type': 'VideoObject',
        name: vid.name,
        description: vid.description,
        thumbnailUrl: [vid.thumbnailUrl],
        uploadDate: vid.uploadDate,
        contentUrl: vid.contentUrl,
        embedUrl: vid.embedUrl
      });
    }
  }

  return items;
}
