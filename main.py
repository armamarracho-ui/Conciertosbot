import requests
import json
import os
import time

# --- CONFIGURACIÓN ---
TM_KEY = os.getenv('TM_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_TOKEN')
TG_CHAT = os.getenv('TELEGRAM_CHAT_ID')

# Ciudades clave para maximizar la cobertura
CITIES = ['Mexico City', 'Monterrey', 'Guadalajara']

def fetch_full_scan(city_name):
    """
    Escanea hasta 1,000 eventos por ciudad (límite máximo de la API gratuita).
    Esto asegura capturar registros nuevos aunque sean para fechas lejanas.
    """
    all_city_events = []
    base_url = "https://app.ticketmaster.com/discovery/v2/events.json"
    
    # Escaneamos 10 páginas de 100 eventos cada una (1,000 eventos en total)
    for page in range(10):
        params = {
            'apikey': TM_KEY,
            'city': city_name,
            'countryCode': 'MX',
            'classificationId': 'KZFzniwnSyZfZ7v7nJ', # Música
            'size': 100,
            'page': page,
            'sort': 'date,asc' 
        }
        
        try:
            response = requests.get(base_url, params=params)
            
            if response.status_code == 429:
                time.sleep(2) # Pausa si alcanzamos el límite de velocidad
                continue
                
            data = response.json()
            events = data.get('_embedded', {}).get('events', [])
            
            if not events:
                break
                
            all_city_events.extend(events)
            time.sleep(0.2) # Respetar el límite de 5 peticiones por segundo
            
        except Exception as e:
            print(f"Error escaneando {city_name} en pág {page}: {e}")
            break
            
    return all_city_events

def run():
    filename = 'seen_events.json'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                seen_ids = set(json.load(f))
            except:
                seen_ids = set()
    else:
        seen_ids = set()

    new_found_count = 0

    for city in CITIES:
        print(f"Escaneando base de datos completa para {city}...")
        # Obtenemos absolutamente todo lo que Ticketmaster nos permite ver (1,000 eventos)
        discovered_events = fetch_full_scan(city)
        
        for event in discovered_events:
            event_id = event['id']
            
            # Si el ID NO está en nuestro archivo, es un registro NUEVO en Ticketmaster
            if event_id not in seen_ids:
                name = event.get('name', 'Evento sin nombre')
                date = event.get('dates', {}).get('start', {}).get('localDate', 'TBA')
                link = event.get('url', '#')
                
                # Precios y detalles
                price_list = event.get('priceRanges', [])
                price_text = f"${price_list[0].get('min')} - ${price_list[0].get('max')} MXN" if price_list else "Por confirmar"
                
                venues = event.get('_embedded', {}).get('venues', [{}])
                v_name = venues[0].get('name', 'Lugar por confirmar')
                actual_city = venues[0].get('city', {}).get('name', city)
                
                image_url = event.get('images', [{}])[0].get('url', '')

                # Mensaje de notificación
                caption = (
                    f"✨ *¡NUEVO REGISTRO EN TICKETMASTER!*\n\n"
                    f"🎸 *{name}*\n"
                    f"🏙️ *Ciudad:* {actual_city}\n"
                    f"📍 *Lugar:* {v_name}\n"
                    f"📅 *Fecha:* {date}\n"
                    f"💰 *Precio:* {price_text}\n\n"
                    f"🔗 [Ver detalles]({link})"
                )

                try:
                    if image_url:
                        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto", 
                            data={'chat_id': TG_CHAT, 'photo': image_url, 'caption': caption, 'parse_mode': 'Markdown'})
                    else:
                        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                            data={'chat_id': TG_CHAT, 'text': caption, 'parse_mode': 'Markdown'})
                    
                    seen_ids.add(event_id)
                    new_found_count += 1
                    time.sleep(1) # Evitar spam en Telegram
                except Exception as e:
                    print(f"Error enviando {event_id}: {e}")

    # Guardar el historial actualizado
    if new_found_count > 0:
        with open(filename, 'w') as f:
            json.dump(list(seen_ids), f)
        print(f"Se encontraron y notificaron {new_found_count} nuevos registros.")
    else:
        print("No se encontraron registros nuevos en este escaneo.")

if __name__ == "__main__":
    run()
