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
    "global": {"name": "the entire world", "country_codes": ["us", "gb", "ca", "au", "in"]}, # Try multiple countries for global news
    "north_america": {"name": "North America", "country_codes": ["us", "ca"]},
    "europe": {"name": "Europe", "country_codes": ["gb", "de", "fr", "es", "it"]}, # Multiple European countries
    "asia": {"name": "Asia", "country_codes": ["in", "cn", "jp", "kr"]}, # Multiple Asian countries (China might have limited coverage on NewsAPI free tier)
    "africa": {"name": "Africa", "country_codes": ["za", "ng", "eg"]}, # Multiple African countries
    "oceania": {"name": "Oceania", "country_codes": ["au", "nz"]},
    "south_america": {"name": "South America", "country_codes": ["br", "ar", "co"]}, # Multiple South American countries
    "middle_east": {"name": "Middle East", "country_codes": ["ae", "sa"]}, # UAE, Saudi Arabia
    "southeast_asia": {"name": "Southeast Asia", "country_codes": ["sg", "ph", "id"]}, # Singapore, Philippines, Indonesia
    "north_africa": {"name": "North Africa", "country_codes": ["eg"]}, # Egypt
    "sub_saharan_africa": {"name": "Sub-Saharan Africa", "country_codes": ["ng", "za"]}, # Nigeria, South Africa
    "east_asia": {"name": "East Asia", "country_codes": ["jp", "kr", "cn"]}, # Japan, South Korea, China
    "south_asia": {"name": "South Asia", "country_codes": ["in", "pk"]}, # India, Pakistan
    "australia_nz": {"name": "Australia & NZ", "country_codes": ["au", "nz"]} 
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
NUM_BATCHES = 4 # Still running 4 times per day (every 6 hours)
# NEW: Reduced BATCH_SIZE to make fewer API calls per run
# Aiming for ~10 categories per run to stay well within 1000 daily calls
BATCH_SIZE = 10 

# --- Functions ---

