"""Catálogo ficticio ampliado. Formato: artista -> álbumes -> canciones.

Para agregar más, añade una entrada a CATALOG; los ids y duraciones se generan solos.
"""

from __future__ import annotations

import re
import unicodedata
import zlib
from typing import Any

# (artista, género, [(álbum, [canciones])])
CATALOG: list[tuple[str, str, list[tuple[str, list[str]]]]] = [
    ("Neón Sur", "electronic", [
        ("Autopista Violeta", ["Pulso Nocturno", "Kilómetro Cero", "Luces de Peaje", "Última Salida"]),
        ("Frecuencia Rota", ["Señal Perdida", "Eco Sintético", "Onda Corta", "Modulación"]),
    ]),
    ("Dunas de Cristal", "electronic", [
        ("Espejismo Digital", ["Oasis Binario", "Arena en Fase", "Horizonte Líquido", "Miragem"]),
        ("Rotor", ["Aspas", "Turbina Lenta", "Viento Solar", "Cierre de Ciclo"]),
    ]),
    ("Pixel Lunar", "electronic", [
        ("Nivel Uno", ["Inicio Rápido", "Moneda Extra", "Jefe Final", "Créditos"]),
        ("Modo Noche", ["Cielo de Ocho Bits", "Luna Retro", "Guardar Partida", "Continuar"]),
    ]),
    ("Brisa de Marzo", "indie", [
        ("Cartas sin Remitente", ["Tinta Azul", "Buzón Vacío", "Estampilla", "Domicilio Conocido"]),
        ("Tardes de Lluvia", ["Paraguas Roto", "Charco de Luz", "Ventana Empañada", "Café Tibio"]),
    ]),
    ("Los Faroles", "indie", [
        ("Calle Abajo", ["Esquina Norte", "Farol Prendido", "Banqueta Larga", "Casa de Huéspedes"]),
        ("Vuelta al Barrio", ["Pan Dulce", "Tianguis", "Sábado Eterno", "Regreso a Casa"]),
    ]),
    ("Mar de Fondo", "indie", [
        ("Marea Baja", ["Orilla", "Caracola", "Bajamar", "Faro Apagado"]),
        ("Salitre", ["Sal en los Labios", "Barco de Papel", "Costa Vacía", "Deriva"]),
    ]),
    ("Cuarteto Aurora", "classical", [
        ("Amanecer en Cuerdas", ["Allegro del Alba", "Adagio de Rocío", "Scherzo Matinal", "Final Luminoso"]),
        ("Noches de Cámara", ["Nocturno Uno", "Nocturno Dos", "Intermezzo", "Despedida en Re"]),
    ]),
    ("Orquesta del Valle", "classical", [
        ("Sinfonía de los Cerros", ["Primer Movimiento", "Andante Montañés", "Danza del Viento", "Coral Final"]),
        ("Suite Campestre", ["Preludio de Trigo", "Gavota del Río", "Minueto", "Rondó del Pastor"]),
    ]),
    ("Trío Medianoche", "jazz", [
        ("Humo y Vinilo", ["Sala Pequeña", "Bourbon Lento", "Solo de Contrabajo", "Última Ronda"]),
        ("Acordes Prestados", ["Blues Azul Pálido", "Escalera de Incendios", "Bossa Nublada", "Swing de Bolsillo"]),
    ]),
    ("Ámbar Quinteto", "jazz", [
        ("Tarde Dorada", ["Miel y Limón", "Paseo Largo", "Trompeta al Sol", "Atardecer en Fa"]),
        ("Improvisos", ["Primera Toma", "Cambio de Tempo", "Dúo Inesperado", "Cierre Libre"]),
    ]),
    ("Rimas del Barrio", "hip-hop", [
        ("Concreto", ["Cemento Fresco", "Terraza", "Ritmo de Obra", "Azotea"]),
        ("Letras en la Pared", ["Spray y Tinta", "Verso Callejero", "Micrófono Prestado", "Sin Filtro"]),
    ]),
    ("Kaos Verbal", "hip-hop", [
        ("Frase Corta", ["Cuatro Compases", "Rima Rápida", "Beat de Cocina", "Plan B"]),
        ("Contraflow", ["A Contratiempo", "Doble Tempo", "Cinta Gastada", "Rewind"]),
    ]),
    ("Luna Candela", "pop", [
        ("Chispa", ["Fuego Artificial", "Brillo en los Ojos", "Bailar Sin Parar", "Estrella Fugaz"]),
        ("Dulce Voltaje", ["Corazón Eléctrico", "Azúcar Morena", "Verano Infinito", "Dime que Sí"]),
    ]),
    ("Versos de Papel", "pop", [
        ("Cuaderno Rosa", ["Primera Página", "Margen Izquierdo", "Tachones", "Dedicatoria"]),
        ("Tinta Fresca", ["Estribillo Nuevo", "Canción de Domingo", "Letra Pequeña", "Fin de Capítulo"]),
    ]),
    ("Granito Rojo", "rock", [
        ("Roca Viva", ["Amplificador al Diez", "Pared de Sonido", "Distorsión", "Sin Tregua"]),
        ("Camino de Tierra", ["Carretera Seca", "Motor Caliente", "Polvo y Gasolina", "Horizonte Rojo"]),
    ]),
    ("Los Cometas Grises", "rock", [
        ("Cola de Luz", ["Impacto", "Órbita Elíptica", "Noche sin Luna", "Cráter"]),
        ("Garage Sessions", ["Ensayo Uno", "Cables Cruzados", "Vecino Molesto", "Toma Final"]),
    ]),
    ("Humo Violeta", "alternative", [
        ("Niebla Densa", ["Visibilidad Cero", "Eco en el Túnel", "Silueta", "Disolver"]),
        ("Contraluz", ["Sombra Larga", "Filtro Gris", "Reflejo Invertido", "Apagón"]),
    ]),
    ("Océano Paralelo", "alternative", [
        ("Corrientes", ["Marea Cruzada", "Profundidad", "Resaca", "Isla Flotante"]),
        ("Otra Dimensión", ["Puerta Lateral", "Tiempo Doblado", "Línea Alterna", "Regreso Parcial"]),
    ]),
]


def slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def expand() -> list[dict[str, Any]]:
    """Convierte CATALOG en filas planas (artista, álbum, canción) como las espera el script."""
    rows: list[dict[str, Any]] = []
    for artist, genre, albums in CATALOG:
        for album, songs in albums:
            for title in songs:
                rows.append({
                    "id": f"artist-{slug(artist)}",
                    "name": artist,
                    "albumId": f"album-{slug(artist)}-{slug(album)}",
                    "albumTitle": album,
                    "songId": f"song-{slug(artist)}-{slug(title)}",
                    "title": title,
                    "genre": genre,
                    "durationSeconds": 150 + zlib.crc32(title.encode()) % 150,
                })
    return rows
