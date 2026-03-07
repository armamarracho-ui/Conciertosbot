import requests
import json
import os
import time

# --- CONFIGURACIÓN ---
# Estos valores se obtienen de los "Secrets" que configuraste en tu repositorio
TM_KEY = os.getenv('TM_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_TOKEN')
TG_CHAT = os.getenv('TELEGRAM_CHAT_ID')

def fetch_all_events(pages=3):
    """
    Consulta la API de Ticketmaster manejando la paginación.
    Trae hasta 100 eventos por página.
    """
    all_events = []
    base_url = "https://app.ticketmaster.com/discovery/v2/events.json"
    
    for page in range(pages):
        # Parámetros de búsqueda: Música en México, ordenado por fecha
        params = {
            'apikey': TM_KEY,
            'countryCode': 'MX',
            'classificationId': 'KZFzniwnSyZfZ7v7nJ',
            'size': 100,
            'page': page,
            'sort': 'date,asc'
        }
        
        try:
            response = requests.get(base_url, params=params)
            
            # Si alcanzamos el límite de peticiones (Rate Limit), esperamos
            if response.status_code == 429:
                print("Límite de API alcanzado temporalmente. Esperando...")
                time.sleep(2)
                continue
                
            data = response.json()
            events = data.get('_embedded', {}).get('events', [])
            
            if not events:
                break
                
            all_events.extend(events)
            time.sleep(0.3) # Pausa técnica para respetar los 5 req/s de la API
            
        except Exception as e:
            print(f"Error obteniendo página {page}: {e}")
            break
            
    return all_events

def run():
    # 1. Cargar el historial de IDs ya notificados
    filename = 'seen_events.json'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                seen_ids = set(json.load(f))
            except json.JSONDecodeError:
                seen_ids = set()
    else:
        seen_ids = set()

    # 2. Ejecutar la búsqueda
    print("Iniciando búsqueda de nuevos conciertos...")
    current_events = fetch_all_events(pages=3) # Revisa hasta 300 eventos
    new_found_ids = []

    for event in current_events:
        event_id = event['id']
        
        # 3. Procesar solo si no lo hemos visto antes
        if event_id not in seen_ids:
            # Extracción segura de datos con .get()
            name = event.get('name', 'Evento sin nombre')
            date = event.get('dates', {}).get('start', {}).get('localDate', 'Fecha por confirmar')
            link = event.get('url', '#')
            
            # Ubicación (Ciudad y Recinto)
            venues = event.get('_embedded', {}).get('venues', [{}])
            venue_name = venues[0].get('name', 'Lugar por confirmar')
            city_name = venues[0].get('city', {}).get('name', 'Ciudad no especificada')
            
            # Imagen
            images = event.get('images', [])
            image_url = images[0].get('url', '') if images else ''

            # 4. Formatear el mensaje para Telegram
            caption = (
                f"🎸 *¡NUEVO CONCIERTO DETECTADO!*\n\n"
                f"🔥 *{name}*\n"
                f"📅 *Fecha:* {date}\n"
                f"🏙️ *Ciudad:* {city_name}\n"
                f"📍 *Lugar:* {venue_name}\n\n"
                f"🔗 [Ver boletos en Ticketmaster]({link})"
            )

            # 5. Enviar a Telegram con foto
            tg_url_photo = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
            
            try:
                if image_url:
                    payload = {
                        'chat_id': TG_CHAT,
                        'photo': image_url,
                        'caption': caption,
                        'parse_mode': 'Markdown'
                    }
                    r = requests.post(tg_url_photo, data=payload)
                else:
                    # Si no hay foto, enviamos solo texto
                    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                                  data={'chat_id': TG_CHAT, 'text': caption, 'parse_mode': 'Markdown'})
                
                # Si el envío fue exitoso, lo marcamos como visto
                new_found_ids.append(event_id)
                seen_ids.add(event_id)
                
                # Pequeña pausa para no saturar el chat de Telegram
                time.sleep(1) 
                
            except Exception as e:
                print(f"Error enviando el evento {event_id}: {e}")

    # 6. Guardar los nuevos IDs en el archivo JSON
    if new_found_ids:
        with open(filename, 'w') as f:
            json.dump(list(seen_ids), f)
        print(f"Éxito: Se notificaron {len(new_found_ids)} nuevos eventos.")
    else:
        print("No se encontraron novedades el día de hoy.")

if __name__ == "__main__":
    run()
    
