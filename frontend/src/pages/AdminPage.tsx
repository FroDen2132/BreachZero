import React, { useEffect, useState } from 'react';
import { PixelShell } from '../components/PixelShell';
import { BreachMeter } from '../components/BreachMeter';
import type { ScenarioSummary } from '../contracts/types';
import { useRoomSocket } from '../hooks/useRoomSocket';

interface AdminStored {
  room_code: string;
  admin_token: string;
}

export const AdminPage: React.FC = () => {
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [teamNamesRaw, setTeamNamesRaw] = useState('ALPHA SQUAD, SİBER KURTLAR, ZERO-DAY EKİBİ');
  const [roomCode, setRoomCode] = useState<string | null>(null);
  const [adminToken, setAdminToken] = useState<string | null>(null);
  const [copyNote, setCopyNote] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const { connected, roomState, feedEvents, debrief, lastError, connect, sendAction } = useRoomSocket();

  useEffect(() => {
    fetch('/api/scenarios')
      .then((r) => r.json())
      .then((list: ScenarioSummary[]) => {
        setScenarios(list);
        setSelectedIds(list.map((s) => s.alert_id));
      })
      .catch(() => setApiError('Senaryo listesi backend sunucusundan alınamadı.'));

    try {
      const saved = sessionStorage.getItem('bz_admin_room');
      if (saved) {
        const parsed = JSON.parse(saved) as AdminStored;
        setRoomCode(parsed.room_code);
        setAdminToken(parsed.admin_token);
        connect({ roomCode: parsed.room_code, role: 'ADMIN', adminToken: parsed.admin_token });
      }
    } catch {
      // ignore
    }
  }, [connect]);

  const handleCreateRoom = async () => {
    setApiError(null);
    const teams = teamNamesRaw
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    try {
      const res = await fetch('/api/rooms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ team_names: teams.length ? teams : undefined, total_waves: 2 }),
      });
      if (!res.ok) throw new Error('Oda oluşturulamadı');
      const data = (await res.json()) as AdminStored;
      setRoomCode(data.room_code);
      setAdminToken(data.admin_token);
      sessionStorage.setItem('bz_admin_room', JSON.stringify(data));
      connect({ roomCode: data.room_code, role: 'ADMIN', adminToken: data.admin_token });
    } catch (err) {
      setApiError(err instanceof Error ? err.message : 'Oda oluşturma hatası');
    }
  };

  const handleCopyCode = async () => {
    if (!roomCode) return;
    try {
      await navigator.clipboard.writeText(roomCode);
      setCopyNote(`KOPYALANDI: ${roomCode}`);
    } catch {
      setCopyNote(`KOD: ${roomCode}`);
    }
    setTimeout(() => setCopyNote(null), 2000);
  };

  const toggleScenario = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const isPaused = roomState?.status === 'PAUSED';
  const isEnded = roomState?.status === 'ENDED';

  return (
    <PixelShell subtitle="Moderatör Kontrol Merkezi (/admin) • Dalga Yönetimi &amp; Maç Sonu Analizi">
      {(apiError || lastError) && (
        <div className="pixel-panel mb-4 border-[#ff3864] bg-[#2b1528] text-[#e6ecff]">
          <strong>HATA:</strong> {apiError || lastError}
        </div>
      )}

      {!roomCode || !adminToken ? (
        <section className="pixel-panel mb-6 flex flex-col gap-4">
          <h2 className="m-0 text-[22px] font-semibold">1. YENİ TURNUVA ODASI OLUŞTUR</h2>
          <div className="flex flex-col gap-2">
            <label htmlFor="team-names-input" className="text-[15px] text-[#b2bfe8]">
              Takım İsimleri (virgülle ayırın):
            </label>
            <input
              id="team-names-input"
              type="text"
              value={teamNamesRaw}
              onChange={(e) => setTeamNamesRaw(e.target.value)}
              className="pixel-input w-full"
            />
          </div>
          <div>
            <button type="button" onClick={handleCreateRoom} className="px-btn px-btn-safe">
              YENİ ODA OLUŞTUR
            </button>
          </div>
        </section>
      ) : (
        <>
          <section className="pixel-panel mb-5 flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="text-[15px] text-[#b2bfe8]">AKTİF ODA KODU</div>
              <div className="flex flex-wrap items-center gap-3 mt-1">
                <span className="font-display-ascii text-[28px] text-[#ffb84d]">{roomCode}</span>
                <button type="button" onClick={handleCopyCode} className="px-btn">
                  {copyNote || 'KODU KOPYALA'}
                </button>
                <span className="pixel-badge bg-[#0c0f1d] text-[#38d9ff] border-[#38d9ff]">
                  {connected ? `DURUM: ${roomState?.status || 'LOBBY'}` : 'BAĞLANIYOR...'}
                </span>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <a
                href={`/host?room=${encodeURIComponent(roomCode)}`}
                target="_blank"
                rel="noreferrer"
                className="px-btn px-btn-amber no-underline"
              >
                /HOST YENİ SEKMEDE AÇ
              </a>
              <a
                href={`/play?room=${encodeURIComponent(roomCode)}`}
                target="_blank"
                rel="noreferrer"
                className="px-btn px-btn-cyan no-underline"
              >
                /PLAY YENİ SEKMEDE AÇ
              </a>
              <button
                type="button"
                onClick={() => {
                  sessionStorage.removeItem('bz_admin_room');
                  setRoomCode(null);
                  setAdminToken(null);
                }}
                className="px-btn"
              >
                YENİ ODA KUR
              </button>
            </div>
          </section>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mb-6">
            <section className="pixel-panel lg:col-span-5 flex flex-col gap-4">
              <h2 className="m-0 text-[20px] font-semibold">SENARYO PAKETİ SEÇİMİ</h2>
              <div className="flex flex-col gap-2">
                {scenarios.map((sc) => {
                  const checked = selectedIds.includes(sc.alert_id);
                  return (
                    <label
                      key={sc.alert_id}
                      className="pixel-card flex items-start gap-3 cursor-pointer"
                      style={{
                        borderColor: checked ? '#2de370' : '#4b588a',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleScenario(sc.alert_id)}
                        className="sr-only"
                      />
                      <span
                        className={`pixel-checkbox-box mt-0.5 ${checked ? 'is-checked' : ''}`}
                        aria-hidden="true"
                      >
                        {checked && (
                          <svg
                            viewBox="0 0 16 16"
                            width={16}
                            height={16}
                            shapeRendering="crispEdges"
                            aria-hidden="true"
                          >
                            <rect x="3" y="8" width="2" height="2" fill="#e6ecff" />
                            <rect x="5" y="10" width="2" height="2" fill="#e6ecff" />
                            <rect x="7" y="8" width="2" height="2" fill="#e6ecff" />
                            <rect x="9" y="6" width="2" height="2" fill="#e6ecff" />
                            <rect x="11" y="4" width="2" height="2" fill="#e6ecff" />
                          </svg>
                        )}
                      </span>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-display-ascii text-[11px] text-[#38d9ff]">
                            {sc.incident_code}
                          </span>
                          <span className="text-[14px] text-[#ffb84d]">{sc.severity}</span>
                          <span className="text-[14px] text-[#b2bfe8]">({sc.sla_seconds}s SLA)</span>
                        </div>
                        <div className="text-[15px] font-semibold text-[#e6ecff] mt-1">{sc.title}</div>
                      </div>
                    </label>
                  );
                })}
              </div>

              <div className="flex flex-wrap gap-2 pt-2 border-t-4 border-[#070912]">
                <button
                  type="button"
                  disabled={isEnded || selectedIds.length === 0}
                  onClick={() => sendAction('ADMIN_START_WAVE', { scenario_ids: selectedIds })}
                  className="px-btn px-btn-safe"
                >
                  DALGAYI BAŞLAT
                </button>
                {isPaused ? (
                  <button
                    type="button"
                    disabled={isEnded}
                    onClick={() => sendAction('ADMIN_RESUME_WAVE', {})}
                    className="px-btn px-btn-cyan"
                  >
                    DEVAM ET
                  </button>
                ) : (
                  <button
                    type="button"
                    disabled={isEnded || roomState?.status !== 'ACTIVE'}
                    onClick={() => sendAction('ADMIN_PAUSE_WAVE', { reason: 'Moderatör molası' })}
                    className="px-btn px-btn-amber"
                  >
                    DURAKLAT (PAUSE)
                  </button>
                )}
                <button
                  type="button"
                  disabled={isEnded}
                  onClick={() => sendAction('ADMIN_END_MATCH', {})}
                  className="px-btn px-btn-threat"
                >
                  MAÇI BİTİR &amp; DEBRIEF
                </button>
              </div>
            </section>

            <section className="pixel-panel lg:col-span-7 flex flex-col gap-4">
              <h2 className="m-0 text-[20px] font-semibold">TAKIM DURUMLARI VE OLAY AKIŞI</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {(roomState?.teams || []).map((t) => (
                  <div key={t.team_id} className="pixel-card flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[16px] font-semibold text-[#e6ecff]">{t.name}</span>
                      <span className="font-display-ascii text-[12px] text-[#38d9ff]">{t.score}</span>
                    </div>
                    <BreachMeter hp={t.hp} compact />
                    <div className="text-[14px] text-[#b2bfe8]">
                      Çözülen: {t.resolved_count} • Seri: {t.streak}
                    </div>
                  </div>
                ))}
              </div>

              <div className="bg-[#070912] border-2 border-[#4b588a] p-3 min-h-[160px] max-h-[240px] overflow-y-auto">
                <div className="text-[15px] font-semibold text-[#38d9ff] mb-2">CANLI OLAY AKIŞI</div>
                {feedEvents.length === 0 ? (
                  <div className="font-log-mono text-[#b2bfe8]">Henüz olay kaydı yok.</div>
                ) : (
                  <ul className="list-none m-0 p-0 flex flex-col gap-1 font-log-mono">
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
          </div>

          {debrief && (
            <section className="pixel-panel flex flex-col gap-4 border-[#2de370]">
              <h2 className="m-0 text-[22px] font-semibold text-[#2de370]">
                MAÇ SONU HATA ANALİZİ (DEBRIEF)
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {debrief.cases.map((c) => (
                  <article key={c.alert_id} className="pixel-card flex flex-col gap-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-display-ascii text-[12px] text-[#ffb84d]">
                        {c.incident_code}
                      </span>
                      <span
                        className="pixel-badge"
                        style={{
                          backgroundColor: c.ground_truth === 'TP' ? '#ff3864' : '#2de370',
                          color: c.ground_truth === 'TP' ? '#e6ecff' : '#070912',
                        }}
                      >
                        GERÇEK: {c.ground_truth}
                      </span>
                    </div>
                    <h3 className="m-0 text-[17px] font-semibold text-[#e6ecff]">{c.title}</h3>
                    {c.mitre_attack.length > 0 && (
                      <div className="font-log-mono text-[#38d9ff]">
                        MITRE ATT&amp;CK: {c.mitre_attack.join(', ')}
                      </div>
                    )}
                    <p className="m-0 font-log-mono text-[#e6ecff] bg-[#0c0f1d] p-2 border-2 border-[#070912]">
                      {c.debrief_explanation}
                    </p>
                  </article>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </PixelShell>
  );
};
