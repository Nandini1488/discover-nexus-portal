import json
import os
import random
import time
import requests
import asyncio
from datetime import datetime, timezone

# --- API Keys Configuration ---
# NewsAPI.org API key should be stored as a GitHub Secret named NEWSAPI_API_KEY.
NEWSAPI_API_KEY = os.getenv('NEWSAPI_API_KEY')
NEWSAPI_BASE_URL = "https://newsapi.org/v2/"

# World News API key should be stored as a GitHub Secret named WORLD_NEWS_API_KEY.
# Sign up here: https://worldnewsapi.com/
WORLD_NEWS_API_KEY = os.getenv('WORLD_NEWS_API_KEY')
WORLD_NEWS_API_BASE_URL = "https://api.worldnewsapi.com/"

# Mistral AI API key should be stored as a GitHub Secret named MISTRAL_API_KEY.
MISTRAL_API_BASE_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY') 

# --- Debugging Print for API Keys ---
if NEWSAPI_API_KEY:
    NEWSAPI_API_KEY = NEWSAPI_API_KEY.strip()
    print(f"NEWSAPI_API_KEY successfully loaded from environment. Length: {len(NEWSAPI_API_KEY)}. Starts with: {NEWSAPI_API_KEY[:5]}... Ends with: {NEWSAPI_API_KEY[-5:]}")
else:
    print("WARNING: NEWSAPI_API_KEY is NOT loaded from environment. Please check GitHub Secrets and workflow env configuration.")

if WORLD_NEWS_API_KEY:
    WORLD_NEWS_API_KEY = WORLD_NEWS_API_KEY.strip()
    print(f"WORLD_NEWS_API_KEY successfully loaded from environment. Length: {len(WORLD_NEWS_API_KEY)}. Starts with: {WORLD_NEWS_API_KEY[:5]}... Ends with: {WORLD_NEWS_API_KEY[-5:]}")
else:
    print("WARNING: WORLD_NEWS_API_KEY is NOT loaded from environment. Please check GitHub Secrets and workflow env configuration.")

if MISTRAL_API_KEY:
    MISTRAL_API_KEY = MISTRAL_API_KEY.strip()
    print(f"MISTRAL_API_KEY successfully loaded from environment. Length: {len(MISTRAL_API_KEY)}. Starts with: {MISTRAL_API_KEY[:5]}... Ends with: {MISTRAL_API_KEY[-5:]}")
else:
    print("WARNING: MISTRAL_API_KEY is NOT loaded from environment. Please check GitHub Secrets and workflow env configuration.")
# --- End Debugging Print ---

# Define the regions and categories that match your index.html
REGIONS = {
    "global": {"name": "the entire world", "country_codes": ["us", "gb", "ca", "au", "in"]}, 
    "north_america": {"name": "North America", "country_codes": ["us", "ca"]},
    "europe": {"name": "Europe", "country_codes": ["gb", "de", "fr", "es", "it"]}, 
    "asia": {"name": "Asia", "country_codes": ["in", "cn", "jp", "kr"]}, 
    "africa": {"name": "Africa", "country_codes": ["za", "ng", "eg"]}, 
    "oceania": {"name": "Oceania", "country_codes": ["au", "nz"]},
    "south_america": {"name": "South America", "country_codes": ["br", "ar", "co"]}, 
    "middle_east": {"name": "Middle East", "country_codes": ["ae", "sa"]}, 
    "southeast_asia": {"name": "Southeast Asia", "country_codes": ["sg", "ph", "id"]}, 
    "north_africa": {"name": "North Africa", "country_codes": ["eg"]}, 
    "sub_saharan_africa": {"name": "Sub-Saharan Africa", "country_codes": ["ng", "za"]}, 
    "east_asia": {"name": "East Asia", "country_codes": ["jp", "kr", "cn"]}, 
    "south_asia": {"name": "South Asia", "country_codes": ["in", "pk"]}, 
    "australia_nz": {"name": "Australia & NZ", "country_codes": ["au", "nz"]} 
}

