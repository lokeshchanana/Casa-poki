import React from 'react';
import { SEO_ROUTES } from '../data/seoRoutes';

export default function FAQSection({ routePath, heading = 'Frequently Asked Questions', subheading = 'Direct answers for buyers, sellers, and investors in Greater Seattle.' }) {
  const route = SEO_ROUTES[routePath];
  const faqs = route?.faqs || [];

  if (!faqs.length) return null;

  return (
    <section className="py-20 bg-white dark:bg-charcoal-dark border-t border-b border-silver/20 transition-colors duration-300">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-12 text-center md:text-left">
          <span className="text-[10px] uppercase tracking-widest text-silver-dark font-bold mb-3 block">
            Market Intelligence & Q&A
          </span>
          <h2 className="text-3xl md:text-4xl font-serif font-bold text-charcoal dark:text-silver">
            {heading}
          </h2>
          {subheading && (
            <p className="text-sm text-charcoal-light dark:text-silver-dark font-sans mt-2">
              {subheading}
            </p>
          )}
        </div>

        <div className="space-y-6">
          {faqs.map((item, idx) => (
            <div
              key={idx}
              className="p-6 bg-ivory dark:bg-charcoal border border-silver/30 dark:border-silver/15 rounded-sm"
            >
              <h3 className="text-lg font-serif font-bold text-charcoal dark:text-silver mb-2">
                {item.question}
              </h3>
              <p className="text-sm font-sans text-charcoal-light dark:text-silver-dark leading-relaxed">
                {item.answer}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
