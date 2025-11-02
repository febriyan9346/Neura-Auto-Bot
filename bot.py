import os
import asyncio
import httpx
import time
import pytz
from datetime import datetime
from decimal import Decimal
from web3 import AsyncWeb3, Web3
from eth_abi.abi import encode as abi_encode
from dotenv import load_dotenv
from colorama import init, Fore, Style

init(autoreset=True)
load_dotenv()
WIB = pytz.timezone('Asia/Jakarta')

NEURA_RPC = 'https://testnet.rpc.neuraprotocol.io/'
CONTRACTS = {
    'SWAP_ROUTER': Web3.to_checksum_address('0x5AeFBA317BAba46EAF98Fd6f381d07673bcA6467'),
    'WANKR': Web3.to_checksum_address('0xbd833b6ecc30caeabf81db18bb0f1e00c6997e7a'),
}

ABIS = {
    'SWAP_ROUTER': '[{"inputs":[{"internalType":"bytes[]","name":"data","type":"bytes[]"}],"name":"multicall","outputs":[{"internalType":"bytes[]","name":"results","type":"bytes[]"}],"stateMutability":"payable","type":"function"}]',
    'ERC20': '''
    [
        {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"}
    ]
    ''',
}
MAX_UINT256 = 2**256 - 1

def get_wib_time():
    """Mendapatkan string waktu WIB saat ini."""
    return datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S WIB')

def logger(level, msg):
    """Fungsi logging kustom dengan warna dan timestamp."""
    now = get_wib_time()
    if level == 'info':
        print(f"{Fore.WHITE}[{now}][➤] {msg}{Style.RESET_ALL}")
    elif level == 'warn':
        print(f"{Fore.YELLOW}[{now}][⚠] {msg}{Style.RESET_ALL}")
    elif level == 'error':
        print(f"{Fore.RED}[{now}][✗] {msg}{Style.RESET_ALL}")
    elif level == 'success':
        print(f"{Fore.GREEN}[{now}][✅] {msg}{Style.RESET_ALL}")
    elif level == 'loading':
        print(f"{Fore.CYAN}[{now}][⟳] {msg}{Style.RESET_ALL}")
    elif level == 'step':
        print(f"\n{Fore.CYAN}{Style.BRIGHT}[{now}][➤] {msg}{Style.RESET_ALL}")

def banner():
    """Menampilkan banner script."""
    print(f"{Fore.CYAN}{Style.BRIGHT}")
    print("---------------------------------------------")
    print("                Neura Bot                ")
    print("---------------------------------------------")
    print(Style.RESET_ALL)

async def fetch_available_tokens():
    """Mengambil token yang tersedia dari subgraph (versi async)."""
    logger('info', 'Mengambil token swap yang tersedia...')
    try:
        endpoint = "https://api.goldsky.com/api/public/project_cmc8t6vh6mqlg01w19r2g15a7/subgraphs/analytics/1.0.1/gn"
        query = "query AllTokens { tokens { id symbol name decimals } }"
        body = {"operationName": "AllTokens", "variables": {}, "query": query}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, json=body, timeout=30.0)
            response.raise_for_status()
        
        tokens = response.json()['data']['tokens']
        
        unique_tokens = {}
        for token in tokens:
            if not token.get('symbol') or ' ' in token['symbol']:
                continue
            symbol = token['symbol'].upper()
            if symbol not in unique_tokens:
                unique_tokens[symbol] = {
                    'address': Web3.to_checksum_address(token['id']),
                    'symbol': symbol,
                    'decimals': int(token['decimals'])
                }
        
        if 'WANKR' in unique_tokens:
            unique_tokens['ANKR'] = {**unique_tokens['WANKR'], 'symbol': 'ANKR'}
        
        sorted_tokens = sorted(unique_tokens.values(), key=lambda t: t['symbol'])
        logger('success', f'Ditemukan {len(sorted_tokens)} token unik yang dapat di-swap.')
        return sorted_tokens
    except Exception as e:
        logger('error', f'Gagal mengambil token: {e}')
        return []

