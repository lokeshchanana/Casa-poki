import React from 'react';
import { ExternalLink } from 'lucide-react';

export function ZillowIcon({ className = "w-5 h-5" }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
      <path d="M11.66 1.76L0 11.7h3.9v10.54h16.2V11.7H24L11.66 1.76zm4.77 17.06h-9.1v-2.32l6.23-5.23H7.55V9.11h8.88v2.32L10.2 16.66h6.23v2.16z" />
    </svg>
  );
}

export function FacebookIcon({ className = "w-5 h-5" }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
    </svg>
  );
}

export function InstagramIcon({ className = "w-5 h-5" }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
      <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
      <line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />
    </svg>
  );
}

export function GoogleIcon({ className = "w-5 h-5" }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
      <path d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.053 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z" />
    </svg>
  );
}

export const SOCIAL_PROFILES = [
  {
    name: 'Zillow',
    label: 'Zillow Profile & Reviews',
    shortLabel: 'Zillow',
    handle: 'Lokeshchanana_re',
    url: 'https://www.zillow.com/profile/Lokeshchanana_re',
    Icon: ZillowIcon,
    hoverText: 'hover:text-[#006AFF]',
    hoverBg: 'hover:bg-[#006AFF]/10',
    hoverBorder: 'hover:border-[#006AFF]/50',
  },
  {
    name: 'Google',
    label: 'Google Reviews & Profile',
    shortLabel: 'Google',
    handle: 'Lokesh Chanana (Loki)',
    url: 'https://share.google/4Ha7jttZI6W7AeiSP',
    Icon: GoogleIcon,
    hoverText: 'hover:text-[#4285F4]',
    hoverBg: 'hover:bg-[#4285F4]/10',
    hoverBorder: 'hover:border-[#4285F4]/50',
  },
  {
    name: 'Instagram',
    label: 'Instagram',
    shortLabel: 'Instagram',
    handle: '@lokeshchanana_re',
    url: 'https://www.instagram.com/lokeshchanana_re',
    Icon: InstagramIcon,
    hoverText: 'hover:text-[#E4405F]',
    hoverBg: 'hover:bg-[#E4405F]/10',
    hoverBorder: 'hover:border-[#E4405F]/50',
  },
  {
    name: 'Facebook',
    label: 'Facebook',
    shortLabel: 'Facebook',
    handle: 'Lokesh Chanana',
    url: 'https://www.facebook.com/share/19qyi21cjW/',
    Icon: FacebookIcon,
    hoverText: 'hover:text-[#1877F2]',
    hoverBg: 'hover:bg-[#1877F2]/10',
    hoverBorder: 'hover:border-[#1877F2]/50',
  },
];

/**
 * Clean icon button row for footers, headers, cards
 */
export function SocialIconRow({ size = 'md', className = '' }) {
  const sizeClasses = {
    sm: 'p-1.5 text-xs',
    md: 'p-2 text-sm',
    lg: 'p-3 text-base',
  }[size] || 'p-2';

  const iconSizes = {
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  }[size] || 'w-4 h-4';

  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      {SOCIAL_PROFILES.map((profile) => {
        const IconComponent = profile.Icon;
        return (
          <a
            key={profile.name}
            href={profile.url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`${profile.name} - ${profile.label}`}
            title={`${profile.name}: ${profile.handle}`}
            className={`border border-silver/40 dark:border-silver/20 rounded-md text-charcoal-light dark:text-silver-dark transition-all duration-200 ${sizeClasses} ${profile.hoverText} ${profile.hoverBg} ${profile.hoverBorder}`}
          >
            <IconComponent className={iconSizes} />
          </a>
        );
      })}
    </div>
  );
}

/**
 * Rich list cards with handles and external link indicators
 */
export function SocialCardsGrid({ className = '' }) {
  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 gap-3 ${className}`}>
      {SOCIAL_PROFILES.map((profile) => {
        const IconComponent = profile.Icon;
        return (
          <a
            key={profile.name}
            href={profile.url}
            target="_blank"
            rel="noopener noreferrer"
            className={`group p-3 border border-silver/30 dark:border-silver/15 bg-white/70 dark:bg-charcoal/70 rounded-md flex items-center justify-between transition-all duration-200 hover:shadow-md ${profile.hoverBorder} ${profile.hoverBg}`}
          >
            <div className="flex items-center gap-3 min-w-0">
              <div className={`p-2 rounded bg-silver/10 text-charcoal dark:text-silver transition-colors ${profile.hoverText}`}>
                <IconComponent className="w-4 h-4 shrink-0" />
              </div>
              <div className="min-w-0 text-left">
                <p className="text-[10px] uppercase tracking-widest font-bold text-silver-dark group-hover:text-charcoal dark:group-hover:text-silver transition-colors">
                  {profile.name}
                </p>
                <p className="text-xs font-semibold text-charcoal dark:text-silver truncate">
                  {profile.handle}
                </p>
              </div>
            </div>
            <ExternalLink className="w-3.5 h-3.5 text-silver-dark group-hover:text-charcoal dark:group-hover:text-silver shrink-0 ml-2 transition-colors opacity-70 group-hover:opacity-100" />
          </a>
        );
      })}
    </div>
  );
}
