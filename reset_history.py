#!/usr/bin/env python3
"""
Script para resetear el historial de partidos enviados
Útil cuando se cambia la lógica de detección de duplicados
"""

import os
import sys

def reset_sent_matches():
    """Resetea el archivo de partidos enviados"""
    sent_matches_file = "sent_matches.json"
    
    try:
        if os.path.exists(sent_matches_file):
            os.remove(sent_matches_file)
            print("✅ Archivo de partidos enviados reseteado correctamente")
            print("📝 El sistema ahora enviará alertas para todos los partidos que cumplan los criterios")
        else:
            print("ℹ️ No existe archivo de partidos enviados para resetear")
            print("📝 El sistema funcionará normalmente")
    except Exception as e:
        print(f"❌ Error al resetear archivo de partidos enviados: {e}")

def main():
    print("=" * 50)
    print("   RESETEO DE HISTORIAL DE PARTIDOS ENVIADOS")
    print("=" * 50)
    
    print("⚠️  ¿Estás seguro de que quieres resetear el historial?")
    print("   Esto hará que se envíen alertas para todos los partidos que cumplan los criterios.")
    print("   (Incluyendo partidos que ya fueron enviados anteriormente)")
    
    response = input("\n¿Continuar? (s/N): ").strip().lower()
    
    if response in ['s', 'si', 'sí', 'y', 'yes']:
        reset_sent_matches()
        print("\n🎉 Reseteo completado!")
    else:
        print("\n❌ Operación cancelada")

if __name__ == "__main__":
    main() 