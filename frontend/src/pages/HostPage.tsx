import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { BreachMeter } from '../components/BreachMeter';
import { PixelShell } from '../components/PixelShell';
import { useRoomSocket } from '../hooks/useRoomSocket';

export const HostPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const urlRoom = (searchParams.get('room') || '').toUpperCase();
  const [roomInput, setRoomInput] = useState(urlRoom);

  const { connected, roomState, feedEvents, debrief, lastError, connect } = useRoomSocket();

  useEffect(() => {
    if (urlRoom) {
      connect({ roomCode: urlRoom, role: 'HOST' });
    }
  }, [urlRoom, connect]);

  const sortedTeams = useMemo(() => {
    if (!roomState) return [];
    return [...roomState.teams].sort((a, b) => b.score - a.score || b.hp - a.hp);
  }, [roomState]);

  const handleJoinHost = (e: React.FormEvent) => {
    e.preventDefault();
    if (!roomInput.trim()) return;
    connect({ roomCode: roomInput.trim().toUpperCase(), role: 'HOST' });
  };

  return (
    <PixelShell subtitle="Amfi Projektörü (/host) • Canlı Breach Meter &amp; Skor Tablosu">
      {lastError && (
        <div className="pixel-panel mb-4 border-[#ff3864] bg-[#2b1528] text-[#e6ecff]">{lastError}</div>
      )}

      {!connected || !roomState ? (
        <section className="pixel-panel max-w-xl mx-auto">
          <h2 className="m-0 mb-3 text-[20px] font-semibold">PROJEKTÖR BAĞLANTISI</h2>
          <form onSubmit={handleJoinHost} className="flex flex-wrap gap-3">
            <input
              type="text"
              value={roomInput}
              onChange={(e) => setRoomInput(e.target.value.toUpperCase())}
              placeholder="ODA KODU (ÖRN: BZ4821)"
              className="pixel-input pixel-input-code flex-1"
              required
            />
            <button type="submit" className="px-btn px-btn-amber">
              PROJEKTÖRÜ BAĞLA
            </button>
          </form>
        </section>
      ) : (
        <div className="flex flex-col gap-5">
          {/* Projector Banner */}
          <section className="bg-[#0c0f1d] border-4 border-[#38d9ff] p-4 shadow-[6px_6px_0px_#070912] flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-baseline gap-3">
              <span className="font-display-ascii text-[18px] text-[#e6ecff]">
                BREACH<span className="text-[#ffb84d]">ZERO</span> /HOST
              </span>
              <span className="text-[18px] font-semibold text-[#b2bfe8]">
                // CANLI WAR ROOM PROJEKTÖRÜ
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div className="bg-[#171c33] border-3 border-[#ffb84d] px-4 py-2">
                <span className="text-[14px] text-[#b2bfe8] mr-2">ODA KODU:</span>
                <span className="font-display-ascii text-[20px] text-[#ffb84d]">
                  {roomState.room_code}
                </span>
              </div>
              <span className="pixel-badge bg-[#171c33] text-[#38d9ff] border-[#38d9ff]">
                DALGA {roomState.current_wave} / {roomState.total_waves}
              </span>
              <span
                className="pixel-badge"
                style={{
                  backgroundColor:
                    roomState.status === 'ACTIVE'
                      ? '#2de370'
                      : roomState.status === 'PAUSED'
                        ? '#ffb84d'
                        : roomState.status === 'LOBBY'
                          ? '#38d9ff'
                          : '#ff3864',
                  color: roomState.status === 'ENDED' ? '#e6ecff' : '#070912',
                }}
              >
                {roomState.status}
              </span>
            </div>
          </section>

          {/* Team Scoreboard & Side-by-Side Breach Meters */}
          <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {sortedTeams.map((team, idx) => (
              <article
                key={team.team_id}
                className="pixel-panel flex flex-col gap-4"
                style={{
                  borderColor: idx === 0 && !team.is_breached ? '#2de370' : team.is_breached ? '#ff3864' : '#4b588a',
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <h3 className="m-0 text-[20px] font-semibold text-[#e6ecff]">{team.name}</h3>
                  <span className="font-display-ascii text-[14px] bg-[#0c0f1d] border-2 border-[#ffb84d] text-[#ffb84d] px-2 py-1">
                    #{idx + 1}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-[#0c0f1d] border-2 border-[#070912] p-2">
                    <div className="text-[14px] text-[#b2bfe8]">PUAN</div>
                    <div className="font-display-ascii text-[16px] text-[#38d9ff] mt-1">{team.score}</div>
                  </div>
                  <div className="bg-[#0c0f1d] border-2 border-[#070912] p-2">
                    <div className="text-[14px] text-[#b2bfe8]">ÇÖZÜLEN / SERİ</div>
                    <div className="font-display-ascii text-[14px] text-[#ffb84d] mt-1">
                      {team.resolved_count} / {team.streak}
                    </div>
                  </div>
                </div>

                <BreachMeter hp={team.hp} compact />
              </article>
            ))}
          </section>

          {/* Live Dramatic Event Feed */}
          <section className="pixel-panel">
            <h2 className="m-0 mb-3 text-[20px] font-semibold text-[#38d9ff]">
              CANLI OLAY AKIŞI (WAR ROOM FEED)
            </h2>
            <div className="bg-[#070912] border-2 border-[#4b588a] p-3 min-h-[150px] max-h-[260px] overflow-y-auto">
              {feedEvents.length === 0 ? (
                <div className="font-log-mono text-[#b2bfe8]">
                  &gt; Oyuncular odaya katılıyor... İlk karar sonrası canlı akış burada belirecek.
                </div>
              ) : (
                <ul className="list-none m-0 p-0 flex flex-col gap-2 font-log-mono">
                  {feedEvents.map((ev) => (
                    <li
                      key={ev.event_id}
                      style={{
                        color:
                          ev.severity === 'THREAT'
                            ? '#ff3864'
                            : ev.severity === 'WARN'
                              ? '#ffb84d'
                              : ev.severity === 'SAFE'
                                ? '#2de370'
                                : '#e6ecff',
                      }}
                    >
                      &gt; [{ev.team_name}] {ev.message}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          {debrief && (
            <section className="pixel-panel border-[#2de370]">
              <h2 className="m-0 mb-3 text-[22px] font-semibold text-[#2de370]">
                FİNAL SIRALAMASI
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {debrief.standings.map((s) => (
                  <div key={s.team_id} className="pixel-card flex items-center justify-between">
                    <span className="font-semibold">
                      #{s.rank} {s.name}
                    </span>
                    <span className="font-display-ascii text-[14px] text-[#2de370]">{s.score}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </PixelShell>
  );
};
