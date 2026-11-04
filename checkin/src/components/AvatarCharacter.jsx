import React from 'react';

/**
 * AvatarCharacter renders an expressive, animated vector avatar
 * with unique facial features, hairstyles, skin tones, accessories,
 * and dynamic animations (blinking, breathing, typing, holding coffee).
 */
export default function AvatarCharacter({
  agentId = 'manager',
  state = 'idle', // 'idle' | 'active' | 'coffee' | 'chatting' | 'relaxing' | 'walking'
  size = 56, // pixel diameter
  facing = 'right', // 'left' | 'right'
  showActionProp = true,
  className = '',
}) {
  // Agent Persona Styles & Features
  const PERSONA_CONFIGS = {
    manager: {
      name: 'Marcus Vance',
      skinTone: '#E0AC82', // Olive / Warm beige
      hairColor: '#4A4A4A', // Salt & pepper dark charcoal
      hairStyle: 'slicked_beard',
      eyeColor: '#3D2314',
      shirtColor: '#1E293B', // Navy blue suit
      tieColor: '#991B1B', // Burgundy tie
      collarColor: '#FFFFFF',
      hasBeard: true,
      beardColor: '#525252',
      hasGlasses: false,
      accessories: 'watch',
    },
    it: {
      name: 'Ian Torres',
      skinTone: '#D49B72', // Tan / Hispanic
      hairColor: '#1F1F1F', // Dark textured curls
      hairStyle: 'curly_crop',
      eyeColor: '#2B1700',
      shirtColor: '#0F172A', // Dark tech hoodie
      tieColor: null,
      collarColor: '#10B981', // Emerald tech lanyard
      hasBeard: true,
      beardColor: '#262626',
      hasGlasses: true,
      glassesColor: '#854D0E', // Tortoiseshell
      accessories: 'lanyard',
    },
    auditor: {
      name: 'Audrey Chen',
      skinTone: '#FCD5B5', // East Asian light tone
      hairColor: '#171717', // Sleek jet-black bob
      hairStyle: 'sleek_bob',
      eyeColor: '#261C14',
      shirtColor: '#F5F5F4', // Cream tailored blazer
      tieColor: null,
      collarColor: '#D97706', // Gold collar accent
      hasBeard: false,
      hasGlasses: true,
      glassesColor: '#94A3B8', // Sleek silver rim
      accessories: 'pearls',
    },
    intake: {
      name: 'Miles Miller',
      skinTone: '#8D5B4C', // Deep bronze / African American
      hairColor: '#1A1A1A', // Clean fade
      hairStyle: 'fade',
      eyeColor: '#1A0C02',
      shirtColor: '#38BDF8', // Light sky-blue rolled-sleeve oxford
      tieColor: null,
      collarColor: '#FFFFFF',
      hasBeard: true,
      beardColor: '#171717',
      hasGlasses: false,
      accessories: 'headset',
    },
    finance: {
      name: 'Fiona Banks',
      skinTone: '#FFE2D1', // Fair porcelain
      hairColor: '#C25E2C', // Strawberry blonde / auburn ponytail
      hairStyle: 'ponytail',
      eyeColor: '#0F766E', // Green eyes
      shirtColor: '#047857', // Emerald green cardigan
      tieColor: null,
      collarColor: '#FFFFFF',
      hasBeard: false,
      hasGlasses: true,
      glassesColor: '#64748B', // Wire-rim glasses
      accessories: 'necklace',
    },
    marketing: {
      name: 'Maya Reyes',
      skinTone: '#C68642', // Warm honey / Latina
      hairColor: '#2A1810', // Dark wavy hair with purple accent
      hairStyle: 'wavy_streak',
      eyeColor: '#451A03',
      shirtColor: '#D97706', // Mustard artist smock
      tieColor: null,
      collarColor: '#A855F7', // Purple silk scarf
      hasBeard: false,
      hasGlasses: false,
      accessories: 'hoops',
    },
    cma: {
      name: 'Carter Hayes',
      skinTone: '#F5CCA0', // Fair / Light peach
      hairColor: '#5C3826', // Chestnut wavy hair
      hairStyle: 'chestnut_wave',
      eyeColor: '#1E3A8A', // Deep blue
      shirtColor: '#78350F', // Brown tweed blazer
      tieColor: null,
      collarColor: '#E2E8F0', // Open-collar light shirt
      hasBeard: true,
      beardColor: '#6B4226',
      hasGlasses: false,
      accessories: 'pencil',
    },
  };

  const p = PERSONA_CONFIGS[agentId] || PERSONA_CONFIGS.manager;
  const isActive = state === 'active';
  const isWalking = state === 'walking';
  const isCoffee = state === 'coffee';
  const isChatting = state === 'chatting';
  const isRelaxing = state === 'relaxing';

  return (
    <div
      className={`relative inline-flex items-center justify-center select-none ${className}`}
      style={{
        width: size,
        height: isWalking ? size * 1.15 : size,
        transform: facing === 'left' ? 'scaleX(-1)' : 'none',
        transition: 'transform 0.2s ease',
      }}
      title={`${p.name} (${state.toUpperCase()})`}
    >
      {/* SVG Animated Character Vector */}
      <svg
        viewBox={isWalking ? "0 0 100 115" : "0 0 100 100"}
        className="w-full h-full drop-shadow-md overflow-visible"
        style={{
          animation: isWalking
            ? 'walkBobbing 0.45s ease-in-out infinite'
            : isActive
            ? 'agentBob 0.6s ease-in-out infinite alternate'
            : 'agentBreathe 3s ease-in-out infinite',
        }}
      >
        <defs>
          {/* Subtle gradient for head depth */}
          <radialGradient id={`skinGrad_${agentId}`} cx="45%" cy="40%" r="60%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#000000" stopOpacity="0.1" />
          </radialGradient>

          {/* Steam glow for coffee */}
          <linearGradient id={`steamGrad_${agentId}`} x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stopColor="#CBD5E1" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
          </linearGradient>
        </defs>

        <style>{`
          @keyframes agentBreathe {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-1.2px); }
          }
          @keyframes agentBob {
            0% { transform: translateY(0) rotate(-0.5deg); }
            100% { transform: translateY(-2px) rotate(0.5deg); }
          }
          @keyframes walkBobbing {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-4px); }
          }
          @keyframes walkLegLeft {
            0% { transform: rotate(-24deg); }
            100% { transform: rotate(24deg); }
          }
          @keyframes walkLegRight {
            0% { transform: rotate(24deg); }
            100% { transform: rotate(-24deg); }
          }
          @keyframes walkArmSwing {
            0% { transform: rotate(-20deg); }
            100% { transform: rotate(20deg); }
          }
          @keyframes agentBlink {
            0%, 88%, 100% { transform: scaleY(1); }
            94% { transform: scaleY(0.1); }
          }
          @keyframes agentTypeLeft {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-4px); }
          }
          @keyframes agentTypeRight {
            0%, 100% { transform: translateY(-3px); }
            50% { transform: translateY(1px); }
          }
          @keyframes steamRise {
            0% { opacity: 0; transform: translateY(0) scaleX(1); }
            50% { opacity: 0.9; }
            100% { opacity: 0; transform: translateY(-10px) scaleX(1.4); }
          }
          @keyframes speechPulse {
            0%, 100% { transform: scale(1); opacity: 0.9; }
            50% { transform: scale(1.1); opacity: 1; }
          }
        `}</style>

        {/* Walking Legs (visible when walking) */}
        {isWalking && (
          <g id="walking_legs">
            {/* Left Leg */}
            <g style={{ transformOrigin: '38px 88px', animation: 'walkLegLeft 0.45s infinite alternate ease-in-out' }}>
              <rect x="33" y="88" width="9" height="20" rx="3" fill="#1E293B" />
              <ellipse cx="36" cy="108" rx="6.5" ry="3.5" fill="#0F172A" />
            </g>
            {/* Right Leg */}
            <g style={{ transformOrigin: '58px 88px', animation: 'walkLegRight 0.45s infinite alternate ease-in-out' }}>
              <rect x="54" y="88" width="9" height="20" rx="3" fill="#1E293B" />
              <ellipse cx="58" cy="108" rx="6.5" ry="3.5" fill="#0F172A" />
            </g>
          </g>
        )}

        {/* 1. Body / Shoulders & Torso */}
        <g id="torso">
          {/* Main Jacket / Sweater */}
          <path
            d="M 18 88 C 20 68, 32 60, 50 60 C 68 60, 80 68, 82 88 C 82 92, 18 92, 18 88 Z"
            fill={p.shirtColor}
          />

          {/* Inner Shirt Collar */}
          <polygon points="42,60 50,72 58,60" fill={p.collarColor} />

          {/* Necktie if present */}
          {p.tieColor && (
            <g id="tie">
              <polygon points="48,64 52,64 54,78 50,84 46,78" fill={p.tieColor} />
              <polygon points="47,63 53,63 51,68 49,68" fill="#7F1D1D" />
            </g>
          )}

          {/* Scarf / Lanyard if present */}
          {p.accessories === 'lanyard' && (
            <path
              d="M 40 60 L 50 78 L 60 60"
              stroke="#10B981"
              strokeWidth="2.5"
              fill="none"
              strokeLinecap="round"
            />
          )}

          {p.accessories === 'pearls' && (
            <circle cx="50" cy="65" r="2" fill="#F8FAFC" />
          )}
        </g>

        {/* 2. Neck */}
        <rect x="44" y="52" width="12" height="12" rx="3" fill={p.skinTone} />
        <rect x="44" y="52" width="12" height="12" rx="3" fill={`url(#skinGrad_${agentId})`} />

        {/* 3. Head & Face */}
        <g id="head">
          {/* Ears */}
          <circle cx="27" cy="42" r="5" fill={p.skinTone} />
          <circle cx="73" cy="42" r="5" fill={p.skinTone} />
          {p.accessories === 'hoops' && (
            <circle cx="74" cy="45" r="3" fill="none" stroke="#F59E0B" strokeWidth="1.5" />
          )}

          {/* Head Base */}
          <ellipse cx="50" cy="40" rx="23" ry="25" fill={p.skinTone} />
          <ellipse cx="50" cy="40" rx="23" ry="25" fill={`url(#skinGrad_${agentId})`} />

          {/* Beard / Stubble if present */}
          {p.hasBeard && (
            <path
              d="M 33 42 C 33 58, 42 62, 50 62 C 58 62, 67 58, 67 42 C 65 52, 57 58, 50 58 C 43 58, 35 52, 33 42 Z"
              fill={p.beardColor}
              opacity="0.9"
            />
          )}

          {/* Eyebrows */}
          <g id="eyebrows" stroke={p.hairColor} strokeWidth="2.2" strokeLinecap="round">
            <line x1="36" y1="30" x2="44" y2="30" />
            <line x1="56" y1="30" x2="64" y2="30" />
          </g>

          {/* Eyes (Blinking Animation) */}
          <g
            id="eyes"
            style={{
              transformOrigin: '50px 36px',
              animation: 'agentBlink 4s infinite',
            }}
          >
            {/* Left Eye */}
            <circle cx="40" cy="36" r="3.2" fill="#FFFFFF" />
            <circle cx="40.5" cy="36" r="2" fill={p.eyeColor} />
            <circle cx="41.2" cy="35.3" r="0.7" fill="#FFFFFF" />

            {/* Right Eye */}
            <circle cx="60" cy="36" r="3.2" fill="#FFFFFF" />
            <circle cx="59.5" cy="36" r="2" fill={p.eyeColor} />
            <circle cx="60.2" cy="35.3" r="0.7" fill="#FFFFFF" />
          </g>

          {/* Glasses if present */}
          {p.hasGlasses && (
            <g id="glasses" stroke={p.glassesColor} strokeWidth="1.8" fill="none">
              <rect x="33" y="31" width="14" height="10" rx="3" fill="#FFFFFF" fillOpacity="0.2" />
              <rect x="53" y="31" width="14" height="10" rx="3" fill="#FFFFFF" fillOpacity="0.2" />
              <line x1="47" y1="35" x2="53" y2="35" />
              <line x1="27" y1="35" x2="33" y2="35" />
              <line x1="67" y1="35" x2="73" y2="35" />
            </g>
          )}

          {/* Nose */}
          <path
            d="M 50 36 L 48.5 42 L 51.5 42"
            stroke={p.skinTone}
            strokeWidth="1.8"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity="0.8"
          />

          {/* Mouth / Smile */}
          {isActive ? (
            // Focused line
            <line x1="46" y1="48" x2="54" y2="48" stroke="#78350F" strokeWidth="1.8" strokeLinecap="round" />
          ) : isChatting ? (
            // Open chatting smile
            <path d="M 45 47 Q 50 53 55 47 Z" fill="#991B1B" />
          ) : (
            // Pleasant smile
            <path d="M 45 47 Q 50 51 55 47" stroke="#78350F" strokeWidth="1.8" fill="none" strokeLinecap="round" />
          )}

          {/* Headset for Miles */}
          {p.accessories === 'headset' && (
            <g id="headset">
              <path d="M 28 38 C 28 20, 72 20, 72 38" fill="none" stroke="#334155" strokeWidth="2.5" />
              <rect x="25" y="36" width="4" height="10" rx="2" fill="#0F172A" />
              <path d="M 27 46 Q 32 52 42 50" fill="none" stroke="#334155" strokeWidth="1.8" />
              <circle cx="43" cy="50" r="2" fill="#EF4444" />
            </g>
          )}

          {/* Pencil behind ear for Carter */}
          {p.accessories === 'pencil' && (
            <line x1="71" y1="28" x2="79" y2="40" stroke="#F59E0B" strokeWidth="2.5" strokeLinecap="round" />
          )}

          {/* 4. Hair Styles */}
          <g id="hair">
            {p.hairStyle === 'slicked_beard' && (
              <path
                d="M 27 34 C 27 16, 50 14, 73 18 C 73 18, 72 28, 69 31 C 65 24, 38 24, 27 34 Z"
                fill={p.hairColor}
              />
            )}

            {p.hairStyle === 'curly_crop' && (
              <path
                d="M 26 32 C 24 16, 40 12, 50 13 C 60 12, 76 16, 74 32 C 70 20, 30 20, 26 32 Z"
                fill={p.hairColor}
              />
            )}

            {p.hairStyle === 'sleek_bob' && (
              <path
                d="M 25 38 C 24 18, 48 14, 75 18 C 77 38, 73 48, 71 50 C 70 32, 68 24, 50 24 C 32 24, 29 32, 27 50 Z"
                fill={p.hairColor}
              />
            )}

            {p.hairStyle === 'fade' && (
              <path
                d="M 28 32 C 28 17, 48 15, 72 17 C 72 26, 68 28, 50 28 C 34 28, 28 26, 28 32 Z"
                fill={p.hairColor}
              />
            )}

            {p.hairStyle === 'ponytail' && (
              <g>
                <path
                  d="M 26 34 C 26 16, 50 14, 74 18 C 72 28, 68 28, 50 26 C 32 26, 28 28, 26 34 Z"
                  fill={p.hairColor}
                />
                {/* Ponytail arch on right */}
                <path d="M 70 24 C 84 20, 88 34, 84 46 C 81 44, 76 34, 72 28 Z" fill={p.hairColor} />
              </g>
            )}

            {p.hairStyle === 'wavy_streak' && (
              <g>
                <path
                  d="M 24 38 C 24 16, 48 14, 76 18 C 76 34, 72 44, 70 46 C 68 30, 68 24, 50 24 C 32 24, 30 30, 27 46 Z"
                  fill={p.hairColor}
                />
                {/* Purple streak highlight */}
                <path d="M 33 22 Q 35 32 30 42" stroke="#A855F7" strokeWidth="2.5" fill="none" strokeLinecap="round" />
              </g>
            )}

            {p.hairStyle === 'chestnut_wave' && (
              <path
                d="M 26 34 C 25 15, 48 14, 74 16 C 72 26, 66 26, 50 25 C 34 25, 29 26, 26 34 Z"
                fill={p.hairColor}
              />
            )}
          </g>
        </g>

        {/* 5. Interactive Action Props (Hands, Typing, Coffee Mug, Clipboard) */}
        {showActionProp && (
          <g id="action_props">
            {/* Active Typing Hands Animation */}
            {isActive && (
              <g id="typing_hands">
                {/* Keyboard silhouette */}
                <rect x="25" y="85" width="50" height="12" rx="2" fill="#334155" />
                {/* Left Hand */}
                <circle
                  cx="35"
                  cy="82"
                  r="4"
                  fill={p.skinTone}
                  style={{ animation: 'agentTypeLeft 0.3s infinite alternate' }}
                />
                {/* Right Hand */}
                <circle
                  cx="65"
                  cy="82"
                  r="4"
                  fill={p.skinTone}
                  style={{ animation: 'agentTypeRight 0.3s infinite alternate' }}
                />
              </g>
            )}

            {/* Coffee Mug & Rising Steam */}
            {isCoffee && (
              <g id="coffee_prop" transform="translate(62, 60)">
                {/* Mug Body */}
                <rect x="0" y="8" width="14" height="16" rx="3" fill="#FFFFFF" stroke="#E2E8F0" strokeWidth="1" />
                <path d="M 14 11 C 18 11, 18 19, 14 19" fill="none" stroke="#FFFFFF" strokeWidth="2" />
                <rect x="2" y="9" width="10" height="2" fill="#78350F" />
                {/* Hand holding mug */}
                <circle cx="-2" cy="16" r="4.5" fill={p.skinTone} />
                {/* Animated Steam Clouds */}
                <path
                  d="M 4 5 Q 7 0 4 -5"
                  stroke={`url(#steamGrad_${agentId})`}
                  strokeWidth="2"
                  fill="none"
                  strokeLinecap="round"
                  style={{ animation: 'steamRise 2s infinite ease-out' }}
                />
                <path
                  d="M 9 6 Q 12 1 9 -4"
                  stroke={`url(#steamGrad_${agentId})`}
                  strokeWidth="2"
                  fill="none"
                  strokeLinecap="round"
                  style={{ animation: 'steamRise 2s infinite ease-out 0.8s' }}
                />
              </g>
            )}

            {/* Walking Arm / Folder Prop */}
            {isWalking && (
              <g id="walking_prop" transform="translate(64, 62)">
                <g style={{ transformOrigin: '0px 0px', animation: 'walkArmSwing 0.45s infinite alternate ease-in-out' }}>
                  <rect x="2" y="6" width="14" height="18" rx="2" fill="#D97706" stroke="#92400E" strokeWidth="1" />
                  <line x1="5" y1="11" x2="13" y2="11" stroke="#FFFFFF" strokeWidth="1.5" />
                  <line x1="5" y1="15" x2="11" y2="15" stroke="#FFFFFF" strokeWidth="1" />
                  <circle cx="1" cy="14" r="4" fill={p.skinTone} />
                </g>
              </g>
            )}

            {/* Chatting Speech Bubble Icon */}
            {isChatting && (
              <g
                id="speech_bubble"
                transform="translate(68, 8)"
                style={{ animation: 'speechPulse 2s infinite ease-in-out' }}
              >
                <rect x="0" y="0" width="24" height="16" rx="6" fill="#3B82F6" />
                <polygon points="4,16 10,16 6,21" fill="#3B82F6" />
                <circle cx="6" cy="8" r="1.5" fill="#FFFFFF" />
                <circle cx="12" cy="8" r="1.5" fill="#FFFFFF" />
                <circle cx="18" cy="8" r="1.5" fill="#FFFFFF" />
              </g>
            )}
          </g>
        )}
      </svg>

      {/* Active Work Pulse Badge Indicator */}
      {isActive && (
        <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-amber-500 border-2 border-white dark:border-charcoal-dark" />
        </span>
      )}

      {/* Relaxing / Break indicator */}
      {(isCoffee || isRelaxing) && (
        <span className="absolute -bottom-1 -right-1 bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 rounded-full p-0.5 border border-amber-300 dark:border-amber-800 shadow-xs text-[10px] flex items-center justify-center">
          ☕
        </span>
      )}
    </div>
  );
}
