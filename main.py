import requests
import json
import os
import time

# --- CONFIGURACIÓN ---
TM_KEY = os.getenv('TM_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_TOKEN')
TG_CHAT = os.getenv('TELEGRAM_CHAT_ID')

def format_date(iso_date):
    """Convierte fechas ISO sencillas a algo más legible."""
    if not iso_date or iso_date == 'TBA':
        return "Por confirmar"
    return iso_date

def fetch_all_events(pages=3):
    all_events = []
    base_url = "https://app.ticketmaster.com/discovery/v2/events.json"
    
    for page in range(pages):
        params = {
            'apikey': TM_KEY,
            'countryCode': 'MX',
            'classificationId': 'KZFzniwnSyZfZ7v7nJ', # Música
            'size': 100,
            'page': page,
            'sort': 'date,asc'
        }
        
        try:
            response = requests.get(base_url, params=params)
            if response.status_code == 429:
                time.sleep(2)
                continue
            
            data = response.json()
            events = data.get('_embedded', {}).get('events', [])
            if not events: break
            
            all_events.extend(events)
            time.sleep(0.3)
        except Exception as e:
            print(f"Error en API: {e}")
            break
    return all_events

def run():
    filename = 'seen_events.json'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try: seen_ids = set(json.load(f))
            except: seen_ids = set()
    else:
        seen_ids = set()

    current_events = fetch_all_events(pages=3)
    new_found_ids = []

    for event in current_events:
        event_id = event['id']
        
        if event_id not in seen_ids:
            # 1. Información Básica
            name = event.get('name', 'Evento sin nombre')
            date = event.get('dates', {}).get('start', {}).get('localDate', 'TBA')
            link = event.get('url', '#')
            
            # 2. Género y Subgénero
            classif = event.get('classifications', [{}])[0]
            genre = classif.get('genre', {}).get('name', 'Música')
            subgenre = classif.get('subGenre', {}).get('name', '')
            full_genre = f"{genre} ({subgenre})" if subgenre else genre

            # 3. Precios (Manejo de rangos)
            price_list = event.get('priceRanges', [])
            if price_list:
                p = price_list[0]
                price_text = f"${p.get('min')} - ${p.get('max')} {p.get('currency')}"
            else:
                price_text = "Por confirmar"

            # 4. Fechas de Venta y Preventas
            sales = event.get('sales', {})
            public_start = sales.get('public', {}).get('startDateTime', 'TBA')[:10]
            
            presales = sales.get('presales', [])
            presale_info = ""
            if presales:
                # Tomamos la primera preventa disponible
                p_name = presales[0].get('name', 'Preventa')
                p_date = presales[0].get('startDateTime', 'TBA')[:10]
                presale_info = f"\n💳 *{p_name}:* {p_date}"

            # 5. Ubicación y Mapa
            venues = event.get('_embedded', {}).get('venues', [{}])
            v_name = venues[0].get('name', 'Lugar por confirmar')
            city = venues[0].get('city', {}).get('name', 'Ciudad desconocida')
            seatmap = event.get('seatmap', {}).get('staticUrl', '')

            # 6. Imagen
            images = event.get('images', [])
            image_url = images[0].get('url', '') if images else ''

            # --- CONSTRUCCIÓN DEL MENSAJE ---
            caption = (
                f"🎸 *{name}*\n"
                f"🏷️ *Género:* {full_genre}\n"
                f"🏙️ *Ciudad:* {city}\n"
                f"📍 *Lugar:* {v_name}\n"
                f"📅 *Fecha Concierto:* {date}\n\n"
                f"💰 *Precios:* {price_text}\n"
                f"🎟️ *Venta General:* {public_start}{presale_info}\n\n"
                f"🔗 [Comprar en Ticketmaster]({link})"
            )
            
            if seatmap:
                caption += f"\n🗺️ [Ver Mapa del Recinto]({seatmap})"

            # --- ENVÍO A TELEGRAM ---
            try:
                if image_url:
                    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto", 
                        data={'chat_id': TG_CHAT, 'photo': image_url, 'caption': caption, 'parse_mode': 'Markdown'})
                else:
                    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                        data={'chat_id': TG_CHAT, 'text': caption, 'parse_mode': 'Markdown'})
                
                new_found_ids.append(event_id)
                seen_ids.add(event_id)
                time.sleep(1.5) # Pausa amigable
            except Exception as e:
                print(f"Error enviando {event_id}: {e}")

    if new_found_ids:
        with open(filename, 'w') as f:
            json.dump(list(seen_ids), f)
        print(f"Notificados {len(new_found_ids)} conciertos.")
    else:
        print("Sin novedades.")

if __name__ == "__main__":
    run()
    
