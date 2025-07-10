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
NEWSAPI_BASE_URL = "https://newsapi.org/v2/top-headlines"

# Mistral AI API key should be stored as a GitHub Secret named MISTRAL_API_KEY.
MISTRAL_API_BASE_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY') 

# --- Debugging Print for API Keys ---
if NEWSAPI_API_KEY:
    NEWSAPI_API_KEY = NEWSAPI_API_KEY.strip()
    print(f"NEWSAPI_API_KEY successfully loaded from environment. Length: {len(NEWSAPI_API_KEY)}. Starts with: {NEWSAPI_API_KEY[:5]}... Ends with: {NEWSAPI_API_KEY[-5:]}")
else:
    print("WARNING: NEWSAPI_API_KEY is NOT loaded from environment. Please check GitHub Secrets and workflow env configuration.")

if MISTRAL_API_KEY:
    MISTRAL_API_KEY = MISTRAL_API_KEY.strip()
    print(f"MISTRAL_API_KEY successfully loaded from environment. Length: {len(MISTRAL_API_KEY)}. Starts with: {MISTRAL_API_KEY[:5]}... Ends with: {MISTRAL_API_KEY[-5:]}")
else:
    print("WARNING: MISTRAL_API_KEY is NOT loaded from environment. Please check GitHub Secrets and workflow env configuration.")
# --- End Debugging Print ---

# Define the regions and categories that match your index.html
# Added country_code for NewsAPI.org
REGIONS = {
    "global": {"name": "the entire world", "country_code": None}, # NewsAPI needs a country, will use 'us' as default for global if needed
    "north_america": {"name": "North America", "country_code": "us"},
    "europe": {"name": "Europe", "country_code": "gb"}, # Using Great Britain as a representative European country
    "asia": {"name": "Asia", "country_code": "in"}, # Using India as a representative Asian country
    "africa": {"name": "Africa", "country_code": "za"}, # Using South Africa
    "oceania": {"name": "Oceania", "country_code": "au"}, # Using Australia
    "south_america": {"name": "South America", "country_code": "br"}, # Using Brazil
    "middle_east": {"name": "Middle East", "country_code": "ae"}, # Using UAE
    "southeast_asia": {"name": "Southeast Asia", "country_code": "sg"}, # Using Singapore
    "north_africa": {"name": "North Africa", "country_code": "eg"}, # Using Egypt
    "sub_saharan_africa": {"name": "Sub-Saharan Africa", "country_code": "ng"}, # Using Nigeria
    "east_asia": {"name": "East Asia", "country_code": "jp"}, # Using Japan
    "south_asia": {"name": "South Asia", "country_code": "pk"}, # Using Pakistan
    "australia_nz": {"name": "Australia & NZ", "country_code": "nz"} # Using New Zealand
}

# Map internal categories to NewsAPI.org categories
NEWSAPI_CATEGORIES = {
    "news": "general",
    "technology": "technology",
    "finance": "business",
    "travel": "general", # NewsAPI doesn't have a specific 'travel' category for top headlines
    "world": "general",
    "weather": "science", # Closest fit for weather-related science news
    "blogs": "general" # NewsAPI doesn't have a specific 'blogs' category for top headlines
}

# --- Constants for incremental update ---
MAX_ARTICLES_PER_CATEGORY = 30 
ARTICLES_TO_FETCH_PER_RUN = 8 

# --- Constants for rotating processing ---
ALL_CATEGORY_KEYS = [(r_key, c_key) for r_key in REGIONS for c_key in NEWSAPI_CATEGORIES]
TOTAL_CATEGORIES = len(ALL_CATEGORY_KEYS) 
NUM_BATCHES = 4 
BATCH_SIZE = (TOTAL_CATEGORIES + NUM_BATCHES - 1) // NUM_BATCHES 

# --- Functions ---

async def fetch_news_from_newsapi(region_key, category_key, page_size=ARTICLES_TO_FETCH_PER_RUN):
    """
    Fetches real news articles from NewsAPI.org.
    """
    country_code = REGIONS[region_key]["country_code"]
    newsapi_category = NEWSAPI_CATEGORIES[category_key]

    # For 'global' region, we can iterate through a few countries or use a default
    # NewsAPI requires a country for top-headlines. Let's default to 'us' for global.
    if country_code is None:
        country_code = 'us' # Default country for global news

    params = {
        "apiKey": NEWSAPI_API_KEY,
        "category": newsapi_category,
        "country": country_code,
        "pageSize": page_size,
        "language": "en"
    }

    try:
        response = requests.get(NEWSAPI_BASE_URL, params=params, timeout=30)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        articles = []
        if data.get('articles'):
            for article_data in data['articles']:
                # Basic validation and fallback for essential fields
                title = article_data.get('title')
                description = article_data.get('description')
                url = article_data.get('url')
                image_url = article_data.get('urlToImage')

                # Skip articles with missing essential data
                if not title or not description or not url:
                    continue
                
                articles.append({
                    "title": title,
                    "content_raw": description, # Store raw description for Mistral to summarize
                    "link": url,
                    "imageUrl_raw": image_url, # Store raw image URL for Mistral to potentially refine
                    "is_simulated": False # This is real data from NewsAPI
                })
        return articles
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from NewsAPI.org for {region_key}/{category_key}: {e}")
        if response and response.text:
            print(f"NewsAPI.org Error Response: {response.text}")
        return [] # Return empty list on error

