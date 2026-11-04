import React from 'react';

/**
 * IsometricCharacter renders a 2.5D isometric vector character
 * matching the art style in the inspiration reference image.
 * Supports multiple distinct animation modes:
 * - 'working_typing': Seated at desk, hands typing on keyboard
 * - 'working_tablet': Seated at desk, drawing on angled graphic tablet
 * - 'walking': Animated walking cycle with leg/arm swing carrying a folder/mug
 * - 'meeting_left' / 'meeting_right': Standing holding document/blueprint discussing
 * - 'pairing_stand': Standing beside a desk, pointing at the monitor
 * - 'leisure_coffee': Sitting/standing relaxing, sipping coffee with steam
 */
export default function IsometricCharacter({
  agentId = 'manager',
  animation = 'working_typing', // 'working_typing' | 'working_tablet' | 'walking' | 'meeting_left' | 'meeting_right' | 'pairing_stand' | 'leisure_coffee'
  scale = 1,
  direction = 'south_east', // isometric facing direction
  className = '',
  onClick,
}) {
  const PERSONAS = {
    manager: {
      name: 'Marcus Vance',
      role: 'General Manager',
      skinTone: '#E0AC82',
      hairColor: '#4A4A4A',
      hairType: 'short_slick',
      clothingTop: '#1E293B', // Navy blue blazer
      clothingBottom: '#334155', // Charcoal trousers
      tieColor: '#991B1B', // Burgundy tie
      collarColor: '#FFFFFF',
      hasBeard: true,
      hasGlasses: false,
    },
    it: {
      name: 'Ian Torres',
      role: 'IT Infrastructure',
      skinTone: '#D49B72',
      hairColor: '#1F1F1F',
      hairType: 'curly_crop',
      clothingTop: '#0F172A', // Dark tech hoodie
      clothingBottom: '#1E293B', // Dark jeans
      tieColor: null,
      collarColor: '#10B981', // Emerald tech lanyard
      hasBeard: true,
      hasGlasses: true,
      glassesColor: '#854D0E',
    },
    auditor: {
      name: 'Audrey Chen',
      role: 'QA & Compliance',
      skinTone: '#FCD5B5',
      hairColor: '#171717',
      hairType: 'sleek_bob',
      clothingTop: '#F5F5F4', // Cream tailored blazer
      clothingBottom: '#44403C', // Dark skirt/slacks
      tieColor: null,
      collarColor: '#D97706',
      hasBeard: false,
      hasGlasses: true,
      glassesColor: '#94A3B8',
    },
    intake: {
      name: 'Miles Miller',
      role: 'Intake & Webhooks',
      skinTone: '#8D5B4C',
      hairColor: '#1A1A1A',
      hairType: 'fade',
      clothingTop: '#38BDF8', // Sky-blue oxford shirt
      clothingBottom: '#1E293B', // Dark slacks
      tieColor: null,
      collarColor: '#FFFFFF',
      hasBeard: true,
      hasGlasses: false,
    },
    finance: {
      name: 'Fiona Banks',
      role: 'Financial Controller',
      skinTone: '#FFE2D1',
      hairColor: '#C25E2C', // Strawberry blonde ponytail
      hairType: 'ponytail',
      clothingTop: '#047857', // Emerald cardigan
      clothingBottom: '#1C1917', // Black trousers
      tieColor: null,
      collarColor: '#FFFFFF',
      hasBeard: false,
      hasGlasses: true,
      glassesColor: '#64748B',
    },
    marketing: {
      name: 'Maya Reyes',
      role: 'Creative Director',
      skinTone: '#C68642',
      hairColor: '#2A1810',
      hairType: 'wavy_streak',
      clothingTop: '#EA580C', // Rust orange smock / artist top
      clothingBottom: '#3B82F6', // Cobalt blue jeans
      tieColor: null,
      collarColor: '#A855F7', // Silk purple scarf
      hasBeard: false,
      hasGlasses: false,
    },
    cma: {
      name: 'Carter Hayes',
      role: 'Valuation & CMA',
      skinTone: '#F5CCA0',
      hairColor: '#5C3826',
      hairType: 'chestnut_wave',
      clothingTop: '#B45309', // Caramel / brown tweed jacket
      clothingBottom: '#1E293B', // Dark slacks
      tieColor: null,
      collarColor: '#F8FAFC',
      hasBeard: true,
      hasGlasses: false,
    },
  };

  const p = PERSONAS[agentId] || PERSONAS.manager;

  return (
    <div
      onClick={onClick}
      className={`relative inline-block cursor-pointer select-none transition-transform hover:scale-110 ${className}`}
      style={{
        transform: `scale(${scale})`,
        transformOrigin: 'bottom center',
      }}
      title={`${p.name} (${p.role}) - ${animation}`}
    >
      <svg
        viewBox="0 0 80 120"
        className="w-16 h-24 overflow-visible drop-shadow-md"
      >
        <defs>
          <linearGradient id={`shadow_${agentId}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#000000" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#000000" stopOpacity="0" />
          </linearGradient>
        </defs>

        <style>{`
          /* Isometric Walk Cycle */
          @keyframes isoWalkLegL {
            0%, 100% { transform: rotate(18deg); }
            50% { transform: rotate(-18deg); }
          }
          @keyframes isoWalkLegR {
            0%, 100% { transform: rotate(-18deg); }
            50% { transform: rotate(18deg); }
          }
          @keyframes isoWalkArmL {
            0%, 100% { transform: rotate(-22deg); }
            50% { transform: rotate(22deg); }
          }
          @keyframes isoWalkArmR {
            0%, 100% { transform: rotate(22deg); }
            50% { transform: rotate(-22deg); }
          }
          @keyframes isoWalkBob {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-3px); }
          }

          /* Typing Hands */
          @keyframes isoTypeL {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-3px); }
          }
          @keyframes isoTypeR {
            0%, 100% { transform: translateY(-3px); }
            50% { transform: translateY(0); }
          }

          /* Tablet Sketching */
          @keyframes isoSketch {
            0% { transform: translate(0, 0); }
            25% { transform: translate(3px, -2px); }
            50% { transform: translate(-2px, 2px); }
            75% { transform: translate(2px, 1px); }
            100% { transform: translate(0, 0); }
          }

          /* Meeting Head Gestures */
          @keyframes isoNod {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            50% { transform: translateY(-1.5px) rotate(2deg); }
          }
          @keyframes isoGesture {
            0%, 100% { transform: rotate(0deg); }
            50% { transform: rotate(8deg); }
          }

          /* Steam Rise */
          @keyframes isoSteam {
            0% { opacity: 0; transform: translateY(0) scaleX(1); }
            50% { opacity: 0.8; }
            100% { opacity: 0; transform: translateY(-8px) scaleX(1.3); }
          }

          /* Eye Blink */
          @keyframes isoBlink {
            0%, 90%, 100% { transform: scaleY(1); }
            95% { transform: scaleY(0.1); }
          }
        `}</style>

        {/* Ground Drop Shadow */}
        <ellipse cx="40" cy="114" rx="20" ry="7" fill={`url(#shadow_${agentId})`} />

        {/* =========================================================================
            STATE 1: WALKING ANIMATION (Walking across floor with leg & arm swing)
            ========================================================================= */}
        {animation === 'walking' && (
          <g style={{ animation: 'isoWalkBob 0.6s infinite ease-in-out' }}>
            {/* Left Leg */}
            <g style={{ transformOrigin: '36px 75px', animation: 'isoWalkLegL 0.6s infinite ease-in-out' }}>
              <rect x="33" y="75" width="7" height="32" rx="3.5" fill={p.clothingBottom} />
              <ellipse cx="36.5" cy="107" rx="5" ry="3.5" fill="#18181B" />
            </g>

            {/* Right Leg */}
            <g style={{ transformOrigin: '44px 75px', animation: 'isoWalkLegR 0.6s infinite ease-in-out' }}>
              <rect x="41" y="75" width="7" height="32" rx="3.5" fill={p.clothingBottom} />
              <ellipse cx="44.5" cy="107" rx="5" ry="3.5" fill="#18181B" />
            </g>

            {/* Torso */}
            <rect x="30" y="42" width="20" height="36" rx="6" fill={p.clothingTop} />
            {p.collarColor && <polygon points="37,42 40,50 43,42" fill={p.collarColor} />}
            {p.tieColor && <polygon points="39,45 41,45 42,56 40,60 38,56" fill={p.tieColor} />}

            {/* Left Arm Swinging with Clipboard/Folder */}
            <g style={{ transformOrigin: '30px 46px', animation: 'isoWalkArmL 0.6s infinite ease-in-out' }}>
              <rect x="25" y="46" width="6" height="24" rx="3" fill={p.clothingTop} />
              <circle cx="28" cy="70" r="3" fill={p.skinTone} />
              {/* Audit Folder in Hand */}
              <rect x="22" y="64" width="12" height="15" rx="1.5" fill="#F59E0B" stroke="#D97706" strokeWidth="1" transform="rotate(-15 28 70)" />
              <line x1="24" y1="68" x2="32" y2="68" stroke="#FFFFFF" strokeWidth="1" />
            </g>

            {/* Right Arm Swinging */}
            <g style={{ transformOrigin: '50px 46px', animation: 'isoWalkArmR 0.6s infinite ease-in-out' }}>
              <rect x="49" y="46" width="6" height="24" rx="3" fill={p.clothingTop} />
              <circle cx="52" cy="70" r="3" fill={p.skinTone} />
            </g>

            {/* Head */}
            <g style={{ transformOrigin: '40px 26px', animation: 'isoNod 2s infinite ease-in-out' }}>
              <ellipse cx="40" cy="28" rx="12" ry="14" fill={p.skinTone} />
              {/* Hair */}
              <ellipse cx="40" cy="22" rx="13" ry="9" fill={p.hairColor} />
              {p.hairType === 'ponytail' && (
                <path d="M 50 18 Q 62 16 58 30 Q 54 24 48 22 Z" fill={p.hairColor} />
              )}
              {p.hairType === 'wavy_streak' && (
                <path d="M 30 18 Q 32 26 28 32" stroke="#A855F7" strokeWidth="2.5" fill="none" strokeLinecap="round" />
              )}
              {p.hasBeard && (
                <path d="M 31 30 Q 40 42 49 30 Q 40 38 31 30 Z" fill={p.hairColor} opacity="0.9" />
              )}
              {/* Eyes & Glasses */}
              <g style={{ transformOrigin: '40px 26px', animation: 'isoBlink 3.5s infinite' }}>
                <circle cx="36" cy="26" r="1.5" fill="#18181B" />
                <circle cx="44" cy="26" r="1.5" fill="#18181B" />
              </g>
              {p.hasGlasses && (
                <g stroke={p.glassesColor || '#475569'} strokeWidth="1.2" fill="none">
                  <rect x="33" y="23" width="7" height="6" rx="1.5" />
                  <rect x="41" y="23" width="7" height="6" rx="1.5" />
                  <line x1="40" y1="26" x2="41" y2="26" />
                </g>
              )}
            </g>
          </g>
        )}

        {/* =========================================================================
            STATE 2: WORKING AT DESK (Typing hands on keyboard + glowing screen)
            ========================================================================= */}
        {animation === 'working_typing' && (
          <g>
            {/* Seated Office Swivel Chair Back */}
            <ellipse cx="40" cy="50" rx="18" ry="24" fill="#27272A" stroke="#18181B" strokeWidth="1.5" />
            <circle cx="40" cy="40" r="14" fill="#3F3F46" />

            {/* Torso leaning forward slightly */}
            <rect x="30" y="44" width="20" height="34" rx="6" fill={p.clothingTop} />
            {p.collarColor && <polygon points="37,44 40,52 43,44" fill={p.collarColor} />}
            {p.tieColor && <polygon points="39,47 41,47 42,58 40,62 38,58" fill={p.tieColor} />}

            {/* Seated Legs tucked under desk */}
            <rect x="33" y="74" width="6" height="20" rx="3" fill={p.clothingBottom} />
            <rect x="41" y="74" width="6" height="20" rx="3" fill={p.clothingBottom} />

            {/* Arms extending forward onto keyboard */}
            <rect x="25" y="48" width="6" height="26" rx="3" fill={p.clothingTop} transform="rotate(22 28 48)" />
            <rect x="49" y="48" width="6" height="26" rx="3" fill={p.clothingTop} transform="rotate(-22 52 48)" />

            {/* Typing Hands */}
            <circle cx="34" cy="76" r="3.5" fill={p.skinTone} style={{ animation: 'isoTypeL 0.25s infinite alternate' }} />
            <circle cx="46" cy="76" r="3.5" fill={p.skinTone} style={{ animation: 'isoTypeR 0.25s infinite alternate' }} />

            {/* Head tilted forward focused */}
            <g transform="translate(0, 2)">
              <ellipse cx="40" cy="27" rx="12" ry="14" fill={p.skinTone} />
              <ellipse cx="40" cy="21" rx="13" ry="9" fill={p.hairColor} />
              {p.hairType === 'ponytail' && (
                <path d="M 50 17 Q 62 15 58 29 Q 54 23 48 21 Z" fill={p.hairColor} />
              )}
              {p.hasBeard && (
                <path d="M 31 29 Q 40 41 49 29 Q 40 37 31 29 Z" fill={p.hairColor} opacity="0.9" />
              )}
              <g style={{ transformOrigin: '40px 25px', animation: 'isoBlink 4s infinite' }}>
                <circle cx="36" cy="25" r="1.5" fill="#18181B" />
                <circle cx="44" cy="25" r="1.5" fill="#18181B" />
              </g>
              {p.hasGlasses && (
                <g stroke={p.glassesColor || '#475569'} strokeWidth="1.2" fill="none">
                  <rect x="33" y="22" width="7" height="6" rx="1.5" />
                  <rect x="41" y="22" width="7" height="6" rx="1.5" />
                  <line x1="40" y1="25" x2="41" y2="25" />
                </g>
              )}
            </g>
          </g>
        )}

        {/* =========================================================================
            STATE 3: GRAPHIC SKETCHING (Maya at drawing tablet)
            ========================================================================= */}
        {animation === 'working_tablet' && (
          <g>
            {/* Swivel Chair Back */}
            <ellipse cx="40" cy="50" rx="18" ry="24" fill="#27272A" stroke="#18181B" strokeWidth="1.5" />
            <rect x="30" y="44" width="20" height="34" rx="6" fill={p.clothingTop} />

            {/* Drawing Tablet in front */}
            <rect x="24" y="66" width="32" height="22" rx="3" fill="#18181B" stroke="#A855F7" strokeWidth="1.5" transform="rotate(-8 40 77)" />
            <rect x="27" y="69" width="26" height="16" rx="1.5" fill="#3B82F6" opacity="0.8" transform="rotate(-8 40 77)" />

            {/* Left Hand holding tablet */}
            <circle cx="26" cy="74" r="3.5" fill={p.skinTone} />

            {/* Right Arm & Stylus Hand Sketching Animation */}
            <g style={{ animation: 'isoSketch 1.2s infinite ease-in-out' }}>
              <rect x="47" y="48" width="6" height="24" rx="3" fill={p.clothingTop} transform="rotate(-25 50 48)" />
              <circle cx="45" cy="75" r="3.5" fill={p.skinTone} />
              {/* Stylus Pen */}
              <line x1="43" y1="73" x2="40" y2="79" stroke="#E2E8F0" strokeWidth="2" strokeLinecap="round" />
            </g>

            {/* Head */}
            <g transform="translate(0, 2)">
              <ellipse cx="40" cy="27" rx="12" ry="14" fill={p.skinTone} />
              <ellipse cx="40" cy="21" rx="13" ry="9" fill={p.hairColor} />
              <path d="M 30 17 Q 32 25 28 31" stroke="#A855F7" strokeWidth="2.5" fill="none" strokeLinecap="round" />
              <g style={{ transformOrigin: '40px 25px', animation: 'isoBlink 4s infinite' }}>
                <circle cx="36" cy="25" r="1.5" fill="#18181B" />
                <circle cx="44" cy="25" r="1.5" fill="#18181B" />
              </g>
            </g>
          </g>
        )}

        {/* =========================================================================
            STATE 4: MEETING IN HALLWAY (Holding document between two people)
            ========================================================================= */}
        {(animation === 'meeting_left' || animation === 'meeting_right') && (
          <g style={{ transformOrigin: '40px 50px', animation: 'isoNod 2.5s infinite ease-in-out' }}>
            {/* Standing Legs */}
            <rect x="34" y="75" width="6" height="33" rx="3" fill={p.clothingBottom} />
            <rect x="42" y="75" width="6" height="33" rx="3" fill={p.clothingBottom} />
            <ellipse cx="37" cy="108" rx="5" ry="3" fill="#18181B" />
            <ellipse cx="45" cy="108" rx="5" ry="3" fill="#18181B" />

            {/* Torso */}
            <rect x="30" y="42" width="20" height="35" rx="6" fill={p.clothingTop} />
            {p.collarColor && <polygon points="37,42 40,50 43,42" fill={p.collarColor} />}
            {p.tieColor && <polygon points="39,45 41,45 42,56 40,60 38,56" fill={p.tieColor} />}

            {/* Arms Holding Shared Document */}
            {animation === 'meeting_left' ? (
              <g>
                {/* Arm reaching right to hold paper */}
                <rect x="46" y="46" width="6" height="22" rx="3" fill={p.clothingTop} transform="rotate(-30 49 46)" />
                <circle cx="56" cy="64" r="3.5" fill={p.skinTone} />
                {/* Paper sheet held outward */}
                <rect x="54" y="52" width="16" height="22" rx="1.5" fill="#FFFFFF" stroke="#CBD5E1" strokeWidth="1" transform="rotate(-10 62 63)" />
                <line x1="56" y1="58" x2="68" y2="58" stroke="#94A3B8" strokeWidth="1" />
                <line x1="56" y1="62" x2="66" y2="62" stroke="#94A3B8" strokeWidth="1" />
              </g>
            ) : (
              <g>
                {/* Arm reaching left to hold paper */}
                <rect x="28" y="46" width="6" height="22" rx="3" fill={p.clothingTop} transform="rotate(30 31 46)" />
                <circle cx="24" cy="64" r="3.5" fill={p.skinTone} />
                {/* Paper sheet held outward */}
                <rect x="10" y="52" width="16" height="22" rx="1.5" fill="#FFFFFF" stroke="#CBD5E1" strokeWidth="1" transform="rotate(10 18 63)" />
                <line x1="12" y1="58" x2="24" y2="58" stroke="#94A3B8" strokeWidth="1" />
                <line x1="12" y1="62" x2="22" y2="62" stroke="#94A3B8" strokeWidth="1" />
              </g>
            )}

            {/* Head */}
            <ellipse cx="40" cy="27" rx="12" ry="14" fill={p.skinTone} />
            <ellipse cx="40" cy="21" rx="13" ry="9" fill={p.hairColor} />
            {p.hasBeard && (
              <path d="M 31 29 Q 40 41 49 29 Q 40 37 31 29 Z" fill={p.hairColor} opacity="0.9" />
            )}
            <circle cx="36" cy="25" r="1.5" fill="#18181B" />
            <circle cx="44" cy="25" r="1.5" fill="#18181B" />
            {/* Open chatting mouth */}
            <ellipse cx="40" cy="33" rx="2" ry="1.5" fill="#78350F" />
          </g>
        )}

        {/* =========================================================================
            STATE 5: OVER-THE-SHOULDER PAIRING (Standing pointing at monitor)
            ========================================================================= */}
        {animation === 'pairing_stand' && (
          <g>
            <rect x="34" y="75" width="6" height="33" rx="3" fill={p.clothingBottom} />
            <rect x="42" y="75" width="6" height="33" rx="3" fill={p.clothingBottom} />
            <rect x="30" y="42" width="20" height="35" rx="6" fill={p.clothingTop} />

            {/* Pointing Arm Gesture */}
            <g style={{ transformOrigin: '48px 46px', animation: 'isoGesture 2s infinite ease-in-out' }}>
              <rect x="46" y="46" width="6" height="24" rx="3" fill={p.clothingTop} transform="rotate(-55 49 46)" />
              <circle cx="64" cy="46" r="3.5" fill={p.skinTone} />
              <line x1="64" y1="46" x2="72" y2="44" stroke={p.skinTone} strokeWidth="2" strokeLinecap="round" />
            </g>

            {/* Head leaning forward */}
            <ellipse cx="42" cy="27" rx="12" ry="14" fill={p.skinTone} />
            <ellipse cx="42" cy="21" rx="13" ry="9" fill={p.hairColor} />
            <circle cx="38" cy="25" r="1.5" fill="#18181B" />
            <circle cx="46" cy="25" r="1.5" fill="#18181B" />
          </g>
        )}

        {/* =========================================================================
            STATE 6: LEISURE COFFEE BREAK (Sitting/Standing with coffee & donuts)
            ========================================================================= */}
        {animation === 'leisure_coffee' && (
          <g>
            {/* Chair Back */}
            <ellipse cx="40" cy="54" rx="18" ry="22" fill="#27272A" stroke="#18181B" strokeWidth="1.5" />
            <rect x="30" y="46" width="20" height="34" rx="6" fill={p.clothingTop} />

            {/* Arm holding coffee mug */}
            <rect x="46" y="48" width="6" height="22" rx="3" fill={p.clothingTop} transform="rotate(-35 49 48)" />
            <circle cx="58" cy="58" r="3.5" fill={p.skinTone} />

            {/* Coffee Mug with Animated Steam */}
            <rect x="56" y="52" width="10" height="12" rx="2" fill="#FFFFFF" stroke="#E2E8F0" strokeWidth="1" />
            <path d="M 66 54 Q 69 58 66 61" stroke="#FFFFFF" strokeWidth="1.5" fill="none" />
            {/* Steam animation */}
            <path d="M 59 48 Q 61 44 59 40" stroke="#CBD5E1" strokeWidth="1.5" fill="none" strokeLinecap="round" style={{ animation: 'isoSteam 2s infinite ease-out' }} />
            <path d="M 63 49 Q 65 45 63 41" stroke="#CBD5E1" strokeWidth="1.5" fill="none" strokeLinecap="round" style={{ animation: 'isoSteam 2s infinite ease-out 0.8s' }} />

            {/* Head smiling */}
            <ellipse cx="40" cy="28" rx="12" ry="14" fill={p.skinTone} />
            <ellipse cx="40" cy="22" rx="13" ry="9" fill={p.hairColor} />
            <circle cx="36" cy="26" r="1.5" fill="#18181B" />
            <circle cx="44" cy="26" r="1.5" fill="#18181B" />
            <path d="M 37 32 Q 40 35 43 32" stroke="#78350F" strokeWidth="1.5" fill="none" strokeLinecap="round" />
          </g>
        )}
      </svg>
    </div>
  );
}
