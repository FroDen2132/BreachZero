import React from 'react';

const PNG_SPRITES = new Set([
  'tool-ip-radar',
  'tool-hash-scanner',
  'tool-cmdb-server',
  'alarm-siren',
  'analyst-ali',
  'analyst-zeynep',
  'analyst-kerem',
  'analyst-elif',
]);

interface ToolIconProps {
  iconId: string;
  alt: string;
}

export const ToolIcon: React.FC<ToolIconProps> = ({ iconId, alt }) => {
  if (PNG_SPRITES.has(iconId)) {
    return (
      <span className="enrich-icon-box">
        <img src={`/sprites/${iconId}.png`} alt={alt} className="pixel-sprite" />
      </span>
    );
  }

  // Fallback 24x24 <rect>-only crispEdges SVG for plugins without custom PNG (e.g. whois -> fallback-globe)
  if (iconId === 'fallback-globe') {
    return (
      <span className="enrich-icon-box">
        <svg viewBox="0 0 24 24" width={32} height={32} shapeRendering="crispEdges" aria-hidden="true">
          <rect x="6" y="2" width="12" height="2" fill="#38d9ff" />
          <rect x="4" y="4" width="2" height="4" fill="#38d9ff" />
          <rect x="18" y="4" width="2" height="4" fill="#38d9ff" />
          <rect x="2" y="8" width="2" height="8" fill="#38d9ff" />
          <rect x="20" y="8" width="2" height="8" fill="#38d9ff" />
          <rect x="4" y="16" width="2" height="4" fill="#38d9ff" />
          <rect x="18" y="16" width="2" height="4" fill="#38d9ff" />
          <rect x="6" y="20" width="12" height="2" fill="#38d9ff" />
          <rect x="4" y="11" width="16" height="2" fill="#38d9ff" />
          <rect x="11" y="4" width="2" height="16" fill="#38d9ff" />
          <rect x="7" y="6" width="2" height="12" fill="#b2bfe8" />
          <rect x="15" y="6" width="2" height="12" fill="#b2bfe8" />
        </svg>
      </span>
    );
  }

  return (
    <span className="enrich-icon-box">
      <svg viewBox="0 0 24 24" width={32} height={32} shapeRendering="crispEdges" aria-hidden="true">
        <rect x="2" y="4" width="20" height="2" fill="#38d9ff" />
        <rect x="2" y="6" width="2" height="12" fill="#38d9ff" />
        <rect x="20" y="6" width="2" height="12" fill="#38d9ff" />
        <rect x="2" y="18" width="20" height="2" fill="#38d9ff" />
        <rect x="6" y="9" width="2" height="2" fill="#ffb84d" />
        <rect x="8" y="11" width="2" height="2" fill="#ffb84d" />
        <rect x="6" y="13" width="2" height="2" fill="#ffb84d" />
        <rect x="12" y="13" width="6" height="2" fill="#e6ecff" />
      </svg>
    </span>
  );
};
