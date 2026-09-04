"""
ScorePro Web — Motor de predicciones
Calcula estadísticas de equipos y genera predicciones de goles, corners y tarjetas
usando un modelo de Poisson, ajustado por condición local/visitante y forma reciente.

Este módulo es independiente del servidor web: recibe una conexión a la base de datos
y devuelve diccionarios de Python con los resultados. Así se puede probar por separado
y reutilizar en cualquier endpoint.
"""

import math
from datetime import datetime, timedelta


# ------------------------------------------------------------------
# PARTE 1: Estadísticas de un equipo (promedios generales, local, visitante, forma)
# ------------------------------------------------------------------

def calcular_stats_equipo(conn, equipo_id: int) -> dict:
    """
    Calcula promedios de un equipo a partir de sus partidos guardados:
    - Generales (todos los partidos)
    - Como local
    - Como visitante
    - Forma reciente (últimos 5 partidos)
    """
    with conn.cursor() as cur:
        # Partidos como local
        cur.execute("""
            select goles_local, goles_visitante, corners_local, corners_visitante,
                   tarjetas_amarillas_local, tarjetas_amarillas_visitante,
                   tarjetas_rojas_local, tarjetas_rojas_visitante, fecha
            from partidos
            where equipo_local_id = %s and finalizado = true
            order by fecha desc
        """, (equipo_id,))
        partidos_local = cur.fetchall()

        # Partidos como visitante
        cur.execute("""
            select goles_local, goles_visitante, corners_local, corners_visitante,
                   tarjetas_amarillas_local, tarjetas_amarillas_visitante,
                   tarjetas_rojas_local, tarjetas_rojas_visitante, fecha
            from partidos
            where equipo_visitante_id = %s and finalizado = true
            order by fecha desc
        """, (equipo_id,))
        partidos_visitante = cur.fetchall()

    def promedio(valores):
        valores_validos = [v for v in valores if v is not None]
        if not valores_validos:
            return 0.0
        return round(sum(valores_validos) / len(valores_validos), 2)

    # Goles anotados/recibidos como local
    goles_anotados_local = [p[0] for p in partidos_local]
    goles_recibidos_local = [p[1] for p in partidos_local]
    corners_favor_local = [p[2] for p in partidos_local]
    corners_contra_local = [p[3] for p in partidos_local]
    tarjetas_local = [
        (p[4] or 0) + (p[6] or 0) if p[4] is not None else None
        for p in partidos_local
    ]

    # Goles anotados/recibidos como visitante
    goles_anotados_visitante = [p[1] for p in partidos_visitante]
    goles_recibidos_visitante = [p[0] for p in partidos_visitante]
    corners_favor_visitante = [p[3] for p in partidos_visitante]
    corners_contra_visitante = [p[2] for p in partidos_visitante]
    tarjetas_visitante = [
        (p[5] or 0) + (p[7] or 0) if p[5] is not None else None
        for p in partidos_visitante
    ]

    # Generales = combinar local + visitante
    goles_anotados_total = goles_anotados_local + goles_anotados_visitante
    goles_recibidos_total = goles_recibidos_local + goles_recibidos_visitante
    corners_favor_total = corners_favor_local + corners_favor_visitante
    tarjetas_total = [t for t in (tarjetas_local + tarjetas_visitante) if t is not None]

    # Forma reciente: combinamos todos los partidos (local+visitante), ordenamos
    # por fecha y tomamos los 5 más recientes para ver la tendencia de goles.
    todos_con_fecha = (
        [(p[8], p[0], "local") for p in partidos_local] +
        [(p[8], p[1], "visitante") for p in partidos_visitante]
    )
    todos_con_fecha.sort(key=lambda x: x[0], reverse=True)
    ultimos_5 = todos_con_fecha[:5]
    goles_forma_reciente = [g for _, g, _ in ultimos_5]

    return {
        "equipo_id": equipo_id,
        "partidos_jugados": len(partidos_local) + len(partidos_visitante),
        "goles_anotados_prom": promedio(goles_anotados_total),
        "goles_recibidos_prom": promedio(goles_recibidos_total),
        "goles_anotados_local_prom": promedio(goles_anotados_local),
        "goles_recibidos_local_prom": promedio(goles_recibidos_local),
        "goles_anotados_visitante_prom": promedio(goles_anotados_visitante),
        "goles_recibidos_visitante_prom": promedio(goles_recibidos_visitante),
        "corners_favor_prom": promedio(corners_favor_total),
        "tarjetas_prom": promedio(tarjetas_total),
        "forma_reciente_goles": goles_forma_reciente,
        "forma_reciente_promedio": promedio(goles_forma_reciente),
    }


