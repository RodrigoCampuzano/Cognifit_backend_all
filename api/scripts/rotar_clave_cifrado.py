#!/usr/bin/env python3
"""Rota DB_ENCRYPTION_KEY: descifra con la clave vieja y vuelve a cifrar con la nueva.

POR QUÉ HACE FALTA UN SCRIPT

Los demás secretos se rotan cambiando una variable de entorno. Este no: los
datos guardados están cifrados **con** la clave, así que reemplazarla sin más
deja los nombres de los alumnos ilegibles para siempre. No hay forma de
recuperarlos después.

QUÉ CIFRA EL SISTEMA

Una sola columna, `academic.students.full_name`, con `pgp_sym_encrypt` de
pgcrypto. El script la busca dinámicamente en vez de asumirlo, para que agregar
otra columna cifrada no lo deje desactualizado en silencio.

CÓMO USARLO

    # 1. Ver qué haría, sin tocar nada (por defecto)
    python rotar_clave_cifrado.py

    # 2. Aplicar
    python rotar_clave_cifrado.py --aplicar

Variables necesarias:

    NEON_DSN          cadena de conexión
    CLAVE_VIEJA       la que está en uso
    CLAVE_NUEVA       la de reemplazo

DESPUÉS DE CORRERLO hay que actualizar DB_ENCRYPTION_KEY en Railway. Entre el
final del script y ese cambio, la aplicación no puede leer los nombres: conviene
hacerlo seguido y fuera de horario de clase.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg


async def columnas_cifradas(con: asyncpg.Connection) -> list[tuple[str, str, str]]:
    """Columnas BYTEA que además se descifran correctamente con la clave vieja.

    Se comprueba el descifrado en lugar de confiar en el tipo: una columna
    BYTEA puede guardar cualquier binario, y aplicarle una rotación a algo que
    no está cifrado lo destruiría.
    """
    filas = await con.fetch(
        """
        SELECT table_schema, table_name, column_name
        FROM information_schema.columns
        WHERE data_type = 'bytea'
          AND table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY 1, 2, 3
        """
    )
    return [(f["table_schema"], f["table_name"], f["column_name"]) for f in filas]


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--aplicar",
        action="store_true",
        help="Escribe los cambios. Sin esto solo informa qué haría.",
    )
    args = p.parse_args()

    faltan = [v for v in ("NEON_DSN", "CLAVE_VIEJA", "CLAVE_NUEVA") if not os.environ.get(v)]
    if faltan:
        print(f"Faltan variables de entorno: {', '.join(faltan)}", file=sys.stderr)
        return 2

    vieja = os.environ["CLAVE_VIEJA"]
    nueva = os.environ["CLAVE_NUEVA"]
    if vieja == nueva:
        print("La clave nueva es igual a la vieja; no hay nada que rotar.", file=sys.stderr)
        return 2

    con = await asyncpg.connect(os.environ["NEON_DSN"])
    try:
        objetivos = []
        for esquema, tabla, col in await columnas_cifradas(con):
            total = await con.fetchval(
                f"SELECT count(*) FROM {esquema}.{tabla} WHERE {col} IS NOT NULL"
            )
            if not total:
                continue
            # ¿Está cifrada con la clave vieja? Si no descifra, no se toca.
            try:
                legibles = await con.fetchval(
                    f"""
                    SELECT count(*) FROM {esquema}.{tabla}
                    WHERE {col} IS NOT NULL
                      AND pgp_sym_decrypt({col}, $1)::text IS NOT NULL
                    """,
                    vieja,
                )
            except asyncpg.PostgresError as exc:
                print(f"  {esquema}.{tabla}.{col}: NO se descifra con la clave vieja ({type(exc).__name__})")
                print("     se omite — rotarla destruiría el dato")
                continue

            objetivos.append((esquema, tabla, col, total))
            print(f"  {esquema}.{tabla}.{col}: {legibles} de {total} filas legibles con la clave vieja")
            if legibles != total:
                print("     ATENCIÓN: hay filas que no descifran. Revisar antes de aplicar.")
                return 1

        if not objetivos:
            print("\nNo se encontró ninguna columna cifrada con la clave vieja.")
            return 1

        if not args.aplicar:
            print("\nSimulación. Nada se modificó. Volver a correr con --aplicar.")
            return 0

        # Todo en una transacción: si algo falla a mitad, no queda un estado
        # donde una tabla usa la clave nueva y otra la vieja.
        async with con.transaction():
            for esquema, tabla, col, total in objetivos:
                n = await con.fetchval(
                    f"""
                    WITH act AS (
                        UPDATE {esquema}.{tabla}
                           SET {col} = pgp_sym_encrypt(pgp_sym_decrypt({col}, $1)::text, $2)
                         WHERE {col} IS NOT NULL
                        RETURNING 1
                    )
                    SELECT count(*) FROM act
                    """,
                    vieja,
                    nueva,
                )
                print(f"  {esquema}.{tabla}.{col}: {n} filas recifradas")

                # Verificación dentro de la misma transacción: si el dato no se
                # lee con la clave nueva, se aborta y no queda nada roto.
                ok = await con.fetchval(
                    f"""
                    SELECT count(*) FROM {esquema}.{tabla}
                    WHERE {col} IS NOT NULL
                      AND pgp_sym_decrypt({col}, $1)::text IS NOT NULL
                    """,
                    nueva,
                )
                if ok != total:
                    raise RuntimeError(
                        f"{esquema}.{tabla}.{col}: solo {ok} de {total} se leen con la "
                        "clave nueva. Se revierte todo."
                    )
                print(f"     verificado: {ok} de {total} legibles con la clave nueva")

        print("\nListo. Ahora hay que actualizar DB_ENCRYPTION_KEY en Railway.")
        print("Hasta que se actualice, la aplicación no puede leer los nombres.")
        return 0
    finally:
        await con.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
