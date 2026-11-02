// Exhaustive list of cities and unincorporated major hubs across King, Pierce, Snohomish, and Thurston Counties
// Includes latitude and longitude for GPS nearest-market calculation

export const WA_COUNTIES_MARKETS = {
  'King County': [
    { name: 'Auburn', lat: 47.3073, lng: -122.2285 },
    { name: 'Bellevue', lat: 47.6101, lng: -122.2015 },
    { name: 'Black Diamond', lat: 47.3087, lng: -122.0032 },
    { name: 'Bothell', lat: 47.7601, lng: -122.2054 },
    { name: 'Burien', lat: 47.4704, lng: -122.3468 },
    { name: 'Carnation', lat: 47.6479, lng: -121.9104 },
    { name: 'Clyde Hill', lat: 47.6307, lng: -122.2185 },
    { name: 'Covington', lat: 47.3648, lng: -122.0940 },
    { name: 'Des Moines', lat: 47.4018, lng: -122.3243 },
    { name: 'Duvall', lat: 47.7423, lng: -121.9857 },
    { name: 'Enumclaw', lat: 47.2043, lng: -121.9915 },
    { name: 'Fall City', lat: 47.5673, lng: -121.8987 },
    { name: 'Federal Way', lat: 47.3223, lng: -122.3126 },
    { name: 'Issaquah', lat: 47.5301, lng: -122.0326 },
    { name: 'Kenmore', lat: 47.7573, lng: -122.2440 },
    { name: 'Kent', lat: 47.3809, lng: -122.2348 },
    { name: 'Kirkland', lat: 47.6769, lng: -122.2060 },
    { name: 'Lake Forest Park', lat: 47.7537, lng: -122.2776 },
    { name: 'Maple Valley', lat: 47.3995, lng: -122.0496 },
    { name: 'Medina', lat: 47.6209, lng: -122.2273 },
    { name: 'Mercer Island', lat: 47.5707, lng: -122.2221 },
    { name: 'Milton (King)', lat: 47.2515, lng: -122.3134 },
    { name: 'Newcastle', lat: 47.5390, lng: -122.1671 },
    { name: 'Normandy Park', lat: 47.4368, lng: -122.3396 },
    { name: 'North Bend', lat: 47.4957, lng: -121.7868 },
    { name: 'Pacific', lat: 47.2654, lng: -122.2487 },
    { name: 'Redmond', lat: 47.6740, lng: -122.1215 },
    { name: 'Renton', lat: 47.4829, lng: -122.2171 },
    { name: 'Sammamish', lat: 47.6163, lng: -122.0356 },
    { name: 'SeaTac', lat: 47.4436, lng: -122.2961 },
    { name: 'Seattle', lat: 47.6062, lng: -122.3321 },
    { name: 'Shoreline', lat: 47.7560, lng: -122.3400 },
    { name: 'Snoqualmie', lat: 47.5287, lng: -121.8254 },
    { name: 'Tukwila', lat: 47.4740, lng: -122.2610 },
    { name: 'Vashon', lat: 47.4476, lng: -122.4593 },
    { name: 'Woodinville', lat: 47.7543, lng: -122.1635 },
    { name: 'Yarrow Point', lat: 47.6437, lng: -122.2179 }
  ],
  'Pierce County': [
    { name: 'Bonney Lake', lat: 47.1884, lng: -122.1837 },
    { name: 'Buckley', lat: 47.1648, lng: -122.0298 },
    { name: 'Carbonado', lat: 47.0818, lng: -122.0526 },
    { name: 'DuPont', lat: 47.0945, lng: -122.6393 },
    { name: 'Eatonville', lat: 46.8687, lng: -122.2735 },
    { name: 'Edgewood', lat: 47.2443, lng: -122.2871 },
    { name: 'Fife', lat: 47.2404, lng: -122.3596 },
    { name: 'Fircrest', lat: 47.2384, lng: -122.5182 },
    { name: 'Gig Harbor', lat: 47.3293, lng: -122.5801 },
    { name: 'Graham', lat: 47.0543, lng: -122.2943 },
    { name: 'Lakewood', lat: 47.1718, lng: -122.5185 },
    { name: 'Milton', lat: 47.2479, lng: -122.3168 },
    { name: 'Orting', lat: 47.0970, lng: -122.2048 },
    { name: 'Puyallup', lat: 47.1854, lng: -122.2929 },
    { name: 'Roy', lat: 47.0034, lng: -122.5437 },
    { name: 'Ruston', lat: 47.2948, lng: -122.5101 },
    { name: 'South Hill', lat: 47.1354, lng: -122.2743 },
    { name: 'Spanaway', lat: 47.1040, lng: -122.4346 },
    { name: 'Steilacoom', lat: 47.1709, lng: -122.5976 },
    { name: 'Sumner', lat: 47.2032, lng: -122.2415 },
    { name: 'Tacoma', lat: 47.2529, lng: -122.4443 },
    { name: 'University Place', lat: 47.2187, lng: -122.5376 }
  ],
  'Snohomish County': [
    { name: 'Arlington', lat: 48.1987, lng: -122.1251 },
    { name: 'Bothell (Snohomish)', lat: 47.7850, lng: -122.2054 },
    { name: 'Brier', lat: 47.7987, lng: -122.2762 },
    { name: 'Darrington', lat: 48.2554, lng: -121.6026 },
    { name: 'Edmonds', lat: 47.8107, lng: -122.3774 },
    { name: 'Everett', lat: 47.9790, lng: -122.2021 },
    { name: 'Gold Bar', lat: 47.8573, lng: -121.6951 },
    { name: 'Granite Falls', lat: 48.0837, lng: -121.9687 },
    { name: 'Index', lat: 47.8207, lng: -121.5543 },
    { name: 'Lake Stevens', lat: 48.0148, lng: -122.0640 },
    { name: 'Lynnwood', lat: 47.8209, lng: -122.3151 },
    { name: 'Marysville', lat: 48.0518, lng: -122.1771 },
    { name: 'Mill Creek', lat: 47.8601, lng: -122.2040 },
    { name: 'Monroe', lat: 47.8554, lng: -122.0012 },
    { name: 'Mountlake Terrace', lat: 47.7884, lng: -122.3082 },
    { name: 'Mukilteo', lat: 47.9445, lng: -122.3046 },
    { name: 'Snohomish', lat: 47.9129, lng: -122.0982 },
    { name: 'Stanwood', lat: 48.2415, lng: -122.3707 },
    { name: 'Sultan', lat: 47.8623, lng: -121.8157 },
    { name: 'Woodway', lat: 47.7887, lng: -122.3857 }
  ],
  'Thurston County': [
    { name: 'Bucoda', lat: 46.7998, lng: -122.8687 },
    { name: 'Lacey', lat: 47.0343, lng: -122.8232 },
    { name: 'Olympia', lat: 47.0379, lng: -122.9007 },
    { name: 'Rainier', lat: 46.8887, lng: -122.6868 },
    { name: 'Rochester', lat: 46.8220, lng: -123.0957 },
    { name: 'Tenino', lat: 46.8568, lng: -122.8574 },
    { name: 'Tumwater', lat: 47.0090, lng: -122.9107 },
    { name: 'Yelm', lat: 46.9415, lng: -122.6049 }
  ]
};

// Flattened alphabetized list of all unique city names
export const ALL_CITIES = Array.from(
  new Set(
    Object.values(WA_COUNTIES_MARKETS).flatMap(cities => cities.map(c => c.name))
  )
).sort((a, b) => a.localeCompare(b));

// Great circle distance formula in miles
export function calculateDistanceMiles(lat1, lon1, lat2, lon2) {
  const R = 3958.8; // Earth's radius in miles
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// Find nearest market based on user's GPS coords
export function findNearestMarket(userLat, userLng) {
  let nearestCity = null;
  let minDistance = Infinity;

  for (const [county, cities] of Object.entries(WA_COUNTIES_MARKETS)) {
    for (const city of cities) {
      const distance = calculateDistanceMiles(userLat, userLng, city.lat, city.lng);
      if (distance < minDistance) {
        minDistance = distance;
        nearestCity = {
          name: city.name,
          county,
          lat: city.lat,
          lng: city.lng,
          distanceMiles: Math.round(distance * 10) / 10
        };
      }
    }
  }

  return nearestCity;
}
