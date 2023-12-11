from flask import Flask, render_template, jsonify, request
from playwright.async_api import async_playwright

app = Flask(__name__)

# Store the Duo code at the application level
duo_code = None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/run_script', methods=['POST'])
async def run_script():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    link_text = await run_playwright_script(username, password)
    return jsonify({'output': link_text})

@app.route('/send_duo_code', methods=['POST'])
def send_duo_code():
    data = request.get_json()
    global duo_code  # Use the global variable
    duo_code = data.get('duoCode')
    print('Received Duo code:', duo_code)
    return str(duo_code)

async def run_playwright_script(username, password):
    async with async_playwright() as play:
        browser = await play.chromium.launch(headless=True)
        context = await browser.new_context()
        
        page = await context.new_page()
        await page.goto('https://brightspace.uri.edu')

        # Automate login using the provided username and password
        await page.get_by_placeholder("someone@example.com").click()
        await page.get_by_placeholder("someone@example.com").fill(username)
        await page.get_by_role("button", name="Next").press("Enter")
        await page.locator("#i0118").fill(password)
        await page.get_by_role("button", name="Sign in").press("Enter")

        # Duo Code Mobile

        try:
            send_mobile_passcode_button = page.locator("button:has-text('Send a passcode')")
            if not send_mobile_passcode_button.is_editable():
                raise Exception("TimeoutError")
            else:
                await send_mobile_passcode_button.click()
                while duo_code is None:
                    if duo_code:
                        await page.get_by_label("Passcode").fill(duo_code)
                        await page.get_by_role("button", name="Verify").click()
                        await page.get_by_role("button", name="Yes").click()
                        target_url = 'https://brightspace.uri.edu/d2l/home'
                        while page.url != target_url:
                            await page.wait_for_url(target_url, timeout=0)
                        auth = await context.storage_state()
                        await page.get_by_role("navigation").get_by_role("link", name="Calendar").click()
                        await page.get_by_role("button", name="Subscribe").click()
                        iframe_locator = await page.wait_for_selector('iframe[name^="d2l_c_"]', timeout=20000)
                        iframe = await iframe_locator.content_frame()
                        dynamic_selector = '[class^="d2l_1_7_"]'  # Replace with the common part of the dynamic class
                        element_selector = await iframe.wait_for_selector(dynamic_selector, timeout=20000)
                        link_element = await element_selector.query_selector('.d2l-textblock')
                        link_text = await link_element.inner_text()

        # Duo Push Flow Code Alternative
        except Exception as e:
            print(e)
            await page.get_by_role("button", name="Yes").click()
            target_url = 'https://brightspace.uri.edu/d2l/home'
            while page.url != target_url:
                await page.wait_for_url(target_url, timeout=0)
            auth = await context.storage_state()
            await page.get_by_role("navigation").get_by_role("link", name="Calendar").click()
            await page.get_by_role("button", name="Subscribe").click()
            iframe_locator = await page.wait_for_selector('iframe[name^="d2l_c_"]', timeout=20000)
            iframe = await iframe_locator.content_frame()
            dynamic_selector = '[class^="d2l_1_7_"]'  # Replace with the common part of the dynamic class
            element_selector = await iframe.wait_for_selector(dynamic_selector, timeout=20000)
            link_element = await element_selector.query_selector('.d2l-textblock')
            link_text = await link_element.inner_text()

    return link_text, username, password, auth

if __name__ == '__main__':
    app.run(port=8000)
