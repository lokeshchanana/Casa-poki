
import React from 'react';
import { Link } from 'react-router-dom';
import { Home, Briefcase, TrendingUp, Building2 } from 'lucide-react';

export default function Resources() {
  const resources = [
    {
      title: 'Buyer Services',
      description: 'Strategic guidance on acquiring residential real estate in Greater Seattle, from off-market networking to offer engineering.',
      icon: <Home className="w-5 h-5" />,
      link: '/buyers',
      image: 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=800&q=80'
    },
    {
      title: 'Seller Services',
      description: 'Data-driven pricing, asset preparation, and omnichannel digital marketing designed to maximize your return.',
      icon: <Briefcase className="w-5 h-5" />,
      link: '/sellers',
      image: 'https://images.unsplash.com/photo-1582407947304-fd86f028f716?auto=format&fit=crop&w=800&q=80'
    },
    {
      title: 'Investment Analysis',
      description: 'Calculating ARV, Cap Rates, and evaluating capital expenditures for multi-family, flips, and portfolios.',
      icon: <TrendingUp className="w-5 h-5" />,
      link: '/investors',
      image: 'https://images.unsplash.com/photo-1460472178825-e5240623afd5?auto=format&fit=crop&w=800&q=80'
    },
    {
      title: 'Commercial Real Estate',
      description: 'Expertise in navigating the complexities of commercial acquisitions, zoning, feasibility, and 1031 exchanges.',
      icon: <Building2 className="w-5 h-5" />,
      link: '/commercial',
      image: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&q=80'
    }
  ];

  return (
    <section id="resources" className="py-24 bg-white dark:bg-charcoal-dark border-b border-silver/20 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        <div className="text-center mb-20 max-w-3xl mx-auto">
          <h2 className="text-3xl md:text-5xl font-serif font-bold text-charcoal dark:text-silver mb-6">Client Resources</h2>
          <p className="text-charcoal-light dark:text-silver-dark font-sans text-lg">
            Targeted solutions built on analytical rigor. Choose your path below.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-12 max-w-5xl mx-auto">
          {resources.map((resource) => (
            <div key={resource.title} className="bg-ivory dark:bg-charcoal border border-silver/30 dark:border-silver/20 overflow-hidden flex flex-col group hover:border-charcoal dark:hover:border-silver transition-colors shadow-lg">
              <div className="h-48 w-full overflow-hidden relative">
                <img src={resource.image} alt={resource.title} className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" />
                <div className="absolute top-4 left-4 p-3 bg-white/90 dark:bg-charcoal-dark/90 backdrop-blur-sm border border-silver/20 text-charcoal dark:text-silver shadow-md">
                  {resource.icon}
                </div>
              </div>
              
              <div className="p-8 flex-1 flex flex-col">
                <h3 className="text-xl font-serif font-bold text-charcoal dark:text-silver mb-4 tracking-wide">{resource.title}</h3>
                <p className="text-charcoal-light dark:text-silver-dark font-sans text-sm leading-relaxed mb-8 flex-1">
                  {resource.description}
                </p>
                
                <Link to={resource.link} className="mt-auto block text-center w-full bg-transparent border border-charcoal dark:border-silver text-charcoal dark:text-silver hover:bg-charcoal hover:text-ivory dark:hover:bg-silver dark:hover:text-charcoal py-3 text-xs uppercase font-bold tracking-widest transition-colors">
                  View Guide
                </Link>
              </div>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
}