# This function is retained for potential future use or debugging, 
# but will no longer be used to populate updates.json in the main loop.
def generate_simulated_content_base(region_name, category_name, count=1):
    """
    Generates more realistic (but still simulated) base content for Mistral AI to summarize.
    Includes more descriptive titles and direct image URLs.
    """
    articles = []
    
    # Define more varied and descriptive content snippets
    sample_contents = {
        "news": [
            {"title_keywords": "Political Development", "content": f"A major political development unfolded in {region_name} today, with implications for upcoming elections. Analysts are closely watching the public's reaction to the new policy proposals.", "image_keywords": "politics, election"},
            {"title_keywords": "Cultural Festival Announced", "content": f"Breaking news from {region_name}: a significant cultural festival has been announced, promising to draw visitors from across the globe. Local authorities are preparing for a large influx of tourists and media.", "image_keywords": "festival, culture"},
            {"title_keywords": "Economic Report Upturn", "content": f"An unexpected economic report from {region_name} indicates a surprising upturn in key sectors. Experts are debating whether this trend is sustainable or a temporary fluctuation.", "image_keywords": "economy, finance"},
            {"title_keywords": "Public Health Initiative", "content": f"A new public health initiative launched in {region_name} aims to tackle a long-standing issue. Early results are promising, but widespread adoption remains a challenge.", "image_keywords": "health, public health"},
            {"title_keywords": "Environmental Activism", "content": f"Environmental activists in {region_name} are calling for urgent action on climate change, citing recent extreme weather events as evidence of escalating crisis. Government response is pending.", "image_keywords": "environment, climate change"}
        ],
        "technology": [
            {"title_keywords": "AI Model Breakthrough", "content": f"Innovators in {region_name} have unveiled a groundbreaking AI model capable of unprecedented data processing speeds. This could revolutionize industries from finance to healthcare.", "image_keywords": "AI, technology, innovation"},
            {"title_keywords": "Quantum Computing", "content": f"A new quantum computing breakthrough from {region_name} promises to unlock solutions to complex problems currently beyond reach. Scientists are cautiously optimistic about its long-term potential.", "image_keywords": "quantum computing, science"},
            {"title_keywords": "Sustainable Energy Solution", "content": f"The tech sector in {region_name} is buzzing about a new sustainable energy storage solution that could drastically reduce reliance on fossil fuels. Pilot projects are already underway.", "image_keywords": "energy, sustainability, tech"},
            {"title_keywords": "Cybersecurity Alert", "content": f"A cybersecurity firm in {region_name} has detected a sophisticated new type of malware, prompting warnings across the digital landscape. Users are advised to update their systems immediately.", "image_keywords": "cybersecurity, hacking"},
            {"title_keywords": "Virtual Reality Advancements", "content": f"Virtual reality advancements in {region_name} are pushing the boundaries of immersive experiences, with new applications emerging in education and entertainment.", "image_keywords": "VR, virtual reality, gaming"}
        ],
        "finance": [
            {"title_keywords": "Stock Market Volatility", "content": f"The stock market in {region_name} experienced a volatile session, driven by investor uncertainty over global trade tensions. Analysts predict continued fluctuations in the short term.", "image_keywords": "stock market, finance, economy"},
            {"title_keywords": "Banking Sector Acquisition", "content": f"A major acquisition in {region_name}'s banking sector is set to reshape the financial landscape. Regulators are reviewing the deal for potential market impact.", "image_keywords": "banking, acquisition, finance"},
            {"title_keywords": "Rising Inflation Concerns", "content": f"Inflation concerns are rising in {region_name} as consumer prices continue to climb. Central bank officials are considering new measures to stabilize the economy.", "image_keywords": "inflation, economy, money"},
            {"title_keywords": "Real Estate Cooling", "content": f"Real estate markets in {region_name} are showing signs of cooling after a period of rapid growth. Experts suggest a more balanced market could emerge in the coming months.", "image_keywords": "real estate, housing"},
            {"title_keywords": "Cryptocurrency Adoption", "content": f"Cryptocurrency adoption is surging in {region_name}, with new regulations being drafted to manage the growing digital asset market.", "image_keywords": "cryptocurrency, blockchain"}
        ],
        "travel": [
            {"title_keywords": "Travel Restrictions Eased", "content": f"New travel restrictions have been eased for visitors to {region_name}, sparking a surge in tourism bookings. Local businesses are preparing for the influx of international guests.", "image_keywords": "travel, tourism, destination"},
            {"title_keywords": "Hidden Gem Destination", "content": f"A hidden gem in {region_name} has been named a top travel destination for next year, known for its pristine natural beauty and unique cultural experiences.", "image_keywords": "travel, nature, culture"},
            {"title_keywords": "Sustainable Tourism", "content": f"Sustainable tourism initiatives are gaining traction in {region_name}, with eco-friendly resorts and responsible travel options becoming increasingly popular.", "image_keywords": "eco-tourism, sustainable travel"},
            {"title_keywords": "Adventure Tourism Boom", "content": f"Adventure tourism is booming in {region_name}, attracting thrill-seekers to its challenging landscapes and outdoor activities.", "image_keywords": "adventure, outdoor, travel"},
            {"title_keywords": "Food Tourism Draws Gourmands", "content": f"Food tourism is drawing gourmands to {region_name}, eager to explore its vibrant culinary scene and traditional dishes.", "image_keywords": "food, cuisine, travel"}
        ],
        "world": [
            {"title_keywords": "Geopolitical Tensions", "content": f"Geopolitical tensions are escalating in a key region, with international bodies calling for de-escalation and dialogue. World leaders are closely monitoring the situation.", "image_keywords": "geopolitics, world map"},
            {"title_keywords": "Global Climate Summit", "content": f"A global summit on climate change concluded with new commitments from major nations, though activists argue more urgent action is needed to meet ambitious targets.", "image_keywords": "climate change, summit"},
            {"title_keywords": "International Aid Efforts", "content": f"International aid efforts are underway to assist a nation recovering from a natural disaster, with humanitarian organizations mobilizing resources worldwide.", "image_keywords": "aid, disaster relief"},
            {"title_keywords": "New Trade Agreement", "content": f"A new trade agreement between several major economies is set to reshape global commerce, promising both opportunities and challenges for various industries.", "image_keywords": "trade, economy, global"},
            {"title_keywords": "UN Health Security Talks", "content": f"Discussions at the United Nations focus on global health security, with renewed calls for international cooperation to prevent future pandemics.", "image_keywords": "UN, health, global health"}
        ],
        "weather": [
            {"title_keywords": "Unprecedented Heatwave", "content": f"An unprecedented heatwave is gripping parts of {region_name}, prompting health warnings and concerns about agricultural impact. Authorities are urging residents to take precautions.", "image_keywords": "heatwave, weather"},
            {"title_keywords": "Severe Storms Disrupt", "content": f"Severe storms have caused widespread disruption across {region_name}, leading to power outages and travel delays. Emergency services are working to restore normalcy.", "image_keywords": "storm, weather, disaster"},
            {"title_keywords": "Precipitation Pattern Changes", "content": f"A new study predicts significant changes in precipitation patterns for {region_name} over the next decade, with implications for water management and agriculture.", "image_keywords": "rain, climate, agriculture"},
            {"title_keywords": "Unusual Cold Fronts", "content": f"Unusual cold fronts are sweeping through {region_name}, bringing record low temperatures and challenging winter conditions. Residents are advised to prepare for prolonged cold spells.", "image_keywords": "cold, winter, snow"},
            {"title_keywords": "Coastal Sea Level Rise", "content": f"Coastal regions in {region_name} are bracing for higher sea levels, with new infrastructure projects being planned to mitigate the impact of climate change.", "image_keywords": "sea level, coast, climate"}
        ],
        "blogs": [
            {"title_keywords": "Viral Social Media Post", "content": f"A popular blogger from {region_name} has published a viral post dissecting the latest social media trends, sparking widespread debate and discussion.", "image_keywords": "social media, blog"},
            {"title_keywords": "Future of Remote Work", "content": f"An insightful opinion piece from {region_name} explores the future of remote work, offering unique perspectives on productivity and work-life balance.", "image_keywords": "remote work, productivity"},
            {"title_keywords": "Unexplored Travel Destinations", "content": f"A new travel blog highlights unexplored destinations in {region_name}, providing practical tips and stunning photography for adventurous readers.", "image_keywords": "travel blog, adventure"},
            {"title_keywords": "Thriving Food Blogging", "content": f"The food blogging scene in {region_name} is thriving, with a recent post showcasing traditional recipes and local culinary secrets gaining international attention.", "image_keywords": "food blog, cuisine"},
            {"title_keywords": "New Tech Gadget Review", "content": f"A tech blog from {region_name} reviews the newest gadgets and software, providing in-depth analysis and recommendations for tech enthusiasts.", "image_keywords": "tech blog, gadgets"}
        ]
    }

    for i in range(count):
        content_item = random.choice(sample_contents.get(category_name, sample_contents["news"]))
        
        title = f"{content_item['title_keywords']} in {region_name}"

        image_url = f"https://picsum.photos/seed/{random.randint(1, 1000)}/600/400/?random&keywords={content_item['image_keywords'].replace(' ', ',')}"

        domain_name = f"{region_name.lower().replace(' ', '-')}-news.com"
        link = f"https://www.{domain_name}/{category_name.lower().replace('_', '-')}/article-{random.randint(10000, 99999)}"
        
        articles.append({
            "title": title,
            "content_raw": content_item['content'],
            "link": link,
            "imageUrl_raw": image_url, 
            "is_simulated": True 
        })
    return articles

