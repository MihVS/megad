BROADCAST_PORT = 52000
RECV_PORT = 42000
BROADCAST_STRING = b'\xAA\x00\x0C\xDA\xCA'
BROADCAST_START = b'\xAA\x00\x00'
BROADCAST_REBOOT = b'\xAA\x00\x03'
BROADCAST_CLEAR = b'\xAA\x00\x02'
BROADCAST_EEPROM = b'\xAA\x00\x09'
BROADCAST_EEPROM_CONFIRM = b'\xAA\x01\x09'
BROADCAST_CHANGE_IP = b'\xAA\x00\x04'
CHECK_DATA = b'\xDA\xCA'
DEFAULT_IP = '192.168.0.14'
BLOCK_SIZE = 256
SEARCH_TIMEOUT = 5
RECV_TIMEOUT = 0.3
DEFAULT_IP_LIST = ['null']
FW_PATH = 'custom_components/megad/fw_megad'

BROWSER_UA = [
    # --- Chrome (Windows / macOS / Linux)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",

    # --- Edge (Windows / macOS)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",

    # --- Firefox (Windows / macOS / Linux)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",

    # --- Safari (macOS / iOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",

    # --- Opera (Windows / macOS)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/108.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 OPR/108.0.0.0",

    # --- Android (Chrome / Samsung)
    "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SAMSUNG SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/26.0 Chrome/130.0.0.0 Mobile Safari/537.36",
]