# Mapping internal categories to NewsAPI.org and World News API categories/keywords
CATEGORIES = {
    "news": {"newsapi_cat": "general", "newsapi_query_keyword": "general news", "worldnewsapi_query": "general news"},
    "technology": {"newsapi_cat": "technology", "newsapi_query_keyword": "technology OR tech", "worldnewsapi_query": "technology OR tech"},
    "finance": {"newsapi_cat": "business", "newsapi_query_keyword": "business OR finance OR economy", "worldnewsapi_query": "business OR finance OR economy"},
    "travel": {"newsapi_cat": "general", "newsapi_query_keyword": "travel OR tourism", "worldnewsapi_query": "travel OR tourism"}, 
    "world": {"newsapi_cat": "general", "newsapi_query_keyword": "world affairs OR international news", "worldnewsapi_query": "world affairs OR international news"},
    "weather": {"newsapi_cat": "science", "newsapi_query_keyword": "weather OR climate", "worldnewsapi_query": "weather OR climate"}, 
    "blogs": {"newsapi_cat": "general", "newsapi_query_keyword": "blogs OR opinion pieces", "worldnewsapi_query": "blogs OR opinion pieces"} 
}

# --- Constants for incremental update ---
MAX_ARTICLES_PER_CATEGORY = 30 
ARTICLES_TO_FETCH_PER_RUN = 8 # Number of articles to try and fetch/process for each category

# --- Constants for rotating processing ---
ALL_CATEGORY_KEYS = [(r_key, c_key) for r_key in REGIONS for c_key in CATEGORIES]
TOTAL_CATEGORIES = len(ALL_CATEGORY_KEYS) 
NUM_BATCHES = 6 # Runs every 4 hours (24/4 = 6 runs per day)
BATCH_SIZE = 10 # Process 10 categories per run

# --- Functions ---

def generate_simulated_content(region_name, category_name, count=ARTICLES_TO_FETCH_PER_RUN):
    """
    Generates simulated content as a last-resort fallback.
    These articles will be explicitly marked as is_simulated=True.
    """
    articles = []
    for i in range(count):
        # Use more descriptive placeholder text for images
        image_text = f"{category_name.replace('_', ' ').title()} {region_name.replace(' ', ' ').title()}"
        
        articles.append({
            "title": f"Simulated {category_name.replace('_', ' ').title()} Headline for {region_name} - {random.randint(100, 999)}",
            "content_raw": f"This is a simulated summary of {category_name.replace('_', ' ')} related to {region_name}, article number {i + 1}. It highlights key developments and insights. This content is for placeholder purposes only.",
            "link": f"https://example.com/simulated/{region_name.lower().replace(' ', '-')}/{category_name.lower().replace(' ', '-')}/{i + 1}",
            "imageUrl_raw": f"https://placehold.co/600x400/CCCCCC/333333?text=SIMULATED+{image_text.upper()}", 
            "is_simulated": True # Explicitly mark as simulated
        })
    return articles