async def get_mistral_summary_and_image(original_title, original_content_raw, category_name, original_image_url_raw):
    """
    Uses Mistral AI API to summarize content and suggest a relevant image URL.
    This function now processes real data from NewsAPI.org.
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

            # Prioritize original_image_url_raw if it's valid
            if original_image_url_raw and (original_image_url_raw.startswith('http://') or original_image_url_raw.startswith('https://')):
                final_image_url = original_image_url_raw
            elif suggested_image_url and (suggested_image_url.startswith('http://') or suggested_image_url.startswith('https://')):
                final_image_url = suggested_image_url
            else:
                # Fallback to a generic placeholder if neither is valid
                image_keywords_for_fallback = category_name.replace('_', '+') + "+" + original_title.replace(' ', '+')
                final_image_url = f"https://placehold.co/600x400/CCCCCC/333333?text={image_keywords_for_fallback}"

            return summary, final_image_url, False # is_simulated = False
        else:
            print(f"Mistral AI API response missing expected structure: {result}")
            return original_content_raw, original_image_url_raw or 'https://placehold.co/600x400/CCCCCC/333333?text=AI+Image+Fallback', True # Fallback on Mistral failure

    except requests.exceptions.RequestException as e:
        print(f"Error calling Mistral AI API: {e}")
        if response and response.text:
            print(f"Mistral AI API Error Response: {response.text}")
        return original_content_raw, original_image_url_raw or 'https://placehold.co/600x400/CCCCCC/333333?text=API+Error+Image', True # Fallback on API error
    except json.JSONDecodeError as e:
        print(f"Error decoding Mistral AI API JSON response: {e}")
        if response and response.text:
            print(f"Raw Mistral AI response text: {response.text}")
        return original_content_raw, original_image_url_raw or 'https://placehold.co/600x400/CCCCCC/333333?text=JSON+Error+Image', True # Fallback on JSON error


def get_current_batch_index():
    """
    Determines which batch of categories to process based on the current UTC hour.
    Assumes workflow runs at 00:00, 06:00, 12:00, 18:00 UTC.
    """
    now_utc = datetime.now(timezone.utc)
    current_hour_utc = now_utc.hour

    if 0 <= current_hour_utc < 6:
        return 0 # 00:00 UTC run
    elif 6 <= current_hour_utc < 12:
        return 1 # 06:00 UTC run
    elif 12 <= current_hour_utc < 18:
        return 2 # 12:00 UTC run
    else: # 18 <= current_hour_utc < 24
        return 3 # 18:00 UTC run

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
        
        print(f"Processing Region: {region_name_full}, Category: {category_key} with NewsAPI.org and Mistral AI...")
        
        if region_key not in all_content:
            all_content[region_key] = {}
        
        # --- Fetch articles from NewsAPI.org ---
        newsapi_articles = await fetch_news_from_newsapi(region_key, category_key, page_size=ARTICLES_TO_FETCH_PER_RUN)
        
        current_processed_articles_batch = [] 
        
        for i, article_from_newsapi in enumerate(newsapi_articles):
            print(f"  - Processing article {i+1}/{len(newsapi_articles)} for {region_key}/{category_key} from NewsAPI...")
            
            # Use Mistral AI to summarize the description and potentially refine the image URL
            summary_content, final_image_url, is_simulated_by_mistral_fallback = await get_mistral_summary_and_image(
                article_from_newsapi['title'], 
                article_from_newsapi['content_raw'], 
                category_key,
                article_from_newsapi['imageUrl_raw']
            )
            
            current_processed_articles_batch.append({
                "title": article_from_newsapi['title'], # Use NewsAPI's title
                "content": summary_content, # Mistral AI's summary
                "link": article_from_newsapi['link'], # NewsAPI's original link
                "imageUrl": final_image_url, # NewsAPI's image or Mistral's suggested fallback
                "is_simulated": is_simulated_by_mistral_fallback # True if Mistral failed, False if NewsAPI/Mistral succeeded
            })
            time.sleep(15) # Shorter delay between article processing within a category

        # --- Incremental Merging Logic ---
        if category_key not in all_content[region_key]:
            all_content[region_key][category_key] = []
            
        existing_articles_for_category = all_content[region_key].get(category_key, [])
        
        # Filter out old simulated articles and combine with new real articles
        # Only keep existing articles that were NOT simulated (i.e., came from NewsAPI in previous runs)
        # and prepend the new batch.
        filtered_existing_articles = [
            art for art in existing_articles_for_category if not art.get('is_simulated', True)
        ]
        combined_articles = current_processed_articles_batch + filtered_existing_articles
        
        # Trim to MAX_ARTICLES_PER_CATEGORY
        all_content[region_key][category_key] = combined_articles[:MAX_ARTICLES_PER_CATEGORY]
        
        print(f"  -> Updated {region_key}/{category_key} with fresh NewsAPI content.")
        print(f"  -> Total articles for {region_key}/{category_key}: {len(all_content[region_key][category_key])}")
        
        time.sleep(30) # Delay between categories/regions

    # 2. Save the updated content to updates.json
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_content, f, indent=2, ensure_ascii=False)
        print(f"Successfully generated and saved content to {output_file_path}")
    except IOError as e:
        print(f"Error writing to file {output_file_path}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
