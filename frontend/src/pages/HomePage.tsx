import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { PixelShell } from '../components/PixelShell';

export const HomePage: React.FC = () => {
  const [roomCode, setRoomCode] = useState('');
  const navigate = useNavigate();

  const cleanCode = roomCode.trim().toUpperCase();

  return (
    <PixelShell subtitle="16-Bit Retro Cyber War Room • Çoklu Oyunculu SOC Triyaj Simülasyonu">
      <section className="pixel-panel mb-6">
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b-4 border-[#070912] pb-3">
            <h2 className="m-0 text-[22px] font-semibold text-[#e6ecff]">
              OPERASYON MERKEZİNE HOŞ GELDİNİZ
            </h2>
            <span className="pixel-badge bg-[#0c0f1d] text-[#38d9ff] border-[#38d9ff]">
              SPRINT 1 // CANLI ÇEKİRDEK
            </span>
          </div>

          <p className="m-0 text-[16px] text-[#b2bfe8]">
            Takımınızla ortak alarm kuyruğunu yönetin, enrichment araçlarıyla kanıt toplayın ve şirket
            sağlığını (<strong className="text-[#2de370]">Breach Meter</strong>) sıfırlamadan gerçek saldırıları
            eskale edin.
          </p>

          <div className="pixel-card flex flex-wrap items-center gap-3">
            <label htmlFor="home-room-input" className="text-[15px] font-semibold text-[#ffb84d]">
              ODA KODU İLE HIZLI GİRİŞ:
            </label>
            <input
              id="home-room-input"
              type="text"
              maxLength={8}
              placeholder="ÖRN: BZ4821"
              value={roomCode}
              onChange={(e) => setRoomCode(e.target.value.toUpperCase())}
              className="pixel-input pixel-input-code w-52"
            />
            <button
              type="button"
              disabled={!cleanCode}
              onClick={() => navigate(`/play?room=${encodeURIComponent(cleanCode)}`)}
              className="px-btn px-btn-cyan"
            >
              OYUNCU OLARAK KATIL (/PLAY)
            </button>
            <button
              type="button"
              disabled={!cleanCode}
              onClick={() => navigate(`/host?room=${encodeURIComponent(cleanCode)}`)}
              className="px-btn px-btn-amber"
            >
              PROJEKTÖRÜ AÇ (/HOST)
            </button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <article className="pixel-panel flex flex-col justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="avatar-box">
                <img src="/sprites/analyst-ali.png" alt="Oyuncu Terminali" />
              </div>
              <h3 className="m-0 text-[20px] font-semibold text-[#38d9ff]">/PLAY — OYUNCU MASASI</h3>
            </div>
            <p className="m-0 text-[15px] text-[#b2bfe8]">
              Ortak kuyruktan alarmı CLAIM et, IP/Hash/CMDB kanıtlarını çek ve TP/FP karar mührünü bas.
            </p>
          </div>
          <Link to="/play" className="px-btn px-btn-cyan no-underline">
            OYUNCU TERMİNALİNİ AÇ
          </Link>
        </article>

        <article className="pixel-panel flex flex-col justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="avatar-box">
                <img src="/sprites/tool-ip-radar.png" alt="Projektör Ekranı" />
              </div>
              <h3 className="m-0 text-[20px] font-semibold text-[#ffb84d]">/HOST — PROJEKTÖR</h3>
            </div>
            <p className="m-0 text-[15px] text-[#b2bfe8]">
              Amfi ekranı için 6 haneli oda kodu, takımların yan yana 10 bloklu Breach Meter barları ve olay akışı.
            </p>
          </div>
          <Link to="/host" className="px-btn px-btn-amber no-underline">
            PROJEKTÖR GÖRÜNÜMÜNÜ AÇ
          </Link>
        </article>

        <article className="pixel-panel flex flex-col justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="avatar-box">
                <img src="/sprites/tool-cmdb-server.png" alt="Moderatör Kontrolü" />
              </div>
              <h3 className="m-0 text-[20px] font-semibold text-[#2de370]">/ADMIN — MODERATÖR</h3>
            </div>
            <p className="m-0 text-[15px] text-[#b2bfe8]">
              Yeni oda oluştur, senaryo dalgalarını başlat/duraklat ve maç sonunda gizli analiz özetini aç.
            </p>
          </div>
          <Link to="/admin" className="px-btn px-btn-safe no-underline">
            MODERATÖR PANELİNİ AÇ
          </Link>
        </article>
      </section>
    </PixelShell>
  );
};