async def fetch_from_newsapi_org(region_key, category_info, page_size):
    """Attempts to fetch news from NewsAPI.org."""
    country_codes_for_region = REGIONS[region_key]["country_codes"]
    newsapi_category = category_info["newsapi_cat"]
    newsapi_query_keyword = category_info["newsapi_query_keyword"] # Use the new key

    for country_code in country_codes_for_region:
        categories_to_try = [newsapi_category]
        if newsapi_category != "general":
            categories_to_try.append("general")

        for current_cat_to_try in categories_to_try:
            params = {
                "category": current_cat_to_try,
                "country": country_code,
                "pageSize": page_size,
                "language": "en"
            }
            headers = {'X-Api-Key': NEWSAPI_API_KEY}
            
            print(f"DEBUG: NewsAPI.org Attempt for {region_key}/{category_info['newsapi_cat']} (Country: {country_code}, Category: '{current_cat_to_try}'): {params}")

            try:
                response = requests.get(f"{NEWSAPI_BASE_URL}top-headlines", params=params, headers=headers, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                fetched_articles = []
                for article_data in data.get('articles', []):
                    title = article_data.get('title')
                    description = article_data.get('description')
                    url = article_data.get('url')
                    image_url = article_data.get('urlToImage')

                    if title and description and url:
                        fetched_articles.append({
                            "title": title,
                            "content_raw": description,
                            "link": url,
                            "imageUrl_raw": image_url,
                            "is_simulated": False
                        })
                if fetched_articles:
                    print(f"DEBUG: Successfully fetched {len(fetched_articles)} articles from NewsAPI.org for {region_key}/{category_info['newsapi_cat']} (Country: {country_code}, Category: '{current_cat_to_try}').")
                    return fetched_articles
                else:
                    print(f"DEBUG: NewsAPI.org returned no articles for {region_key}/{category_info['newsapi_cat']} (Country: {country_code}, Category: '{current_cat_to_try}').")
                    time.sleep(1) # Small delay
                    continue

            except requests.exceptions.HTTPError as http_err:
                error_response = {}
                try:
                    error_response = http_err.response.json()
                except json.JSONDecodeError:
                    pass
                print(f"Error from NewsAPI.org for {region_key}/{category_info['newsapi_cat']} (Country: {country_code}, Category: '{current_cat_to_try}'): {http_err}. Response: {error_response}")
                time.sleep(1) # Small delay
                continue
            except requests.exceptions.RequestException as e:
                print(f"Network error from NewsAPI.org for {region_key}/{category_info['newsapi_cat']} (Country: {country_code}, Category: '{current_cat_to_try}'): {e}")
                time.sleep(1) # Small delay
                continue
    
    # For 'global' region, try the /everything endpoint with query
    # Use the new newsapi_query_keyword here
    if region_key == "global" and newsapi_query_keyword:
        params = {
            'q': newsapi_query_keyword,
            'language': 'en',
            'pageSize': page_size,
            'sortBy': 'relevancy'
        }
        headers = {'X-Api-Key': NEWSAPI_API_KEY}
        print(f"DEBUG: NewsAPI.org Attempt for global/{category_info['newsapi_cat']} (Query: '{newsapi_query_keyword}'): {params}")
        try:
            response = requests.get(f"{NEWSAPI_BASE_URL}everything", params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            fetched_articles = []
            for article_data in data.get('articles', []):
                title = article_data.get('title')
                description = article_data.get('description')
                url = article_data.get('url')
                image_url = article_data.get('urlToImage')
                if title and description and url:
                    fetched_articles.append({
                        "title": title,
                        "content_raw": description,
                        "link": url,
                        "imageUrl_raw": image_url,
                        "is_simulated": False
                    })
            if fetched_articles:
                print(f"DEBUG: Successfully fetched {len(fetched_articles)} articles from NewsAPI.org (everything) for global/{category_info['newsapi_cat']}.")
                return fetched_articles
            else:
                print(f"DEBUG: NewsAPI.org (everything) returned no articles for global/{category_info['newsapi_cat']}.")
        except requests.exceptions.RequestException as e:
            print(f"Error from NewsAPI.org (everything) for global/{category_info['newsapi_cat']}: {e}")
    
    return [] # Return empty if no articles found from NewsAPI.org

async def fetch_from_worldnewsapi(region_key, category_info, page_size):
    """Attempts to fetch news from World News API."""
    country_codes_for_region = REGIONS[region_key]["country_codes"]
    query_keyword = category_info["worldnewsapi_query"]

    # World News API often works better with 'search-news' and keywords for categories
    # It also uses 'source-countries' for filtering.
    
    for country_code in country_codes_for_region:
        params = {
            'api-key': WORLD_NEWS_API_KEY,
            'text': query_keyword,
            'language': 'en',
            'number': page_size, # World News API uses 'number' for page size
            'source-countries': country_code
        }
        print(f"DEBUG: World News API Attempt for {region_key}/{category_info['worldnewsapi_query']} (Country: {country_code}, Query: '{query_keyword}'): {params}")
        try:
            response = requests.get(f"{WORLD_NEWS_API_BASE_URL}search-news", params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            fetched_articles = []
            for article_data in data.get('news', []): # World News API uses 'news' key
                title = article_data.get('title')
                content_text = article_data.get('text') # World News API uses 'text' for content
                url = article_data.get('url')
                image_url = article_data.get('image') # World News API uses 'image' for image URL

                if title and content_text and url:
                    fetched_articles.append({
                        "title": title,
                        "content_raw": content_text,
                        "link": url,
                        "imageUrl_raw": image_url,
                        "is_simulated": False
                    })
            if fetched_articles:
                print(f"DEBUG: Successfully fetched {len(fetched_articles)} articles from World News API for {region_key}/{category_info['worldnewsapi_query']} (Country: {country_code}).")
                return fetched_articles
            else:
                print(f"DEBUG: World News API returned no articles for {region_key}/{category_info['worldnewsapi_query']} (Country: {country_code}).")
                time.sleep(1) # Small delay
                continue

        except requests.exceptions.HTTPError as http_err:
            error_response = {}
            try:
                error_response = http_err.response.json()
            except json.JSONDecodeError:
                pass
            print(f"Error from World News API for {region_key}/{category_info['worldnewsapi_query']} (Country: {country_code}): {http_err}. Response: {error_response}")
            time.sleep(1) # Small delay
            continue
        except requests.exceptions.RequestException as e:
            print(f"Network error from World News API for {region_key}/{category_info['worldnewsapi_query']} (Country: {country_code}): {e}")
            time.sleep(1) # Small delay
            continue
    
    # For 'global' region, try a broader search without country filter
    if region_key == "global" and query_keyword:
        params = {
            'api-key': WORLD_NEWS_API_KEY,
            'text': query_keyword,
            'language': 'en',
            'number': page_size
        }
        print(f"DEBUG: World News API Attempt for global/{category_info['worldnewsapi_query']} (Query: '{query_keyword}'): {params}")
        try:
            response = requests.get(f"{WORLD_NEWS_API_BASE_URL}search-news", params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            fetched_articles = []
            for article_data in data.get('news', []):
                title = article_data.get('title')
                content_text = article_data.get('text')
                url = article_data.get('url')
                image_url = article_data.get('image')
                if title and content_text and url:
                    fetched_articles.append({
                        "title": title,
                        "content_raw": content_text,
                        "link": url,
                        "imageUrl_raw": image_url,
                        "is_simulated": False
                    })
            if fetched_articles:
                print(f"DEBUG: Successfully fetched {len(fetched_articles)} articles from World News API (global search) for global/{category_info['worldnewsapi_query']}.")
                return fetched_articles
            else:
                print(f"DEBUG: World News API (global search) returned no articles for global/{category_info['worldnewsapi_query']}.")
        except requests.exceptions.RequestException as e:
            print(f"Error from World News API (global search) for global/{category_info['worldnewsapi_query']}: {e}")

    return [] # Return empty if no articles found from World News API

async def get_mistral_summary_and_image(original_title, original_content_raw, category_name, original_image_url_raw):
    """
    Uses Mistral AI API to summarize content and suggest a relevant image URL.
    This function now processes real data from NewsAPI.org or World News API.
    """
    prompt = f"""
    You are an AI assistant for a news portal. Your task is to take the following article
    title and content, and generate a concise summary (around 50-70 words) for a news feed.
    The summary should capture the main points and be engaging.
    Additionally, suggest a relevant direct image URL. If an image URL is provided, validate it. If it's missing or invalid, suggest a new one.
    Prioritize real image URLs if available and valid. If generating, use 'https://picsum.photos/600/400/?random' or 'https://placehold.co/600x400/HEX/HEX?text=TEXT'.

    Original Title: "{original_title}"
    Original Content: "{original_content_raw}"
    Category: "{category_name}"
    Original Image URL (if available): "{original_image_url_raw}"

    Provide the output in JSON format with the following schema:
    {{
      "summary": "string",
      "suggestedImageUrl": "string"
    }}
    """

    payload = {
        "model": "mistral-tiny",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }

    try:
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {MISTRAL_API_KEY}'
        }
        
        response = requests.post(MISTRAL_API_BASE_URL, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        result = response.json()
        
        print(f"DEBUG: Raw Mistral AI response for '{original_title}': {json.dumps(result, indent=2)}")

        if result.get('choices') and result['choices'][0].get('message') and result['choices'][0]['message'].get('content'):
            json_string = result['choices'][0]['message']['content']
            parsed_json = json.loads(json_string)
            
            summary = parsed_json.get('summary', original_content_raw)
            suggested_image_url = parsed_json.get('suggestedImageUrl', '')

            if original_image_url_raw and (original_image_url_raw.startswith('http://') or original_image_url_raw.startswith('https://')):
                final_image_url = original_image_url_raw
            elif suggested_image_url and (suggested_image_url.startswith('http://') or suggested_image_url.startswith('https://')):
                final_image_url = suggested_image_url
            else:
                image_keywords_for_fallback = category_name.replace('_', '+') + "+" + original_title.replace(' ', '+')
                final_image_url = f"https://placehold.co/600x400/CCCCCC/333333?text=AI+Image+Fallback"

            return summary, final_image_url, False # Mistral successfully processed
        else:
            print(f"Mistral AI API response missing expected structure for '{original_title}': {result}")
            return original_content_raw, original_image_url_raw or 'https://placehold.co/600x400/CCCCCC/333333?text=AI+Process+Failed', True 

    except requests.exceptions.RequestException as e:
        print(f"Error calling Mistral AI API for '{original_title}': {e}")
        if response and response.text:
            print(f"Mistral AI API Error Response: {response.text}")
        return original_content_raw, original_image_url_raw or 'https://placehold.co/600x400/CCCCCC/333333?text=API+Error+Image', True 
    except json.JSONDecodeError as e:
        print(f"Error decoding Mistral AI API JSON response for '{original_title}': {e}")
        if response and response.text:
            print(f"Raw Mistral AI response text: {response.text}")
        return original_content_raw, original_image_url_raw or 'https://placehold.co/600x400/CCCCCC/333333?text=JSON+Error+Image', True 


def get_current_batch_index():
    """
    Determines which batch of categories to process based on the current UTC hour.
    Assumes workflow runs at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC.
    """
    now_utc = datetime.now(timezone.utc)
    current_hour_utc = now_utc.hour

    if 0 <= current_hour_utc < 4:
        return 0 
    elif 4 <= current_hour_utc < 8:
        return 1 
    elif 8 <= current_hour_utc < 12:
        return 2 
    elif 12 <= current_hour_utc < 16:
        return 3 
    elif 16 <= current_hour_utc < 20:
        return 4 
    else: # 20 <= current_hour_utc < 24
        return 5 

async def main():
    output_file_path = 'updates.json'
    all_content = {}
    
    if os.path.exists(output_file_path):
        try:
            with open(output_file_path, 'r', encoding='utf-8') as f:
                all_content = json.load(f)
            print(f"Successfully loaded existing content from {output_file_path}")
        except json.JSONDecodeError as e:
            print(f"Error decoding existing {output_file_path}: {e}. Starting with empty content.")
            all_content = {}
        except IOError as e:
            print(f"Error reading existing {output_file_path}: {e}. Starting with empty content.")
            all_content = {}
    else:
        print(f"No existing {output_file_path} found. Starting with empty content.")

    all_content['last_updated_utc'] = datetime.now(timezone.utc).isoformat()

    current_batch_idx = get_current_batch_index()
    start_idx = current_batch_idx * BATCH_SIZE
    end_idx = min(start_idx + BATCH_SIZE, TOTAL_CATEGORIES)
    categories_to_process_in_this_run = ALL_CATEGORY_KEYS[start_idx:end_idx]

    print(f"--- Processing Batch {current_batch_idx + 1}/{NUM_BATCHES} ({len(categories_to_process_in_this_run)} categories) ---")

    for region_key, category_key in categories_to_process_in_this_run:
        region_name_full = REGIONS[region_key]["name"]
        category_info = CATEGORIES[category_key]
        
        print(f"Processing Region: {region_name_full}, Category: {category_key} with NewsAPI.org, World News API, and Mistral AI...")
        
        if region_key not in all_content:
            all_content[region_key] = {}
        
        articles_to_add = []

        # 1. Attempt to fetch from NewsAPI.org
        if NEWSAPI_API_KEY:
            newsapi_articles = await fetch_from_newsapi_org(region_key, category_info, ARTICLES_TO_FETCH_PER_RUN)
            if newsapi_articles:
                articles_to_add = newsapi_articles
                print(f"  -> Fetched {len(newsapi_articles)} articles from NewsAPI.org for {region_key}/{category_key}.")
            else:
                print(f"  -> NewsAPI.org returned no articles for {region_key}/{category_key}. Trying World News API.")
        else:
            print(f"  -> NEWSAPI_API_KEY not configured. Skipping NewsAPI.org for {region_key}/{category_key}.")

        # 2. If NewsAPI.org failed, attempt to fetch from World News API
        if not articles_to_add and WORLD_NEWS_API_KEY:
            worldnewsapi_articles = await fetch_from_worldnewsapi(region_key, category_info, ARTICLES_TO_FETCH_PER_RUN)
            if worldnewsapi_articles:
                articles_to_add = worldnewsapi_articles
                print(f"  -> Fetched {len(worldnewsapi_articles)} articles from World News API for {region_key}/{category_key}.")
            else:
                print(f"  -> World News API returned no articles for {region_key}/{category_key}. Falling back to simulated content (not published).")
        elif not articles_to_add and not WORLD_NEWS_API_KEY:
            print(f"  -> WORLD_NEWS_API_KEY not configured. Skipping World News API for {region_key}/{category_key}.")
            
        current_processed_articles_batch = [] 

        if articles_to_add: # Only process with Mistral if we got articles from either API
            for i, article_raw in enumerate(articles_to_add):
                print(f"  - Processing article {i+1}/{len(articles_to_add)} for {region_key}/{category_key} with Mistral AI...")
                
                summary_content, final_image_url, mistral_processing_failed = await get_mistral_summary_and_image(
                    article_raw['title'], 
                    article_raw['content_raw'], 
                    category_key,
                    article_raw['imageUrl_raw']
                )
                
                current_processed_articles_batch.append({
                    "title": article_raw['title'], 
                    "content": summary_content, 
                    "link": article_raw['link'], 
                    "imageUrl": final_image_url, 
                    "is_simulated": article_raw['is_simulated'] or mistral_processing_failed # True if original was simulated OR Mistral failed
                })
                time.sleep(20) # Delay after each Mistral AI call
        else:
            # If no articles from either API, generate simulated content, but mark it as such
            # This content will NOT be published to updates.json if it's purely simulated.
            simulated_fallback_articles = generate_simulated_content(
                region_name_full, category_key, count=ARTICLES_TO_FETCH_PER_RUN
            )
            print(f"  -> No real articles found for {region_key}/{category_key}. Generated simulated fallback content (will be filtered by frontend).")
            # We don't add simulated_fallback_articles to current_processed_articles_batch
            # because we are explicitly NOT publishing simulated content to updates.json.

        # --- Incremental Merging Logic ---
        # ONLY update the category if we have new, successfully processed (non-simulated) articles from APIs.
        if current_processed_articles_batch: # If this batch contains real articles processed by Mistral
            if category_key not in all_content[region_key]:
                all_content[region_key][category_key] = []
                
            existing_articles_for_category = all_content[region_key].get(category_key, [])
            
            # Filter out old articles that were marked as simulated (e.g., if Mistral failed on them previously, or if they were old simulated content).
            filtered_existing_articles = [
                art for art in existing_articles_for_category if not art.get('is_simulated', False) 
            ]
            
            combined_articles = current_processed_articles_batch + filtered_existing_articles
            
            all_content[region_key][category_key] = combined_articles[:MAX_ARTICLES_PER_CATEGORY]
            print(f"  -> Total articles for {region_key}/{category_key}: {len(all_content[region_key][category_key])}")
        else:
            print(f"  -> {region_key}/{category_key} content remains unchanged (no new real articles successfully processed).")
        
        time.sleep(45) # Delay between categories/regions

    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_content, f, indent=2, ensure_ascii=False)
        print(f"Successfully generated and saved content to {output_file_path}")
    except IOError as e:
        print(f"Error writing to file {output_file_path}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
