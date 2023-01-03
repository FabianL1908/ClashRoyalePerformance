import requests
import pandas as pd
import json
import os

clan_tag = "28L2UYYU"

headers = {
    'authority': 'royaleapi.com',
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'origin': 'https://royaleapi.com',
    'referer': 'https://royaleapi.com/player/20YL0G20V',
    'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'traceparent': '00-cc2ec1d73cd13a17c1f490fd800c44e0-bf3081fde16842b9-01',
    'tracestate': '2412609@nr=0-1-2412609-174388290-bf3081fde16842b9----1671480583081',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
}

def get_names_df():
    url = f"https://royaleapi.com/clan/{clan_tag}"
    html = requests.get(url, headers=headers).content
    df = pd.read_html(html, encoding='utf-8')[0]
    
    names = df["Name"].apply(lambda x: x.split("#")[0][:-1])
    player_ids = df["Name"].apply(lambda x: x.split("#")[1].split(" ")[0])
    df = pd.DataFrame({"Name": names, "Player_id": player_ids})
    return df

def add_tokens(df):
    tokens = []
    for index, row in df.iterrows():
        name, player_id = row
        url = f"https://royaleapi.com/player/{player_id}"
        html = requests.get(url, headers=headers).text
        token = html.split("token:")[1].split("\n")[0].split("'")[1]
        tokens.append(token)
        break
    df["Token"] = tokens[0]
    return df

def add_cw_history(df):
    maxs_5 = []
    maxs_20 = []
    mean_5 = []
    mean_20 = []
    
    for index, row in df.iterrows():
        name, player_id, token = row
        data = {"player_tag":f"{player_id}","player_name":f"{name}","token":f"{token}"}
        data = json.dumps(data)
        response = requests.post('https://royaleapi.com/data/player/cw2_history', headers=headers, data=data)
        my_dict = response.json()
        cw_df = pd.DataFrame(my_dict["rows"])
        cw_df = cw_df[["log_date", "clan_league", "contribution"]]
        maxs_5.append(cw_df["contribution"][:5].max())
        maxs_20.append(cw_df["contribution"][:20].max())
        mean_5.append(cw_df["contribution"][:5].mean())
        mean_20.append(cw_df["contribution"][:20].mean())

    df["max_5"] = maxs_5
    df["max_20"] = maxs_20
    df["mean_5"] = mean_5
    df["mean_20"] = mean_20

    return df

def create_df():
    df = get_names_df()
    df = add_tokens(df)
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
            df_new_players = add_tokens(df_new_players)
            df_new_players = add_cw_history(df_new_players)
             #### Send whatsapp message
            print(df_new_players)
            df_new = create_df()
            df_new.to_csv("stats.csv", index=False, encoding="utf-8")
