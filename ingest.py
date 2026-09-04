"""
ScorePro Web — Job de ingesta de datos
Trae partidos, equipos y estadísticas desde API-Football y los guarda en Neon (PostgreSQL).

Este script está pensado para correr automáticamente 1 vez al día vía GitHub Actions.
NUNCA lo ejecutes en un loop ni lo llames desde el frontend/backend en cada request:
API-Football tiene un límite de 100 solicitudes/día en el plan gratis.

Variables de entorno requeridas (se configuran como Secrets en GitHub):
- API_FOOTBALL_KEY   -> tu API key de API-Football
- DATABASE_URL       -> connection string de Neon (postgresql://...)
"""

import os
import sys
import time
import requests
import psycopg2
from psycopg2.extras import execute_values

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_FOOTBALL_KEY}

# ------------------------------------------------------------------
# CONFIGURACIÓN: qué ligas y temporada vamos a seguir.
# Empezamos con pocas ligas para no agotar las 100 solicitudes/día.
# IDs oficiales de API-Football (los más comunes):
#   39  = Premier League
#   140 = La Liga
#   135 = Serie A
#   61  = Ligue 1
#   78  = Bundesliga
# ------------------------------------------------------------------
LIGAS_SEGUIDAS = [
    {"id": 140, "nombre": "La Liga"},
]
# IMPORTANTE: los planes gratis de API-Football solo dan acceso a un rango fijo
# de temporadas históricas (confirmado por la propia API: "Free plans do not have
# access to this season, try from 2022 to 2024"). Usamos 2023 por ser una temporada
# completa (2023-2024) dentro de ese rango. Si más adelante se paga un plan superior,
# se puede subir este valor a la temporada actual.
TEMPORADA = 2023

# Límite de seguridad: cuántas solicitudes máximo hace este script por corrida.
# Deja margen sobre el límite diario de 100, para no agotarlo por completo.
MAX_SOLICITUDES_POR_CORRIDA = 70

contador_solicitudes = 0


def llamar_api(endpoint: str, params: dict) -> dict:
    """Hace una solicitud a API-Football, respetando el límite de solicitudes."""
    global contador_solicitudes

    if contador_solicitudes >= MAX_SOLICITUDES_POR_CORRIDA:
        print(f"Límite de {MAX_SOLICITUDES_POR_CORRIDA} solicitudes alcanzado. Deteniendo corrida.")
        return None

    url = f"{API_BASE_URL}/{endpoint}"
    response = requests.get(url, headers=HEADERS, params=params, timeout=30)
    contador_solicitudes += 1

    if response.status_code != 200:
        print(f"Error {response.status_code} al llamar {endpoint}: {response.text[:200]}")
        return None

    data = response.json()

    # Diagnóstico: mostramos siempre cuántos resultados trajo la llamada y si
    # la API reportó algún error/aviso en el cuerpo de la respuesta (esto no
    # cuenta como solicitud extra, es solo para leer los logs).
    n_resultados = len(data.get("response", []))
    errores = data.get("errors")
    print(f"  [debug] {endpoint} params={params} -> {n_resultados} resultados"
          + (f" | errors={errores}" if errores else ""))

    time.sleep(1)  # pausa breve entre llamadas, buena práctica con APIs gratuitas
    return data


def conectar_db():
    return psycopg2.connect(DATABASE_URL)


def guardar_equipos(conn, equipos: list):
    """Inserta o actualiza equipos en la tabla 'equipos'."""
    if not equipos:
        return
    with conn.cursor() as cur:
        query = """
            insert into equipos (id, nombre, liga, pais, logo_url, temporada)
            values %s
            on conflict (id) do update set
                nombre = excluded.nombre,
                logo_url = excluded.logo_url
        """
        valores = [
            (e["id"], e["nombre"], e["liga"], e["pais"], e["logo_url"], e["temporada"])
            for e in equipos
        ]
        execute_values(cur, query, valores)
    conn.commit()
    print(f"  {len(equipos)} equipos guardados/actualizados.")


