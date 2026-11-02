import React, { useState } from 'react';
import { Search, MapPin, Bed, Bath, Square, DollarSign, Filter, ArrowUpRight, CheckCircle, Sparkles, Building } from 'lucide-react';

const MOCK_PROPERTIES = [
  {
    id: 'nwmls-101',
    title: 'Modern Queen Anne Hill Residence',
    address: '1420 4th Ave W, Seattle, WA 98119',
    city: 'Seattle',
    price: 1395000,
    beds: 4,
    baths: 3.5,
    sqft: 2850,
    status: 'Active',
    image: 'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=1200&q=85',
    type: 'Single Family',
    mlsId: 'NWMLS# 2198042'
  },
  {
    id: 'nwmls-102',
    title: 'Bellevue Luxury Waterfront Estate',
    address: '10412 NE 24th St, Bellevue, WA 98004',
    city: 'Bellevue',
    price: 2450000,
    beds: 5,
    baths: 4.5,
    sqft: 4120,
    status: 'Active',
    image: 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=85',
    type: 'Single Family',
    mlsId: 'NWMLS# 2199104'
  },
  {
    id: 'nwmls-103',
    title: 'Kirkland Lake Washington Residence',
    address: '228 Lake St S #302, Kirkland, WA 98033',
    city: 'Kirkland',
    price: 975000,
    beds: 2,
    baths: 2.0,
    sqft: 1420,
    status: 'Pending',
    image: 'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=1200&q=85',
    type: 'Condo',
    mlsId: 'NWMLS# 2197541'
  },
  {
    id: 'nwmls-104',
    title: 'Redmond Tech Corridor Estate',
    address: '8910 164th Ave NE, Redmond, WA 98052',
    city: 'Redmond',
    price: 1650000,
    beds: 4,
    baths: 3.0,
    sqft: 3100,
    status: 'Active',
    image: 'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&q=85',
    type: 'Single Family',
    mlsId: 'NWMLS# 2196620'
  },
  {
    id: 'nwmls-105',
    title: 'Renton Highlands Craftsman',
    address: '4218 NE 12th St, Renton, WA 98059',
    city: 'Renton',
    price: 849000,
    beds: 3,
    baths: 2.5,
    sqft: 2150,
    status: 'Sold',
    image: 'https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=1200&q=85',
    type: 'Single Family',
    mlsId: 'NWMLS# 2189401'
  },
  {
    id: 'nwmls-106',
    title: 'Capitol Hill Skyline Penthouse',
    address: '715 E Bellevue Dr #5A, Seattle, WA 98102',
    city: 'Seattle',
    price: 1125000,
    beds: 2,
    baths: 2.0,
    sqft: 1680,
    status: 'Active',
    image: 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=1200&q=85',
    type: 'Condo',
    mlsId: 'NWMLS# 2199850'
  }
];

