import React from 'react';

interface BreachMeterProps {
  hp: number;
  compact?: boolean;
}

export const BreachMeter: React.FC<BreachMeterProps> = ({ hp, compact = false }) => {
  const activeBlocks = Math.ceil(Math.max(0, Math.min(100, hp)) / 10);

  let blockColor = '#2de370';
  let topHighlight = '#7df5a8';
  let bottomShade = '#157a3b';
  let statusText = 'GÜVENLİ';
  let badgeColor = '#2de370';

  if (hp <= 0) {
    blockColor = '#ff3864';
    topHighlight = '#ff87a2';
    bottomShade = '#991636';
    statusText = 'BREACHED';
    badgeColor = '#ff3864';
  } else if (hp <= 30) {
    blockColor = '#ff3864';
    topHighlight = '#ff87a2';
    bottomShade = '#991636';
    statusText = 'KRİTİK İHLAL';
    badgeColor = '#ff3864';
  } else if (hp <= 60) {
    blockColor = '#ffb84d';
    topHighlight = '#ffda99';
    bottomShade = '#9c6314';
    statusText = 'RİSK ALTINDA';
    badgeColor = '#ffb84d';
  }

  return (
    <div>
      <div
        className={
          compact
            ? 'flex flex-col items-start gap-1.5 mb-2'
            : 'flex items-center justify-between gap-2 mb-2'
        }
      >
        <span
          className="pixel-badge whitespace-nowrap"
          style={{
            backgroundColor: badgeColor,
            color: hp <= 30 ? '#e6ecff' : '#070912',
            borderColor: bottomShade,
          }}
        >
          {statusText}
        </span>
        <span
          className={`font-display-ascii whitespace-nowrap ${compact ? 'text-[11px]' : 'text-[14px]'}`}
          style={{ color: badgeColor, whiteSpace: 'nowrap' }}
        >
          {`${hp} / 100 HP`}
        </span>
      </div>

      <div
        className="grid grid-cols-10 gap-1.5 bg-[#0c0f1d] p-2 border-4"
        style={{
          borderColor: hp <= 30 ? '#ff3864' : '#4b588a',
          boxShadow: 'inset 2px 2px 0px #070912, 3px 3px 0px #070912',
        }}
        role="progressbar"
        aria-valuenow={hp}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        {Array.from({ length: 10 }).map((_, idx) => {
          const isActive = idx < activeBlocks;
          return (
            <div
              key={idx}
              style={{
                height: compact ? '18px' : '28px',
                border: '2px solid #070912',
                backgroundColor: isActive ? blockColor : '#171c33',
                boxShadow: isActive
                  ? `inset 0 3px 0 ${topHighlight}, inset 0 -3px 0 ${bottomShade}`
                  : 'inset 0 3px 0 rgba(7, 9, 18, 0.5)',
              }}
            />
          );
        })}
      </div>
    </div>
  );
};