def calcular_h2h(conn, equipo_a_id: int, equipo_b_id: int, limite: int = 10) -> dict:
    """Historial de enfrentamientos directos entre dos equipos, en cualquier condición."""
    with conn.cursor() as cur:
        cur.execute("""
            select goles_local, goles_visitante, corners_local, corners_visitante,
                   tarjetas_amarillas_local, tarjetas_amarillas_visitante,
                   tarjetas_rojas_local, tarjetas_rojas_visitante,
                   equipo_local_id, fecha
            from partidos
            where finalizado = true
              and ((equipo_local_id = %s and equipo_visitante_id = %s)
                or (equipo_local_id = %s and equipo_visitante_id = %s))
            order by fecha desc
            limit %s
        """, (equipo_a_id, equipo_b_id, equipo_b_id, equipo_a_id, limite))
        partidos = cur.fetchall()

    if not partidos:
        return {"partidos_encontrados": 0, "goles_promedio_total": 0.0, "corners_promedio_total": 0.0}

    total_goles = []
    total_corners = []
    for p in partidos:
        gl, gv, cl, cv = p[0], p[1], p[2], p[3]
        if gl is not None and gv is not None:
            total_goles.append(gl + gv)
        if cl is not None and cv is not None:
            total_corners.append(cl + cv)

    return {
        "partidos_encontrados": len(partidos),
        "goles_promedio_total": round(sum(total_goles) / len(total_goles), 2) if total_goles else 0.0,
        "corners_promedio_total": round(sum(total_corners) / len(total_corners), 2) if total_corners else 0.0,
    }


# ------------------------------------------------------------------
# PARTE 2: Modelo de predicción (Poisson)
# ------------------------------------------------------------------

def _probabilidad_poisson(lam: float, k: int) -> float:
    """P(X = k) para una variable con distribución Poisson de media lam."""
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def _probabilidad_mayor_a(lam: float, umbral: float) -> float:
    """
    P(X > umbral) sumando la Poisson desde 0 hasta el entero más cercano al umbral,
    y restando de 1. Útil para calcular over/under (ej. +2.5 goles).
    """
    k_max = int(umbral) + 1
    acumulado = sum(_probabilidad_poisson(lam, k) for k in range(0, k_max))
    return round(1 - acumulado, 3)


