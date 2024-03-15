import requests
import threading
import random
import logging
from dhooks import Webhook, Embed
import time

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(levelname)s: %(message)s')

class XboxGamertagBot:
    def __init__(self, config):
        self.proxies = self.load_data(config['proxies_file'])
        self.tokens = self.load_data(config['tokens_file'])
        self.gamertags = self.load_data(config['gamertags_file'])
        self.webhook_url = config['webhook_url']
        self.webhook = Webhook(self.webhook_url)
        self.session = requests.Session()

    def load_data(self, file_path):
        try:
            with open(file_path, 'r') as file:
                return [line.strip() for line in file.readlines() if line.strip()]
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
            return []

    def send_webhook_notification(self, message, gamertag, success=True):
        color = 0x00ff00 if success else 0xff0000
        embed = Embed(description=message, color=color)
        embed.add_field(name="Gamertag", value=gamertag, inline=False)
        self.webhook.send(embed=embed)

    def parse_proxy(self, proxy):
        if proxy:
            user_pass, host_port = proxy.split('@')
            return {
                'http': f'http://{user_pass}@{host_port}',
            }
        return None

    def handle_response_errors(self, response):
        if response.status_code == 429:
            logging.error("Rate limit exceeded. Please wait before making further requests.")
        elif response.status_code == 401:
            logging.error("Unauthorized. Check if the token is correct or has expired.")
        elif response.status_code == 403:
            logging.error("Forbidden. Access denied to the resource.")
        elif response.status_code == 404:
            logging.error("Not found. The requested resource could not be found.")
        else:
            logging.error(f"Error: {response.status_code}. {response.text}")
            
    def reserve_gamertag(self, gamertag, token, proxy):
        url = 'https://gamertag.xboxlive.com/gamertags/reserve'
        headers = {
        'Host': 'gamertag.xboxlive.com',
        'Content-Length': '78',
        'Sec-Ch-Ua': '"Chromium";v="121", "Not A(Brand";v="99"',
        'X-Xbl-Contract-Version': '1',
        'Sec-Ch-Ua-Mobile': '?0',
        'Authorization': f'XBL3.0 x={token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.85 Safari/537.36',
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*',
        'Ms-Cv': 'E/s/dzfDoeyIUGjv1jmCOM.0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Origin': 'https://social.xbox.com',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://social.xbox.com/',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'Priority': 'u=1, i',
        'Connection': 'close'
    }
        proxies = self.parse_proxy(proxy)
        payload = {
            'gamertag': gamertag,
            'reservationId': '0',
            'targetGamertagFields': 'gamertag'
        }

        try:
            response = self.session.post(url, headers=headers, json=payload, proxies=proxies)
            if response.status_code == 200 and response.json().get('gamertagSuffix') == '':
                logging.info(f"Reserved gamertag: {gamertag}")
                return True
            else:
                logging.error(f"Failed to reserve gamertag: {gamertag}, Status Code: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            logging.error(f"Error while reserving gamertag '{gamertag}': {e}")
            return False

    def claim_gamertag(self, gamertag, token, proxy):
        url = 'https://accounts.xboxlive.com/users/current/profile/gamertag'
        headers = {
        'Host': 'accounts.xboxlive.com',
        'Content-Length': '167',
        'Sec-Ch-Ua': '"Chromium";v="121", "Not A(Brand";v="99"',
        'X-Xbl-Contract-Version': '6',
        'Sec-Ch-Ua-Mobile': '?0',
        'Authorization': f'XBL3.0 x={token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.160 Safari/537.36',
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*',
        'Ms-Cv': 'epDWv0veXknVHWUqdcKrg9.0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Origin': 'https://social.xbox.com',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://social.xbox.com/',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'Priority': 'u=1, i'
    }
        proxies = self.parse_proxy(proxy)
        payload = {
        'reservationId': '0',
        'gamertag': {
            'gamertag': gamertag,
            'gamertagSuffix': '',
            'classicGamertag': gamertag
        },
        'preview': False,
        'useLegacyEntitlement': False
    }

        try:
            response = self.session.post(url, headers=headers, json=payload, proxies=proxies)
            if response.status_code == 200:
                logging.info(f"Claimed gamertag: {gamertag}")
                return True
            else:
                logging.error(f"Failed to claim gamertag: {gamertag}, Status Code: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            logging.error(f"Error while claiming gamertag '{gamertag}': {e}")
            return False
        
    def process_response(self, response, gamertag):
        if response.status_code == 200:
            data = response.json()
            if data.get('gamertagSuffix') == '':
                logging.info('Gamertag reservation successful!')
                logging.info(data)
                return True
            else:
                logging.info('Suffix is not blank. Retry needed.')
                logging.info(data)
                return False
        else:
            self.handle_response_errors(response)
            return False

    def process_gamertag(self, gamertag):
        max_attempts = 1000  # Set a maximum number of attempts to avoid infinite loops
        attempt = 0
        reserved = False

        while not reserved and attempt < max_attempts:
            token = random.choice(self.tokens)
            proxy = random.choice(self.proxies) if self.proxies else None
            reserved = self.reserve_gamertag(gamertag, token, proxy)
            
            if reserved:
                if self.claim_gamertag(gamertag, token, proxy):
                    self.send_webhook_notification(f"Successfully claimed gamertag: {gamertag}", gamertag, True)
                else:
                    self.send_webhook_notification(f"Failed to claim gamertag after reservation: {gamertag}", gamertag, False)
                break  # Exit the loop if reservation (and possibly claim) was successful
            else:
                logging.info(f"Attempt {attempt + 1} to reserve gamertag {gamertag} failed. Retrying...")
                attempt += 1

        if attempt == max_attempts:
            logging.error(f"Maximum attempts reached. Failed to reserve gamertag: {gamertag}")

    def run(self):
        threads = []
        for gamertag in self.gamertags:
            thread = threading.Thread(target=self.process_gamertag, args=(gamertag,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

if __name__ == "__main__":
    config = {
        'proxies_file': 'proxies.txt',
        'tokens_file': 'tokens.txt',
        'gamertags_file': 'gamertags.txt',
        'webhook_url': 'https://discord.com/api/webhooks/1207659272360693810/D57lOKtM9r9VLKHZQncrCGNcIVH-htAZ09q4by4tbGgkkr3Lw9kCrbVBV_8qt3ZUvYce'
    }

    bot = XboxGamertagBot(config)
    bot.run()
