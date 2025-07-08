import json
import os
import random
import time
import requests
import asyncio # Import asyncio for running async functions
from datetime import datetime, timezone # Import for time-based batching

# --- Configuration ---
# Using Mistral AI API for content enhancement/summarization.
# IMPORTANT: Mistral AI does NOT fetch raw news. It processes text you provide.
# For a production portal, you'd need to replace generate_simulated_content_base
# with a mechanism to fetch raw news (e.g., RSS feeds, a basic news API for URLs, or web scraping).

# Mistral AI API key should be stored as a GitHub Secret named MISTRAL_API_KEY.
MISTRAL_API_BASE_URL = "https://api.mistral.ai/v1/chat/completions"
# Ensure the API key is loaded from the environment variable (GitHub Secret)
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY') 

# --- Debugging Print ---
if MISTRAL_API_KEY:
    # Strip any potential whitespace from the API key
    MISTRAL_API_KEY = MISTRAL_API_KEY.strip()
    print(f"MISTRAL_API_KEY successfully loaded from environment. Length: {len(MISTRAL_API_KEY)}. Starts with: {MISTRAL_API_KEY[:5]}... Ends with: {MISTRAL_API_KEY[-5:]}")
else:
    print("WARNING: MISTRAL_API_KEY is NOT loaded from environment. Please check GitHub Secrets and workflow env configuration.")
# --- End Debugging Print ---

# Define the regions and categories that match your index.html
# These are used for generating simulated content and structuring the output JSON.
REGIONS = {
    "global": {"name": "the entire world", "country_code": None},
    "north_america": {"name": "North America", "country_code": "us"},
    "europe": {"name": "Europe", "country_code": "gb"},
    "asia": {"name": "Asia", "country_code": "in"},
    "africa": {"name": "Africa", "country_code": "za"},
    "oceania": {"name": "Oceania", "country_code": "au"},
    "south_america": {"name": "South America", "country_code": "br"},
    "middle_east": {"name": "Middle East", "country_code": "ae"},
    "southeast_asia": {"name": "Southeast Asia", "country_code": "sg"},
    "north_africa": {"name": "North Africa", "country_code": "eg"},
    "sub_saharan_africa": {"name": "Sub-Saharan Africa", "country_code": "ng"},
    "east_asia": {"name": "East Asia", "country_code": "jp"},
    "south_asia": {"name": "South Asia", "country_code": "pk"},
    "australia_nz": {"name": "Australia & NZ", "country_code": "nz"}
}

CATEGORIES = {
    "news": "general news",
    "technology": "technology innovations",
    "finance": "financial market insights",
    "travel": "travel guides and tips",
    "world": "international affairs and geopolitics",
    "weather": "global weather forecasts",
    "blogs": "featured articles and opinion pieces"
}

# --- Constants for incremental update ---
MAX_ARTICLES_PER_CATEGORY = 30 # Desired maximum articles to keep per category
ARTICLES_TO_FETCH_PER_RUN = 1 # Number of NEW articles to attempt to generate per category per run

# --- Constants for rotating processing ---
ALL_CATEGORY_KEYS = [(r_key, c_key) for r_key in REGIONS for c_key in CATEGORIES]
TOTAL_CATEGORIES = len(ALL_CATEGORY_KEYS) # 14 regions * 7 categories = 98
NUM_BATCHES = 4 # Since workflow runs every 6 hours (24/6 = 4 runs per day)
BATCH_SIZE = (TOTAL_CATEGORIES + NUM_BATCHES - 1) // NUM_BATCHES # Ceiling division

# --- Functions ---

def generate_simulated_content_base(region_name, category_name, count=15):
    """
    Generates simulated *base* content. In a real scenario, this would be
    replaced by fetching raw articles from a news source.
    """
    articles = []
    for i in range(count):
        title = f"Simulated {category_name.replace('_', ' ').title()} Headline {i + 1} for {region_name}"
        content = f"This is a placeholder for the full content of a simulated article about {category_name.replace('_', ' ')} in {region_name}. It would typically be a longer text that Mistral would summarize."
        link = f"https://example.com/{region_name.lower().replace(' ', '-')}/{category_name.lower().replace(' ', '-')}/{i + 1}"
        
        # We'll let Mistral suggest an image URL, but provide a fallback if it struggles.
        # For a real app, you'd get actual image URLs from your news source.
        image_url_placeholder = f"https://placehold.co/600x400/CCCCCC/333333?text={category_name.title()}+{i+1}"

        articles.append({
            "title": title,
            "content": content,
            "link": link,
            "imageUrl": image_url_placeholder, # This will be replaced by Mistral's suggestion
            "is_simulated": True # Mark as simulated content
        })
    return articles