def guardar_partidos(conn, partidos: list):
    """Inserta o actualiza partidos en la tabla 'partidos'."""
    if not partidos:
        return
    with conn.cursor() as cur:
        query = """
            insert into partidos (
                id, equipo_local_id, equipo_visitante_id, liga, temporada, fecha, arbitro,
                goles_local, goles_visitante, corners_local, corners_visitante,
                tarjetas_amarillas_local, tarjetas_amarillas_visitante,
                tarjetas_rojas_local, tarjetas_rojas_visitante,
                faltas_local, faltas_visitante, finalizado
            )
            values %s
            on conflict (id) do update set
                goles_local = excluded.goles_local,
                goles_visitante = excluded.goles_visitante,
                corners_local = excluded.corners_local,
                corners_visitante = excluded.corners_visitante,
                tarjetas_amarillas_local = excluded.tarjetas_amarillas_local,
                tarjetas_amarillas_visitante = excluded.tarjetas_amarillas_visitante,
                tarjetas_rojas_local = excluded.tarjetas_rojas_local,
                tarjetas_rojas_visitante = excluded.tarjetas_rojas_visitante,
                faltas_local = excluded.faltas_local,
                faltas_visitante = excluded.faltas_visitante,
                finalizado = excluded.finalizado,
                actualizado_en = now()
        """
        valores = [
            (
                p["id"], p["equipo_local_id"], p["equipo_visitante_id"], p["liga"],
                p["temporada"], p["fecha"], p["arbitro"],
                p["goles_local"], p["goles_visitante"],
                p["corners_local"], p["corners_visitante"],
                p["tarjetas_amarillas_local"], p["tarjetas_amarillas_visitante"],
                p["tarjetas_rojas_local"], p["tarjetas_rojas_visitante"],
                p["faltas_local"], p["faltas_visitante"], p["finalizado"],
            )
            for p in partidos
        ]
        execute_values(cur, query, valores)
    conn.commit()
    print(f"  {len(partidos)} partidos guardados/actualizados.")


import re


def obtener_temporada_disponible(liga_id: int) -> int:
    """
    Determina qué temporada usar para esta liga. Intenta primero con TEMPORADA.
    Si la API responde con el error típico de plan gratis
    ("Free plans do not have access to this season, try from AAAA to BBBB"),
    se extrae el rango permitido del propio mensaje y se usa el año más
    reciente de ese rango automáticamente.
    """
    data = llamar_api("teams", {"league": liga_id, "season": TEMPORADA})
    if data is None:
        return TEMPORADA

    errores = data.get("errors")
    if errores and isinstance(errores, dict):
        mensaje = errores.get("plan", "")
        match = re.search(r"from (\d{4}) to (\d{4})", mensaje)
        if match:
            anio_max = int(match.group(2))
            print(f"  Ajustando temporada automáticamente a {anio_max} según el rango permitido por tu plan.")
            return anio_max

    return TEMPORADA



    """Trae los equipos de una liga/temporada desde API-Football."""
    data = llamar_api("teams", {"league": liga_id, "season": temporada})
    if not data or "response" not in data:
        return []

    equipos = []
    for item in data["response"]:
        equipo = item["team"]
        equipos.append({
            "id": equipo["id"],
            "nombre": equipo["name"],
            "liga": str(liga_id),
            "pais": equipo.get("country"),
            "logo_url": equipo.get("logo"),
            "temporada": temporada,
        })
    return equipos


def obtener_equipos_de_liga(liga_id: int, temporada: int) -> list:
    """Trae los equipos de una liga/temporada desde API-Football."""
    data = llamar_api("teams", {"league": liga_id, "season": temporada})
    if not data or "response" not in data:
        return []

    equipos = []
    for item in data["response"]:
        equipo = item["team"]
        equipos.append({
            "id": equipo["id"],
            "nombre": equipo["name"],
            "liga": str(liga_id),
            "pais": equipo.get("country"),
            "logo_url": equipo.get("logo"),
            "temporada": temporada,
        })
    return equipos

