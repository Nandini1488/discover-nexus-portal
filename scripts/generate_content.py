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
            "imageUrl": image_url_placeholder # This will be replaced by Gemini's suggestion
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
            return parsed_json.get('summary', original_content), parsed_json.get('suggestedImageUrl', 'https://placehold.co/600x400/CCCCCC/333333?text=AI+Image+Fallback')
        else:
            print(f"Gemini API response missing expected structure: {result}")
            return original_content, 'https://placehold.co/600x400/CCCCCC/333333?text=AI+Image+Fallback'

    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        if response and response.text:
            print(f"Gemini API Error Response: {response.text}")
        return original_content, 'https://placehold.co/600x400/CCCCCC/333333?text=AI+Image+Fallback'
    except json.JSONDecodeError as e:
        print(f"Error decoding Gemini API JSON response: {e}")
        if response and response.text: # Check if response exists before accessing .text
            print(f"Raw Gemini response text: {response.text}")
        return original_content, 'https://placehold.co/600x400/CCCCCC/333333?text=AI+Image+Fallback'


async def main(): # Make main function async
    all_content = {}
    
    # Use a session to persist connection settings across requests, potentially speeding things up
    # and being more efficient with connections.
    session = requests.Session() # requests.Session is synchronous, fine to use here

    for region_key, region_data in REGIONS.items():
        region_name_full = region_data["name"]
        
        all_content[region_key] = {}

        for category_key, category_keyword in CATEGORIES.items():
            print(f"Processing Region: {region_name_full}, Category: {category_key} with Gemini...")
            
            # 1. Get base simulated articles (replace with real news source in production)
            base_articles = generate_simulated_content_base(region_name_full, category_key, count=10) # Reduced count for faster demo/lower token usage

            processed_articles = []
            for i, article in enumerate(base_articles):
                print(f"  - Processing article {i+1}/{len(base_articles)} for {region_key}/{category_key}...")
                # 2. Use Gemini to summarize and suggest image URL
                # AWAIT the async function call
                summary_content, suggested_image_url = await get_gemini_summary_and_image(
                    article['title'], article['content'], category_keyword
                )
                
                processed_articles.append({
                    "title": article['title'],
                    "content": summary_content, # Gemini's summary
                    "link": article['link'],
                    "imageUrl": suggested_image_url # Gemini's suggested image URL
                })
                time.sleep(1) # Small delay between Gemini calls to be courteous

            all_content[region_key][category_key] = processed_articles
            time.sleep(5) # Larger delay between categories/regions

    output_file_path = 'updates.json'
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_content, f, indent=2, ensure_ascii=False)
        print(f"Successfully generated and saved content to {output_file_path}")
    except IOError as e:
        print(f"Error writing to file {output_file_path}: {e}")

if __name__ == "__main__":
    # Run the async main function using asyncio
    asyncio.run(main())
