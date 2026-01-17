'''
The is the first version of the scraper script using Playwright sync API. 
Which tends to be simpler but less scalable than the async version.
'''


from playwright.sync_api import sync_playwright
import time, urllib.parse
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


def scrape_posts(posts, seen):
    """
    Scrapes and prints details of the given posts locator.
    """
    Usernames = []
    DisplayNames = []
    VerifiedStatus = []
    for i in range(posts.count()):
        post = posts.nth(i)
        selector = post.locator('a')
        try:
            username = selector.first.get_attribute("href")
            if username in seen:
                continue
            seen.add(username)
        except:
            username = "N/A" 
        try:
            displayName = selector.second.text_content()
        except:
            displayName = "N/A" 
        try:
            verified  = True if selector.locator("svg[aria-label='Verified account']").first.count() > 0 else False
        except:
            verified = False 

        Usernames.append(username) 
        DisplayNames.append(displayName) 
        VerifiedStatus.append(verified) 

    return Usernames, DisplayNames, VerifiedStatus


def infinite_scroll_and_scrape(page, post_data, seen, max_scrolls=50):
    last_count = 0
    stagnant_scrolls = 0

    for scroll in range(max_scrolls):
        page.keyboard.press("End")

        page.wait_for_timeout(1500)  # small, controlled wait

        posts = page.locator('article[role="article"]')
        Usernames, DisplayNames, VerifiedStatus = scrape_posts(posts, seen)
        post_data['Usernames'].extend(Usernames)
        post_data['DisplayNames'].extend(DisplayNames)
        post_data['VerifiedStatus'].extend(VerifiedStatus)

        current_count = len(post_data['Usernames'])
        print(f"Scroll {scroll+1} | Visible: {posts.count()} | Total scraped: {current_count}")

        # Check for stagnation........
        if current_count == last_count:
            stagnant_scrolls += 1
            if stagnant_scrolls >= 3:
                print("No new tweets loading. Stopping.")
                break
        else:
            stagnant_scrolls = 0

        last_count = current_count


def main(query, max_scrolls=50, mode='top'):
    post_data = {
            'Usernames': [],
            'DisplayNames': [],
            'VerifiedStatus': []
        }
    with sync_playwright() as p:
        # Starting.......
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            java_script_enabled=True
        )
        context.add_cookies([
            {
                "name": "auth_token",
                "value": "1212...Auth_Token...1212",
                "domain": ".x.com",
                "path": "/",
                "secure": True,
                "httpOnly": True
            },
            {
                "name": "ct0",
                "value": "1212...CT0 Token...1212",
                "domain": ".x.com",
                "path": "/",
                "secure": True
            }
        ])
        page = context.new_page()
        page.route("**/*", lambda route: (
            route.abort()
            if route.request.resource_type in ["image", "video", "font", "stylesheet"]
            else route.continue_()
        ))

        try:
            page.goto(f"https://x.com/search?q={urllib.parse.quote(query)}&src=typed_query&f={mode}", wait_until="networkidle")
        
            page.wait_for_selector('article[role="article"]', timeout=60000)

            seen = set()

            infinite_scroll_and_scrape(page, post_data, seen, max_scrolls)

            context.close()
            browser.close()

            print("Scraping completed.")

            print(f"Total Scraped Posts: {len(post_data['Usernames'])}")
            print(post_data)
        except Exception as e:
            print(f"An error occurred: {e}")
            context.close()
            browser.close()

        return post_data


def scrape_parallel(query, max_scrolls=10):
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Start scraping both URLs in parallel
        future_live = executor.submit(main, query, max_scrolls, "live")
        future_top  = executor.submit(main, query, max_scrolls, "top")

        results_live = future_live.result()
        results_top  = future_top.result()

    # Merge results
    merged = {
        'Usernames': [],
        'DisplayNames': [],
        'VerifiedStatus': []
    }
    seen = set()

    for data in [results_live, results_top]:
        for u, d, v in zip(data['Usernames'], data['DisplayNames'], data['VerifiedStatus']):
            if u not in seen:
                seen.add(u)
                merged['Usernames'].append(u)
                merged['DisplayNames'].append(d)
                merged['VerifiedStatus'].append(v)

    print(f"Total unique posts: {len(merged['Usernames'])}")
    return merged

if __name__ == "__main__":
    query = "Physics and astronomy"
    final_data = scrape_parallel(query, max_scrolls=5)