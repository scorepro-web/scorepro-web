import { useEffect, useState } from "react";

// URL del backend ya desplegado en Render (Etapa 3).
const API_URL = "https://scorepro-web.onrender.com";

function VistaEquipos({ onSeleccionarEquipo }) {
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
    <>
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
            <button
              key={equipo.id}
              className="team-card"
              onClick={() => onSeleccionarEquipo(equipo.id)}
            >
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
    </>
  );
}

function EstadisticaDestacada({ etiqueta, valor }) {
  return (
    <div className="stat-tile">
      <span className="stat-tile-valor">{valor}</span>
      <span className="stat-tile-etiqueta">{etiqueta}</span>
    </div>
  );
}

function BarraForma({ goles }) {
  // goles viene en orden más reciente primero; lo invertimos para mostrar
  // el orden cronológico de izquierda a derecha.
  const partidos = [...goles].reverse();
  const maximo = Math.max(...partidos, 1);

  return (
    <div className="forma-chart">
      {partidos.map((g, i) => (
        <div key={i} className="forma-barra-wrap">
          <div
            className="forma-barra"
            style={{ height: `${Math.max((g / maximo) * 100, 8)}%` }}
          />
          <span className="forma-valor">{g}</span>
        </div>
      ))}
    </div>
  );
}

function VistaFichaEquipo({ equipoId, onVolver }) {
  const [ficha, setFicha] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setCargando(true);
    setError(null);
    fetch(`${API_URL}/equipos/${equipoId}`)
      .then((res) => {
        if (!res.ok) throw new Error("No se pudo cargar la ficha del equipo.");
        return res.json();
      })
      .then((data) => {
        setFicha(data);
        setCargando(false);
      })
      .catch((err) => {
        setError(err.message);
        setCargando(false);
      });
  }, [equipoId]);

  return (
    <>
      <button className="back-link" onClick={onVolver}>
        ← Volver a equipos
      </button>

      {cargando && (
        <div className="status-block">
          <div className="spinner" aria-hidden="true" />
          <p>Cargando estadísticas del equipo…</p>
        </div>
      )}

      {error && (
        <div className="status-block status-block-error">
          <p>{error}</p>
        </div>
      )}

      {!cargando && !error && ficha && (
        <>
          <div className="team-header">
            <div className="team-header-crest">
              {ficha.logo_url ? (
                <img src={ficha.logo_url} alt="" />
              ) : (
                <span>{ficha.nombre.slice(0, 2).toUpperCase()}</span>
              )}
            </div>
            <div>
              <h1>{ficha.nombre}</h1>
              <p>
                {ficha.pais} · Temporada {ficha.temporada} ·{" "}
                {ficha.estadisticas.partidos_jugados} partidos jugados
              </p>
            </div>
          </div>

          <section className="panel">
            <h2 className="panel-title">Promedios generales</h2>
            <div className="stat-row">
              <EstadisticaDestacada
                etiqueta="Goles a favor"
                valor={ficha.estadisticas.goles_anotados_prom}
              />
              <EstadisticaDestacada
                etiqueta="Goles en contra"
                valor={ficha.estadisticas.goles_recibidos_prom}
              />
              <EstadisticaDestacada
                etiqueta="Corners a favor"
                valor={ficha.estadisticas.corners_favor_prom}
              />
              <EstadisticaDestacada
                etiqueta="Tarjetas por partido"
                valor={ficha.estadisticas.tarjetas_prom}
              />
            </div>
          </section>

          <section className="panel panel-split">
            <div>
              <h2 className="panel-title">Como local</h2>
              <div className="stat-row">
                <EstadisticaDestacada
                  etiqueta="Goles a favor"
                  valor={ficha.estadisticas.goles_anotados_local_prom}
                />
                <EstadisticaDestacada
                  etiqueta="Goles en contra"
                  valor={ficha.estadisticas.goles_recibidos_local_prom}
                />
              </div>
            </div>
            <div>
              <h2 className="panel-title">Como visitante</h2>
              <div className="stat-row">
                <EstadisticaDestacada
                  etiqueta="Goles a favor"
                  valor={ficha.estadisticas.goles_anotados_visitante_prom}
                />
                <EstadisticaDestacada
                  etiqueta="Goles en contra"
                  valor={ficha.estadisticas.goles_recibidos_visitante_prom}
                />
              </div>
            </div>
          </section>

          <section className="panel">
            <h2 className="panel-title">Forma reciente (últimos partidos)</h2>
            {ficha.estadisticas.forma_reciente_goles.length > 0 ? (
              <>
                <BarraForma goles={ficha.estadisticas.forma_reciente_goles} />
                <p className="forma-promedio">
                  Promedio reciente:{" "}
                  <strong>{ficha.estadisticas.forma_reciente_promedio}</strong> goles/partido
                </p>
              </>
            ) : (
              <p className="forma-promedio">
                Aún no hay suficientes partidos recientes registrados.
              </p>
            )}
          </section>
        </>
      )}
    </>
  );
}

export default function App() {
  const [equipoSeleccionado, setEquipoSeleccionado] = useState(null);

  return (
    <div className="page">
      <header className="topbar">
        <div className="topbar-inner">
          <span className="brand">
            <span className="brand-mark">SP</span>
            ScorePro
          </span>
          <nav className="nav">
            <span
              className={`nav-item ${!equipoSeleccionado ? "active" : ""}`}
              onClick={() => setEquipoSeleccionado(null)}
            >
              Equipos
            </span>
            <span className="nav-item">Comparar</span>
          </nav>
        </div>
      </header>

      <main className="content">
        {equipoSeleccionado ? (
          <VistaFichaEquipo
            equipoId={equipoSeleccionado}
            onVolver={() => setEquipoSeleccionado(null)}
          />
        ) : (
          <VistaEquipos onSeleccionarEquipo={setEquipoSeleccionado} />
        )}
      </main>
    </div>
  );
}