def obtener_partidos_de_liga(liga_id: int, temporada: int) -> list:
    """Trae los fixtures (partidos) ya finalizados de una liga/temporada."""
    data = llamar_api("fixtures", {"league": liga_id, "season": temporada, "status": "FT"})
    if not data or "response" not in data:
        return []

    partidos = []
    for item in data["response"]:
        fixture = item["fixture"]
        teams = item["teams"]
        goals = item["goals"]
        # Nota: corners, tarjetas y faltas NO vienen en /fixtures.
        # Requieren una llamada extra a /fixtures/statistics por partido.
        # Para no agotar la cuota, esa llamada se hace en un paso aparte
        # (ver obtener_estadisticas_partido), priorizando partidos recientes.
        partidos.append({
            "id": fixture["id"],
            "equipo_local_id": teams["home"]["id"],
            "equipo_visitante_id": teams["away"]["id"],
            "liga": str(liga_id),
            "temporada": temporada,
            "fecha": fixture["date"],
            "arbitro": fixture.get("referee"),
            "goles_local": goals["home"],
            "goles_visitante": goals["away"],
            "corners_local": None,
            "corners_visitante": None,
            "tarjetas_amarillas_local": None,
            "tarjetas_amarillas_visitante": None,
            "tarjetas_rojas_local": None,
            "tarjetas_rojas_visitante": None,
            "faltas_local": None,
            "faltas_visitante": None,
            "finalizado": True,
        })
    return partidos


def obtener_estadisticas_partido(conn, fixture_id: int):
    """Trae corners, tarjetas y faltas de un partido específico y actualiza la tabla."""
    data = llamar_api("fixtures/statistics", {"fixture": fixture_id})
    if not data or not data.get("response") or len(data["response"]) < 2:
        return

    def extraer(stats_equipo, nombre_stat):
        for s in stats_equipo["statistics"]:
            if s["type"] == nombre_stat:
                return s["value"] if isinstance(s["value"], int) else 0
        return 0

    local = data["response"][0]
    visitante = data["response"][1]

    valores = (
        extraer(local, "Corner Kicks"), extraer(visitante, "Corner Kicks"),
        extraer(local, "Yellow Cards"), extraer(visitante, "Yellow Cards"),
        extraer(local, "Red Cards"), extraer(visitante, "Red Cards"),
        extraer(local, "Fouls"), extraer(visitante, "Fouls"),
        fixture_id,
    )

    with conn.cursor() as cur:
        cur.execute("""
            update partidos set
                corners_local = %s, corners_visitante = %s,
                tarjetas_amarillas_local = %s, tarjetas_amarillas_visitante = %s,
                tarjetas_rojas_local = %s, tarjetas_rojas_visitante = %s,
                faltas_local = %s, faltas_visitante = %s,
                actualizado_en = now()
            where id = %s
        """, valores)
    conn.commit()


def partidos_sin_estadisticas(conn, limite: int) -> list:
    """Devuelve ids de partidos finalizados que aún no tienen corners/tarjetas cargados."""
    with conn.cursor() as cur:
        cur.execute("""
            select id from partidos
            where finalizado = true and corners_local is null
            order by fecha desc
            limit %s
        """, (limite,))
        return [row[0] for row in cur.fetchall()]


def main():
    if not API_FOOTBALL_KEY or not DATABASE_URL:
        print("ERROR: faltan las variables de entorno API_FOOTBALL_KEY y/o DATABASE_URL.")
        sys.exit(1)

    conn = conectar_db()
    print("Conectado a la base de datos.")

    for liga in LIGAS_SEGUIDAS:
        print(f"\nProcesando liga: {liga['nombre']} (id {liga['id']})")

        temporada_real = obtener_temporada_disponible(liga["id"])
        if temporada_real is None:
            print(f"  No se encontró ninguna temporada con datos disponibles para esta liga en tu plan. Se omite.")
            continue
        if temporada_real != TEMPORADA:
            print(f"  Aviso: la temporada configurada ({TEMPORADA}) no tiene datos en tu plan. Usando {temporada_real} en su lugar.")

        equipos = obtener_equipos_de_liga(liga["id"], temporada_real)
        guardar_equipos(conn, equipos)

        partidos = obtener_partidos_de_liga(liga["id"], temporada_real)
        guardar_partidos(conn, partidos)

    # Con lo que quede de cuota, completamos estadísticas (corners/tarjetas/faltas)
    # de los partidos más recientes que aún no las tengan.
    restantes = MAX_SOLICITUDES_POR_CORRIDA - contador_solicitudes
    if restantes > 0:
        pendientes = partidos_sin_estadisticas(conn, restantes)
        print(f"\nCompletando estadísticas de {len(pendientes)} partidos...")
        for fixture_id in pendientes:
            obtener_estadisticas_partido(conn, fixture_id)

    print(f"\nCorrida terminada. Solicitudes usadas a la API: {contador_solicitudes}")
    conn.close()


if __name__ == "__main__":
    main()
