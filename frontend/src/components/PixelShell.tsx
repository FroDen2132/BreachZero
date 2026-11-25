import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

interface PixelShellProps {
  subtitle: string;
  children: React.ReactNode;
  shake?: boolean;
}

export const PixelShell: React.FC<PixelShellProps> = ({ subtitle, children, shake = false }) => {
  const [scanlinesOn, setScanlinesOn] = useState(false);
  const location = useLocation();

  useEffect(() => {
    if (scanlinesOn) {
      document.body.classList.remove('scanlines-off');
    } else {
      document.body.classList.add('scanlines-off');
    }
  }, [scanlinesOn]);

  const navItems = [
    { path: '/', label: 'GİRİŞ' },
    { path: '/play', label: '/PLAY' },
    { path: '/host', label: '/HOST' },
    { path: '/admin', label: '/ADMIN' },
  ];

  return (
    <>
      <div className="crt-scanlines" aria-hidden="true" />
      <div className={`max-w-[1340px] mx-auto px-4 py-5 ${shake ? 'is-shaking' : ''}`}>
        <header className="pixel-panel mb-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="avatar-box">
              <img src="/sprites/alarm-siren.png" alt="BreachZero" className="pixel-sprite" />
            </div>
            <div>
              <h1
                className="font-display-ascii m-0 text-[20px] sm:text-[24px] tracking-wide text-[#e6ecff]"
                style={{ textShadow: '4px 4px 0px #070912' }}
              >
                BREACH<span className="text-[#38d9ff]">ZERO</span>
              </h1>
              <p className="m-0 mt-1 text-[15px] text-[#b2bfe8]">{subtitle}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {navItems.map((item) => {
              const active = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`px-btn no-underline ${active ? 'px-btn-amber' : ''}`}
                >
                  {item.label}
                </Link>
              );
            })}
            <button
              type="button"
              onClick={() => setScanlinesOn((prev) => !prev)}
              className="px-btn px-btn-cyan"
              aria-pressed={scanlinesOn}
            >
              {scanlinesOn ? 'CRT SCANLINE: AÇIK' : 'CRT SCANLINE: KAPALI'}
            </button>
          </div>
        </header>

        {children}
      </div>
    </>
  );
};