export default function FeaturedHomes() {
  const [selectedCity, setSelectedCity] = useState('All');
  const [selectedStatus, setSelectedStatus] = useState('All');
  const [searchTerm, setSearchTerm] = useState('');

  const filteredProperties = MOCK_PROPERTIES.filter(p => {
    const matchesCity = selectedCity === 'All' || p.city === selectedCity;
    const matchesStatus = selectedStatus === 'All' || p.status === selectedStatus;
    const matchesSearch = p.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          p.address.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          p.city.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCity && matchesStatus && matchesSearch;
  });

  return (
    <section id="homes" className="py-24 bg-slate-50 dark:bg-navy-950 transition-colors duration-300 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-14 space-y-4">
          <div className="inline-flex items-center gap-2 bg-cyan/10 border border-cyan/30 px-4 py-1.5 rounded-full text-cyan-dark dark:text-cyan text-xs font-bold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5" /> NWMLS Property Search Showcase
          </div>
          <h2 className="text-3xl sm:text-5xl font-serif font-extrabold text-slate-900 dark:text-white tracking-tight">
            Featured Washington Properties
          </h2>
          <p className="text-slate-600 dark:text-slate-300 text-base sm:text-lg">
            Explore active, pending, and recently sold residences across Greater Seattle & Puget Sound.
          </p>
        </div>

        {/* Search & Filter Bar */}
        <div className="bg-white dark:bg-navy-900 p-5 sm:p-7 rounded-3xl border border-slate-200 dark:border-navy-700 shadow-xl shadow-slate-200/50 dark:shadow-2xl mb-12 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
            
            {/* Search Input */}
            <div className="md:col-span-6 relative">
              <Search className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search neighborhood, street, or city..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-slate-50 dark:bg-navy-950 border border-slate-300 dark:border-navy-700 rounded-xl pl-11 pr-4 py-3.5 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-cyan text-sm font-medium"
              />
            </div>

            {/* City Dropdown */}
            <div className="md:col-span-3">
              <select
                value={selectedCity}
                onChange={(e) => setSelectedCity(e.target.value)}
                className="w-full bg-slate-50 dark:bg-navy-950 border border-slate-300 dark:border-navy-700 rounded-xl px-4 py-3.5 text-slate-900 dark:text-white focus:outline-none focus:border-cyan text-sm font-semibold cursor-pointer"
              >
                <option value="All">All Cities</option>
                <option value="Seattle">Seattle</option>
                <option value="Bellevue">Bellevue</option>
                <option value="Kirkland">Kirkland</option>
                <option value="Redmond">Redmond</option>
                <option value="Renton">Renton</option>
              </select>
            </div>

            {/* Status Dropdown */}
            <div className="md:col-span-3">
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="w-full bg-slate-50 dark:bg-navy-950 border border-slate-300 dark:border-navy-700 rounded-xl px-4 py-3.5 text-slate-900 dark:text-white focus:outline-none focus:border-cyan text-sm font-semibold cursor-pointer"
              >
                <option value="All">All Statuses</option>
                <option value="Active">Active</option>
                <option value="Pending">Pending</option>
                <option value="Sold">Sold</option>
              </select>
            </div>

          </div>
        </div>

        {/* Property Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {filteredProperties.map(property => (
            <div 
              key={property.id}
              className="bg-white dark:bg-navy-900 rounded-3xl overflow-hidden border border-slate-200 dark:border-navy-700 hover:border-cyan/50 dark:hover:border-cyan/50 transition-all duration-300 shadow-xl shadow-slate-200/60 dark:shadow-2xl hover:-translate-y-1 flex flex-col group"
            >
              {/* Image & Badges */}
              <div className="relative h-64 overflow-hidden">
                <img 
                  src={property.image} 
                  alt={property.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                />
                
                {/* Status Badge */}
                <div className="absolute top-4 left-4">
                  <span className={`px-3.5 py-1 rounded-full text-xs font-extrabold shadow-lg uppercase tracking-wider ${
                    property.status === 'Active' ? 'bg-emerald-500 text-navy-950' :
                    property.status === 'Pending' ? 'bg-amber-400 text-navy-950' : 'bg-slate-700 text-white'
                  }`}>
                    {property.status}
                  </span>
                </div>

                {/* Price Overlay */}
                <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between">
                  <div className="bg-slate-950/85 dark:bg-navy-950/85 backdrop-blur-md px-4 py-1.5 rounded-xl border border-cyan/40 text-white font-serif font-extrabold text-xl">
                    ${property.price.toLocaleString()}
                  </div>
                  <div className="bg-slate-950/80 dark:bg-navy-950/80 backdrop-blur-md px-2.5 py-1 rounded-lg text-[10px] text-slate-300 font-mono">
                    {property.mlsId}
                  </div>
                </div>
              </div>

              {/* Card Content */}
              <div className="p-6 flex-1 flex flex-col justify-between space-y-4">
                <div>
                  <h3 className="text-xl font-serif font-bold text-slate-900 dark:text-white group-hover:text-cyan-dark dark:group-hover:text-cyan transition-colors mb-1.5">
                    {property.title}
                  </h3>
                  <p className="text-slate-500 dark:text-slate-400 text-xs flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-cyan shrink-0" />
                    <span className="truncate">{property.address}</span>
                  </p>
                </div>

                {/* Property Specs */}
                <div className="grid grid-cols-3 gap-2 py-3 px-3 rounded-2xl bg-slate-100 dark:bg-navy-950 border border-slate-200 dark:border-navy-800 text-center text-slate-700 dark:text-slate-300 text-xs font-semibold">
                  <div className="flex flex-col items-center">
                    <span className="text-cyan-dark dark:text-cyan font-extrabold flex items-center gap-1">
                      <Bed className="w-3.5 h-3.5" /> {property.beds}
                    </span>
                    <span className="text-[10px] text-slate-400">Bedrooms</span>
                  </div>
                  <div className="flex flex-col items-center border-x border-slate-200 dark:border-navy-800">
                    <span className="text-cyan-dark dark:text-cyan font-extrabold flex items-center gap-1">
                      <Bath className="w-3.5 h-3.5" /> {property.baths}
                    </span>
                    <span className="text-[10px] text-slate-400">Bathrooms</span>
                  </div>
                  <div className="flex flex-col items-center">
                    <span className="text-cyan-dark dark:text-cyan font-extrabold flex items-center gap-1">
                      <Square className="w-3.5 h-3.5" /> {property.sqft.toLocaleString()}
                    </span>
                    <span className="text-[10px] text-slate-400">Sq Ft</span>
                  </div>
                </div>

                {/* CTA */}
                <a
                  href="#contact"
                  className="w-full inline-flex items-center justify-center gap-2 bg-slate-900 dark:bg-navy-800 hover:bg-cyan-dark dark:hover:bg-cyan text-white dark:text-slate-200 hover:text-white dark:hover:text-navy-950 font-bold py-3 rounded-xl transition-all text-xs shadow-md"
                >
                  <span>Schedule Private Showing</span>
                  <ArrowUpRight className="w-4 h-4" />
                </a>
              </div>
            </div>
          ))}
        </div>

        {/* NWMLS Notice */}
        <div className="mt-12 p-4 rounded-2xl bg-white dark:bg-navy-900 border border-slate-200 dark:border-navy-700 text-center text-xs text-slate-500 dark:text-slate-400 max-w-2xl mx-auto flex items-center justify-center gap-2 shadow-sm">
          <CheckCircle className="w-4 h-4 text-cyan shrink-0" />
          <span>Listing data schema prepared for NWMLS RESO API synchronization. Want to tour any home in Seattle or list your property? Call Loki at (801) 860-1052.</span>
        </div>

      </div>
    </section>
  );
}