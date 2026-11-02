
import React from 'react';

export default function Hero() {
  return (
    <section className="relative pt-20 pb-28 lg:pt-32 lg:pb-40 bg-ivory dark:bg-charcoal overflow-hidden border-b border-silver/30 dark:border-silver/10 transition-colors duration-300">
      
      {/* Background Image / Overlay */}
      <div className="absolute inset-0 z-0">
        <img 
          src="https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=2000&q=80" 
          alt="Luxury Architecture"
          className="w-full h-full object-cover opacity-60 dark:opacity-[0.50] grayscale"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent to-ivory dark:to-charcoal"></div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
        
        <span className="inline-block py-1 px-3 rounded border border-charcoal/20 dark:border-silver/20 text-[10px] uppercase tracking-[0.2em] font-semibold text-charcoal-light dark:text-silver-dark mb-6">
          Greater Seattle Specialists
        </span>

        <h1 className="text-4xl md:text-5xl lg:text-6xl font-serif font-bold text-charcoal dark:text-silver leading-tight mb-6">
          Dedicated, Personalized <br/>
          <span className="italic font-light">Real Estate Service.</span>
        </h1>
        
        <p className="max-w-3xl mx-auto text-base md:text-lg text-charcoal-light dark:text-silver-dark font-sans leading-relaxed mb-12">
          As your dedicated real estate agent, I act as your strategic enabler. By deeply understanding the market, I ensure you have the insight needed to make the right decisions while fiercely protecting your best interests every step of the way.
        </p>

      </div>
    </section>
  );
}
