# NowGoal Scraper con GitHub Actions

Este proyecto es un scraper automático para NowGoal.com que identifica partidos de fútbol en vivo que cumplen criterios específicos y envía alertas a Telegram. Está configurado para ejecutarse automáticamente en GitHub Actions.

## 🎯 Criterios de Filtrado

El scraper busca partidos que cumplan **TODOS** estos criterios:
- **Minuto del partido**: Entre 30-60 minutos (incluye medio tiempo)
- **Situación del marcador**: 
  - Un equipo pierde por exactamente 1 gol Y tiene igual o más córners que el rival, O
  - El partido está empatado Y al menos un equipo tiene córners
- **Estado**: Partido en progreso (no finalizado)

## 🚀 Configuración para GitHub Actions

### 1. Configurar Secrets en GitHub

Ve a tu repositorio en GitHub → Settings → Secrets and variables → Actions → New repository secret

Agrega estos secrets:
```
TELEGRAM_BOT_TOKEN = tu_token_del_bot
TELEGRAM_CHAT_ID = tu_chat_id
```

### 2. Obtener Token de Telegram Bot

1. Habla con [@BotFather](https://t.me/botfather) en Telegram
2. Crea un nuevo bot: `/newbot`
3. Sigue las instrucciones y guarda el token

### 3. Obtener Chat ID

**Para canal privado:**
1. Agrega tu bot al canal como administrador
2. Envía un mensaje de prueba al canal
3. Ve a: `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
4. Busca el `chat.id` (será negativo para canales)

**Para chat personal:**
1. Envía un mensaje a tu bot
2. Ve a: `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
3. Busca el `chat.id`

## 📅 Programación Automática

El scraper se ejecuta:
- **Cada 15 minutos** entre las 8:00 y 23:00 UTC
- **Manualmente** desde GitHub Actions (pestaña Actions → NowGoal Scraper → Run workflow)

## 🔄 Sistema Anti-Duplicados

- **Archivo de estado**: `sent_matches.json` rastrea partidos enviados
- **Ventana de tiempo**: Un mismo partido no se reenvía por 1 hora
- **Limpieza automática**: Registros antiguos (>6 horas) se eliminan automáticamente
- **Identificación única**: Basada en equipos + minuto + marcador

## 📁 Estructura del Proyecto

```
NowGoal/
├── .github/
│   └── workflows/
│       └── scraper.yml          # Configuración GitHub Actions
├── telegram.py                   # Script principal
├── requirements.txt              # Dependencias Python
├── README.md                     # Este archivo
└── sent_matches.json            # Estado de mensajes enviados (generado automáticamente)
```

## 🛠️ Ejecución Local

### Requisitos
- Python 3.11+
- Google Chrome
- ChromeDriver

### Instalación
```bash
pip install -r requirements.txt
```

### Ejecutar localmente
```bash
# Con variables de entorno
export TELEGRAM_BOT_TOKEN="tu_token"
export TELEGRAM_CHAT_ID="tu_chat_id"
python telegram.py

# O editar directamente en el código las credenciales (líneas 738-741)
python telegram.py
```

## ⚙️ Configuración Avanzada

### Cambiar horarios de ejecución
Edita `.github/workflows/scraper.yml`, línea 5:
```yaml
- cron: '*/15 8-23 * * *'  # Cada 15 minutos, 8:00-23:00 UTC
```

### Cambiar criterios de filtrado
Edita `telegram.py`, función `main()`:
```python
MIN_MINUTE_FILTER = 30  # Minuto mínimo
MAX_MINUTE_FILTER = 60  # Minuto máximo
```

### Ajustar tiempo anti-duplicados
Edita `telegram.py`, función `filter_unsent_matches()`:
```python
# Línea con: (current_time - sent_matches[match_hash]) > 3600
# 3600 = 1 hora en segundos
```

## 🐛 Solución de Problemas

### Error: "ChromeDriver not found"
- **GitHub Actions**: Se instala automáticamente
- **Local**: Instalar ChromeDriver manualmente o usar `webdriver-manager`

### Error: "Telegram API"
- Verificar que el bot token sea correcto
- Verificar que el chat ID sea correcto
- Verificar que el bot tenga permisos en el canal

### No se ejecuta automáticamente
- Verificar que los secrets estén configurados
- Verificar la sintaxis del archivo YAML
- El repositorio debe tener activadas las GitHub Actions

## 📊 Salida del Programa

### Consola
- Lista detallada de partidos que cumplen criterios
- Estadísticas de partidos encontrados
- Estado de envío de mensajes de Telegram

### Archivo JSON
- `nowgoal_matches_losing_or_drawing_more_corners_filtered.json`
- Contiene todos los datos extraídos de partidos relevantes

### Telegram
- Mensaje de encabezado con criterios
- Un mensaje por cada liga
- Un mensaje detallado por cada partido

## 🔒 Seguridad

- **Nunca subas tokens o credenciales** al código fuente
- Usa GitHub Secrets para información sensible
- El código actual tiene credenciales de ejemplo que debes cambiar

## 📈 Mejoras Futuras

- [ ] Soporte para múltiples canales de Telegram
- [ ] Filtros personalizables por liga
- [ ] Interfaz web para configuración
- [ ] Integración con bases de datos
- [ ] Alertas por email adicionales

## Instalación

### 1. Instalar Python
Asegúrate de tener Python 3.7 o superior instalado en tu sistema.

### 2. Instalar dependencias
Abre PowerShell en la carpeta del proyecto y ejecuta:

```powershell
pip install -r requirements.txt
```

### 3. Instalar Chrome
El script requiere Google Chrome instalado en tu sistema.

## Uso

### Opción 1: Script automático (Recomendado)
```powershell
python nowgoal_scraper_auto.py
```

### Opción 2: Script básico
```powershell
python nowgoal_scraper.py
```

## Funcionalidades

El script realiza las siguientes acciones:

1. **Navega** a https://www.nowgoal.com/
2. **Busca y hace clic** en el botón "Hot/Live" (elemento con ID `li_FilterLive`)
3. **Extrae datos** de la tabla usando XPath `//*[@id="mintable"]`
4. **Guarda los datos** en archivos CSV y Excel con timestamp
5. **Muestra un resumen** de los datos extraídos

## Características técnicas

- **Selenium WebDriver** para automatización del navegador
- **Pandas** para manipulación de datos
- **Manejo automático de ChromeDriver** (en la versión auto)
- **Múltiples selectores** para mayor robustez
- **Guardado en múltiples formatos** (CSV y Excel)
- **Manejo de errores** comprehensive
- **User-Agent personalizado** para evitar detección

## Configuración

### Modo Headless
Para ejecutar sin interfaz gráfica, modifica la línea en el archivo:
```python
scraper = NowGoalScraperAuto(headless=True)  # Cambiar False a True
```

### Timeouts
Los timeouts están configurados para 15 segundos. Puedes ajustarlos si tu conexión es lenta.

## Archivos de salida

Los datos se guardan en:
- **CSV**: `nowgoal_data_YYYYMMDD_HHMMSS.csv`
- **Excel**: `nowgoal_data_YYYYMMDD_HHMMSS.xlsx`

## Solución de problemas

### Error de ChromeDriver
Si usas `nowgoal_scraper.py` y obtienes errores de ChromeDriver:
1. Usa `nowgoal_scraper_auto.py` en su lugar
2. O instala ChromeDriver manualmente desde https://chromedriver.chromium.org/

### Timeout al cargar la página
- Verifica tu conexión a internet
- Aumenta los valores de timeout en el código
- Algunos sitios pueden bloquear bots temporalmente

### Elemento no encontrado
El script incluye múltiples selectores de respaldo. Si aún así falla:
- El sitio web puede haber cambiado su estructura
- Verifica que el sitio esté disponible manualmente

## Notas importantes

- **Uso responsable**: Respeta los términos de servicio del sitio web
- **Rate limiting**: El script incluye delays para no sobrecargar el servidor
- **Detección de bots**: Se incluyen medidas básicas para evitar detección

## Ejemplo de salida

```
🚀 Iniciando web scraping de NowGoal...
🔧 Configurando ChromeDriver automáticamente...
✅ Driver de Chrome configurado correctamente
🌐 Navegando a https://www.nowgoal.com/
✅ Página cargada correctamente
🔍 Buscando el botón Hot/Live...
✅ Botón Hot/Live encontrado
✅ Clic en Hot/Live realizado
📊 Extrayendo datos de la tabla...
✅ Tabla encontrada
📊 Encontradas 50 filas en la tabla
✅ Extraídas 49 filas de datos
📋 Datos extraídos:
   - Filas: 49
   - Columnas: 8
✅ Datos guardados en CSV: c:\Users\saavedra\Desktop\NowGoal\nowgoal_data_20250616_143022.csv
✅ Datos guardados en Excel: c:\Users\saavedra\Desktop\NowGoal\nowgoal_data_20250616_143022.xlsx
🧹 Navegador cerrado

🎉 ¡Scraping completado exitosamente!
```
