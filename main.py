"""
ScorePro Web — Backend / API propia
Servidor FastAPI que lee de la base de datos Neon y expone endpoints REST para
consultar equipos, comparaciones y predicciones.

Variables de entorno requeridas:
- DATABASE_URL -> connection string de Neon (la misma que usa el job de ingesta)
"""

import os
import psycopg2
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from prediction_engine import calcular_stats_equipo, calcular_h2h, calcular_stats_arbitro, generar_prediccion

DATABASE_URL = os.environ.get("DATABASE_URL")

app = FastAPI(title="ScorePro Web API", version="1.0")

# Permite que el frontend (en otro dominio, ej. Vercel) pueda llamar a este backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en producción se puede restringir al dominio del frontend
    allow_methods=["GET"],
    allow_headers=["*"],
)


def conectar_db():
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL no está configurada en el servidor.")
    return psycopg2.connect(DATABASE_URL)


@app.get("/")
def raiz():
    return {"mensaje": "ScorePro Web API funcionando.", "docs": "/docs"}


@app.get("/equipos")
def listar_equipos(liga: str | None = Query(default=None, description="Filtrar por id de liga, ej. 140")):
    """Devuelve el listado de equipos guardados, opcionalmente filtrado por liga."""
    conn = conectar_db()
    try:
        with conn.cursor() as cur:
            if liga:
                cur.execute(
                    "select id, nombre, liga, pais, logo_url, temporada from equipos where liga = %s order by nombre",
                    (liga,),
                )
            else:
                cur.execute("select id, nombre, liga, pais, logo_url, temporada from equipos order by nombre")
            filas = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "id": f[0], "nombre": f[1], "liga": f[2], "pais": f[3],
            "logo_url": f[4], "temporada": f[5],
        }
        for f in filas
    ]


@app.get("/equipos/{equipo_id}")
def ficha_equipo(equipo_id: int):
    """Ficha de un equipo: datos básicos + estadísticas (generales, local, visitante, forma)."""
    conn = conectar_db()
    try:
        with conn.cursor() as cur:
            cur.execute("select id, nombre, liga, pais, logo_url, temporada from equipos where id = %s", (equipo_id,))
            fila = cur.fetchone()
        if not fila:
            raise HTTPException(status_code=404, detail="Equipo no encontrado.")

        stats = calcular_stats_equipo(conn, equipo_id)
    finally:
        conn.close()

    return {
        "id": fila[0], "nombre": fila[1], "liga": fila[2], "pais": fila[3],
        "logo_url": fila[4], "temporada": fila[5],
        "estadisticas": stats,
    }


@app.get("/comparar")
def comparar_equipos(a: int = Query(..., description="id del equipo A"), b: int = Query(..., description="id del equipo B")):
    """Compara dos equipos: estadísticas de cada uno + historial de enfrentamientos (H2H)."""
    conn = conectar_db()
    try:
        with conn.cursor() as cur:
            cur.execute("select id, nombre, logo_url from equipos where id in (%s, %s)", (a, b))
            filas = {f[0]: {"id": f[0], "nombre": f[1], "logo_url": f[2]} for f in cur.fetchall()}

        if a not in filas or b not in filas:
            raise HTTPException(status_code=404, detail="Uno o ambos equipos no fueron encontrados.")

        stats_a = calcular_stats_equipo(conn, a)
        stats_b = calcular_stats_equipo(conn, b)
        h2h = calcular_h2h(conn, a, b)
    finally:
        conn.close()

    return {
        "equipo_a": {**filas[a], "estadisticas": stats_a},
        "equipo_b": {**filas[b], "estadisticas": stats_b},
        "h2h": h2h,
    }


@app.get("/prediccion")
def prediccion_partido(
    a: int = Query(..., description="id del equipo local"),
    b: int = Query(..., description="id del equipo visitante"),
    arbitro: str | None = Query(default=None, description="Nombre del árbitro asignado (opcional)"),
):
    """Genera la predicción de un partido entre el equipo A (local) y el equipo B (visitante).
    Si se indica el nombre del árbitro asignado, se usa su historial de tarjetas como ajuste."""
    conn = conectar_db()
    try:
        with conn.cursor() as cur:
            cur.execute("select id, nombre from equipos where id in (%s, %s)", (a, b))
            filas = {f[0]: f[1] for f in cur.fetchall()}

        if a not in filas or b not in filas:
            raise HTTPException(status_code=404, detail="Uno o ambos equipos no fueron encontrados.")

        stats_a = calcular_stats_equipo(conn, a)
        stats_b = calcular_stats_equipo(conn, b)
        h2h = calcular_h2h(conn, a, b)
        stats_arbitro = calcular_stats_arbitro(conn, arbitro) if arbitro else None
        prediccion = generar_prediccion(stats_a, stats_b, h2h, condicion_a="local", stats_arbitro=stats_arbitro)
    finally:
        conn.close()

    return {
        "equipo_local": {"id": a, "nombre": filas[a]},
        "equipo_visitante": {"id": b, "nombre": filas[b]},
        "prediccion": prediccion,
    }
