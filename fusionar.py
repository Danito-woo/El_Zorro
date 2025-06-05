#!/usr/bin/env python3
import os
import re
import shutil
import sys
from collections import defaultdict
from colorama import init, Fore, Style

# Inicializar colores en Windows
init(autoreset=True)

# Tokens que NO cuentan para coincidencias
STOPWORDS = {'page', 'libro', 'commision', 'commission', 'reward'}

# Patrón para detectar ficheros manifest
MANIFEST_RE = re.compile(r'.*manifest.*\.txt$', re.IGNORECASE)

def normalizar_nombre(nombre):
    s = nombre.replace('_', ' ')
    s = re.sub(r'[^A-Za-z0-9 ]+', '', s)
    tokens = s.lower().split()
    return [t for t in tokens if not t.isdigit() and t not in STOPWORDS]

def encontrar_comunes(n1, n2):
    p1, p2 = normalizar_nombre(n1), normalizar_nombre(n2)
    comunes = set()
    for i in range(len(p1)):
        for j in range(len(p2)):
            k = 0
            while i+k < len(p1) and j+k < len(p2) and p1[i+k] == p2[j+k]:
                k += 1
                if k >= 3 or (k >= 2 and i == j):
                    comunes.add(' '.join(p1[i:i+k]))
    return list(comunes)

def agrupar_carpetas_unicas(raiz):
    carpetas = []
    for root, dirs, _ in os.walk(raiz):
        for d in dirs:
            carpetas.append(os.path.join(root, d))

    grupos, usadas = [], set()
    for idx, ci in enumerate(carpetas):
        if ci in usadas: continue
        ni = os.path.basename(ci)
        grupo, todas = [ci], []
        for cj in carpetas[idx+1:]:
            if cj in usadas: continue
            com = encontrar_comunes(ni, os.path.basename(cj))
            if com:
                grupo.append(cj)
                todas.extend(com)
        if len(grupo) > 1:
            usadas.update(grupo)
            grupos.append((max(set(todas), key=len), grupo))
    return grupos

def mostrar_grupos(grupos):
    print(Fore.CYAN + "\n=== FUSIONES SUGERIDAS ===" + Style.RESET_ALL)
    for nombre, rutas in grupos:
        print(Fore.MAGENTA + f"\nFusión: '{nombre}'" + Style.RESET_ALL)
        for r in rutas:
            print("  " + Fore.YELLOW + r + Style.RESET_ALL)

def fusionar_y_resumir(grupos):
    confirm = input(Fore.CYAN + "\n¿Procedemos? (sí/no): " + Style.RESET_ALL).strip().lower()
    if confirm != 'sí':
        print(Fore.RED + "⚠️ Operación cancelada." + Style.RESET_ALL)
        return

    resumen = []
    for nombre, rutas in grupos:
        padre = os.path.dirname(rutas[0])
        nueva = os.path.join(padre, nombre.replace(' ', '_'))
        os.makedirs(nueva, exist_ok=True)

        moved_count = 0
        manifest_entries = []
        seen_entries = set()

        # Recolectar y mover
        for carpeta in rutas:
            for item in os.listdir(carpeta):
                src = os.path.join(carpeta, item)
                dst = os.path.join(nueva, item)

                # MANIFEST: recolectar contenido y luego eliminar
                if MANIFEST_RE.match(item):
                    try:
                        with open(src, 'r', encoding='utf-8') as mf:
                            for line in mf:
                                line = line.rstrip('\n')
                                # saltar encabezados o separadores
                                if line.startswith('#') or set(line) <= {'-', ' '}:
                                    continue
                                if line and line not in seen_entries:
                                    manifest_entries.append(line)
                                    seen_entries.add(line)
                    except Exception:
                        pass
                    continue

                # Mover ficheros normales
                if not os.path.exists(dst):
                    try:
                        shutil.move(src, dst)
                        moved_count += 1
                    except Exception:
                        pass

            # tras procesar, eliminar posibles manifest y luego carpeta
            for item in os.listdir(carpeta):
                path = os.path.join(carpeta, item)
                if MANIFEST_RE.match(item):
                    try: os.remove(path)
                    except: pass
            try:
                os.rmdir(carpeta)
            except:
                pass

        # escribir manifest fusionado
        if manifest_entries:
            mfpath = os.path.join(nueva, '_manifest.txt')
            try:
                with open(mfpath, 'w', encoding='utf-8') as mf:
                    mf.write('# Mapping: Sequential Filename : Original Filename (PostID: ...)\n')
                    mf.write('------------------------------------------------------------\n')
                    for entry in manifest_entries:
                        mf.write(entry + '\n')
            except Exception:
                pass

        print(Fore.GREEN + f"✅ Fusionado '{nombre}' ({moved_count} ítems) → {nueva}" + Style.RESET_ALL)
        resumen.append((nueva, len(rutas)))

    # Resumen final
    print(Fore.CYAN + "\n=== RESUMEN FINAL ===" + Style.RESET_ALL)
    for nueva, count in resumen:
        print(Fore.GREEN + f"• {os.path.basename(nueva)}:" + Style.RESET_ALL +
              f" {count} carpetas fusionadas → {nueva}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(Fore.RED + "Uso: python fusion_carpetas.py <ruta_carpeta_raíz>" + Style.RESET_ALL)
        sys.exit(1)
    raiz = sys.argv[1]
    if not os.path.isdir(raiz):
        print(Fore.RED + "❌ Ruta inválida." + Style.RESET_ALL)
        sys.exit(1)

    grupos = agrupar_carpetas_unicas(raiz)
    if not grupos:
        print(Fore.GREEN + "✔️ No se encontraron carpetas para fusionar." + Style.RESET_ALL)
    else:
        mostrar_grupos(grupos)
        fusionar_y_resumir(grupos)
