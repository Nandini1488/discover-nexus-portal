import json
import os
import random
import time
import requests
import asyncio # Import asyncio for running async functions

# --- Configuration ---
# Using Gemini API (gemini-2.0-flash model) for content enhancement/summarization.
# IMPORTANT: Gemini API does NOT fetch raw news. It processes text you provide.
# For a production portal, you'd need to replace generate_simulated_content_base
# with a mechanism to fetch raw news (e.g., RSS feeds, a basic news API for URLs, or web scraping).

# Gemini API is typically accessed via Google Cloud. For local development or
# within environments that provide it, you might not need an explicit API key here.
# However, if deploying to a custom environment that requires it, you'd set it up.
# For Canvas environment, the API key is automatically provided in the fetch call.
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
# Ensure the API key is loaded from the environment variable (GitHub Secret)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') 

# --- Debugging Print ---
if GEMINI_API_KEY:
    # Strip any potential whitespace from the API key
    GEMINI_API_KEY = GEMINI_API_KEY.strip()
    print(f"GEMINI_API_KEY successfully loaded from environment. Length: {len(GEMINI_API_KEY)}. Starts with: {GEMINI_API_KEY[:5]}... Ends with: {GEMINI_API_KEY[-5:]}")
else:
    print("WARNING: GEMINI_API_KEY is NOT loaded from environment. Please check GitHub Secrets and workflow env configuration.")
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

# --- Functions ---

def generate_simulated_content_base(region_name, category_name, count=15):
    """
    Generates simulated *base* content. In a real scenario, this would be
    replaced by fetching raw articles from a news source.
    """
    articles = []
    for i in range(count):
        title = f"Simulated {category_name.replace('_', ' ').title()} Headline {i + 1} for {region_name}"
        content = f"This is a placeholder for the full content of a simulated article about {category_name.replace('_', ' ')} in {region_name}. It would typically be a longer text that Gemini would summarize."
        link = f"https://example.com/{region_name.lower().replace(' ', '-')}/{category_name.lower().replace(' ', '-')}/{i + 1}"
        
        # We'll let Gemini suggest an image URL, but provide a fallback if it struggles.
        # For a real app, you'd get actual image URLs from your news source.
        image_url_placeholder = f"https://placehold.co/600x400/CCCCCC/333333?text={category_name.title()}+{i+1}"

        articles.append({
            "title": title,
            "content": content,
            "link": link,
            "imageUrl": image_url_placeholder, # This will be replaced by Gemini's suggestion
            "is_simulated": True # Mark as simulated content
        })
    return articles

