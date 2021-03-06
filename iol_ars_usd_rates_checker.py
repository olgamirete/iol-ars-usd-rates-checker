import trio
import httpx
import json
import getpass
# import pprint
import time

def authenticate_and_get_access_token():
    
    access_token = ''

    while True:
        access_token = get_new_access_token()
        if check_if_properly_authenticated(access_token) == False:
            flag_stop = input('Could not log in. Do you want to try again? (Y)es / (N)o: ')
            if flag_stop.lower() == 'y':
                pass
            elif flag_stop.lower() == 'n':
                exit()
            else:
                print('That is not a valid option.')
        else:
            break
    return access_token

def get_new_access_token():
    url = 'https://api.invertironline.com/token'
    user_access_data = {'grant_type': 'password'}
    user_access_data['username'] = input('Por favor ingrese su usuario: ')
    user_access_data['password'] = getpass.getpass('Por favor ingrese su contraseña: ')
    res = httpx.post(url, data=user_access_data)
    
    if res.status_code == 200:
        access_object = json.loads(res.text)
        access_token = access_object['access_token']
    else:
        access_token = ''

    return access_token

def check_if_properly_authenticated(access_token):
    
    client = httpx.Client()

    client.headers.update({
        'Authorization': 'bearer ' + access_token
    })
    res = client.get('https://api.invertironline.com/api/v2/estadocuenta')

    if res.status_code == 200:
        return True
    else:
        return False

def get_url_by_bono(mercado, bono):
    url = f'https://api.invertironline.com/api/v2/{mercado}/Titulos/{bono}/Cotizacion'
    return url

async def get_bono_dict(mercado, bono, client):
    res = await client.get(
        get_url_by_bono(mercado, bono)
    )
    return json.loads(res.text)

def get_max_precio_venta(bono_dict):
    max_precio_venta = 0
    puntas = bono_dict['puntas']
    for punta in puntas:
        max_precio_venta = max(max_precio_venta, punta['precioVenta'])
    return max_precio_venta

def get_min_precio_compra(bono_dict):
    min_precio_compra = get_max_precio_venta(bono_dict)
    puntas = bono_dict['puntas']
    for punta in puntas:
        min_precio_compra = min(min_precio_compra, punta['precioCompra'])
    return min_precio_compra

def get_precio_venta(bono_dict):
    try:
        return bono_dict['puntas'][0]['precioVenta']
    except IndexError:
        return 0

def get_precio_compra(bono_dict):
    try:
        return bono_dict['puntas'][0]['precioCompra']
    except IndexError:
        return 0

async def start_http_request(par_de_bonos_ARS_USD, currency, client):
    mercado = par_de_bonos_ARS_USD['mercado']
    par_de_bonos_ARS_USD['bono_dict_' + currency] = await get_bono_dict(
        mercado,
        par_de_bonos_ARS_USD[currency],
        client)
    return True

def round_rate_and_format_as_str(rate, decimals):
    try:
        rate = str(round(rate, decimals))
    except:
        rate = '-'
    return rate

def calculate_rates_and_store_in_dict(par_de_bonos_ARS_USD, flag_ignore_zeroes = True):

    precio_compra_bono_ARS = get_precio_compra(par_de_bonos_ARS_USD['bono_dict_ARS'])
    precio_venta_bono_ARS = get_precio_venta(par_de_bonos_ARS_USD['bono_dict_ARS'])
    precio_compra_bono_USD = get_precio_compra(par_de_bonos_ARS_USD['bono_dict_USD'])
    precio_venta_bono_USD = get_precio_venta(par_de_bonos_ARS_USD['bono_dict_USD'])

    # Rate ARS/USD when going from ARS to USD
    try:
        rate_when_ARS_to_USD = precio_venta_bono_ARS/precio_compra_bono_USD
        if flag_ignore_zeroes == True and rate_when_ARS_to_USD == 0:
            rate_when_ARS_to_USD = '-'
    except ZeroDivisionError:
        rate_when_ARS_to_USD = '-'
    
    # Rate ARS/USD when going from USD to ARS
    try:
        rate_when_USD_to_ARS = precio_compra_bono_ARS/precio_venta_bono_USD
        if flag_ignore_zeroes == True and rate_when_USD_to_ARS == 0:
            rate_when_USD_to_ARS = '-'
    except ZeroDivisionError:
        rate_when_USD_to_ARS = '-'
    
    par_de_bonos_ARS_USD['ARS/USD_when_ARS_to_USD'] = rate_when_ARS_to_USD
    par_de_bonos_ARS_USD['ARS/USD_when_USD_to_ARS'] = rate_when_USD_to_ARS
    
    return True

