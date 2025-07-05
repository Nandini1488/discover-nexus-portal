import json
import os
import random
import time
import requests

# --- Configuration ---
# You'll need to sign up for a NewsAPI.org key: https://newsapi.org/
# The free developer tier allows up to 100 requests per day.
# Store this key as a GitHub Secret named NEWS_API_KEY
NEWS_API_KEY = os.getenv('NEWS_API_KEY') # Fetched from GitHub Secrets

# --- Debugging Print ---
if NEWS_API_KEY:
    print("NEWS_API_KEY successfully loaded from environment.")
else:
    print("WARNING: NEWS_API_KEY is NOT loaded from environment. Please check GitHub Secrets.")
# --- End Debugging Print ---

# Define the regions and categories that match your index.html
# Mapping regions to NewsAPI country codes (simplified, NewsAPI mostly by country)
REGIONS = {
    "global": {"name": "the entire world", "country_code": None}, # No specific country code for global
    "north_america": {"name": "North America", "country_code": "us"}, # Focusing on US for simplicity
    "europe": {"name": "Europe", "country_code": "gb"}, # Focusing on UK for Europe example
    "asia": {"name": "Asia", "country_code": "in"}, # Focusing on India for Asia example
    "africa": {"name": "Africa", "country_code": "ng"}, # Focusing on Nigeria for Africa example
    "oceania": {"name": "Oceania", "country_code": "au"}, # Focusing on Australia for Oceania example
    "south_america": {"name": "South America", "country_code": "br"}, # Focusing on Brazil for South America example
    "middle_east": {"name": "Middle East", "country_code": "ae"}, # Focusing on UAE for Middle East example
    "southeast_asia": {"name": "Southeast Asia", "country_code": "sg"}, # Focusing on Singapore for Southeast Asia example
    "north_africa": {"name": "North Africa", "country_code": "eg"}, # Focusing on Egypt for North Africa example
    "sub_saharan_africa": {"name": "Sub-Saharan Africa", "country_code": "za"}, # Focusing on South Africa for Sub-Saharan Africa example
    "east_asia": {"name": "East Asia", "country_code": "jp"}, # Focusing on Japan for East Asia example
    "south_asia": {"name": "South Asia", "country_code": "pk"}, # Focusing on Pakistan for South Asia example
    "australia_nz": {"name": "Australia & NZ", "country_code": "nz"} # Focusing on New Zealand for Australia & NZ example
}

CATEGORIES = {
    # For /top-headlines, these should ideally map to NewsAPI categories
    # NewsAPI categories: business, entertainment, general, health, science, sports, technology
    "news": "general", # Using 'general' as a broad category for news
    "technology": "technology",
    "finance": "business",
    "travel": "general", # No direct 'travel' category, using general
    "world": "general", # No direct 'world' category, using general
    "weather": "science", # No direct 'weather' category, using science
    "blogs": "general" # No direct 'blogs' category, using general
}

# --- Functions ---

def fetch_content_from_newsapi(api_endpoint, params, query_description=""):
    """
    Fetches real news articles from NewsAPI.org using the specified endpoint and parameters.
    """
    if not NEWS_API_KEY:
        print("NEWS_API_KEY is not set. Cannot fetch real news.")
        return []

    # Add API key to parameters
    params['apiKey'] = NEWS_API_KEY

    try:
        response = requests.get(f"https://newsapi.org/v2/{api_endpoint}", params=params, timeout=10)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        
        articles = []
        for article in data.get('articles', []):
            # Ensure essential fields exist before adding
            if article.get('title') and article.get('description') and article.get('url'):
                articles.append({
                    "title": article['title'],
                    "content": article['description'],
                    "link": article['url'],
                    "imageUrl": article.get('urlToImage', 'https://placehold.co/600x400/CCCCCC/333333?text=Image+Unavailable')
                })
        return articles
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching from NewsAPI for {query_description}: {e}")
        # Print the response body for more details on API errors (e.g., rate limits)
        if response.text:
            print(f"API Error Response: {response.text}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Network or other error fetching from NewsAPI for {query_description}: {e}")
        return []

def generate_simulated_content(region_name, category_name, count=15):
    """
    Generates simulated content as a fallback or for categories not covered by NewsAPI.
    """
    articles = []
    for i in range(count):
        hex_color_bg = ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])
        hex_color_text = ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])

        title = f"{category_name.replace('_', ' ').title()} Update {i + 1} for {region_name}"
        content = f"This is a simulated summary of {category_name.replace('_', ' ')} related to {region_name}, article number {i + 1}. It highlights key developments and insights."
        link = f"https://example.com/{region_name.lower().replace(' ', '-')}/{category_name.lower().replace(' ', '-')}/{i + 1}"
        image_url = f"https://placehold.co/600x400/{hex_color_bg}/{hex_color_text}?text={category_name.title()}+{i+1}"

        articles.append({
            "title": title,
            "content": content,
            "link": link,
            "imageUrl": image_url
        })
    return articles

def main():
    all_content = {}
    
    for region_key, region_data in REGIONS.items():
        region_name_full = region_data["name"]
        country_code = region_data["country_code"]
        
        all_content[region_key] = {}

        for category_key, newsapi_category in CATEGORIES.items():
            print(f"Processing Region: {region_name_full}, Category: {category_key}")
            
            articles = []
            if NEWS_API_KEY:
                if region_key == "global":
                    # Use /everything endpoint for global searches with a query
                    query_term = newsapi_category # Use the mapped category as a query term
                    params = {
                        'q': query_term,
                        'language': 'en',
                        'pageSize': 10,
                        'sortBy': 'relevancy' # Good for /everything
                    }
                    articles = fetch_content_from_newsapi("everything", params, 
                                                           query_description=f"query '{query_term}' for global/{category_key}")
                else:
                    # Use /top-headlines endpoint for specific countries and categories
                    if country_code: # Ensure country code exists for top-headlines
                        params = {
                            'country': country_code,
                            'category': newsapi_category,
                            'language': 'en',
                            'pageSize': 10
                        }
                        articles = fetch_content_from_newsapi("top-headlines", params, 
                                                               query_description=f"category '{newsapi_category}', country '{country_code}' for {region_key}/{category_key}")
                    else:
                        print(f"Skipping NewsAPI for {region_key}/{category_key}: No country code provided for /top-headlines.")
            
            if not articles:
                print(f"NewsAPI returned no articles or failed for {region_key}/{category_key}. Falling back to simulated content.")
                articles = generate_simulated_content(region_name_full, category_key, count=15)
            
            all_content[region_key][category_key] = articles
            time.sleep(5) # Increased sleep time to 5 seconds to be courteous to API

    output_file_path = 'updates.json'
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_content, f, indent=2, ensure_ascii=False)
        print(f"Successfully generated and saved content to {output_file_path}")
    except IOError as e:
        print(f"Error writing to file {output_file_path}: {e}")

if __name__ == "__main__":
    main()
