#!/usr/bin/env python3
"""
Script de utilidad para gestionar el historial de partidos enviados
"""

import os
import json
import time
from datetime import datetime

def show_duplicates_menu():
    """Muestra el menú de opciones para gestionar duplicados"""
    print("=" * 60)
    print("   GESTOR DE HISTORIAL DE PARTIDOS ENVIADOS")
    print("=" * 60)
    print("1. Ver historial actual")
    print("2. Limpiar historial (eliminar registros antiguos)")
    print("3. Resetear completamente el historial")
    print("4. Ver estadísticas del historial")
    print("5. Salir")
    print("=" * 60)

def load_sent_matches():
    """Carga el archivo de partidos enviados"""
    sent_matches_file = "sent_matches.json"
    try:
        if os.path.exists(sent_matches_file):
            with open(sent_matches_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"❌ Error al cargar archivo: {e}")
        return {}

def save_sent_matches(sent_matches):
    """Guarda el archivo de partidos enviados"""
    sent_matches_file = "sent_matches.json"
    try:
        with open(sent_matches_file, 'w', encoding='utf-8') as f:
            json.dump(sent_matches, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error al guardar archivo: {e}")
        return False

def show_current_history():
    """Muestra el historial actual"""
    sent_matches = load_sent_matches()
    current_time = time.time()
    
    if not sent_matches:
        print("📋 Historial de partidos enviados: VACÍO")
        return
    
    print(f"📋 Historial de partidos enviados ({len(sent_matches)} registros):")
    print("-" * 80)
    
    # Ordenar por tiempo (más recientes primero)
    sorted_matches = sorted(sent_matches.items(), key=lambda x: x[1], reverse=True)
    
    for i, (match_hash, timestamp) in enumerate(sorted_matches, 1):
        time_diff = current_time - timestamp
        hours_diff = time_diff / 3600
        
        if hours_diff < 1:
            time_str = f"{time_diff/60:.0f}min"
        else:
            time_str = f"{hours_diff:.1f}h"
        
        date_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
        print(f"   {i:2d}. Hash: {match_hash[:12]}... | {date_str} (hace {time_str})")

def clean_old_records():
    """Limpia registros antiguos"""
    sent_matches = load_sent_matches()
    if not sent_matches:
        print("ℹ️ No hay registros para limpiar")
        return
    
    print("🧹 Limpieza de registros antiguos...")
    print("¿Cuántas horas de antigüedad máximo? (por defecto 24): ", end="")
    
    try:
        hours_input = input().strip()
        hours_to_keep = int(hours_input) if hours_input else 24
    except ValueError:
        hours_to_keep = 24
    
    current_time = time.time()
    cutoff_time = current_time - (hours_to_keep * 3600)
    
    original_count = len(sent_matches)
    cleaned_matches = {}
    
    for match_hash, timestamp in sent_matches.items():
        if timestamp > cutoff_time:
            cleaned_matches[match_hash] = timestamp
    
    removed_count = original_count - len(cleaned_matches)
    
    if save_sent_matches(cleaned_matches):
        print(f"✅ Limpieza completada: {removed_count} registros eliminados")
        print(f"📊 Registros restantes: {len(cleaned_matches)}")
    else:
        print("❌ Error al guardar los cambios")

def reset_history():
    """Resetea completamente el historial"""
    print("⚠️ ¿Estás seguro de que quieres resetear completamente el historial?")
    print("   Esto eliminará TODOS los registros de partidos enviados.")
    print("   (s/N): ", end="")
    
    response = input().strip().lower()
    if response in ['s', 'si', 'sí', 'y', 'yes']:
        sent_matches_file = "sent_matches.json"
        try:
            if os.path.exists(sent_matches_file):
                os.remove(sent_matches_file)
                print("✅ Historial reseteado completamente")
            else:
                print("ℹ️ No existe archivo de historial para resetear")
        except Exception as e:
            print(f"❌ Error al resetear: {e}")
    else:
        print("❌ Operación cancelada")

def show_statistics():
    """Muestra estadísticas del historial"""
    sent_matches = load_sent_matches()
    if not sent_matches:
        print("📊 No hay estadísticas disponibles (historial vacío)")
        return
    
    current_time = time.time()
    timestamps = list(sent_matches.values())
    
    # Estadísticas básicas
    total_records = len(sent_matches)
    oldest_time = min(timestamps)
    newest_time = max(timestamps)
    
    oldest_age = (current_time - oldest_time) / 3600
    newest_age = (current_time - newest_time) / 3600
    
    # Registros por hora (últimas 24 horas)
    last_24h = current_time - (24 * 3600)
    records_24h = sum(1 for ts in timestamps if ts > last_24h)
    
    print("📊 ESTADÍSTICAS DEL HISTORIAL")
    print("-" * 40)
    print(f"Total de registros: {total_records}")
    print(f"Registros en últimas 24h: {records_24h}")
    print(f"Registro más antiguo: {oldest_age:.1f} horas")
    print(f"Registro más reciente: {newest_age:.1f} horas")
    
    # Distribución por horas
    print("\n📈 Distribución por horas:")
    for i in range(24):
        hour_start = current_time - ((i + 1) * 3600)
        hour_end = current_time - (i * 3600)
        count = sum(1 for ts in timestamps if hour_start < ts <= hour_end)
        if count > 0:
            print(f"   Hace {i}h: {count} registros")

def main():
    """Función principal del gestor"""
    while True:
        show_duplicates_menu()
        
        try:
            choice = input("Selecciona una opción (1-5): ").strip()
            
            if choice == '1':
                show_current_history()
            elif choice == '2':
                clean_old_records()
            elif choice == '3':
                reset_history()
            elif choice == '4':
                show_statistics()
            elif choice == '5':
                print("👋 ¡Hasta luego!")
                break
            else:
                print("❌ Opción inválida. Por favor selecciona 1-5.")
                
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
        
        input("\nPresiona Enter para continuar...")

if __name__ == "__main__":
    main() 