class SwapBot:
    def __init__(self, private_key):
        # Instance Async untuk mengirim transaksi
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(NEURA_RPC))
        self.account = self.w3.eth.account.from_key(private_key)
        self.address = self.account.address

    def _encode_inner_swap(self, token_in, token_out, deadline_ms, amount_in_wei):
        """Helper untuk encode data swap internal (porting dari JS)."""
        types = ['address', 'address', 'uint256', 'address', 'uint256', 'uint256', 'uint256', 'uint256']
        values = [
            Web3.to_checksum_address(token_in),
            Web3.to_checksum_address(token_out),
            0,
            self.address,
            deadline_ms,
            amount_in_wei,
            27,
            0
        ]
        encoded_params = abi_encode(types, values)
        return '0x1679c792' + encoded_params.hex()

    def _encode_router_multicall(self, calls):
        """Helper untuk encode data multicall router - FIXED VERSION."""
        # Function selector untuk multicall(bytes[])
        function_selector = '0xac9650d8'
        
        # Encode parameter menggunakan abi_encode
        encoded_params = abi_encode(['bytes[]'], [calls])
        
        return function_selector + encoded_params.hex()
    
    async def get_swap_back_amount(self, token_b):
        """Mendapatkan jumlah tokenB untuk di-swap kembali (seluruh balance)."""
        if token_b['symbol'] == 'ANKR':
            balance_wei = await self.w3.eth.get_balance(self.address)
            gas_reserve = Web3.to_wei('0.005', 'ether')
            if balance_wei > gas_reserve:
                return str(Web3.from_wei(balance_wei - gas_reserve, 'ether'))
        else:
            token_b_contract = self.w3.eth.contract(address=token_b['address'], abi=ABIS['ERC20'])
            token_b_balance = await token_b_contract.functions.balanceOf(self.address).call()
            if token_b_balance > 0:
                amount_decimal = Decimal(token_b_balance) / (10**token_b['decimals'])
                return str(amount_decimal)
        return None

    async def perform_swap(self, token_in, token_out, amount_in_str):
        """Melakukan satu operasi swap."""
        try:
            amount_in_decimal = Decimal(amount_in_str)
            if amount_in_decimal <= 0:
                raise ValueError("Jumlah harus positif")
        except Exception:
            raise ValueError(f'Jumlah tidak valid atau nol: "{amount_in_str}"')
        
        logger('step', f"Menukar {amount_in_str} {token_in['symbol']} → {token_out['symbol']}...")
        
        try:
            amount_in_wei = int(amount_in_decimal * (10**token_in['decimals']))
            is_native_swap_in = token_in['symbol'] == 'ANKR'
            
            current_nonce = await self.w3.eth.get_transaction_count(self.address)
            current_gas_price = await self.w3.eth.gas_price

            if not is_native_swap_in:
                token_contract = self.w3.eth.contract(address=token_in['address'], abi=ABIS['ERC20'])
                allowance = await token_contract.functions.allowance(self.address, CONTRACTS['SWAP_ROUTER']).call()

                if allowance < amount_in_wei:
                    logger('loading', f"Menyetujui {token_in['symbol']} untuk router...")
                    approve_tx_data = token_contract.functions.approve(
                        CONTRACTS['SWAP_ROUTER'],
                        MAX_UINT256
                    ).build_transaction({
                        'from': self.address,
                        'nonce': current_nonce,
                        'gasPrice': current_gas_price
                    })
                    
                    approve_tx_data['gas'] = await self.w3.eth.estimate_gas(approve_tx_data)
                    
                    signed_tx = self.w3.eth.account.sign_transaction(approve_tx_data, self.account.key)
                    tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                    receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash)
                    
                    if receipt['status'] != 1:
                        raise Exception('Transaksi approve gagal')
                    logger('success', f'Approval berhasil. (Tx: {tx_hash.hex()})')
                    current_nonce += 1
                else:
                    logger('info', 'Allowance sudah mencukupi.')
            
            deadline_ms = (int(time.time() * 1000)) + (20 * 60 * 1000)
            token_in_address_for_router = CONTRACTS['WANKR'] if is_native_swap_in else token_in['address']

            inner = self._encode_inner_swap(
                token_in=token_in_address_for_router,
                token_out=token_out['address'],
                deadline_ms=deadline_ms,
                amount_in_wei=amount_in_wei
            )
            
            inner_bytes = Web3.to_bytes(hexstr=inner)
            
            data = self._encode_router_multicall([inner_bytes])
            tx_value = amount_in_wei if is_native_swap_in else 0

            logger('info', 'Mengirim transaksi swap...')
            
            swap_tx = {
                'to': CONTRACTS['SWAP_ROUTER'],
                'data': data,
                'value': tx_value,
                'from': self.address,
                'nonce': current_nonce,
                'gas': 600_000,
                'gasPrice': current_gas_price
            }

            signed_swap_tx = self.w3.eth.account.sign_transaction(swap_tx, self.account.key)
            swap_tx_hash = await self.w3.eth.send_raw_transaction(signed_swap_tx.rawTransaction)
            
            logger('loading', f'Tx swap terkirim. Hash: {swap_tx_hash.hex()}')
            
            receipt = await self.w3.eth.wait_for_transaction_receipt(swap_tx_hash)
            
            if receipt['status'] != 1:
                raise Exception('Tx swap gagal di on-chain.')
            
            logger('success', f'Swap berhasil: https://testnet.neuraprotocol.io/tx/{receipt.transactionHash.hex()}')

        except Exception as e:
            msg = str(e)
            logger('error', f'Swap gagal: {msg}')
            raise e

    async def perform_swap_with_retries(self, token_in, token_out, amount_in_str, max_retries=3):
        """Mencoba swap dengan logika retry."""
        for i in range(max_retries):
            try:
                await self.perform_swap(token_in, token_out, amount_in_str)
                return True
            except Exception as e:
                message = str(e)
                if 'Jumlah tidak valid atau nol' in message:
                    logger('error', f'Swap dibatalkan: {message}')
                    return False
                
                logger('warn', f"Percobaan {i + 1}/{max_retries} gagal: {message}. Mencoba lagi dalam 10 detik...")
                
                if i == max_retries - 1:
                    logger('error', f'Swap gagal setelah {max_retries} percobaan.')
                    return False
                await asyncio.sleep(10)
        return False

