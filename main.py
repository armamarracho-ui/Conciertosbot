import requests
import json
import os
import time

# --- CONFIGURACIÓN DE SEGURIDAD ---
# Estos valores se leen de los "Secrets" de GitHub para que nadie robe tus llaves
TM_KEY = os.getenv('TM_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_TOKEN')
TG_CHAT = os.getenv('TELEGRAM_CHAT_ID')

def fetch_all_events(pages=10):
    """
    Consulta la API de Ticketmaster manejando la paginación.
    Trae 100 eventos por página para no perderse nada.
    """
    all_events = []
    base_url = "https://app.ticketmaster.com/discovery/v2/events.json"
    
    for page in range(pages):
        params = {
            'apikey': TM_KEY,
            'countryCode': 'MX',
            'classificationId': 'KZFzniwnSyZfZ7v7nJ', # Categoría: Música
            'size': 100,
            'page': page,
            'sort': 'date,asc'
        }
        
        try:
            response = requests.get(base_url, params=params)
            
            # Si Ticketmaster nos pide ir más lento (Error 429), esperamos
            if response.status_code == 429:
                print("Límite de API alcanzado temporalmente. Esperando 2 segundos...")
                time.sleep(2)
                continue
                
            data = response.json()
            events = data.get('_embedded', {}).get('events', [])
            
            if not events:
                break
                
            all_events.extend(events)
            time.sleep(0.3) # Pausa técnica para respetar el límite de 5 req/s
            
        except Exception as e:
            print(f"Error obteniendo página {page}: {e}")
            break
            
    return all_events

def run():
    # 1. Cargar el historial de conciertos ya enviados
    filename = 'seen_events.json'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                seen_ids = set(json.load(f))
            except:
                seen_ids = set()
    else:
        seen_ids = set()

    # 2. Iniciar la búsqueda
    print("Iniciando búsqueda de nuevos conciertos en México...")
    current_events = fetch_all_events(pages=3)
    new_found_ids = []

    for event in current_events:
        event_id = event['id']
        
        # 3. Solo procesar si el ID es nuevo
        if event_id not in seen_ids:
            # --- Extracción de Datos Inteligente ---
            name = event.get('name', 'Evento sin nombre')
            date = event.get('dates', {}).get('start', {}).get('localDate', 'Fecha por confirmar')
            link = event.get('url', '#')
            
            # Clasificación: Género y Subgénero
            classif = event.get('classifications', [{}])[0]
            genre = classif.get('genre', {}).get('name', 'Música')
            sub = classif.get('subGenre', {}).get('name', '')
            full_genre = f"{genre} ({sub})" if sub else genre

            # Rango de Precios
            price_list = event.get('priceRanges', [])
            if price_list:
                p = price_list[0]
                price_text = f"${p.get('min')} - ${p.get('max')} {p.get('currency')}"
            else:
                price_text = "Por confirmar"

            # Fechas de Ventas y Preventas
            sales = event.get('sales', {})
            pub_start = sales.get('public', {}).get('startDateTime', 'TBA')[:10]
            
            presale_info = ""
            if 'presales' in sales:
                ps = sales['presales'][0]
                ps_name = ps.get('name', 'Preventa')
                ps_date = ps.get('startDateTime', 'TBA')[:10]
                presale_info = f"\n💳 *{ps_name}:* {ps_date}"

            # Ubicación y Ciudad
            venues = event.get('_embedded', {}).get('venues', [{}])
            v_name = venues[0].get('name', 'Lugar por confirmar')
            city = venues[0].get('city', {}).get('name', 'Ciudad desconocida')
            seatmap = event.get('seatmap', {}).get('staticUrl', '')

            # Imagen del evento
            images = event.get('images', [])
            image_url = images[0].get('url', '') if images else ''

            # --- Construcción del Mensaje ---
            caption = (
                f"🎸 *¡NUEVO CONCIERTO DETECTADO!*\n\n"
                f"🔥 *{name}*\n"
                f"🏷️ *Género:* {full_genre}\n"
                f"🏙️ *Ciudad:* {city}\n"
                f"📍 *Lugar:* {v_name}\n"
                f"📅 *Fecha:* {date}\n\n"
                f"💰 *Precios:* {price_text}\n"
                f"🎟️ *Venta General:* {pub_start}{presale_info}\n\n"
                f"🔗 [Comprar en Ticketmaster]({link})"
            )
            
            if seatmap:
                caption += f"\n🗺️ [Ver Mapa del Recinto]({seatmap})"

            # --- Envío a Telegram ---
            try:
                if image_url:
                    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto", 
                        data={'chat_id': TG_CHAT, 'photo': image_url, 'caption': caption, 'parse_mode': 'Markdown'})
                else:
                    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                        data={'chat_id': TG_CHAT, 'text': caption, 'parse_mode': 'Markdown'})
                
                # Guardar como visto
                new_found_ids.append(event_id)
                seen_ids.add(event_id)
                
                # Pausa para no saturar a Telegram
                time.sleep(1.5) 
            except Exception as e:
                print(f"Error enviando evento {event_id}: {e}")

    # 4. Actualizar el historial para no repetir notificaciones
    if new_found_ids:
        with open(filename, 'w') as f:
            json.dump(list(seen_ids), f)
        print(f"Éxito: Se notificaron {len(new_found_ids)} conciertos nuevos.")
    else:
        print("Finalizado: No se encontraron novedades hoy.")

if __name__ == "__main__":
    run()
        
