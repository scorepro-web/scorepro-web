import { useEffect, useState } from "react";

// URL del backend ya desplegado en Render (Etapa 3).
const API_URL = "https://scorepro-web.onrender.com";

// Ligas soportadas por el backend (Etapa 6: se agregó Premier League a La Liga).
const LIGAS = [
  { id: "140", nombre: "La Liga" },
  { id: "39", nombre: "Premier League" },
];

function VistaEquipos({ onSeleccionarEquipo }) {
  const [liga, setLiga] = useState(LIGAS[0].id);
  const [equipos, setEquipos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setCargando(true);
    setError(null);
    fetch(`${API_URL}/equipos?liga=${liga}`)
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
  }, [liga]);

  return (
    <>
      <div className="content-header">
        <h1>{LIGAS.find((l) => l.id === liga)?.nombre} · 2023-2024</h1>
        <p>Selecciona un equipo para ver sus estadísticas de la temporada.</p>
      </div>

      <div className="liga-tabs">
        {LIGAS.map((l) => (
          <button
            key={l.id}
            className={`liga-tab ${liga === l.id ? "active" : ""}`}
            onClick={() => setLiga(l.id)}
          >
            {l.nombre}
          </button>
        ))}
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

function SelectorEquipo({ equipos, valor, onCambiar, etiqueta }) {
  return (
    <div className="selector-equipo">
      <label className="selector-etiqueta">{etiqueta}</label>
      <select
        className="selector-input"
        value={valor ?? ""}
        onChange={(e) => onCambiar(e.target.value ? Number(e.target.value) : null)}
      >
        <option value="">Selecciona un equipo…</option>
        {equipos.map((eq) => (
          <option key={eq.id} value={eq.id}>
            {eq.nombre}
          </option>
        ))}
      </select>
    </div>
  );
}

function VistaComparador() {
  const [liga, setLiga] = useState(LIGAS[0].id);
  const [equipos, setEquipos] = useState([]);
  const [equipoLocal, setEquipoLocal] = useState(null);
  const [equipoVisitante, setEquipoVisitante] = useState(null);
  const [arbitro, setArbitro] = useState("");
  const [comparacion, setComparacion] = useState(null);
  const [prediccion, setPrediccion] = useState(null);
  const [analisis, setAnalisis] = useState(null);
  const [cargandoAnalisis, setCargandoAnalisis] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/equipos?liga=${liga}`)
      .then((res) => res.json())
      .then((data) => {
        setEquipos(data);
        // Al cambiar de liga, los equipos elegidos antes ya no aplican.
        setEquipoLocal(null);
        setEquipoVisitante(null);
        setComparacion(null);
        setPrediccion(null);
      })
      .catch(() => setError("No se pudo cargar la lista de equipos."));
  }, [liga]);

  const puedeComparar =
    equipoLocal && equipoVisitante && equipoLocal !== equipoVisitante;

  function comparar() {
    setCargando(true);
    setError(null);
    setComparacion(null);
    setPrediccion(null);
    setAnalisis(null);

    Promise.all([
      fetch(`${API_URL}/comparar?a=${equipoLocal}&b=${equipoVisitante}`).then((r) => {
        if (!r.ok) throw new Error("No se pudo comparar los equipos.");
        return r.json();
      }),
      fetch(`${API_URL}/prediccion?a=${equipoLocal}&b=${equipoVisitante}${arbitro.trim() ? `&arbitro=${encodeURIComponent(arbitro.trim())}` : ""}`).then((r) => {
        if (!r.ok) throw new Error("No se pudo generar la predicción.");
        return r.json();
      }),
    ])
      .then(([datosComparacion, datosPrediccion]) => {
        setComparacion(datosComparacion);
        setPrediccion(datosPrediccion);
        setCargando(false);
      })
      .catch((err) => {
        setError(err.message);
        setCargando(false);
      });
  }

  function generarAnalisis() {
    setCargandoAnalisis(true);
    setAnalisis(null);
    const params = `a=${equipoLocal}&b=${equipoVisitante}${arbitro.trim() ? `&arbitro=${encodeURIComponent(arbitro.trim())}` : ""}`;
    fetch(`${API_URL}/prediccion/analisis?${params}`)
      .then((r) => {
        if (!r.ok) throw new Error("No se pudo generar el análisis con IA.");
        return r.json();
      })
      .then((data) => {
        setAnalisis(data.analisis);
        setCargandoAnalisis(false);
      })
      .catch(() => {
        setAnalisis("No se pudo generar el análisis en este momento. Intenta de nuevo en unos segundos.");
        setCargandoAnalisis(false);
      });
  }

  return (
    <>
      <div className="content-header">
        <h1>Comparador de equipos</h1>
        <p>Elige un local y un visitante para ver la predicción del partido.</p>
      </div>

      <div className="liga-tabs">
        {LIGAS.map((l) => (
          <button
            key={l.id}
            className={`liga-tab ${liga === l.id ? "active" : ""}`}
            onClick={() => setLiga(l.id)}
          >
            {l.nombre}
          </button>
        ))}
      </div>

      <div className="comparador-selectores">
        <SelectorEquipo
          equipos={equipos}
          valor={equipoLocal}
          onCambiar={setEquipoLocal}
          etiqueta="Equipo local"
        />
        <span className="comparador-vs">vs</span>
        <SelectorEquipo
          equipos={equipos}
          valor={equipoVisitante}
          onCambiar={setEquipoVisitante}
          etiqueta="Equipo visitante"
        />
        <button
          className="comparador-boton"
          disabled={!puedeComparar || cargando}
          onClick={comparar}
        >
          {cargando ? "Comparando…" : "Comparar"}
        </button>
      </div>

      <div className="arbitro-input-wrap">
        <label className="selector-etiqueta">Árbitro asignado (opcional)</label>
        <input
          type="text"
          className="selector-input arbitro-input"
          placeholder="Ej. Antonio Mateu Lahoz"
          value={arbitro}
          onChange={(e) => setArbitro(e.target.value)}
        />
        <span className="arbitro-nota">
          Si lo indicas, ajustamos la predicción de tarjetas con su historial (solo
          disponible si tenemos 3 o más partidos suyos registrados).
        </span>
      </div>

      {equipoLocal && equipoVisitante && equipoLocal === equipoVisitante && (
        <div className="status-block status-block-error">
          <p>Elige dos equipos distintos para comparar.</p>
        </div>
      )}

      {error && (
        <div className="status-block status-block-error">
          <p>{error}</p>
        </div>
      )}

      {comparacion && prediccion && (
        <>
          <div className="versus-header">
            <div className="versus-equipo">
              <div className="versus-crest">
                <span>{comparacion.equipo_a.nombre.slice(0, 2).toUpperCase()}</span>
              </div>
              <span className="versus-nombre">{comparacion.equipo_a.nombre}</span>
            </div>
            <span className="versus-vs">vs</span>
            <div className="versus-equipo">
              <div className="versus-crest">
                <span>{comparacion.equipo_b.nombre.slice(0, 2).toUpperCase()}</span>
              </div>
              <span className="versus-nombre">{comparacion.equipo_b.nombre}</span>
            </div>
          </div>

          <div className="comparativa-stats">
            <div className="comparativa-fila">
              <span className="comparativa-valor">
                {comparacion.equipo_a.estadisticas.goles_anotados_prom}
              </span>
              <span className="comparativa-etiqueta">Goles prom.</span>
              <span className="comparativa-valor">
                {comparacion.equipo_b.estadisticas.goles_anotados_prom}
              </span>
            </div>
            <div className="comparativa-fila">
              <span className="comparativa-valor">
                {comparacion.equipo_a.estadisticas.corners_favor_prom}
              </span>
              <span className="comparativa-etiqueta">Corners prom.</span>
              <span className="comparativa-valor">
                {comparacion.equipo_b.estadisticas.corners_favor_prom}
              </span>
            </div>
            <div className="comparativa-fila">
              <span className="comparativa-valor">
                {comparacion.equipo_a.estadisticas.tarjetas_prom}
              </span>
              <span className="comparativa-etiqueta">Tarjetas prom.</span>
              <span className="comparativa-valor">
                {comparacion.equipo_b.estadisticas.tarjetas_prom}
              </span>
            </div>
          </div>

          {comparacion.h2h.partidos_encontrados > 0 && (
            <p className="h2h-nota">
              Últimos {comparacion.h2h.partidos_encontrados} enfrentamientos directos:
              promedio de {comparacion.h2h.goles_promedio_total} goles y{" "}
              {comparacion.h2h.corners_promedio_total} corners por partido.
            </p>
          )}

          <section className="panel prediccion-panel">
            <h2 className="panel-title">Predicción del partido</h2>

            <div className="prediccion-grid">
              <div className="prediccion-bloque">
                <span className="prediccion-etiqueta">Goles esperados</span>
                <span className="prediccion-valor">
                  {prediccion.prediccion.goles_totales_esperados}
                </span>
                <span className="prediccion-detalle">
                  +2.5 goles: {Math.round(prediccion.prediccion.prob_mas_2_5_goles * 100)}%
                </span>
              </div>
              <div className="prediccion-bloque">
                <span className="prediccion-etiqueta">Corners esperados</span>
                <span className="prediccion-valor">
                  {prediccion.prediccion.corners_esperados}
                </span>
                <span className="prediccion-detalle">
                  +9.5 corners: {Math.round(prediccion.prediccion.prob_mas_9_5_corners * 100)}%
                </span>
              </div>
              <div className="prediccion-bloque">
                <span className="prediccion-etiqueta">Tarjetas esperadas</span>
                <span className="prediccion-valor">
                  {prediccion.prediccion.tarjetas_esperadas}
                </span>
                <span className="prediccion-detalle">
                  +3.5 tarjetas: {Math.round(prediccion.prediccion.prob_mas_3_5_tarjetas * 100)}%
                </span>
              </div>
            </div>

            {prediccion.prediccion.arbitro && (
              <p className="arbitro-aplicado">
                Ajustado con el historial de {prediccion.prediccion.arbitro.nombre} (
                {prediccion.prediccion.arbitro.partidos_dirigidos} partidos dirigidos,
                promedio de {prediccion.prediccion.arbitro.tarjetas_promedio} tarjetas).
              </p>
            )}
            {arbitro.trim() && !prediccion.prediccion.arbitro && (
              <p className="arbitro-aplicado">
                No encontramos suficiente historial de "{arbitro}" en nuestros datos
                (mínimo 3 partidos), así que la predicción no incluye este ajuste.
              </p>
            )}

            <div className="marcadores-probables">
              <span className="panel-title" style={{ marginBottom: 8 }}>
                Marcadores más probables
              </span>
              <div className="marcadores-lista">
                {prediccion.prediccion.marcadores_mas_probables.map((m) => (
                  <span key={m.marcador} className="marcador-chip">
                    {m.marcador} · {m.probabilidad_pct}%
                  </span>
                ))}
              </div>
            </div>

            <div className="analisis-ia-wrap">
              {!analisis && (
                <button
                  className="analisis-ia-boton"
                  onClick={generarAnalisis}
                  disabled={cargandoAnalisis}
                >
                  {cargandoAnalisis ? "Generando análisis…" : "✨ Generar análisis con IA"}
                </button>
              )}
              {analisis && (
                <div className="analisis-ia-texto">
                  <span className="analisis-ia-etiqueta">Análisis</span>
                  <p>{analisis}</p>
                </div>
              )}
            </div>
          </section>
        </>
      )}
    </>
  );
}

export default function App() {
  const [vista, setVista] = useState("equipos"); // "equipos" | "comparar"
  const [equipoSeleccionado, setEquipoSeleccionado] = useState(null);

  function irAEquipos() {
    setVista("equipos");
    setEquipoSeleccionado(null);
  }

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
              className={`nav-item ${vista === "equipos" ? "active" : ""}`}
              onClick={irAEquipos}
            >
              Equipos
            </span>
            <span
              className={`nav-item ${vista === "comparar" ? "active" : ""}`}
              onClick={() => setVista("comparar")}
            >
              Comparar
            </span>
          </nav>
        </div>
      </header>

      <main className="content">
        {vista === "comparar" ? (
          <VistaComparador />
        ) : equipoSeleccionado ? (
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
