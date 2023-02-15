from logging import exception
from web3 import Web3
import pandas as pd
import numpy as np
import requests, json
import schedule
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import web3

w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/*******'))
api_key = "*******" ## api key for etherscan apis
telegram_chatID = "*********"
telegram_api = "https://api.telegram.org/bot**********/sendMessage?" ## followed by chat_id = *** (sendMessage, getUpdates)&text="" 
blocknative_api = "https://api.blocknative.com/gasprices/blockprices"

## load the address from excel file into a dataframe
whales_excel = pd.read_excel('whales.xlsx', sheet_name='Possible_Insiders')
## convert the dataframe into a dictionary for easy reference
address_dict = dict(zip(whales_excel['Name'], whales_excel.Address))

def get_gas_price():
    header = {"Authorization": "aa78f5b1-53cd-46ab-a48d-4e9627686e69"}
    gas_price = requests.get(url=blocknative_api, headers=header).json()
    gas_price_gwei = (gas_price['blockPrices'][0])['baseFeePerGas']
    return gas_price_gwei

def get_opensea_details(assetContract):
    opensea_api = "https://api.opensea.io/api/v1/asset_contract/"+ assetContract +"?format=json"
    requests.get(opensea_api).json()

def send_tele_msg(msg): ## this function sends telegram message
    base_url = telegram_api + "chat_id=" + telegram_chatID +'&text=' +msg +"&parse_mode=Markdown"
    requests.get(base_url)


def whale_stalker(dict):
        for whale, addr in dict.items():
            try: 
                ## load database
                database = pd.read_csv('whale_stalking_database.csv')
                etherscan_api = "https://api.etherscan.io/api?module=account&action=tokennfttx&address=" + addr +"&page=1&offset=100&sort=desc&apikey=" + api_key
                latest_txns = requests.get(etherscan_api).json()['result']  # this is to get the latest 100 transactions from the etherscan api...

                txn_list = []
                for txn in latest_txns:
                    if txn["from"] == "0x0000000000000000000000000000000000000000":   # filter for minted transactions
                        txn_list.append(txn)
                mint_txn = pd.DataFrame(txn_list)    # convert the  mint transactions into a dataframe
                mint_txn = mint_txn.drop_duplicates(subset='contractAddress', keep="first")    # remove duplicate NFTs
                mint_txn['lameArtist'] = mint_txn.apply(lambda x: w3.eth.getTransaction(x['hash'])['from'].lower() != x['to'] , 1) ## make sure that contract caller is actually the whale and not someone else doing for marketing
                mint_txn = mint_txn[mint_txn['lameArtist'] == False] ## filter for non lame artists
                mint_txn['Whale'] = whale
                mint_txn['contractAddress_Whale'] = mint_txn['contractAddress'] + mint_txn['Whale']
                mint_txn = mint_txn[['tokenName', 'contractAddress', 'hash','lameArtist','to','Whale','contractAddress_Whale']]


                new_mints = mint_txn[~mint_txn['contractAddress_Whale'].isin(database['contractAddress_Whale'])] ### check minted transactions against database to find new mints (rows) that are not the same token-whale combi, aka new rows

                # send tele messages to broadcast these new mints

                if not new_mints.empty:

                    for index, row in new_mints.iterrows():
                        whale_name = row['Whale']
                        nft_name = row['tokenName']
                        contract_address = row['contractAddress']
                        whale_address = row['to']
                        print(whale+" has minted "+nft_name)
                        #print(f"{whale_name} #{whale_address} has just minted {nft_name}")
                        send_tele_msg(f"[{whale_name}](https://etherscan.io/address/{whale_address})\n%23{whale_address} has just minted [{nft_name}](https://etherscan.io/address/{contract_address})\n%23{contract_address}")
                        ## time to check if contractAddress has appeared before, if it has appeared before, it means that this new row is a new whale that minted the same project, time to find out how many whales has minted this proj
                        involved_whale_count = (database['contractAddress'].tolist()).count(contract_address) + 1
                        try:
                            if involved_whale_count > 1:
                                opensea_api = "https://api.opensea.io/api/v1/asset_contract/"+ contract_address +"?format=json"
                                url = requests.get(opensea_api).json()
                                discord_url = url['collection']['discord_url']
                                discord_url = str(discord_url) if discord_url != None else 'nothing.com' 
                                twitter_url = "www.twitter.com/" + str(url['collection']['twitter_username'])
                                twitter_url = str(twitter_url) if twitter_url != None else 'nothing.com'
                                website_url = url['external_link']
                                website_url = str(website_url) if website_url != None else 'nothing.com'
                                description = url['description']
                                slug = url['collection']['slug']
                                opensea_url = "https://opensea.io/collection/"+slug+"?collectionSlug="+slug+"&search[sortAscending]=true&search[sortBy]=PRICE&search[toggles][0]=BUY_NOW"

                                keyboard = [[InlineKeyboardButton("OpenSea", url=opensea_url)],
                                            [InlineKeyboardButton("Website", url=website_url),
                                            InlineKeyboardButton("Twitter", url=twitter_url),
                                            InlineKeyboardButton("Discord", url=discord_url)]]
                                reply_markup = InlineKeyboardMarkup(keyboard)
                                data = {"chat_id": "-593049303",
                                        "text": f"{str(involved_whale_count)} whales have minted [{nft_name}](https://etherscan.io/address/{contract_address})\n#{contract_address}\nDescription: _{description}_\nGas Prices Now: {get_gas_price()}",
                                        "parse_mode": "Markdown", 
                                        "reply_markup": json.dumps(reply_markup.to_dict())}
                            
                                requests.get(url='https://api.telegram.org/bot1965746307:AAFMt18_qK70cXZpv6DQKA_mLyd7ZKbGjBc/sendMessage', data=data)
                        except Exception as e:
                            print(e)



                    updated_database = database.append([new_mints])
                    updated_database.to_csv('whale_stalking_database.csv', index=False)


                else:
                    print("No new updates from " + whale)


            except Exception as e:
                print(e)



schedule.every(1).minutes.do(whale_stalker, address_dict)

while True:
     schedule.run_pending()
     time.sleep(1)