async def get_mistral_summary_and_image(original_title, original_content, category_name):
    """
    Uses Mistral AI API to summarize content and suggest a relevant image URL.
    Ensures structured JSON output.
    """
    prompt = f"""
    You are an AI assistant for a news portal. Your task is to take the following article
    title and content, and generate a concise summary (around 50-70 words) for a news feed.
    Additionally, suggest a relevant placeholder image URL that visually represents the article's topic.

    Original Title: "{original_title}"
    Original Content: "{original_content}"
    Category: "{category_name}"

    Provide the output in JSON format with the following schema:
    {{
      "summary": "string",
      "suggestedImageUrl": "string"
    }}
    """

    # Mistral AI payload structure
    payload = {
        "model": "mistral-tiny", # Using mistral-tiny for potentially higher free tier limits
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"} # Requesting JSON output
    }

    try:
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {MISTRAL_API_KEY}' # Mistral uses Bearer token for auth
        }
        
        response = requests.post(MISTRAL_API_BASE_URL, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get('choices') and result['choices'][0].get('message') and result['choices'][0]['message'].get('content'):
            json_string = result['choices'][0]['message']['content']
            parsed_json = json.loads(json_string)
            return parsed_json.get('summary', original_content), parsed_json.get('suggestedImageUrl', 'https://placehold.co/600x400/CCCCCC/333333?text=AI+Image+Fallback'), False # is_simulated = False
        else:
            print(f"Mistral AI API response missing expected structure: {result}")
            return original_content, 'https://placehold.co/600x400/CCCCCC/333333?text=AI+Image+Fallback', True # Fallback to simulated if structure is wrong

    except requests.exceptions.RequestException as e:
        print(f"Error calling Mistral AI API: {e}")
        if response and response.text:
            print(f"Mistral AI API Error Response: {response.text}")
        return original_content, 'https://placehold.co/600x400/CCCCCC/333333?text=AI+Image+Fallback', True # Fallback to simulated on API error
    except json.JSONDecodeError as e:
        print(f"Error decoding Mistral AI API JSON response: {e}")
        if response and response.text: # Check if response exists before accessing .text
            print(f"Raw Mistral AI response text: {response.text}")
        return original_content, 'https://placehold.co/600x400/CCCCCC/333333?text=AI+Image+Fallback', True # Fallback to simulated on JSON error


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

async def main(): # Make main function async
    output_file_path = 'updates.json'
    all_content = {}
    
    # 1. Attempt to load existing content from updates.json
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

    # Determine which slice of categories to process in this run
    current_batch_idx = get_current_batch_index()
    start_idx = current_batch_idx * BATCH_SIZE
    end_idx = min(start_idx + BATCH_SIZE, TOTAL_CATEGORIES)
    categories_to_process_in_this_run = ALL_CATEGORY_KEYS[start_idx:end_idx]

    print(f"--- Processing Batch {current_batch_idx + 1}/{NUM_BATCHES} ({len(categories_to_process_in_this_run)} categories) ---")

    # Use a session to persist connection settings across requests, potentially speeding things up
    session = requests.Session() # requests.Session is synchronous, fine to use here

    for region_key, category_key in categories_to_process_in_this_run:
        region_name_full = REGIONS[region_key]["name"]
        category_keyword = CATEGORIES[category_key]

        print(f"Processing Region: {region_name_full}, Category: {category_key} with Mistral AI...")
        
        # Ensure the region exists in all_content structure
        if region_key not in all_content:
            all_content[region_key] = {}
        
        # 1. Get base simulated articles (replace with real news source in production)
        # Fetch only ARTICLES_TO_FETCH_PER_RUN new articles for this cycle
        base_articles = generate_simulated_content_base(
            region_name_full, category_key, count=ARTICLES_TO_FETCH_PER_RUN
        ) 

        current_processed_articles_batch = [] # This will hold the articles generated in this specific run
        
        for i, article in enumerate(base_articles):
            print(f"  - Processing article {i+1}/{len(base_articles)} for {region_key}/{category_key}...")
            # 2. Use Mistral AI to summarize and suggest image URL
            summary_content, suggested_image_url, is_simulated_by_mistral_fallback = await get_mistral_summary_and_image(
                article['title'], article['content'], category_keyword
            )
            
            current_processed_articles_batch.append({
                "title": article['title'],
                "content": summary_content, # Mistral AI's summary (or fallback)
                "link": article['link'],
                "imageUrl": suggested_image_url, # Mistral AI's suggested image URL (or fallback)
                "is_simulated": is_simulated_by_mistral_fallback # True if Mistral AI failed, False if Mistral AI succeeded
            })
            # Keep generous delays between individual LLM calls
            time.sleep(30) 

        # --- Incremental Merging Logic ---
        existing_articles_for_category = all_content[region_key].get(category_key, [])
        
        # Check if the new batch has *any* non-simulated (Mistral AI-generated) content
        new_batch_has_mistral_content = any(not art.get('is_simulated', True) for art in current_processed_articles_batch)

        if new_batch_has_mistral_content:
            # If the new batch contains Mistral AI content, prepend it and then filter existing simulated
            # This ensures new Mistral AI content always takes precedence
            filtered_existing_articles = [
                art for art in existing_articles_for_category if not art.get('is_simulated', True)
            ]
            combined_articles = current_processed_articles_batch + filtered_existing_articles
            print(f"  -> Updated {region_key}/{category_key} with fresh Mistral AI content.")
        else:
            # If the new batch is entirely simulated (Mistral AI calls failed),
            # we still prepend it to show "fresher" simulated content if no real content exists,
            # but we don't filter out existing real content.
            combined_articles = current_processed_articles_batch + existing_articles_for_category
            print(f"  -> New batch for {region_key}/{category_key} was simulated. Merging with existing content.")
        
        # Trim the list to the maximum desired number of articles
        all_content[region_key][category_key] = combined_articles[:MAX_ARTICLES_PER_CATEGORY]
        
        print(f"  -> Total articles for {region_key}/{category_key}: {len(all_content[region_key][category_key])}")
        
        # Keep generous delays between categories/regions
        time.sleep(60) 

    # 2. Save the updated content to updates.json
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_content, f, indent=2, ensure_ascii=False)
        print(f"Successfully generated and saved content to {output_file_path}")
    except IOError as e:
        print(f"Error writing to file {output_file_path}: {e}")

if __name__ == "__main__":
    # Run the async main function using asyncio
    asyncio.run(main())
