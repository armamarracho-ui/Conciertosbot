import requests
import json
import os
import time

# --- SECURITY CONFIGURATION ---
TM_KEY = os.getenv('TM_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_TOKEN')
TG_CHAT = os.getenv('TELEGRAM_CHAT_ID')

# Using Lat/Long + Radius is 100x more accurate than city strings.
# This catches all municipalities (Zapopan, Iztacalco, Apodaca, etc.)
REGIONS = {
    'CDMX & Area Metropolitana': '19.4326,-99.1332',
    'Monterrey & Alrededores': '25.6866,-100.3161',
    'Guadalajara & Zapopan': '20.6597,-103.3496'
}

def fetch_geo_scan(region_name, latlong):
    """
    Scans a 50km radius around the coordinates to catch absolutely everything.
    Max 1,000 events per region (10 pages x 100 events).
    """
    all_regional_events = []
    base_url = "https://app.ticketmaster.com/discovery/v2/events.json"
    
    for page in range(10):
        params = {
            'apikey': TM_KEY,
            'latlong': latlong,
            'radius': 50,
            'unit': 'km',
            'classificationId': 'KZFzniwnSyZfZ7v7nJ', # Music Category
            'size': 100,
            'page': page,
            'sort': 'date,asc' 
        }
        
        try:
            response = requests.get(base_url, params=params)
            
            if response.status_code == 429:
                print("Rate limit hit. Sleeping for 2 seconds...")
                time.sleep(2)
                continue
                
            data = response.json()
            events = data.get('_embedded', {}).get('events', [])
            if not events:
                break
                
            all_regional_events.extend(events)
            time.sleep(0.3) # Respect the 5 req/sec limit
            
        except Exception as e:
            print(f"Error scanning {region_name} page {page}: {e}")
            break
            
    return all_regional_events

def run():
    filename = 'seen_events.json'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try: seen_ids = set(json.load(f))
            except: seen_ids = set()
    else:
        seen_ids = set()

    new_found_count = 0

    for region, coords in REGIONS.items():
        print(f"Executing deep geo-scan for {region}...")
        discovered_events = fetch_geo_scan(region, coords)
        
        for event in discovered_events:
            event_id = event['id']
            
            if event_id not in seen_ids:
                # 1. Basic Info
                name = event.get('name', 'Unnamed Event')
                date = event.get('dates', {}).get('start', {}).get('localDate', 'TBA')
                time_start = event.get('dates', {}).get('start', {}).get('localTime', '')
                datetime_str = f"{date} {time_start}".strip()
                link = event.get('url', '#')
                
                # 2. Genre & Subgenre
                classif = event.get('classifications', [{}])[0]
                genre = classif.get('genre', {}).get('name', 'Music')
                sub = classif.get('subGenre', {}).get('name', '')
                full_genre = f"{genre} ({sub})" if sub else genre

                # 3. Prices
                price_list = event.get('priceRanges', [])
                if price_list:
                    p = price_list[0]
                    price_text = f"${p.get('min')} - ${p.get('max')} {p.get('currency')}"
                else:
                    price_text = "To be confirmed"

                # 4. Sales & Presales
                sales = event.get('sales', {})
                pub_start = sales.get('public', {}).get('startDateTime', 'TBA')[:10]
                
                presales_list = sales.get('presales', [])
                presale_info = ""
                if presales_list:
                    presale_info = "\n\n💳 *PRESALES:*"
                    # Loop through up to 3 presales so the message doesn't get too long
                    for ps in presales_list[:3]:
                        ps_name = ps.get('name', 'Presale')
                        ps_date = ps.get('startDateTime', 'TBA')[:10]
                        presale_info += f"\n• {ps_name}: {ps_date}"

                # 5. Venue & Location
                venues = event.get('_embedded', {}).get('venues', [{}])
                v_name = venues[0].get('name', 'Venue TBC')
                actual_city = venues[0].get('city', {}).get('name', 'Unknown City')
                
                # 6. Seat Map & Image
                seatmap = event.get('seatmap', {}).get('staticUrl', '')
                image_url = event.get('images', [{}])[0].get('url', '')

                # --- MESSAGE CONSTRUCTION ---
                caption = (
                    f"✨ *NEW CONCERT DETECTED!*\n\n"
                    f"🎸 *{name}*\n"
                    f"🏷️ *Genre:* {full_genre}\n"
                    f"🏙️ *City:* {actual_city}\n"
                    f"📍 *Venue:* {v_name}\n"
                    f"📅 *Event Date:* {datetime_str}\n\n"
                    f"💰 *Prices:* {price_text}\n"
                    f"🎟️ *General Sale:* {pub_start}"
                    f"{presale_info}\n\n"
                    f"🔗 [Buy on Ticketmaster]({link})"
                )
                
                if seatmap:
                    caption += f"\n🗺️ [View Venue Seat Map]({seatmap})"

                # --- TELEGRAM DELIVERY ---
                try:
                    if image_url:
                        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto", 
                            data={'chat_id': TG_CHAT, 'photo': image_url, 'caption': caption, 'parse_mode': 'Markdown'})
                    else:
                        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                            data={'chat_id': TG_CHAT, 'text': caption, 'parse_mode': 'Markdown'})
                    
                    seen_ids.add(event_id)
                    new_found_count += 1
                    time.sleep(1.2) # Throttle to avoid Telegram spam blocks
                except Exception as e:
                    print(f"Error sending {event_id}: {e}")

    # 7. Save State
    if new_found_count > 0:
        with open(filename, 'w') as f:
            json.dump(list(seen_ids), f)
        print(f"Success: {new_found_count} new events notified.")
    else:
        print("Scan complete. No new events found.")

if __name__ == "__main__":
    run()
