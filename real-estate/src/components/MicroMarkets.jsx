
import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function MicroMarkets() {
  const markets = [
    {
      name: 'Eastside Tech Core',
      tag: 'High-Basis Innovation Corridor',
      cities: 'Bellevue, Kirkland, Redmond, Sammamish, Issaquah, Woodinville',
      data: { target: '$1.4M+', dom: '10 Days' },
      image: '/hero_eastside.jpg',
      link: '/markets/eastside-core'
    },
    {
      name: 'Seattle Urban Core',
      tag: 'Transit, Density & Split-Asset',
      cities: 'Seattle, Shoreline, Lake Forest Park',
      data: { target: '$880K+', dom: '14 Days' },
      image: '/hero_seattle.jpg',
      link: '/markets/seattle-core'
    },
    {
      name: 'North Sound Corridor',
      tag: 'Sprawl & Norming Absorption',
      cities: 'Lynnwood, Edmonds, Bothell, Everett, Marysville',
      data: { target: '$740K+', dom: '18 Days' },
      image: '/hero_north.jpg',
      link: '/markets/north-sound'
    },
    {
      name: 'South Sound Hub',
      tag: 'JBLM Defense & Value Baseline',
      cities: 'Kent, Renton, Auburn, Tacoma, Gig Harbor, Puyallup',
      data: { target: '$560K+', dom: '20 Days' },
      image: '/hero_south.jpg',
      link: '/markets/south-sound'
    },
    {
      name: 'Capital & Exurban Fringe',
      tag: 'State Govt & Space Value',
      cities: 'Olympia, Lacey, Tumwater, Yelm',
      data: { target: '$510K+', dom: '22 Days' },
      image: '/hero_thurston.jpg',
      link: '/markets/thurston-belt'
    }
  ];

  return (
    <section id="markets" className="py-24 bg-white dark:bg-charcoal-dark border-b border-silver/20 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-8">
          <div className="max-w-2xl">
            <span className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-4 block">Market Analytics</span>
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-serif font-bold text-charcoal dark:text-silver leading-tight">
              Strategic Micro-Markets
            </h2>
          </div>
          <p className="text-charcoal-light dark:text-silver-dark text-sm max-w-sm">
            Evaluating distinct sectors of the Greater Seattle region. *Data sourced from recent NWMLS/Redfin aggregations.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {markets.map((market) => (
            <Link to={market.link} key={market.name} className="group block relative border border-silver/30 dark:border-silver/10 hover:border-charcoal dark:hover:border-silver transition-all duration-300 bg-ivory dark:bg-charcoal overflow-hidden flex flex-col">
              
              <div className="h-48 w-full overflow-hidden relative">
                <img src={market.image} alt={market.name} className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110 opacity-90 group-hover:opacity-100" />
                <div className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-charcoal/90 to-transparent p-4">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-silver-dark">{market.tag}</p>
                </div>
              </div>

              <div className="p-6 flex-1 flex flex-col">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="font-serif font-bold text-xl text-charcoal dark:text-silver pr-4">{market.name}</h3>
                  <ArrowUpRight className="w-5 h-5 text-silver-dark group-hover:text-charcoal dark:group-hover:text-silver transition-colors shrink-0" />
                </div>
                
                <p className="text-xs text-charcoal-light dark:text-silver-dark mb-8 flex-1 italic">
                  Primary Cities: {market.cities}
                </p>

                <div className="pt-6 border-t border-silver/20 flex justify-between items-center mt-auto">
                  <div>
                    <p className="text-[9px] uppercase tracking-widest text-silver-dark mb-1">Avg Target</p>
                    <p className="font-serif font-bold text-lg text-charcoal dark:text-silver">{market.data.target}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[9px] uppercase tracking-widest text-silver-dark mb-1">Avg DOM</p>
                    <p className="font-serif font-bold text-lg text-charcoal dark:text-silver">{market.data.dom}</p>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>

      </div>
    </section>
  );
}
