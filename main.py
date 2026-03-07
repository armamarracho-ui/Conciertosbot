import requests
import json
import os
import time

# Configuración desde Secrets de GitHub
TM_KEY = os.getenv('TM_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_TOKEN')
TG_CHAT = os.getenv('TELEGRAM_CHAT_ID')

def fetch_all_events(max_pages=3):
    """Obtiene eventos manejando la paginación para evitar el límite de 100."""
    all_events = []
    # Clasificación 'KZFzniwnSyZfZ7v7nJ' es para Música
    base_url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={TM_KEY}&countryCode=MX&classificationId=KZFzniwnSyZfZ7v7nJ&size=100&sort=date,asc"
    
    for page in range(max_pages):
        url = f"{base_url}&page={page}"
        try:
            response = requests.get(url).json()
            events = response.get('_embedded', {}).get('events', [])
            if not events:
                break
            all_events.extend(events)
            # Respetamos el límite de 5 peticiones por segundo de la API gratuita
            time.sleep(0.2) 
        except Exception as e:
            print(f"Error en página {page}: {e}")
            break
            
    return all_events

def run():
    # 1. Cargar IDs ya vistos
    if os.path.exists('seen_events.json'):
        with open('seen_events.json', 'r') as f:
            seen_ids = set(json.load(f))
    else:
        seen_ids = set()

    current_events = fetch_all_events(max_pages=3) # Revisa hasta 300 eventos
    new_found_ids = []

    for event in current_events:
        event_id = event['id']
        
        if event_id not in seen_ids:
            # 2. Extraer datos (Nombre, Fecha, Ciudad, Lugar, Imagen)
            name = event.get('name', 'Evento sin nombre')
            date = event['dates']['start'].get('localDate', 'TBA')
            link = event.get('url', '')
            
            # Extraer Ciudad y Recinto
            venue_info = event.get('_embedded', {}).get('venues', [{}])[0]
            venue_name = venue_info.get('name', 'Lugar desconocido')
            city_name = venue_info.get('city', {}).get('name', 'Ciudad no especificada')
            
            # Extraer la imagen (usamos la primera disponible)
            image_url = event.get('images', [{}])[0].get('url', '')

            # 3. Formatear mensaje
            msg = (
                f"🎸 *{name}*\n"
                f"📅 *Fecha:* {date}\n"
                f"🏙️ *Ciudad:* {city_name}\n"
                f"📍 *Lugar:* {venue_name}\n\n"
                f"🔗 [Ver en Ticketmaster]({link})"
            )

            # 4. Enviar a Telegram con Foto
            tg_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
            payload = {
                'chat_id': TG_CHAT,
                'photo': image_url,
                'caption': msg,
                'parse_mode': 'Markdown'
            }
            
            try:
                r = requests.post(tg_url, data=payload)
                if r.status_code == 200:
                    new_found_ids.append(event_id)
                    seen_ids.add(event_id)
                time.sleep(1) # Pausa para no saturar Telegram
            except Exception as e:
                print(f"Error enviando a Telegram: {e}")

    # 5. Guardar el estado actualizado
    if new_found_ids:
        with open('seen_events.json', 'w') as f:
            json.dump(list(seen_ids), f)
        print(f"Éxito: {len(new_found_ids)} nuevos conciertos enviados.")
    else:
        print("Sin conciertos nuevos el día de hoy.")

if __name__ == "__main__":
    run()
            date = event['dates']['start'].get('localDate', 'TBA')
            venue = event['_embedded']['venues'][0]['name'] if '_embedded' in event else "Lugar desconocido"
            link = event['url']
            
            # Formatear mensaje
            msg = f"🎟️ *NUEVO CONCIERTO DETECTADO*\n\n🎸 *{name}*\n📅 Fecha: {date}\n📍 Lugar: {venue}\n🔗 [Comprar Boletos]({link})"
            
            # Enviar a Telegram
            tg_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            requests.post(tg_url, data={'chat_id': TG_CHAT, 'text': msg, 'parse_mode': 'Markdown'})
            
            new_found.append(event_id)
            seen_ids.add(event_id)

    # Si hubo nuevos, actualizamos el archivo para mañana
    if new_found:
        with open('seen_events.json', 'w') as f:
            json.dump(list(seen_ids), f)
        print(f"Se notificaron {len(new_found)} conciertos nuevos.")
    else:
        print("No hay novedades hoy.")

if __name__ == "__main__":
    run()
