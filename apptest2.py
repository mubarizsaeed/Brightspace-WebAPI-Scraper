
from flask import Flask, render_template, jsonify, request
from playwright.async_api import async_playwright

duo_code = None
app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/run_script', methods=['POST'])
async def run_script():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    auth_method = data.get('authMethod')

    if auth_method == 'duoCodeMobile' or auth_method == 'duoPush':
        AllData = await run_playwright_script(username, password, auth_method)
    else:
        AllData = "Unsupported authentication method"

    return jsonify({'output': AllData})

@app.route('/send_duo_code', methods=['POST'])
def send_duo_code():
    data = request.get_json()
    global duo_code  # Use the global variable
    duo_code = data.get('duoCode')
    print('Received Duo code:', duo_code)
    return str(duo_code)

async def run_playwright_script(username, password, auth_method):
    link_text, auth = None, None

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

        if auth_method == 'duoCodeMobile':
            await page.locator("button:has-text('Send a passcode')").click()
            while duo_code is None:
                if duo_code is not None:
                    await page.get_by_label("Passcode").fill(duo_code)
                    await page.get_by_role("button", name="Verify").click()
                    await page.get_by_role("button", name="Yes").click()
    
        elif auth_method == 'duoPush':
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
    app.run(debug=True, port=8000)

