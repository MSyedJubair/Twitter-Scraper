"""
This is the final version of the scraper script using Playwright async API.
It scrapes posts from X (Twitter) based on search queries,
handling infinite scrolling and avoiding duplicates. Async and sync is the only 
difference between this and the previous version.
"""

from playwright.async_api import async_playwright
import asyncio
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

async def scrape_posts(posts, seen):
    """
    Scrapes and prints details of the given posts locator.
    """
    Usernames = []
    DisplayNames = []
    VerifiedStatus = []
    
    count = await posts.count()
    for i in range(count):
        post = posts.nth(i)
        selector = post.locator('a')
        try:
            username = await selector.first.get_attribute("href")
            if username in seen:
                continue
            seen.add(username)
        except:
            username = "N/A" 
        try:
            displayName = await selector.nth(1).text_content()
        except:
            displayName = "N/A" 
        try:
            verified_count = await selector.locator("svg[aria-label='Verified account']").first.count()
            verified = True if verified_count > 0 else False
        except:
            verified = False 

        Usernames.append(username) 
        DisplayNames.append(displayName) 
        VerifiedStatus.append(verified) 

    return Usernames, DisplayNames, VerifiedStatus


async def infinite_scroll_and_scrape(page, post_data, seen, max_scrolls=50):
    last_count = 0
    stagnant_scrolls = 0

    for scroll in range(max_scrolls):
        await page.keyboard.press("End")

        # Wait for new content with timeout - much faster than hard wait
        try:
            await page.wait_for_function(
                f"document.querySelectorAll('article[role=\"article\"]').length > {len(post_data['Usernames'])}",
                timeout=3000
            )
        except:
            # If timeout, still check for new posts
            await asyncio.sleep(0.5)

        posts = page.locator('article[role="article"]')
        Usernames, DisplayNames, VerifiedStatus = await scrape_posts(posts, seen)
        post_data['Usernames'].extend(Usernames)
        post_data['DisplayNames'].extend(DisplayNames)
        post_data['VerifiedStatus'].extend(VerifiedStatus)

        current_count = len(post_data['Usernames'])
        posts_count = await posts.count()
        print(f"Scroll {scroll+1} | Visible: {posts_count} | Total scraped: {current_count}")

        # Check for stagnation
        if current_count == last_count:
            stagnant_scrolls += 1
            if stagnant_scrolls >= 3:
                print("No new tweets loading. Stopping.")
                break
        else:
            stagnant_scrolls = 0

        last_count = current_count


async def main(query, max_scrolls=50, mode='top'):
    post_data = {
        'Usernames': [],
        'DisplayNames': [],
        'VerifiedStatus': []
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        
        await context.add_cookies([
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
        
        page = await context.new_page()
        
        # Block unnecessary resources
        await page.route("**/*", lambda route: (
            route.abort()
            if route.request.resource_type in ["image", "video", "font", "stylesheet"]
            else route.continue_()
        ))

        try:
            await page.goto(
                f"https://x.com/search?q={urllib.parse.quote(query)}&src=typed_query&f={mode}",
                wait_until="networkidle",
                timeout=30000
            )
        
            await page.wait_for_selector('article[role="article"]', timeout=60000)

            seen = set()
            await infinite_scroll_and_scrape(page, post_data, seen, max_scrolls)

            print(f"Total Scraped Posts: {len(post_data['Usernames'])}")

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            await context.close()
            await browser.close()

        return post_data


async def scrape_parallel(query, max_scrolls=10):
    """Scrape both live and top modes in parallel"""
    results_live, results_top = await asyncio.gather(
        main(query, max_scrolls, "live"),
        main(query, max_scrolls, "top")
    )

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


async def run_all_queries(queries, max_scrolls=10):
    """Run all queries concurrently"""
    tasks = [scrape_parallel(q, max_scrolls) for q in queries]
    results = await asyncio.gather(*tasks)
    return results


if __name__ == "__main__":
    queries = [
        "Physics and astronomy",
        "Astrophysics",
        "Quantum mechanics",
        "Cosmology"
    ]
    
    # Run all queries concurrently
    results = asyncio.run(run_all_queries(queries, max_scrolls=15))
    
    # Merge all results safely
    final_data = {
        'Usernames': [],
        'DisplayNames': [],
        'VerifiedStatus': []
    }
    seen = set()

    for data in results:
        for u, d, v in zip(data['Usernames'], data['DisplayNames'], data['VerifiedStatus']):
            if u not in seen:
                seen.add(u)
                final_data['Usernames'].append(u)
                final_data['DisplayNames'].append(d)
                final_data['VerifiedStatus'].append(v)

    print(f"\n\nTotal unique posts from all queries: {len(final_data['Usernames'])}")