def generar_prediccion(stats_a: dict, stats_b: dict, h2h: dict, condicion_a: str = "local") -> dict:
    """
    Genera la predicción de un partido entre equipo_a y equipo_b.
    condicion_a: "local" o "visitante" — de qué lado juega el equipo_a.

    Metodología (Poisson ajustado):
    1. Fuerza de ataque/defensa de cada equipo en su condición (local/visitante).
    2. Goles esperados = ataque del equipo x debilidad defensiva del rival.
    3. Se pondera con la forma reciente (peso menor) y con el historial H2H (peso menor).
    4. Se aplica Poisson sobre el resultado combinado para sacar probabilidades.
    """
    if condicion_a == "local":
        ataque_a = stats_a["goles_anotados_local_prom"]
        defensa_b = stats_b["goles_recibidos_visitante_prom"]
        ataque_b = stats_b["goles_anotados_visitante_prom"]
        defensa_a = stats_a["goles_recibidos_local_prom"]
    else:
        ataque_a = stats_a["goles_anotados_visitante_prom"]
        defensa_b = stats_b["goles_recibidos_local_prom"]
        ataque_b = stats_b["goles_anotados_local_prom"]
        defensa_a = stats_a["goles_recibidos_visitante_prom"]

    # Goles esperados base: promedio entre el ataque propio y la debilidad defensiva rival.
    goles_esperados_a = round((ataque_a + defensa_b) / 2, 2) if (ataque_a or defensa_b) else 1.0
    goles_esperados_b = round((ataque_b + defensa_a) / 2, 2) if (ataque_b or defensa_a) else 1.0

    # Ajuste leve por forma reciente (20% de peso) y por historial H2H (10% de peso),
    # evitando que un solo factor domine la predicción por completo.
    if stats_a["forma_reciente_promedio"] > 0:
        goles_esperados_a = round(goles_esperados_a * 0.8 + stats_a["forma_reciente_promedio"] * 0.2, 2)
    if stats_b["forma_reciente_promedio"] > 0:
        goles_esperados_b = round(goles_esperados_b * 0.8 + stats_b["forma_reciente_promedio"] * 0.2, 2)

    if h2h["partidos_encontrados"] >= 3:
        h2h_promedio_por_equipo = h2h["goles_promedio_total"] / 2
        goles_esperados_a = round(goles_esperados_a * 0.9 + h2h_promedio_por_equipo * 0.1, 2)
        goles_esperados_b = round(goles_esperados_b * 0.9 + h2h_promedio_por_equipo * 0.1, 2)

    # Evitar valores en cero que rompan el cálculo de Poisson.
    goles_esperados_a = max(goles_esperados_a, 0.1)
    goles_esperados_b = max(goles_esperados_b, 0.1)

    goles_totales_esperados = round(goles_esperados_a + goles_esperados_b, 2)

    # Corners y tarjetas: promedio simple entre ambos equipos (más simple que goles,
    # ya que no hay tanta literatura de "ataque/defensa" para estos eventos).
    corners_esperados = round(
        (stats_a["corners_favor_prom"] + stats_b["corners_favor_prom"]), 2
    ) or 9.0
    tarjetas_esperadas = round(
        (stats_a["tarjetas_prom"] + stats_b["tarjetas_prom"]), 2
    ) or 4.0

    # Matriz de probabilidades de marcador exacto (0-0 hasta 5-5)
    matriz_marcadores = []
    for goles_a in range(0, 6):
        for goles_b in range(0, 6):
            prob = (
                _probabilidad_poisson(goles_esperados_a, goles_a) *
                _probabilidad_poisson(goles_esperados_b, goles_b)
            )
            matriz_marcadores.append({
                "marcador": f"{goles_a}-{goles_b}",
                "probabilidad": round(prob, 4),
            })
    marcadores_mas_probables = sorted(
        matriz_marcadores, key=lambda m: m["probabilidad"], reverse=True
    )[:3]

    return {
        "goles_esperados_a": goles_esperados_a,
        "goles_esperados_b": goles_esperados_b,
        "goles_totales_esperados": goles_totales_esperados,
        "prob_mas_2_5_goles": _probabilidad_mayor_a(goles_totales_esperados, 2.5),
        "corners_esperados": corners_esperados,
        "prob_mas_9_5_corners": _probabilidad_mayor_a(corners_esperados, 9.5),
        "tarjetas_esperadas": tarjetas_esperadas,
        "prob_mas_3_5_tarjetas": _probabilidad_mayor_a(tarjetas_esperadas, 3.5),
        "marcadores_mas_probables": [
            {"marcador": m["marcador"], "probabilidad_pct": round(m["probabilidad"] * 100, 1)}
            for m in marcadores_mas_probables
        ],
    }
