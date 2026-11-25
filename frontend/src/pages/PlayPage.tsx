import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AlertQueue } from '../components/AlertQueue';
import { BreachMeter } from '../components/BreachMeter';
import { PixelShell } from '../components/PixelShell';
import { ToolIcon } from '../components/ToolIcon';
import { ANALYST_AVATARS, ENRICHER_LABELS, type DecisionType } from '../contracts/types';
import { getStoredSession, useRoomSocket } from '../hooks/useRoomSocket';

export const PlayPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialRoom = (searchParams.get('room') || '').toUpperCase();

  const [roomCodeInput, setRoomCodeInput] = useState(initialRoom);
  const [nickname, setNickname] = useState('');
  const [teamId, setTeamId] = useState('team_1');
  const [avatarId, setAvatarId] = useState<string>('analyst-ali');
  const [availableTeams, setAvailableTeams] = useState<Array<{ team_id: string; name: string }>>([
    { team_id: 'team_1', name: 'ALPHA SQUAD' },
    { team_id: 'team_2', name: 'SİBER KURTLAR' },
    { team_id: 'team_3', name: 'ZERO-DAY EKİBİ' },
  ]);
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [shake, setShake] = useState(false);
  const prevHpRef = useRef<number | null>(null);

  const {
    connected,
    session,
    roomState,
    lastDecision,
    debrief,
    lastError,
    clearError,
    connect,
    sendAction,
  } = useRoomSocket();

  // Fetch teams dynamically when room code is entered
  useEffect(() => {
    const clean = roomCodeInput.trim().toUpperCase();
    if (clean.length < 4) return;
    fetch(`/api/rooms/${encodeURIComponent(clean)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && Array.isArray(data.teams) && data.teams.length > 0) {
          setAvailableTeams(data.teams.map((t: { team_id: string; name: string }) => ({ team_id: t.team_id, name: t.name })));
        }
      })
      .catch(() => { });
  }, [roomCodeInput]);

  // Auto-reconnect on F5 if this tab already holds a sessionStorage token for ?room=...
  useEffect(() => {
    if (initialRoom) {
      const stored = getStoredSession(initialRoom);
      if (stored && !session) {
        setNickname(stored.nickname);
        setTeamId(stored.team_id);
        setAvatarId(stored.avatar_id);
        connect({
          roomCode: initialRoom,
          role: 'PLAYER',
          teamId: stored.team_id,
          nickname: stored.nickname,
          avatarId: stored.avatar_id,
        });
      }
    }
  }, [initialRoom, session, connect]);

  const myTeam = useMemo(() => {
    if (!roomState || !session?.team_id) return null;
    return roomState.teams.find((t) => t.team_id === session.team_id) || null;
  }, [roomState, session?.team_id]);

  // Trigger screen shake when team HP drops
  useEffect(() => {
    if (!myTeam) return;
    if (prevHpRef.current !== null && myTeam.hp < prevHpRef.current) {
      setShake(true);
      const t = setTimeout(() => setShake(false), 400);
      prevHpRef.current = myTeam.hp;
      return () => clearTimeout(t);
    }
    prevHpRef.current = myTeam.hp;
  }, [myTeam?.hp]);

  // Auto-select claimed alert or first alert in queue
  useEffect(() => {
    if (!myTeam || myTeam.queue.length === 0) return;
    const stillExists = myTeam.queue.some((a) => a.alert_id === selectedAlertId);
    if (!stillExists) {
      const mine = myTeam.queue.find((a) => a.claimed_by_player_id === session?.player_id);
      setSelectedAlertId((mine || myTeam.queue[0]).alert_id);
    }
  }, [myTeam, selectedAlertId, session?.player_id]);

  const activeAlert = useMemo(() => {
    if (!myTeam) return null;
    return myTeam.queue.find((a) => a.alert_id === selectedAlertId) || myTeam.queue[0] || null;
  }, [myTeam, selectedAlertId]);

  const isClaimedByMe =
    Boolean(activeAlert) &&
    activeAlert?.status === 'CLAIMED' &&
    activeAlert?.claimed_by_player_id === session?.player_id;

  const isRoomPaused = roomState?.status === 'PAUSED';
  const canOperate = isClaimedByMe && !myTeam?.is_breached && roomState?.status === 'ACTIVE';

  const handleJoin = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanCode = roomCodeInput.trim().toUpperCase();
    if (!cleanCode) return;
    setSearchParams({ room: cleanCode }, { replace: true });
    connect({
      roomCode: cleanCode,
      role: 'PLAYER',
      teamId,
      nickname: nickname.trim() || 'Analist',
      avatarId,
    });
  };

  const submitDecision = (decision: DecisionType) => {
    if (!activeAlert) return;
    sendAction('SUBMIT_DECISION', { alert_id: activeAlert.alert_id, decision });
  };

  if (!connected || !session) {
    return (
      <PixelShell subtitle="Oyuncu Terminali (/play) • Takımına Katıl &amp; Kuyruğu Savun">
        <section className="pixel-panel max-w-2xl mx-auto">
          <h2 className="m-0 mb-4 text-[22px] font-semibold">SOC NÖBETİNE KATIL</h2>
          {lastError && (
            <div className="pixel-card mb-4 border-[#ff3864] bg-[#2b1528] text-[#e6ecff]">
              {lastError}
            </div>
          )}
          <form onSubmit={handleJoin} className="flex flex-col gap-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1">
                <label htmlFor="play-room" className="text-[15px] text-[#b2bfe8]">
                  Oda Kodu
                </label>
                <input
                  id="play-room"
                  type="text"
                  required
                  value={roomCodeInput}
                  onChange={(e) => setRoomCodeInput(e.target.value.toUpperCase())}
                  placeholder="ÖRN: BZ4821"
                  className="pixel-input pixel-input-code"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label htmlFor="play-nick" className="text-[15px] text-[#b2bfe8]">
                  Takma Ad
                </label>
                <input
                  id="play-nick"
                  type="text"
                  required
                  maxLength={20}
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  placeholder="Ali K."
                  className="pixel-input"
                />
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="play-team" className="text-[15px] text-[#b2bfe8]">
                Takım Seçimi
              </label>
              <select
                id="play-team"
                value={teamId}
                onChange={(e) => setTeamId(e.target.value)}
                className="pixel-select"
              >
                {availableTeams.map((t) => (
                  <option key={t.team_id} value={t.team_id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-2">
              <span className="text-[15px] text-[#b2bfe8]">16×16 Piksel Analist Avatarı</span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {ANALYST_AVATARS.map((av) => {
                  const selected = avatarId === av.id;
                  return (
                    <button
                      key={av.id}
                      type="button"
                      onClick={() => setAvatarId(av.id)}
                      aria-pressed={selected}
                      className={`pixel-card flex flex-col items-center gap-2 cursor-pointer ${selected ? '' : 'opacity-80 hover:opacity-100'
                        }`}
                      style={{
                        backgroundColor: selected ? '#232a4a' : '#12172b',
                        borderColor: selected ? '#38d9ff' : '#4b588a',
                        boxShadow: selected
                          ? 'inset 2px 2px 0px #38d9ff, 4px 4px 0px #070912'
                          : 'inset 2px 2px 0px #1e2647, 4px 4px 0px #070912',
                      }}
                    >
                      <div
                        className="avatar-box"
                        style={{
                          borderColor: selected ? '#38d9ff' : '#4b588a',
                        }}
                      >
                        <img src={`/sprites/${av.id}.png`} alt={av.label} />
                      </div>
                      <span
                        className="text-[15px] font-semibold"
                        style={{ color: selected ? '#38d9ff' : '#e6ecff' }}
                      >
                        {av.label}
                      </span>
                      <span
                        className="pixel-badge"
                        style={{
                          backgroundColor: selected ? '#38d9ff' : '#0c0f1d',
                          color: selected ? '#070912' : '#b2bfe8',
                          borderColor: selected ? '#070912' : '#4b588a',
                        }}
                      >
                        {selected ? 'SEÇİLİ' : 'SEÇ'}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            <button type="submit" className="px-btn px-btn-safe mt-2">
              TERMİNALE BAĞLAN
            </button>
          </form>
        </section>
      </PixelShell>
    );
  }

  return (
    <PixelShell
      subtitle={`Oda: ${roomState?.room_code || roomCodeInput} • Takım: ${myTeam?.name || session.team_id}`}
      shake={shake}
    >
      {isRoomPaused && (
        <div className="pixel-panel mb-4 border-[#ffb84d] bg-[#2b2110] text-[#ffb84d] text-center font-semibold">
          OYUN MODERATÖR TARAFINDAN DURAKLATILDI — TÜM SLA SAYAÇLARI DONDURULDU
        </div>
      )}

      {lastError && (
        <div className="pixel-panel mb-4 border-[#ff3864] bg-[#2b1528] flex items-center justify-between gap-3">
          <span>{lastError}</span>
          <button type="button" onClick={clearError} className="px-btn">
            KAPAT
          </button>
        </div>
      )}

      {lastDecision && (
        <div
          className="pixel-panel mb-4 flex flex-wrap items-center justify-between gap-2"
          style={{
            borderColor: lastDecision.score_delta >= 0 ? '#2de370' : '#ff3864',
          }}
        >
          <span className="font-semibold">
            SON KARAR ({lastDecision.outcome}): {lastDecision.score_delta >= 0 ? '+' : ''}
            {lastDecision.score_delta} Puan • {lastDecision.hp_delta} HP
          </span>
          <span className="font-display-ascii text-[12px] text-[#38d9ff]">
            STREAK: {lastDecision.new_streak}
          </span>
        </div>
      )}

      {/* Top Team HUD */}
      {myTeam && (
        <section className="pixel-panel mb-5 grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
          <div className="lg:col-span-4 flex items-center gap-4">
            <div className="pixel-card flex-1">
              <div className="text-[14px] text-[#b2bfe8]">TAKIM SKORU</div>
              <div className="font-display-ascii text-[18px] text-[#38d9ff] mt-1">{myTeam.score}</div>
            </div>
            <div className="pixel-card flex-1">
              <div className="text-[14px] text-[#b2bfe8]">SERİ / ÇÖZÜLEN</div>
              <div className="font-display-ascii text-[16px] text-[#ffb84d] mt-1">
                {myTeam.streak} / {myTeam.resolved_count}
              </div>
            </div>
          </div>
          <div className="lg:col-span-8">
            <BreachMeter hp={myTeam.hp} />
          </div>
        </section>
      )}

      {debrief ? (
        <section className="pixel-panel flex flex-col gap-4 border-[#2de370]">
          <h2 className="m-0 text-[22px] font-semibold text-[#2de370]">
            MAÇ SONA ERDİ — EĞİTİM ANALİZİ (DEBRIEF)
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {debrief.cases.map((c) => (
              <article key={c.alert_id} className="pixel-card flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="font-display-ascii text-[12px] text-[#ffb84d]">{c.incident_code}</span>
                  <span
                    className="pixel-badge"
                    style={{
                      backgroundColor: c.ground_truth === 'TP' ? '#ff3864' : '#2de370',
                      color: c.ground_truth === 'TP' ? '#e6ecff' : '#070912',
                    }}
                  >
                    DOĞRU KARAR: {c.ground_truth}
                  </span>
                </div>
                <h3 className="m-0 text-[17px] font-semibold">{c.title}</h3>
                <p className="m-0 font-log-mono text-[#e6ecff] bg-[#0c0f1d] p-3 border-2 border-[#070912]">
                  {c.debrief_explanation}
                </p>
              </article>
            ))}
          </div>
        </section>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Left: Shared Queue */}
          <section className="pixel-panel lg:col-span-5 flex flex-col gap-3">
            <div className="flex items-center justify-between border-b-4 border-[#070912] pb-2">
              <h2 className="m-0 text-[20px] font-semibold">ORTAK ALARM KUYRUĞU</h2>
              <span className="font-display-ascii text-[12px] text-[#ffb84d]">
                DALGA {roomState?.current_wave || 0}
              </span>
            </div>
            <AlertQueue
              alerts={myTeam?.queue || []}
              currentPlayerId={session.player_id}
              selectedAlertId={selectedAlertId}
              teamBreached={Boolean(myTeam?.is_breached) || isRoomPaused}
              onSelect={setSelectedAlertId}
              onClaim={(aid) => sendAction('CLAIM_ALERT', { alert_id: aid })}
              onRelease={(aid) => sendAction('RELEASE_ALERT', { alert_id: aid })}
            />
          </section>

          {/* Right: Interactive Stamp Desk */}
          <section className="pixel-panel lg:col-span-7 flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b-4 border-[#070912] pb-2">
              <h2 className="m-0 text-[20px] font-semibold">İNCELEME VE DAMGA MASASI</h2>
              {activeAlert && (
                <span className="font-display-ascii text-[12px] text-[#ffb84d]">
                  {activeAlert.incident_code}
                </span>
              )}
            </div>

            {!activeAlert ? (
              <div className="pixel-card text-[#b2bfe8]">
                İncelemek için soldaki kuyruktan bir alarm seçin veya üstlenin.
              </div>
            ) : (
              <>
                <div className="relative bg-[#12172b] border-4 border-[#4b588a] p-4 flex flex-col gap-3">
                  <div className={`flex flex-wrap items-center justify-between gap-2 ${activeAlert.status === 'RESOLVED' ? 'pr-48' : ''}`}>
                    <h3 className="m-0 text-[18px] font-semibold text-[#e6ecff]">{activeAlert.title}</h3>
                  </div>
                  {activeAlert.status === 'RESOLVED' && (
                    <div
                      className="pixel-seal absolute top-4 right-4 z-10 pointer-events-none"
                      style={{
                        color:
                          lastDecision?.alert_id === activeAlert.alert_id &&
                          lastDecision.outcome.includes('FALSE_NEGATIVE')
                            ? '#ff3864'
                            : '#2de370',
                      }}
                    >
                      {lastDecision?.alert_id === activeAlert.alert_id
                        ? lastDecision.outcome === 'CORRECT_FP' || lastDecision.outcome === 'FALSE_NEGATIVE'
                          ? 'FALSE POSITIVE'
                          : 'TRUE POSITIVE'
                        : 'MÜHÜRLENDİ'}
                    </div>
                  )}

                  <div className="bg-[#0c0f1d] border-2 border-[#4b588a] p-3 font-log-mono text-[#e6ecff] flex flex-col gap-1">
                    <div>
                      <span className="text-[#38d9ff] font-semibold">[KAYNAK]</span>{' '}
                      {activeAlert.source.hostname} ({activeAlert.source.ip}:{activeAlert.source.port})
                    </div>
                    <div>
                      <span className="text-[#38d9ff] font-semibold">[HEDEF]</span>{' '}
                      {activeAlert.destination.hostname} ({activeAlert.destination.ip}:{activeAlert.destination.port})
                    </div>
                    <div>
                      <span className="text-[#38d9ff] font-semibold">[KULLANICI]</span>{' '}
                      {activeAlert.user.name} ({activeAlert.user.department || 'Bilinmiyor'})
                    </div>
                    {activeAlert.process && (
                      <div>
                        <span className="text-[#38d9ff] font-semibold">[SÜREÇ]</span>{' '}
                        {activeAlert.process.command_line || activeAlert.process.name}
                      </div>
                    )}
                    {activeAlert.file?.sha256 && (
                      <div className="break-all">
                        <span className="text-[#38d9ff] font-semibold">[SHA256]</span>{' '}
                        {activeAlert.file.sha256}
                      </div>
                    )}
                    <div className="pt-2 mt-1 border-t border-[#232a4a] text-[#b2bfe8] break-all">
                      {activeAlert.raw_log}
                    </div>
                  </div>

                  {/* Evidence Terminal */}
                  <div className="bg-[#070912] border-2 border-[#38d9ff] p-3 min-h-[140px]">
                    <div className="text-[16px] font-semibold text-[#38d9ff] mb-2">
                      KANIT GÜNLÜĞÜ ({activeAlert.evidence_cards.length})
                    </div>
                    {activeAlert.evidence_cards.length === 0 ? (
                      <div className="font-log-mono text-[#b2bfe8]">
                        &gt; Henüz ek kanıt çekilmedi. Bileti CLAIM ettikten sonra aşağıdaki araçları kullanın.
                      </div>
                    ) : (
                      <ul className="list-none m-0 p-0 flex flex-col gap-2 font-log-mono">
                        {activeAlert.evidence_cards.map((card) => (
                          <li
                            key={card.enricher_id}
                            style={{
                              color:
                                card.verdict_signal === 'MALICIOUS'
                                  ? '#ff3864'
                                  : card.verdict_signal === 'SUSPICIOUS'
                                    ? '#ffb84d'
                                    : card.verdict_signal === 'BENIGN'
                                      ? '#2de370'
                                      : '#e6ecff',
                            }}
                          >
                            &gt; [{card.display_name}] ({card.source_mode}) {card.summary}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>

                {/* Enrichment Controls */}
                <div className="flex flex-col gap-2">
                  <div className="text-[15px] text-[#b2bfe8]">
                    ENRICHMENT ARAÇLARI (İLK SORGU -10 PUAN • TEKRAR OKUMA ÜCRETSİZ):
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {activeAlert.available_enrichers.map((eid) => {
                      const alreadyFetched = activeAlert.evidence_cards.some((c) => c.enricher_id === eid);
                      const meta = ENRICHER_LABELS[eid] || {
                        label: `[${eid.toUpperCase()}]`,
                        iconId: 'fallback-terminal',
                      };
                      return (
                        <button
                          key={eid}
                          type="button"
                          disabled={!canOperate}
                          onClick={() =>
                            sendAction('RUN_ENRICHER', { alert_id: activeAlert.alert_id, enricher_id: eid })
                          }
                          className="px-btn px-btn-cyan justify-between"
                        >
                          <span className="flex items-center gap-2">
                            <ToolIcon iconId={meta.iconId} alt={meta.label} />
                            <span>{meta.label}</span>
                          </span>
                          <span className="text-[14px]" style={{ color: alreadyFetched ? '#2de370' : '#b2bfe8' }}>
                            {alreadyFetched ? 'TAMAM' : '-10P'}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Stamp Pad */}
                <div className="bg-[#0c0f1d] border-4 border-[#4b588a] p-4 flex flex-col gap-3">
                  <div className="text-[15px] font-semibold text-[#b2bfe8]">
                    {isClaimedByMe
                      ? 'KARAR MÜHRÜ (SAHİP: SİZ)'
                      : activeAlert.status === 'CLAIMED'
                        ? `BU BİLET ${activeAlert.claimed_by_nickname} TARAFINDAN KİLİTLİ`
                        : 'KARAR VERMEK İÇİN ÖNCE KUYRUKTAN [CLAIM] YAPIN'}
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <button
                      type="button"
                      disabled={!canOperate}
                      onClick={() => submitDecision('FP')}
                      className="px-btn px-btn-safe py-3"
                    >
                      [FALSE POSITIVE - KAPAT]
                    </button>
                    <button
                      type="button"
                      disabled={!canOperate}
                      onClick={() => submitDecision('TP')}
                      className="px-btn px-btn-threat py-3"
                    >
                      [TRUE POSITIVE - ESKALE ET]
                    </button>
                  </div>
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </PixelShell>
  );
};