def get_clean_list_of_rates(ars2usd_or_usd2ars, pares_de_bonos_dict):
    
    dict_key = None

    if ars2usd_or_usd2ars == 'ars2usd':
        dict_key = 'ARS/USD_when_ARS_to_USD'
    elif ars2usd_or_usd2ars == 'usd2ars':
        dict_key = 'ARS/USD_when_USD_to_ARS'
    
    if dict_key is not None:
        rates_list = []
        for par_de_bonos in pares_de_bonos_dict:
            try:
                rates_list.append(float(par_de_bonos[dict_key]))
            except ValueError:
                pass # If the rate could not be calculated before and is thus
                    # showing a '-' character, we have to ignore it while
                    # checking for maximums and minimums.
        return rates_list
    else:
        raise RuntimeError('Wrong value for argument "ars2usd_or_usd2ars" ' \
                         + 'in function "get_clean_list_of_rates". Please ' \
                         + 'use only the values "ars2usd" or "usd2ars".')

def print_rates_for_par_de_bonos_ARS_USD(par_de_bonos_ARS_USD, decimals):

    label_1 = par_de_bonos_ARS_USD['ARS'] + ' -> ' + par_de_bonos_ARS_USD['USD']
    label_2 = par_de_bonos_ARS_USD['USD'] + ' -> ' + par_de_bonos_ARS_USD['ARS']
    
    rate_1 = round_rate_and_format_as_str(
        par_de_bonos_ARS_USD['ARS/USD_when_ARS_to_USD'],
        decimals)
    rate_2 = round_rate_and_format_as_str(
        par_de_bonos_ARS_USD['ARS/USD_when_USD_to_ARS'],
        decimals)
    
    text_to_print = f'{label_1}: {rate_1}\t/--/\t{label_2}: {rate_2}'
    
    print(text_to_print)
    
    return True

async def update_rates(access_token, pares_de_bonos_ARS_USD):
    async with httpx.AsyncClient() as client:
    # client = httpx.AsyncClient()

        client.headers.update({
            'Authorization': 'bearer ' + access_token
        })
        
        async with trio.open_nursery() as nursery:
            for par_ARS_USD in pares_de_bonos_ARS_USD:
                nursery.start_soon(start_http_request, par_ARS_USD, 'ARS', client)
                nursery.start_soon(start_http_request, par_ARS_USD, 'USD', client)

    # await client.aclose()

def main():
    
    access_token = ''
    pares_de_bonos_ARS_USD = json.load(open('files/bonos_ARS_USD.json'))

    while True:
        decision = input('(C)heck rates / (E)xit: ')
        
        if decision.lower() == 'c':
            try:
                # Check if already authenticated
                if check_if_properly_authenticated(access_token) == False:
                    access_token = authenticate_and_get_access_token()

                start_time = time.time()
                # Lo siguiente corre de modo asincrónico.
                trio.run(update_rates, access_token, pares_de_bonos_ARS_USD)
                # Lo siguiente corre de modo sincrónico, una vez que la parte
                # asincrónica haya terminado.
                for par_ARS_USD in pares_de_bonos_ARS_USD:
                    calculate_rates_and_store_in_dict(par_ARS_USD)
                    print_rates_for_par_de_bonos_ARS_USD(par_ARS_USD, 2)
                
                rate_when_ars2usd = min(get_clean_list_of_rates('ars2usd', pares_de_bonos_ARS_USD))
                rate_when_usd2ars = max(get_clean_list_of_rates('usd2ars', pares_de_bonos_ARS_USD))
                
                print(rate_when_ars2usd)
                print(rate_when_usd2ars)
                print(rate_when_usd2ars/rate_when_ars2usd-1)

                # pprint.pprint(pares_de_bonos_ARS_USD)
                # print(pares_de_bonos_ARS_USD)
                running_time = round(time.time()-start_time, 2)
                print('Consulta realizada en ' + str(running_time) + ' segundos.')
            except httpx.exceptions.ReadTimeout:
                print('La consulta no se pudo realizar en el tiempo esperado.')
                print('Por favor, inténtelo de nuevo.')

        elif decision.lower() == 'e':
            exit()
        else:
            print('That is not a valid option')

main()