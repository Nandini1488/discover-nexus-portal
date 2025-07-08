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

def generate_simulated_content_base(region_name, category_name, count=1): # Changed default count to 1
    """
    Generates more realistic (but still simulated) base content for Mistral AI to summarize.
    """
    articles = []
    sample_contents = {
        "news": [
            f"A major political development unfolded in {region_name} today, with implications for upcoming elections. Analysts are closely watching the public's reaction to the new policy proposals.",
            f"Breaking news from {region_name}: a significant cultural festival has been announced, promising to draw visitors from across the globe. Local authorities are preparing for a large influx of tourists and media.",
            f"An unexpected economic report from {region_name} indicates a surprising upturn in key sectors. Experts are debating whether this trend is sustainable or a temporary fluctuation.",
            f"A new public health initiative launched in {region_name} aims to tackle a long-standing issue. Early results are promising, but widespread adoption remains a challenge.",
            f"Environmental activists in {region_name} are calling for urgent action on climate change, citing recent extreme weather events as evidence of escalating crisis. Government response is pending."
        ],
        "technology": [
            f"Innovators in {region_name} have unveiled a groundbreaking AI model capable of unprecedented data processing speeds. This could revolutionize industries from finance to healthcare.",
            f"A new quantum computing breakthrough from {region_name} promises to unlock solutions to complex problems currently beyond reach. Scientists are cautiously optimistic about its long-term potential.",
            f"The tech sector in {region_name} is buzzing about a new sustainable energy storage solution that could drastically reduce reliance on fossil fuels. Pilot projects are already underway.",
            f"A cybersecurity firm in {region_name} has detected a sophisticated new type of malware, prompting warnings across the digital landscape. Users are advised to update their systems immediately.",
            f"Virtual reality advancements in {region_name} are pushing the boundaries of immersive experiences, with new applications emerging in education and entertainment."
        ],
        "finance": [
            f"The stock market in {region_name} experienced a volatile session, driven by investor uncertainty over global trade tensions. Analysts predict continued fluctuations in the short term.",
            f"A major acquisition in {region_name}'s banking sector is set to reshape the financial landscape. Regulators are reviewing the deal for potential market impact.",
            f"Inflation concerns are rising in {region_name} as consumer prices continue to climb. Central bank officials are considering new measures to stabilize the economy.",
            f"Real estate markets in {region_name} are showing signs of cooling after a period of rapid growth. Experts suggest a more balanced market could emerge in the coming months.",
            f"Cryptocurrency adoption is surging in {region_name}, with new regulations being drafted to manage the growing digital asset market."
        ],
        "travel": [
            f"New travel restrictions have been eased for visitors to {region_name}, sparking a surge in tourism bookings. Local businesses are preparing for the influx of international guests.",
            f"A hidden gem in {region_name} has been named a top travel destination for next year, known for its pristine natural beauty and unique cultural experiences.",
            f"Sustainable tourism initiatives are gaining traction in {region_name}, with eco-friendly resorts and responsible travel options becoming increasingly popular.",
            f"Adventure tourism is booming in {region_name}, attracting thrill-seekers to its challenging landscapes and outdoor activities.",
            f"Food tourism is drawing gourmands to {region_name}, eager to explore its vibrant culinary scene and traditional dishes."
        ],
        "world": [
            f"Geopolitical tensions are escalating in a key region, with international bodies calling for de-escalation and dialogue. World leaders are closely monitoring the situation.",
            f"A global summit on climate change concluded with new commitments from major nations, though activists argue more urgent action is needed to meet ambitious targets.",
            f"International aid efforts are underway to assist a nation recovering from a natural disaster, with humanitarian organizations mobilizing resources worldwide.",
            f"A new trade agreement between several major economies is set to reshape global commerce, promising both opportunities and challenges for various industries.",
            f"Discussions at the United Nations focus on global health security, with renewed calls for international cooperation to prevent future pandemics."
        ],
        "weather": [
            f"An unprecedented heatwave is gripping parts of {region_name}, prompting health warnings and concerns about agricultural impact. Authorities are urging residents to take precautions.",
            f"Severe storms have caused widespread disruption across {region_name}, leading to power outages and travel delays. Emergency services are working to restore normalcy.",
            f"A new study predicts significant changes in precipitation patterns for {region_name} over the next decade, with implications for water management and agriculture.",
            f"Unusual cold fronts are sweeping through {region_name}, bringing record low temperatures and challenging winter conditions. Residents are advised to prepare for prolonged cold spells.",
            f"Coastal regions in {region_name} are bracing for higher sea levels, with new infrastructure projects being planned to mitigate the impact of climate change."
        ],
        "blogs": [
            f"A popular blogger from {region_name} has published a viral post dissecting the latest social media trends, sparking widespread debate and discussion.",
            f"An insightful opinion piece from {region_name} explores the future of remote work, offering unique perspectives on productivity and work-life balance.",
            f"A new travel blog highlights unexplored destinations in {region_name}, providing practical tips and stunning photography for adventurous readers.",
            f"The food blogging scene in {region_name} is thriving, with a recent post showcasing traditional recipes and local culinary secrets gaining international attention.",
            f"A tech blog from {region_name} reviews the newest gadgets and software, providing in-depth analysis and recommendations for tech enthusiasts."
        ]
    }

    for i in range(count):
        # Use a random sample from the relevant category's content
        content_options = sample_contents.get(category_name, sample_contents["news"]) # Default to news if category not found
        content = random.choice(content_options)
        
        # Make the title more dynamic, but still related to the simulated content
        title_prefix = f"Latest {category_name.replace('_', ' ').title()} Update"
        title = f"{title_prefix} from {region_name} - {random.randint(100, 999)}" # Add random number to make titles unique

        link = f"https://example.com/{region_name.lower().replace(' ', '-')}/{category_name.lower().replace(' ', '-')}/{i + 1}"
        
        # Generate a more relevant placeholder image URL based on category and region
        image_query = f"{category_name.replace('_', '+')}+{region_name.replace(' ', '+')}"
        image_url = f"https://placehold.co/600x400/{random.choice(['CCCCCC', 'FF5733', '33FF57', '3357FF'])}/{random.choice(['333333', 'FFFFFF'])}?text={category_name.title()}+{region_name.replace(' ', '+')}"

        articles.append({
            "title": title,
            "content": content,
            "link": link,
            "imageUrl": image_url, # This will be the placeholder, Mistral won't generate real images
            "is_simulated": True # Still marked as simulated as it's not real news data
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
    The summary should capture the main points and be engaging.
    Additionally, suggest a relevant placeholder image URL (e.g., from placehold.co or unsplash.com with relevant keywords)
    that visually represents the article's topic. Do NOT generate base64 images.

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
        
        # --- DEBUG PRINT: Print raw Mistral response ---
        print(f"DEBUG: Raw Mistral AI response for '{original_title}': {json.dumps(result, indent=2)}")
        # --- END DEBUG PRINT ---

        if result.get('choices') and result['choices'][0].get('message') and result['choices'][0]['message'].get('content'):
            json_string = result['choices'][0]['message']['content']
            parsed_json = json.loads(json_string)
            
            # Use the suggestedImageUrl from Mistral if it's a valid URL, otherwise fallback
            mistral_suggested_image_url = parsed_json.get('suggestedImageUrl', '')
            if not mistral_suggested_image_url or not (mistral_suggested_image_url.startswith('http://') or mistral_suggested_image_url.startswith('https://')):
                # Fallback to a more descriptive placeholder if Mistral doesn't provide a valid URL
                mistral_suggested_image_url = f"https://placehold.co/600x400/CCCCCC/333333?text={category_name.title()}+{original_title.split(' ')[-1]}"

            return parsed_json.get('summary', original_content), mistral_suggested_image_url, False # is_simulated = False
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
