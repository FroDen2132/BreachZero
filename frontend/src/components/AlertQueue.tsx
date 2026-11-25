import React from 'react';
import type { PublicAlert } from '../contracts/types';

interface AlertQueueProps {
  alerts: PublicAlert[];
  currentPlayerId: string | null;
  selectedAlertId: string | null;
  teamBreached: boolean;
  onSelect: (alertId: string) => void;
  onClaim: (alertId: string) => void;
  onRelease: (alertId: string) => void;
}

function formatTimer(sec: number): string {
  const mm = String(Math.floor(sec / 60)).padStart(2, '0');
  const ss = String(sec % 60).padStart(2, '0');
  return `${mm}:${ss}`;
}

export const AlertQueue: React.FC<AlertQueueProps> = ({
  alerts,
  currentPlayerId,
  selectedAlertId,
  teamBreached,
  onSelect,
  onClaim,
  onRelease,
}) => {
  if (alerts.length === 0) {
    return (
      <div className="pixel-card text-[#b2bfe8]">
        Kuyrukta henüz alarm yok. Moderatörün dalga başlatmasını bekleyin.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 gap-3">
      {alerts.map((alert) => {
        const isClaimed = alert.status === 'CLAIMED';
        const isMine = isClaimed && alert.claimed_by_player_id === currentPlayerId;
        const isCriticalSla =
          (alert.status === 'UNCLAIMED' || alert.status === 'CLAIMED') &&
          alert.remaining_sla <= Math.max(20, Math.floor(alert.sla_seconds * 0.25));
        const isDone = alert.status === 'RESOLVED' || alert.status === 'EXPIRED';
        const isSelected = selectedAlertId === alert.alert_id;

        let borderColor = '#4b588a';
        if (isSelected) borderColor = '#38d9ff';
        else if (isCriticalSla) borderColor = '#ff3864';
        else if (isClaimed) borderColor = '#ffb84d';

        return (
          <article
            key={alert.alert_id}
            onClick={() => onSelect(alert.alert_id)}
            className="pixel-card cursor-pointer flex flex-col gap-3"
            style={{
              borderColor,
              backgroundColor: isCriticalSla ? '#2b1528' : isDone ? '#12172b' : '#232a4a',
              opacity: isDone ? 0.75 : 1,
            }}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="font-display-ascii text-[11px] text-[#38d9ff]">{alert.incident_code}</span>
                <span className="text-[#b2bfe8]">•</span>
                <span className="text-[15px] font-semibold text-[#b2bfe8]">{alert.severity}</span>
              </div>

              {isCriticalSla ? (
                <span className="pixel-badge bg-[#ff3864] text-[#e6ecff]">
                  <span className="pixel-led pixel-led-red" />
                  SLA CRITICAL
                </span>
              ) : isClaimed ? (
                <span className="pixel-badge bg-[#ffb84d] text-[#070912]">
                  {isMine
                    ? 'SİZDE'
                    : `CLAIMED BY ${(alert.claimed_by_nickname || '').toLocaleUpperCase('tr-TR')}`}
                </span>
              ) : alert.status === 'RESOLVED' ? (
                <span className="pixel-badge bg-[#2de370] text-[#070912]">ÇÖZÜLDÜ</span>
              ) : alert.status === 'EXPIRED' ? (
                <span className="pixel-badge bg-[#ff3864] text-[#e6ecff]">SLA DOLDU</span>
              ) : (
                <span className="pixel-badge bg-[#0c0f1d] text-[#38d9ff] border-[#38d9ff]">UNCLAIMED</span>
              )}
            </div>

            <h3 className="m-0 text-[17px] font-semibold text-[#e6ecff]">{alert.title}</h3>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t-2 border-[#070912]">
              <div className="flex items-center gap-2">
                {isClaimed && alert.claimed_by_avatar_id ? (
                  <>
                    <div className="avatar-box">
                      <img
                        src={`/sprites/${alert.claimed_by_avatar_id}.png`}
                        alt={alert.claimed_by_nickname || 'Analist'}
                      />
                    </div>
                    <div>
                      <div className="text-[15px] font-semibold text-[#ffb84d]">{alert.claimed_by_nickname}</div>
                      <div className="text-[14px] text-[#b2bfe8]">Kanıt: {alert.evidence_cards.length}</div>
                    </div>
                  </>
                ) : (
                  <div className="flex items-center gap-2">
                    {isCriticalSla && (
                      <div className="avatar-box" style={{ borderColor: '#ff3864' }}>
                        <img src="/sprites/alarm-siren.png" alt="Alarm Sireni" />
                      </div>
                    )}
                    <span className="font-display-ascii text-[14px]" style={{ color: isCriticalSla ? '#ff3864' : '#ffb84d' }}>
                      {formatTimer(alert.remaining_sla)}
                    </span>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                {isClaimed && (
                  <span className="font-display-ascii text-[12px] text-[#ffb84d]">
                    {formatTimer(alert.remaining_sla)}
                  </span>
                )}
                {alert.status === 'UNCLAIMED' && (
                  <button
                    type="button"
                    disabled={teamBreached}
                    onClick={() => onClaim(alert.alert_id)}
                    className="px-btn px-btn-cyan"
                  >
                    [CLAIM]
                  </button>
                )}
                {isMine && (
                  <button
                    type="button"
                    disabled={teamBreached}
                    onClick={() => onRelease(alert.alert_id)}
                    className="px-btn px-btn-amber"
                  >
                    [RELEASE]
                  </button>
                )}
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
};