async def main_task():
    """Fungsi yang berisi logika utama script (untuk dijalankan dalam loop)."""
    banner()

    pks = [v for k, v in os.environ.items() if k.startswith('PRIVATE_KEY_') and v]

    if not pks:
        logger('error', 'Tidak ada PRIVATE_KEY ditemukan di file .env. Mohon tambahkan PRIVATE_KEY_1, dll.')
        return

    logger('info', f'Ditemukan {len(pks)} wallet di file .env.')

    tokens = await fetch_available_tokens()
    if not tokens:
        return

    print('\nToken yang tersedia:')
    for i, t in enumerate(tokens):
        print(f"{i + 1}. {t['symbol']}")

    try:
        from_index_str = input(f'\n{Fore.YELLOW}Masukkan nomor token untuk di-swap DARI: {Style.RESET_ALL}')
        to_index_str = input(f'{Fore.YELLOW}Masukkan nomor token untuk di-swap KE: {Style.RESET_ALL}')
        from_index = int(from_index_str) - 1
        to_index = int(to_index_str) - 1

        if not (0 <= from_index < len(tokens) and 0 <= to_index < len(tokens) and from_index != to_index):
            logger('error', 'Pilihan token tidak valid.')
            return

        token_a = tokens[from_index]
        token_b = tokens[to_index]

        amount_a_str = input(f'{Fore.YELLOW}Masukkan jumlah {token_a["symbol"]} untuk di-swap: {Style.RESET_ALL}')
        repeat_str = input(f'{Fore.YELLOW}Berapa kali swap per wallet? (default: 1): {Style.RESET_ALL}')
        repeats = int(repeat_str) if repeat_str.isdigit() and int(repeat_str) > 0 else 1
    
    except (ValueError, EOFError):
        logger('error', 'Input tidak valid.')
        return
    except KeyboardInterrupt:
        logger('warn', 'Input dibatalkan oleh pengguna.')
        return

    for pk in pks:
        bot = SwapBot(pk)
        logger('step', f"--- Memproses Wallet {bot.address[:10]}... ---")
        try:
            for j in range(repeats):
                logger('step', f"--- Siklus Swap {j + 1}/{repeats} ---")
                
                swap_success = await bot.perform_swap_with_retries(token_a, token_b, amount_a_str)

                if swap_success:
                    logger('loading', 'Menunggu 10 detik sebelum swap kembali...')
                    await asyncio.sleep(10)
                    
                    amount_b_to_swap_str = await bot.get_swap_back_amount(token_b)

                    if amount_b_to_swap_str:
                        await bot.perform_swap_with_retries(token_b, token_a, amount_b_to_swap_str)
                    else:
                        logger('warn', f"Tidak ada balance {token_b['symbol']} ditemukan. Melewati swap kembali.")
                else:
                    logger('warn', f"Melewati swap kembali karena swap awal dari {token_a['symbol']} gagal.")

                if j < repeats - 1:
                     logger('loading', 'Menunggu 10 detik sebelum siklus berikutnya...')
                     await asyncio.sleep(10)
            
            logger('success', f"Semua siklus untuk wallet {bot.address[:10]}... selesai.")

        except Exception as e:
            logger('error', f"Alur swap gagal untuk wallet {bot.address}: {e}")
        
        logger('loading', 'Menunggu 10 detik sebelum wallet berikutnya...')
        await asyncio.sleep(10)

    logger('success', 'Semua tugas swap untuk putaran ini selesai.')

async def run_loop_24h():
    """Menjalankan main_task dalam loop 24 jam."""
    while True:
        try:
            logger('info', 'Memulai putaran siklus baru...')
            await main_task()
            logger('info', 'Putaran siklus selesai. Menunggu 24 jam untuk putaran berikutnya...')
            await asyncio.sleep(24 * 60 * 60)
        except (KeyboardInterrupt):
            logger('warn', 'Loop dihentikan oleh pengguna. Keluar.')
            break
        except Exception as e:
            logger('error', f'Terjadi error kritis di loop utama: {e}. Mencoba lagi dalam 1 jam.')
            await asyncio.sleep(60 * 60)

if __name__ == "__main__":
    try:
        asyncio.run(run_loop_24h())
    except KeyboardInterrupt:
        logger('info', 'Skrip dihentikan oleh pengguna.')
