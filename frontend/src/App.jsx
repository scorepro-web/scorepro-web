import { useEffect, useState } from "react";

// URL del backend ya desplegado en Render (Etapa 3).
const API_URL = "https://scorepro-web.onrender.com";

export default function App() {
  const [equipos, setEquipos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/equipos`)
      .then((res) => {
        if (!res.ok) throw new Error("El servidor respondió con un error.");
        return res.json();
      })
      .then((data) => {
        setEquipos(data);
        setCargando(false);
      })
      .catch((err) => {
        setError(err.message);
        setCargando(false);
      });
  }, []);

  return (
    <div className="page">
      <header className="topbar">
        <div className="topbar-inner">
          <span className="brand">
            <span className="brand-mark">SP</span>
            ScorePro
          </span>
          <nav className="nav">
            <span className="nav-item active">Equipos</span>
            <span className="nav-item">Comparar</span>
          </nav>
        </div>
      </header>

      <main className="content">
        <div className="content-header">
          <h1>La Liga · 2023-2024</h1>
          <p>Selecciona un equipo para ver sus estadísticas de la temporada.</p>
        </div>

        {cargando && (
          <div className="status-block">
            <div className="spinner" aria-hidden="true" />
            <p>
              Cargando equipos… si es la primera visita en un rato, el servidor
              puede tardar hasta un minuto en despertar.
            </p>
          </div>
        )}

        {error && (
          <div className="status-block status-block-error">
            <p>No se pudo conectar con el servidor: {error}</p>
          </div>
        )}

        {!cargando && !error && (
          <div className="grid">
            {equipos.map((equipo) => (
              <button key={equipo.id} className="team-card">
                <div className="team-card-crest">
                  {equipo.logo_url ? (
                    <img src={equipo.logo_url} alt="" />
                  ) : (
                    <span>{equipo.nombre.slice(0, 2).toUpperCase()}</span>
                  )}
                </div>
                <div className="team-card-body">
                  <span className="team-card-name">{equipo.nombre}</span>
                  <span className="team-card-meta">{equipo.pais}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
