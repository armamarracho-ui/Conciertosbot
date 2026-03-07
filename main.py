import requests
import json
import os

# 1. Configuración desde variables de entorno (por seguridad)
TM_KEY = os.getenv('TM_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_TOKEN')
TG_CHAT = os.getenv('TELEGRAM_CHAT_ID')

def fetch_concerts():
    # Buscaremos conciertos en México (puedes cambiar countryCode o city)
    # Clasificación 'KZFzniwnSyZfZ7v7nJ' es para Música
    url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={TM_KEY}&countryCode=MX&classificationId=KZFzniwnSyZfZ7v7nJ&size=100&sort=date,asc"
    
    try:
        response = requests.get(url).json()
        return response.get('_embedded', {}).get('events', [])
    except Exception as e:
        print(f"Error al conectar con la API: {e}")
        return []

def run():
    # Cargar eventos ya notificados anteriormente
    if os.path.exists('seen_events.json'):
        with open('seen_events.json', 'r') as f:
            seen_ids = set(json.load(f))
    else:
        seen_ids = set()

    current_events = fetch_concerts()
    new_found = []

    for event in current_events:
        event_id = event['id']
        if event_id not in seen_ids:
            name = event['name']
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
