import requests
import pandas as pd
import json
import os
from heyoo import WhatsApp
import urllib
import sys

clan_tag = "28L2UYYU"

headers = {
    'authority': 'royaleapi.com',
    'accept': '*/*',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'referer': 'https://royaleapi.com/player/CVC0JVR0P',
    'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
}

def get_bearer_token():
    url = f"https://royaleapi.com/player/CVC0JVR0P"
    html = requests.get(url, headers=headers).text
    try:
        token = html.split("token:")[1].split("\n")[0].split("'")[1]
    except IndexError:
        sys.exit(0)
    return token

bearer_token = get_bearer_token()
headers["authorization"] = f'Bearer {bearer_token}'

def get_names_df():
    url = f"https://royaleapi.com/clan/{clan_tag}"
    html = requests.get(url, headers=headers).content
    df = pd.read_html(html, encoding='utf-8')[0]

    names = df["Name"].apply(lambda x: x.split("#")[0].rstrip())
    player_ids = df["Name"].apply(lambda x: x.split("#")[1].split(" ")[0])
    df = pd.DataFrame({"Name": names, "Player_id": player_ids})
    return df


def add_cw_history(df):
    maxs_5 = []
    maxs_20 = []
    mean_5 = []
    mean_20 = []
    
    for index, row in df.iterrows():
        name, player_id = row
        # we have to double encode the player_name
        encoded_name = urllib.parse.quote(name)
        double_encoded_name = urllib.parse.quote(encoded_name)
        get_url = f"https://royaleapi.com/player/cw2_history/{player_id}?player_name={double_encoded_name}&clan_tag={clan_tag}"
        #print(get_url)
        response = requests.get(get_url, headers=headers)
        my_dict = response.json()
        cw_df = pd.DataFrame(my_dict["rows"])
        try:
            cw_df = cw_df[["log_date", "clan_league", "contribution"]]
            maxs_5.append(cw_df["contribution"][:5].max())
            maxs_20.append(cw_df["contribution"][:20].max())
            mean_5.append(cw_df["contribution"][:5].mean())
            mean_20.append(cw_df["contribution"][:20].mean())
        except:
            maxs_5.append(0)
            maxs_20.append(0)
            mean_5.append(0)
            mean_20.append(0)
        
    df["max_5"] = maxs_5
    df["max_20"] = maxs_20
    df["mean_5"] = mean_5
    df["mean_20"] = mean_20

    return df

def send_whatsapp_message(message):
    phone_number = os.environ["PHONE_NUMBER"]
    phone_number_id = os.environ["PHONE_NUMBER_ID"]
    access_token = os.environ["WHATSAPP_ACCESS_TOKEN"]
    messenger = WhatsApp(access_token,phone_number_id=phone_number_id)
    messenger.send_message(message, phone_number)    

def create_df():
    df = get_names_df()
    df = add_cw_history(df)
    return df
    
if __name__ == "__main__":
    if not os.path.exists("stats.csv"):
        df = create_df()
        df.to_csv("stats.csv", index=False, encoding="utf-8")
    else:
        df_old = pd.read_csv("stats.csv")
        df_names = get_names_df()
        # get new players
        df_new_players = df_old.merge(df_names, how="right", indicator=True)
        df_new_players = df_new_players.query("_merge == 'right_only'")[["Name","Player_id"]]
        if len(df_new_players) > 0:
            df_new_players = add_cw_history(df_new_players)
            df_new_players = df_new_players.round({"max_5": 1, "max_20": 1, "mean_5": 1, "mean_20": 1})
             #### Send whatsapp message
            df_print = df_new_players[["Name", "max_5", "max_20", "mean_5", "mean_20"]].to_string(index=False, header=False)
            print(df_print)
            
            send_whatsapp_message(str(df_print))
            df_new = create_df()
            df_new.to_csv("stats.csv", index=False, encoding="utf-8")
