"""
Web Scraper para NowGoal.com
Extrae datos de la tabla de partidos en vivo después de hacer clic en "Hot"
Filtra y muestra solo los partidos que cumplen:
- Se encuentran entre el minuto 30 y 60 (incluido el medio tiempo).
- Un equipo va perdiendo y tiene igual o más córners que el equipo que va ganando.
- O, el partido está empatado y un equipo tiene igual o más córners que el otro.
Ahora incluye alertas a Telegram con sistema anti-duplicados.
"""

import time
import re
import json
import os
import requests
import hashlib
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

class NowGoalScraper:
    def __init__(self, headless=False, min_minute=30, max_minute=60):
        """
        Inicializa el scraper

        Args:
            headless (bool): Si True, ejecuta el navegador sin interfaz gráfica
            min_minute (int): Minuto mínimo para el filtro de partidos.
            max_minute (int): Minuto máximo para el filtro de partidos.
        """
        self.driver = None
        self.headless = headless
        self.min_minute = min_minute
        self.max_minute = max_minute
        self.base_url = "https://www.nowgoal.com/"
        self.sent_matches_file = "sent_matches.json"

    def setup_driver(self):
        """Configura y inicializa el driver de Chrome"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless")

        # Opciones adicionales para evitar detección y GitHub Actions
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # User agent actualizado a una versión más reciente
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

        try:
            # Detectar si estamos en GitHub Actions
            if os.getenv('GITHUB_ACTIONS'):
                # En GitHub Actions, usar chromedriver del PATH
                service = Service('/usr/local/bin/chromedriver')
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # En local, usar webdriver-manager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("✅ Driver de Chrome configurado correctamente")
        except Exception as e:
            print(f"❌ Error al configurar el driver: {e}")
            print("Asegúrate de tener ChromeDriver instalado y en el PATH")
            raise

    def navigate_to_site(self):
        """Navega a la página de NowGoal"""
        try:
            print(f"🌐 Navegando a {self.base_url}")
            self.driver.get(self.base_url)

            # Esperar a que la página cargue
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("✅ Página cargada correctamente")

            # Esperar un poco más para que se cargue completamente
            time.sleep(3)

        except TimeoutException:
            print("❌ Timeout al cargar la página")
            raise
        except Exception as e:
            print(f"❌ Error al navegar al sitio: {e}")
            raise

    def click_hot_button(self):
        """Hace clic en el botón Hot/Live"""
        try:
            print("🔍 Buscando el botón Hot/Live...")

            # Esperar a que el elemento esté presente y sea clickeable
            wait = WebDriverWait(self.driver, 15)

            # Intentar diferentes selectores
            selectors = [
                (By.ID, "li_FilterLive"),
                (By.XPATH, "//li[@id='li_FilterLive']"),
                (By.XPATH, "//li[contains(@onclick, 'FilterByOption(2)')]"),
                (By.XPATH, "//span[text()='Live']/parent::li"),
                (By.XPATH, "//li[contains(@class, 'on') and .//span[text()='Live']]")
            ]

            hot_button = None
            for selector_type, selector_value in selectors:
                try:
                    print(f"   Intentando selector: {selector_type}")
                    hot_button = wait.until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    print(f"   ✅ Elemento encontrado")
                    break
                except TimeoutException:
                    continue

            if not hot_button:
                print("❌ No se pudo encontrar el botón Hot/Live")
                raise Exception("Botón Hot/Live no encontrado")

            print("✅ Botón Hot/Live encontrado")

            # Scroll hasta el elemento si es necesario
            self.driver.execute_script("arguments[0].scrollIntoView(true);", hot_button)
            time.sleep(1)

            # Hacer clic usando JavaScript para evitar problemas
            self.driver.execute_script("arguments[0].click();", hot_button)
            print("✅ Clic en Hot/Live realizado")

            # Esperar a que se cargue el contenido después del clic
            time.sleep(5)

        except Exception as e:
            print(f"❌ Error al hacer clic en Hot/Live: {e}")
            raise

    def extract_match_data(self):
        """Extrae los datos de partidos usando selectores CSS específicos"""
        try:
            print("📊 Extrayendo datos de partidos...")

            # Esperar a que la tabla esté presente
            wait = WebDriverWait(self.driver, 15)

            # Buscar la tabla principal
            try:
                table = wait.until(
                    EC.presence_of_element_located((By.ID, "mintable"))
                )
                print("✅ Tabla 'mintable' encontrada")
            except TimeoutException:
                print("❌ No se pudo encontrar la tabla 'mintable'")
                return []

            matches = []
            current_league = "Liga no especificada"

            # Obtener todas las filas para poder iterar en orden y detectar ligas y partidos
            all_rows = table.find_elements(By.TAG_NAME, "tr")

            for row in all_rows:
                try:
                    # Verificar si es una fila de liga
                    if "Leaguestitle" in row.get_attribute("class"):
                        league_element = row.find_element(By.CSS_SELECTOR, ".LGname")
                        current_league = league_element.text.strip()
                        continue

                    # Verificar si es una fila de partido
                    if "tds" in row.get_attribute("class"):
                        match_data = self.parse_match_row_with_css(row, current_league)
                        if match_data:
                            matches.append(match_data)

                except Exception as e:
                    # Se ignoran errores de filas individuales para no detener el scraping completo
                    continue

            print(f"✅ Se encontraron {len(matches)} partidos válidos")
            return matches

        except Exception as e:
            print(f"❌ Error al extraer datos de la tabla: {e}")
            return []

    def parse_match_row_with_css(self, row, current_league):
        """Parsea una fila de partido usando selectores CSS específicos"""
        try:
            match_info = {
                'league': current_league,
                'time': '', # Este campo se mantiene pero se omite en la salida detallada
                'home_team': '',
                'away_team': '',
                'score': '',
                'status': '',
                'minute_actual': '',
                'half_time_score': '',
                'corners': '', # Mantener para referencia general (ej. "5-3" como texto raw)
                'corners_home': '0', # Córners del equipo local
                'corners_away': '0', # Córners del equipo visitante
                'yellow_home': '0',
                'yellow_away': '0',
                'red_home': '0',
                'red_away': '0',
                'odds_full_time_home_win': '',
                'odds_full_time_draw': '',
                'odds_full_time_away_win': '',
                'link': ''
            }

            # Extraer tiempo (time) - se mantiene para datos internos, no se muestra en salida detallada
            try:
                time_element = row.find_element(By.CSS_SELECTOR, 'td[name="timeData"]')
                match_info['time'] = time_element.get_attribute('data-t') or time_element.text.strip()
            except NoSuchElementException:
                pass

            # Extraer equipo local (home_team)
            try:
                home_team_a = row.find_element(By.XPATH, './/td[starts-with(@id, "ht_")]/a[starts-with(@id, "team1_")]')
                full_text = home_team_a.text.strip()
                match_info['home_team'] = re.sub(r'\s*\(N\)\s*$', '', full_text)
                match_info['link'] = home_team_a.get_attribute('href') or ''
            except NoSuchElementException:
                pass

            # Extraer equipo visitante (away_team)
            try:
                away_team_a = row.find_element(By.XPATH, './/td[starts-with(@id, "gt_")]/a[starts-with(@id, "team2_")]')
                match_info['away_team'] = away_team_a.text.strip()
            except NoSuchElementException:
                pass

            # Extraer marcador (score)
            try:
                score_element = row.find_element(By.CSS_SELECTOR, 'td.f-b b')
                match_info['score'] = score_element.text.strip()
            except NoSuchElementException:
                pass

            # Extraer estado del partido (status) y el minuto numérico
            try:
                status_element = row.find_element(By.CSS_SELECTOR, 'td.status')
                status_text = status_element.text.strip()
                match_info['status'] = status_text

                # Extraer solo el número del minuto si existe, o '45' para HT
                minute_match = re.match(r'^\d+', status_text)
                if minute_match:
                    match_info['minute_actual'] = minute_match.group(0)
                elif status_text.strip().lower() in ['ht', 'pausa', 'half-time']:
                    match_info['minute_actual'] = '45' # Medio tiempo se considera minuto 45
            except NoSuchElementException:
                pass

            # Extraer marcador del primer tiempo (half_time_score)
            try:
                ht_score_element = row.find_element(By.CSS_SELECTOR, 'span[id^="hht_"]')
                match_info['half_time_score'] = ht_score_element.text.strip()
            except NoSuchElementException:
                pass

            # Extraer corners (divididos) - ¡Corrección aquí!
            try:
                corners_element = row.find_element(By.CSS_SELECTOR, 'span[id^="cr_"]')
                corners_text = corners_element.text.strip()
                match_info['corners'] = corners_text # Guarda el texto original completo (e.g., "5-3" or "-")

                if '-' in corners_text: # Si el formato es "X-Y" (sin o con espacios)
                    parts = [p.strip() for p in corners_text.split('-')] # Divide por '-' y limpia espacios
                    if len(parts) == 2:
                        try:
                            home_c = int(parts[0])
                            away_c = int(parts[1])
                            match_info['corners_home'] = str(home_c)
                            match_info['corners_away'] = str(away_c)
                        except ValueError:
                            # Esto ocurre si "X" o "Y" no son números válidos (ej. "N/A-N/A"). Mantiene '0'.
                            pass
                # Si el texto no es 'X-Y' ni '-', o está vacío, los valores corners_home/away permanecen '0'
            except NoSuchElementException:
                pass # El elemento de córners no se encontró. Los valores predeterminados '0' son correctos.
            except Exception as e:
                # Captura cualquier otra excepción inesperada durante la extracción de córners.
                print(f"DEBUG: Error general al extraer córners para {match_info.get('home_team')} vs {match_info.get('away_team')}: {e}")
                pass


            # Extraer tarjetas amarillas equipo local
            try:
                yellow_home_element = row.find_element(By.CSS_SELECTOR, 'td[id^="ht_"] span.yellowcard')
                match_info['yellow_home'] = yellow_home_element.text.strip()
            except NoSuchElementException:
                pass

            # Extraer tarjetas amarillas equipo visitante
            try:
                yellow_away_element = row.find_element(By.CSS_SELECTOR, 'td[id^="gt_"] span.yellowcard')
                match_info['yellow_away'] = yellow_away_element.text.strip()
            except NoSuchElementException:
                pass

            # Extraer tarjetas rojas equipo local
            try:
                red_home_element = row.find_element(By.CSS_SELECTOR, 'td[id^="ht_"] span.redcard')
                match_info['red_home'] = red_home_element.text.strip()
            except NoSuchElementException:
                pass

            # Extraer tarjetas rojas equipo visitante
            try:
                red_away_element = row.find_element(By.CSS_SELECTOR, 'td[id^="gt_"] span.redcard')
                match_info['red_away'] = red_away_element.text.strip()
            except NoSuchElementException:
                pass

            # Extraer cuotas de apuestas
            try:
                odds_td = row.find_element(By.CSS_SELECTOR, 'td.oddstd')
                odds_elements = odds_td.find_elements(By.CSS_SELECTOR, 'p.odds1')

                if len(odds_elements) >= 3:
                    match_info['odds_full_time_home_win'] = odds_elements[0].text.strip().replace(',', '.')
                    match_info['odds_full_time_draw'] = odds_elements[1].text.strip().replace(',', '.')
                    match_info['odds_full_time_away_win'] = odds_elements[2].text.strip().replace(',', '.')

            except NoSuchElementException:
                pass
            except IndexError:
                pass

            if match_info['home_team'] or match_info['away_team'] or match_info['score']:
                return match_info

            return None

        except Exception as e:
            # print(f"DEBUG: Error general al parsear fila de partido para liga {current_league}: {e}")
            return None

    def is_losing_or_drawing_with_more_corners(self, match):
        """
        Determina si un equipo va perdiendo por 1 gol o empatando y tiene igual o más córners que el rival,
        y si el partido está en el rango de minutos especificado.

        Args:
            match (dict): Diccionario con la información del partido.

        Returns:
            tuple: (bool, str) - True si cumple el criterio, False en caso contrario,
                   y una cadena que describe el motivo del filtro.
        """
        minute_actual_str = match.get('minute_actual', '').strip()
        score_str = match.get('score', '').strip()
        corners_home_str = match.get('corners_home', '0').strip()
        corners_away_str = match.get('corners_away', '0').strip()

        # 1. Validación de Minuto
        if not minute_actual_str:
            return False, "Minuto no disponible o partido no en progreso"
        
        current_minute = 0
        try:
            current_minute = int(minute_actual_str)
        except ValueError:
            return False, "Minuto inválido"

        if not (self.min_minute <= current_minute <= self.max_minute):
            return False, f"Minuto {current_minute} fuera de rango {self.min_minute}-{self.max_minute}"

        # 2. Validación de Marcador
        if not score_str or score_str == '-' or ' - ' not in score_str:
            return False, "Marcador no válido"

        try:
            home_goals, away_goals = map(int, score_str.split(' - '))
        except ValueError:
            return False, "Marcador inválido"

        # 3. Validación de Córners
        try:
            home_corners = int(corners_home_str)
            away_corners = int(corners_away_str)
        except ValueError:
            return False, "Córners inválidos o no numéricos"

        # Lógica del filtro: equipo perdiendo por 1 gol o empatando con igual o más córners
        
        # Caso 1: Equipo local perdiendo por 1 gol
        if home_goals < away_goals and (away_goals - home_goals) == 1:
            if home_corners >= away_corners:
                return True, f"Local pierde por 1 gol ({home_goals}-{away_goals}) con ≥ córners ({home_corners}-{away_corners})"
            else:
                return False, f"Local pierde por 1 gol ({home_goals}-{away_goals}) con < córners ({home_corners}-{away_corners})"
        
        # Caso 2: Equipo visitante perdiendo por 1 gol
        elif away_goals < home_goals and (home_goals - away_goals) == 1:
            if away_corners >= home_corners:
                return True, f"Visitante pierde por 1 gol ({home_goals}-{away_goals}) con ≥ córners ({home_corners}-{away_corners})"
            else:
                return False, f"Visitante pierde por 1 gol ({home_goals}-{away_goals}) con < córners ({home_corners}-{away_corners})"
        
        # Caso 3: Empate
        elif home_goals == away_goals:
            # En caso de empate, si al menos un equipo tiene igual o más córners que el otro, pasa el filtro.
            if home_corners >= away_corners or away_corners >= home_corners: 
                return True, f"Empate ({home_goals}-{away_goals}), Córners ({home_corners}-{away_corners})"
            else:
                return False, f"Empate ({home_goals}-{away_goals}), córners no válidos ({home_corners}-{away_corners})"
        
        return False, "Condición de marcador/córners no cubierta"


    def display_matches(self, matches_to_display):
        """
        Muestra los partidos filtrados en la consola.
        Args:
            matches_to_display (list): Lista de diccionarios de partidos ya filtrados.
        """
        if not matches_to_display:
            print("\n" + "="*100)
            print("❌ No se encontraron partidos que cumplan el criterio de perdedor/empatado con más/igual córners "
                  f"(min. {self.min_minute}-{self.max_minute}).")
            print("="*100)
            return

        print("\n" + "="*100)
        print(f"⚽ ALERTA: PARTIDOS EN VIVO - NOWGOAL.COM")
        print(f"   Criterio: Equipo Empatado/Perdiendo con ≥ Córners")
        print(f"   Rango de Minutos: {self.min_minute}-{self.max_minute}")
        print("="*100)

        current_league = ""
        displayed_count = 0

        for i, match in enumerate(matches_to_display, 1):
            if match['league'] != current_league:
                current_league = match['league']
                print(f"\n🏆 LIGA: {current_league}")
                print("=" * 80)

            displayed_count += 1

            home_score, away_score = '?', '?'
            if match.get('score') and match['score'] != '-' and ' - ' in match['score']:
                try:
                    home_score, away_score = match['score'].split(' - ')
                except ValueError:
                    pass
            
            filter_reason = match.get('filter_reason', 'N/A')

            print(f"\n📍 PARTIDO {displayed_count}:")
            print(f"   🏠 Equipo Local:     {match.get('home_team', 'N/A')}")
            print(f"   ✈️  Equipo Visitante:  {match.get('away_team', 'N/A')}")
            print(f"   ⚽ Marcador:         {home_score} - {away_score}")
            print(f"   📊 Minuto:           {match.get('minute_actual', 'N/A')}")
            print(f"   📐 Córners (L-V):    {match.get('corners_home', '0')} - {match.get('corners_away', '0')}")
            print(f"   ✅ Motivo Filtro:    {filter_reason}")
            print(f"   🟨 Tarjetas Amarillas: L:{match.get('yellow_home', '0')} V:{match.get('yellow_away', '0')}")
            print(f"   🟥 Tarjetas Rojas:    L:{match.get('red_home', '0')} V:{match.get('red_away', '0')}")
            print(f"   💰 Cuotas (1X2):     H:{match.get('odds_full_time_home_win', 'N/A')} X:{match.get('odds_full_time_draw', 'N/A')} A:{match.get('odds_full_time_away_win', 'N/A')}")
            print(f"   🔗 Link:             {match.get('link', 'N/A')}")
            print("-" * 80)

        print(f"\n📊 Total de partidos que cumplen el criterio (min. {self.min_minute}-{self.max_minute}): {displayed_count}")
        print("="*100)

    def export_to_json(self, matches_to_export, filename="nowgoal_matches_losing_or_drawing_more_corners_filtered.json"):
        """Exporta solo los partidos que cumplen el criterio a un archivo JSON"""
        try:
            if not matches_to_export:
                print("❌ No hay datos de partidos para exportar con el criterio actual.")
                return False

            export_data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "filter_minute_range": f"{self.min_minute}-{self.max_minute}",
                "total_matches_filtered_by_criteria": len(matches_to_export),
                "matches": matches_to_export
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Datos filtrados exportados a: {filename}")
            return True
        except Exception as e:
            print(f"❌ Error al exportar datos: {e}")
            return False

    def _escape_telegram_markdown_v2(self, text):
        """
        Escapa caracteres especiales para Telegram MarkdownV2.
        https://core.telegram.org/bots/api#markdownv2-style
        """
        if text is None:
            return "N/A"
        text = str(text)
        
        # Caracteres que DEBEN ser escapados en MarkdownV2
        reserved_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        # Escapar cada carácter reservado
        for char in reserved_chars:
            text = text.replace(char, '\\' + char)
        
        return text

    def send_telegram_alert(self, matches_to_alert, bot_token, chat_id):
        """
        Envía una alerta de Telegram con los partidos filtrados, un mensaje por partido.
        """
        if not matches_to_alert:
            print("📣 No hay partidos filtrados para enviar a Telegram.")
            return

        print("Enviando alertas de Telegram...")

        # Primero enviamos un mensaje de encabezado
        header_message = (
            "🎯 *NOWGOAL ALERTA DE PARTIDOS EN VIVO*\n\n"
            "📋 *Criterios:*\n"
            "• Equipo perdiendo por 1 gol o empatado\n"
            "• Con igual o más córners que el rival\n"
            f"• Minuto: {self._escape_telegram_markdown_v2(f'{self.min_minute}-{self.max_minute}')}\n\n"
            f"⏰ Reporte: {self._escape_telegram_markdown_v2(time.strftime('%Y-%m-%d %H:%M:%S'))}"
        )

        telegram_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        # Enviar mensaje de encabezado
        try:
            response = requests.post(
                telegram_api_url,
                params={
                    "chat_id": chat_id,
                    "text": header_message,
                    "parse_mode": "MarkdownV2",
                    "disable_web_page_preview": True
                }
            )
            response.raise_for_status()
            print("✅ Mensaje de encabezado enviado con éxito.")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error al enviar mensaje de encabezado: {e}")
            return

        # Enviar un mensaje por cada partido
        current_league = ""
        for match in matches_to_alert:
            # Si es una nueva liga, enviar el nombre de la liga como mensaje separado
            if match['league'] != current_league:
                current_league = match['league']
                league_message = f"🏆 *{self._escape_telegram_markdown_v2(current_league.upper())}*"
                try:
                    response = requests.post(
                        telegram_api_url,
                        params={
                            "chat_id": chat_id,
                            "text": league_message,
                            "parse_mode": "MarkdownV2",
                            "disable_web_page_preview": True
                        }
                    )
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    print(f"❌ Error al enviar nombre de liga: {e}")
                    continue

            # Preparar el mensaje del partido
            home_score, away_score = '?', '?'
            if match.get('score') and match['score'] != '-' and ' - ' in match['score']:
                try:
                    home_score, away_score = match['score'].split(' - ')
                except ValueError:
                    pass

            home_team = self._escape_telegram_markdown_v2(match.get('home_team'))
            away_team = self._escape_telegram_markdown_v2(match.get('away_team'))
            filter_reason = self._escape_telegram_markdown_v2(match.get('filter_reason', 'N/A'))

            match_message = f"""