async def fetch_news_from_newsapi(region_key, category_key, page_size=ARTICLES_TO_FETCH_PER_RUN):
    """
    Fetches real news articles from NewsAPI.org.
    Includes a fallback to 'general' category if the specific category is not applicable.
    Tries multiple countries for regions with multiple country codes.
    """
    country_codes_for_region = REGIONS[region_key]["country_codes"]
    newsapi_category = NEWSAPI_CATEGORIES[category_key]

    articles = []
    
    # Iterate through each country code for the region
    for country_code in country_codes_for_region:
        # List of categories to try, starting with the specific one, then general
        categories_to_try = [newsapi_category]
        if newsapi_category != "general":
            categories_to_try.append("general") # Add general as a fallback

        # Iterate through categories for the current country
        for current_cat_to_try in categories_to_try:
            params = {
                "apiKey": NEWSAPI_API_KEY, # This should now be correctly populated
                "category": current_cat_to_try,
                "country": country_code,
                "pageSize": page_size,
                "language": "en"
            }
            
            print(f"DEBUG: Attempting NewsAPI Request Params for {region_key}/{category_key} (Country: {country_code}, Category: '{current_cat_to_try}'): {params}")

            try:
                response = requests.get(NEWSAPI_BASE_URL, params=params, timeout=30)
                response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
                data = response.json()

                if data.get('articles'):
                    for article_data in data['articles']:
                        # Basic validation and fallback for essential fields
                        title = article_data.get('title')
                        description = article_data.get('description')
                        url = article_data.get('url')
                        image_url = article_data.get('urlToImage')

                        # Skip articles with missing essential data
                        if not title or not description or not url:
                            print(f"DEBUG: Skipping article due to missing title, description, or URL for {region_key}/{category_key} (Country: {country_code}, Category: '{current_cat_to_try}').")
                            continue
                        
                        articles.append({
                            "title": title,
                            "content_raw": description, # Store raw description for Mistral to summarize
                            "link": url,
                            "imageUrl_raw": image_url, # Store raw image URL for Mistral to potentially refine
                            "is_simulated": False # This is real data from NewsAPI
                        })
                    print(f"DEBUG: Successfully fetched {len(articles)} articles from NewsAPI for {region_key}/{category_key} (Country: {country_code}, Category: '{current_cat_to_try}').")
                    return articles # Return immediately upon successful fetch from any country/category combo
                else:
                    print(f"DEBUG: NewsAPI returned no articles for {region_key}/{category_key} (Country: {country_code}, Category: '{current_cat_to_try}'). Trying next category/country if available.")
                    continue # Try the next category or country

            except requests.exceptions.HTTPError as http_err:
                error_response = {}
                try:
                    error_response = http_err.response.json()
                except json.JSONDecodeError:
                    pass # Not a JSON error response

                if error_response.get('code') == 'categoryNotApplicable':
                    print(f"DEBUG: NewsAPI returned 'categoryNotApplicable' for {region_key}/{category_key} (Country: {country_code}, Category: '{current_cat_to_try}'). Trying next category/country if available.")
                    continue # Continue to the next category in categories_to_try or next country
                else:
                    print(f"Error fetching from NewsAPI.org for {region_key}/{category_key} (Country: {country_code}, Category: '{current_cat_to_try}'): {http_err}")
                    if http_err.response and http_err.response.text:
                        print(f"NewsAPI.org Error Response: {http_err.response.text}")
                    continue # Continue to next category/country on other HTTP errors

            except requests.exceptions.RequestException as e:
                print(f"Error fetching from NewsAPI.org for {region_key}/{category_key} (Country: {country_code}, Category: '{current_cat_to_try}'): {e}")
                continue # Continue to next category/country on general request errors

    print(f"DEBUG: No articles found from NewsAPI for {region_key}/{category_key} after trying all countries and categories. No new content will be published for this section.")
    return [] # Return empty list if no articles found after all attempts from NewsAPI

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
                # Fallback to a generic placeholder if neither is valid or if Mistral didn't provide one
                image_keywords_for_fallback = category_name.replace('_', '+') + "+" + original_title.replace(' ', '+')
                final_image_url = f"https://placehold.co/600x400/CCCCCC/333333?text={image_keywords_for_fallback}"

            # Return 'True' for 'is_simulated' only if Mistral *failed to process*, not if the original was simulated.
            # Here, the original article is always from NewsAPI.
            return summary, final_image_url, False # Mistral successfully processed NewsAPI content

        else:
            print(f"Mistral AI API response missing expected structure for '{original_title}': {result}")
            # If Mistral fails, use original raw content/image, and mark as simulated (due to AI processing failure)
            return original_content_raw, original_image_url_raw or 'https://placehold.co/600x400/CCCCCC/333333?text=AI+Process+Failed', True 

    except requests.exceptions.RequestException as e:
        print(f"Error calling Mistral AI API for '{original_title}': {e}")
        if response and response.text:
            print(f"Mistral AI API Error Response: {response.text}")
        # If Mistral API call fails, use original raw content/image, and mark as simulated (due to AI processing failure)
        return original_content_raw, original_image_url_raw or 'https://placehold.co/600x400/CCCCCC/333333?text=API+Error+Image', True 
    except json.JSONDecodeError as e:
        print(f"Error decoding Mistral AI API JSON response for '{original_title}': {e}")
        if response and response.text:
            print(f"Raw Mistral AI response text: {response.text}")
        # If JSON decoding fails, use original raw content/image, and mark as simulated (due to AI processing failure)
        return original_content_raw, original_image_url_raw or 'https://placehold.co/600x400/CCCCCC/333333?text=JSON+Error+Image', True 


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
        
        # --- Attempt to fetch articles from NewsAPI.org ---
        newsapi_articles = await fetch_news_from_newsapi(region_key, category_key, page_size=ARTICLES_TO_FETCH_PER_RUN)
        
        current_processed_articles_batch = [] 
        
        if newsapi_articles: # Only proceed if real news articles were successfully found from NewsAPI
            print(f"  -> Successfully fetched {len(newsapi_articles)} articles from NewsAPI for {region_key}/{category_key}. Now processing with Mistral AI.")
            for i, article_from_newsapi in enumerate(newsapi_articles):
                print(f"  - Processing article {i+1}/{len(newsapi_articles)} for {region_key}/{category_key} from NewsAPI...")
                
                # Use Mistral AI to summarize the description and potentially refine the image URL
                summary_content, final_image_url, mistral_processing_failed = await get_mistral_summary_and_image(
                    article_from_newsapi['title'], 
                    article_from_newsapi['content_raw'], 
                    category_key,
                    article_from_newsapi['imageUrl_raw']
                )
                
                current_processed_articles_batch.append({
                    "title": article_from_newsapi['title'], # Use original title from NewsAPI
                    "content": summary_content, # Mistral AI's summary
                    "link": article_from_newsapi['link'], # Original link from NewsAPI
                    "imageUrl": final_image_url, # NewsAPI's image or Mistral's suggested fallback
                    "is_simulated": mistral_processing_failed # True if Mistral failed to process this specific real article
                })
                time.sleep(15) # Shorter delay between article processing within a category
        else:
            print(f"  -> NewsAPI.org returned no articles for {region_key}/{category_key}. This section will NOT be updated in this run to avoid simulated content.")
            # current_processed_articles_batch remains empty, so no new content will be added for this category.

        # --- Incremental Merging Logic ---
        # ONLY update the category if we have new, successfully processed (non-simulated) articles from NewsAPI.
        if current_processed_articles_batch:
            if category_key not in all_content[region_key]:
                all_content[region_key][category_key] = []
                
            existing_articles_for_category = all_content[region_key].get(category_key, [])
            
            # Filter out old articles that were marked as simulated (e.g., if Mistral failed on them previously).
            # This ensures we only retain existing *real* articles.
            filtered_existing_articles = [
                art for art in existing_articles_for_category if not art.get('is_simulated', False) # Default to False, assuming existing is real unless marked
            ]
            
            combined_articles = current_processed_articles_batch + filtered_existing_articles
            
            # Trim to MAX_ARTICLES_PER_CATEGORY
            all_content[region_key][category_key] = combined_articles[:MAX_ARTICLES_PER_CATEGORY]
            print(f"  -> Total articles for {region_key}/{category_key}: {len(all_content[region_key][category_key])}")
        else:
            # If no new real articles were fetched and processed successfully, 
            # we explicitly do nothing to this category in all_content.
            # Its state (empty, or old real news) will be preserved.
            print(f"  -> {region_key}/{category_key} content remains unchanged (no new real articles successfully processed).")
        
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
