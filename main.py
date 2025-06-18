#!/usr/bin/env python3
"""
NowGoal Scraper Optimizado para GitHub Actions
Extrae datos de partidos en vivo y envía alertas a Telegram
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from config import validate_config, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DEBUG_MODE, HEADLESS_MODE

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Función principal del scraper"""
    try:
        logger.info("🚀 Iniciando NowGoal Scraper...")
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info(f"🔧 Modo debug: {DEBUG_MODE}")
        logger.info(f"🔧 Modo headless: {HEADLESS_MODE}")
        
        # Validar configuración
        validate_config()
        logger.info("✅ Configuración validada correctamente")
        
        # Importar el scraper (importación tardía para evitar errores de dependencias)
        try:
            from nowgoal_scraper import NowGoalScraper
        except ImportError:
            logger.error("❌ No se pudo importar NowGoalScraper")
            # Si no existe, usar una versión simplificada
            run_simple_test()
            return
        
        # Ejecutar scraper
        scraper = NowGoalScraper(headless=HEADLESS_MODE)
        matches = scraper.run_scraping(export_json=True)
        
        if matches:
            logger.info(f"✅ Scraping completado. Se encontraron {len(matches)} partidos")
            
            # Aquí puedes agregar lógica adicional para procesar los partidos
            # y enviar alertas específicas a Telegram
            
        else:
            logger.warning("⚠️ No se encontraron partidos")
            
    except Exception as e:
        logger.error(f"❌ Error durante la ejecución: {e}")
        sys.exit(1)

def run_simple_test():
    """Ejecuta una prueba simple para verificar que todo funciona"""
    logger.info("🧪 Ejecutando prueba simple...")
    
    # Probar conexión a Telegram
    import requests
    
    test_message = f"🧪 **Prueba de NowGoal Scraper**\\n📅 {datetime.now()}\\n✅ GitHub Actions funcionando correctamente"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': test_message,
        'parse_mode': 'MarkdownV2'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            logger.info("✅ Mensaje de prueba enviado a Telegram correctamente")
        else:
            logger.error(f"❌ Error al enviar mensaje: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Error de conexión a Telegram: {e}")

if __name__ == "__main__":
    main()