⚽ *{home_team} vs {away_team}*

📊 *Estado del Partido:*
• Marcador: {self._escape_telegram_markdown_v2(f'{home_score}-{away_score}')}
• Minuto: {self._escape_telegram_markdown_v2(match.get('minute_actual'))}
• Córners: {self._escape_telegram_markdown_v2(match.get('corners_home', '0'))} \\- {self._escape_telegram_markdown_v2(match.get('corners_away', '0'))}

🎯 *Análisis:*
• {filter_reason}

📈 *Cuotas:*
• Local: {self._escape_telegram_markdown_v2(match.get('odds_full_time_home_win', 'N/A'))}
• Empate: {self._escape_telegram_markdown_v2(match.get('odds_full_time_draw', 'N/A'))}
• Visitante: {self._escape_telegram_markdown_v2(match.get('odds_full_time_away_win', 'N/A'))}

🟨 *Tarjetas Amarillas:* L:{self._escape_telegram_markdown_v2(match.get('yellow_home', '0'))} V:{self._escape_telegram_markdown_v2(match.get('yellow_away', '0'))}
🟥 *Tarjetas Rojas:* L:{self._escape_telegram_markdown_v2(match.get('red_home', '0'))} V:{self._escape_telegram_markdown_v2(match.get('red_away', '0'))}"""

            if match.get('link') and match['link'] != 'N/A':
                match_message += f"\n\n🔗 [Ver Detalles]({self._escape_telegram_markdown_v2(match['link'])})"

            # Enviar el mensaje del partido
            try:
                response = requests.post(
                    telegram_api_url,
                    params={
                        "chat_id": chat_id,
                        "text": match_message,
                        "parse_mode": "MarkdownV2",
                        "disable_web_page_preview": True
                    }
                )
                response.raise_for_status()
                print(f"✅ Alerta enviada para {home_team} vs {away_team}")
                # Pequeña pausa entre mensajes para evitar límites de rate
                time.sleep(0.5)
            except requests.exceptions.RequestException as e:
                print(f"❌ Error al enviar alerta para {home_team} vs {away_team}: {e}")
                if hasattr(response, 'json'):
                    print(f"Error de la API de Telegram: {response.json()}")
                continue

        print("✅ Proceso de envío de alertas completado.")

    def generate_match_hash(self, match):
        """
        Genera un hash único para identificar un partido específico.
        Solo usa los equipos para evitar duplicados cuando cambia el minuto o marcador.
        """
        # Crear un identificador único basado únicamente en los equipos
        # Esto evita que se envíen mensajes duplicados cuando cambia el minuto o marcador
        match_key = f"{match.get('home_team', '')}_{match.get('away_team', '')}"
        return hashlib.md5(match_key.encode()).hexdigest()

    def load_sent_matches(self):
        """
        Carga el archivo de partidos ya enviados.
        """
        try:
            if os.path.exists(self.sent_matches_file):
                with open(self.sent_matches_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"⚠️ Error al cargar archivo de partidos enviados: {e}")
            return {}

    def save_sent_matches(self, sent_matches):
        """
        Guarda el archivo de partidos ya enviados.
        """
        try:
            with open(self.sent_matches_file, 'w', encoding='utf-8') as f:
                json.dump(sent_matches, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error al guardar archivo de partidos enviados: {e}")

    def clean_old_sent_matches(self, sent_matches, hours_to_keep=6):
        """
        Limpia los registros de partidos enviados que son muy antiguos.
        """
        current_time = time.time()
        cutoff_time = current_time - (hours_to_keep * 3600)  # 6 horas en segundos
        
        cleaned_matches = {}
        for match_hash, timestamp in sent_matches.items():
            if timestamp > cutoff_time:
                cleaned_matches[match_hash] = timestamp
                
        return cleaned_matches

    def reset_sent_matches(self):
        """
        Resetea completamente el archivo de partidos enviados.
        Útil para limpiar el historial cuando se cambia la lógica de detección de duplicados.
        """
        try:
            if os.path.exists(self.sent_matches_file):
                os.remove(self.sent_matches_file)
                print("✅ Archivo de partidos enviados reseteado correctamente")
            else:
                print("ℹ️ No existe archivo de partidos enviados para resetear")
        except Exception as e:
            print(f"❌ Error al resetear archivo de partidos enviados: {e}")

    def filter_unsent_matches(self, matches):
        """
        Filtra solo los partidos que no han sido enviados recientemente.
        """
        sent_matches = self.load_sent_matches()
        sent_matches = self.clean_old_sent_matches(sent_matches)
        
        unsent_matches = []
        current_time = time.time()
        
        for match in matches:
            match_hash = self.generate_match_hash(match)
            
            # Si el partido no ha sido enviado o fue enviado hace más de 1 hora
            if match_hash not in sent_matches or (current_time - sent_matches[match_hash]) > 3600:
                unsent_matches.append(match)
                sent_matches[match_hash] = current_time
                
        # Guardar los partidos actualizados
        self.save_sent_matches(sent_matches)
        
        return unsent_matches

    def run_scraping(self, export_json=True, send_telegram=True):
        """Ejecuta el proceso completo de scraping"""
        try:
            print("🚀 Iniciando web scraping de NowGoal...")

            self.setup_driver()
            self.navigate_to_site()
            self.click_hot_button()

            all_matches = self.extract_match_data()

            if all_matches:
                filtered_matches = []
                for match in all_matches:
                    is_relevant, reason = self.is_losing_or_drawing_with_more_corners(match)
                    if is_relevant:
                        match['filter_reason'] = reason # Añadir el motivo para mostrarlo
                        filtered_matches.append(match)

                self.display_matches(filtered_matches)

                if export_json:
                    self.export_to_json(filtered_matches)

                if send_telegram:
                    # Obtener credenciales de Telegram desde variables de entorno
                    telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
                    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
                    
                    # Para compatibilidad con ejecución local, usar valores por defecto si no están las variables de entorno
                    if not telegram_bot_token:
                        telegram_bot_token = "7915400009:AAEbX7983vUykGYYCXZkiAAWbH2ODP1dn7g"
                    if not telegram_chat_id:
                        telegram_chat_id = "-1002739074153"

                    if telegram_bot_token and telegram_chat_id:
                        # Filtrar solo partidos que no han sido enviados
                        unsent_matches = self.filter_unsent_matches(filtered_matches)
                        
                        if unsent_matches:
                            print(f"📤 Enviando {len(unsent_matches)} partidos nuevos a Telegram...")
                            self.send_telegram_alert(unsent_matches, telegram_bot_token, telegram_chat_id)
                        else:
                            print("✅ No hay partidos nuevos para enviar a Telegram.")
                    else:
                        print("⚠️ Las credenciales de Telegram no están configuradas. No se enviarán alertas.")

                return filtered_matches
            else:
                print("❌ No se pudieron extraer datos de partidos")
                return []

        except Exception as e:
            print(f"❌ Error durante el scraping: {e}")
            return []
        finally:
            self.cleanup()

    def cleanup(self):
        """Cierra el navegador y limpia recursos"""
        if self.driver:
            self.driver.quit()
            print("🧹 Navegador cerrado")

def main():
    """Función principal"""
    print("=" * 50)
    print("   WEB SCRAPER NOWGOAL.COM")
    print("   (Equipo empatado/perdiendo con más/igual córners, Min. 30-60)")
    print("=" * 50)

    # Configura los minutos de filtro aquí
    MIN_MINUTE_FILTER = 30
    MAX_MINUTE_FILTER = 60

    # Detectar si estamos en GitHub Actions para usar modo headless
    is_github_actions = os.getenv('GITHUB_ACTIONS', 'false').lower() == 'true'
    
    scraper = NowGoalScraper(
        headless=is_github_actions,  # Headless en GitHub Actions, con ventana en local
        min_minute=MIN_MINUTE_FILTER,
        max_minute=MAX_MINUTE_FILTER
    )

    # Opción para resetear el historial de partidos enviados
    # Descomenta la siguiente línea si quieres limpiar el historial
    # scraper.reset_sent_matches()

    scraper.run_scraping(export_json=True, send_telegram=True)

    print("\n🎉 Proceso completado!")

if __name__ == "__main__":
    main()