async def get_gemini_summary_and_image(original_title, original_content, category_name):
    """
    Uses Gemini API to summarize content and suggest a relevant image URL.
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

    # chat_history needs to be a list of dictionaries as per Gemini API format
    chat_history = [{ "role": "user", "parts": [{ "text": prompt }] }]
    
    payload = {
        "contents": chat_history,
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "summary": { "type": "STRING" },
                    "suggestedImageUrl": { "type": "STRING" }
                },
                "propertyOrdering": ["summary", "suggestedImageUrl"]
            }
        }
    }

    try:
        headers = {'Content-Type': 'application/json'}
        api_url = GEMINI_API_BASE_URL
        
        # Only append API key if it's actually present (i.e., loaded from env)
        if GEMINI_API_KEY:
            api_url += f"?key={GEMINI_API_KEY}"

        # Use requests.post for synchronous call within the async function
        response = requests.post(api_url, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get('candidates') and result['candidates'][0].get('content') and result['candidates'][0]['content'].get('parts'):
            json_string = result['candidates'][0]['content']['parts'][0]['text']
            parsed_json = json.loads(json_string)
            return parsed_json.get('summary', original_content), parsed_json.get('suggestedImageUrl', 'https://placehold.co/600x400/CCCCCC/333333?text=AI+Image+Fallback'), False # is_simulated = False
        else:
            print(f"Gemini API response missing expected structure: {result}")
            return original_content, 'https://placehold.co/600x400/CCCCCC/333333?text=AI+Image+Fallback', True # Fallback to simulated if structure is wrong

    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        if response and response.text:
            print(f"Gemini API Error Response: {response.text}")
        return original_content, 'https://placehold.co/600x400/CCCCCC/333333?text=AI+Image+Fallback', True # Fallback to simulated on API error
    except json.JSONDecodeError as e:
        print(f"Error decoding Gemini API JSON response: {e}")
        if response and response.text: # Check if response exists before accessing .text
            print(f"Raw Gemini response text: {response.text}")
        return original_content, 'https://placehold.co/600x400/CCCCCC/333333?text=AI+Image+Fallback', True # Fallback to simulated on JSON error


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

    # Use a session to persist connection settings across requests, potentially speeding things up
    session = requests.Session() # requests.Session is synchronous, fine to use here

    for region_key, region_data in REGIONS.items():
        region_name_full = region_data["name"]
        
        # Ensure the region exists in all_content structure
        if region_key not in all_content:
            all_content[region_key] = {}

        for category_key, category_keyword in CATEGORIES.items():
            print(f"Processing Region: {region_name_full}, Category: {category_key} with Gemini...")
            
            # 1. Get base simulated articles (replace with real news source in production)
            # Keeping count at 3 articles per category.
            base_articles = generate_simulated_content_base(region_name_full, category_key, count=3) 

            current_processed_articles = [] # This will hold the articles for the current run
            
            # Flag to check if any article in this batch was successfully processed by Gemini
            any_gemini_success_in_batch = False

            for i, article in enumerate(base_articles):
                print(f"  - Processing article {i+1}/{len(base_articles)} for {region_key}/{category_key}...")
                # 2. Use Gemini to summarize and suggest image URL
                summary_content, suggested_image_url, is_simulated_by_gemini_fallback = await get_gemini_summary_and_image(
                    article['title'], article['content'], category_keyword
                )
                
                # If Gemini successfully processed, mark as not simulated
                if not is_simulated_by_gemini_fallback:
                    any_gemini_success_in_batch = True

                current_processed_articles.append({
                    "title": article['title'],
                    "content": summary_content, # Gemini's summary (or fallback)
                    "link": article['link'],
                    "imageUrl": suggested_image_url, # Gemini's suggested image URL (or fallback)
                    "is_simulated": is_simulated_by_gemini_fallback # True if Gemini failed, False if Gemini succeeded
                })
                # FURTHER INCREASED delay between individual Gemini calls
                time.sleep(5) # Increased from 3 seconds

            # --- Merging Logic ---
            # Check if there's existing content for this category and if it contains non-simulated articles
            existing_content_for_category = all_content[region_key].get(category_key, [])
            existing_has_real_content = any(not art.get('is_simulated', True) for art in existing_content_for_category)

            # Check if the newly generated content contains non-simulated articles
            new_has_real_content = any(not art.get('is_simulated', True) for art in current_processed_articles)

            if new_has_real_content:
                # If the new batch has real Gemini content, use it
                all_content[region_key][category_key] = current_processed_articles
                print(f"  -> Updated {region_key}/{category_key} with fresh Gemini content.")
            elif existing_has_real_content:
                # If new batch is all simulated, but existing content has real Gemini content, keep existing
                print(f"  -> Keeping existing Gemini content for {region_key}/{category_key} (new batch was simulated).")
                # No change to all_content[region_key][category_key] needed as it already holds existing
            else:
                # If both new and existing are simulated, use the new simulated content
                all_content[region_key][category_key] = current_processed_articles
                print(f"  -> Updated {region_key}/{category_key} with new simulated content (no real content available).")
            
            # FURTHER INCREASED delay between categories/regions
            time.sleep(20) # Increased from 10 seconds

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
