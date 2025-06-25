import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from os import environ, makedirs
import os
import shutil
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers import combining, cron
from modules.calc import get_options_data
from modules.ticker_dwn import dwn_data
from cachetools import TTLCache, cached
import orjson
import discord
import aiofiles
import asyncio

# Load environment variables
load_dotenv()

# Configuration
TICKERS = ["^SPX", "^NDX"]  # Yahoo Finance format
EXPIRATIONS = ["0dte", "1dte", "opex", "monthly", "all"]
GREEKS = ["delta", "gamma", "vanna", "charm"]
VISUALIZATIONS = {
    "delta": ["Absolute Delta Exposure", "Delta Exposure By Calls/Puts", "Delta Exposure Profile"],
    "gamma": ["Absolute Gamma Exposure", "Gamma Exposure By Calls/Puts", "Gamma Exposure Profile"],
    "vanna": ["Absolute Vanna Exposure", "Implied Volatility Average", "Vanna Exposure Profile"],
    "charm": ["Absolute Charm Exposure", "Charm Exposure Profile"],
}
PLOT_DIR = "plots"
TZ = "Europe/Madrid"  # CEST timezone
DISCORD_CHANNEL_IDS = {
    "^SPX/0dte/delta": 1387377585427841094,  # Replace with actual channel IDs
    "^SPX/0dte/gamma": 1387376148950028288,
    "^SPX/0dte/vanna": 1387376757413515344,
    "^SPX/0dte/charm": 1387377438589194270,
    "^SPX/1dte/delta": 1387377603031207976,
    "^SPX/1dte/gamma": 1387376325399941231,
    "^SPX/1dte/vanna": 1387376810559275158,
    "^SPX/1dte/charm": 1387377460810744019,
    "^SPX/opex/delta": 1387377627505102909,
    "^SPX/opex/gamma": 1387376441389486131,
    "^SPX/opex/vanna": 1387376838757711913,
    "^SPX/opex/charm": 1387377489562828952,
    "^SPX/monthly/delta": 1387377650565382234,
    "^SPX/monthly/gamma": 1387376549967167569,
    "^SPX/monthly/vanna": 1387376930101395528,
    "^SPX/monthly/charm": 1387377520105619627,
    "^SPX/all/delta": 1387377665589116938,
    "^SPX/all/gamma": 1387376590912229396,
    "^SPX/all/vanna": 1387376953237180537,
    "^SPX/all/charm": 1387377535570018404,
    "^NDX/0dte/delta": 1387378772805947492,
    "^NDX/0dte/gamma": 1387377700465016862,
    "^NDX/0dte/vanna": 1387378541284425828,
    "^NDX/0dte/charm": 1387378654039904417,
    "^NDX/1dte/delta": 1387378789184442378,
    "^NDX/1dte/gamma": 1387378422325448795,
    "^NDX/1dte/vanna": 1387378559214948393,
    "^NDX/1dte/charm": 1387378677075021856,
    "^NDX/opex/delta": 1387378811393282208,
    "^NDX/opex/gamma": 1387378439182352476,
    "^NDX/opex/vanna": 1387378578173198366,
    "^NDX/opex/charm": 1387378698826682409,
    "^NDX/monthly/delta": 1387378837318275132,
    "^NDX/monthly/gamma": 1387378471835144292,
    "^NDX/monthly/vanna": 1387378607344848977,
    "^NDX/monthly/charm": 1387378733371097128,
    "^NDX/all/delta": 1387378868247203901,
    "^NDX/all/gamma": 1387378499417014392,
    "^NDX/all/vanna": 1387378622293344356,
    "^NDX/all/charm": 1387378750827794644,
}

# Initialize cache
cache = TTLCache(maxsize=150, ttl=60 * 15)  # 15-minute cache

# Check and clean plot directory on first run
try:
    shutil.rmtree(PLOT_DIR)
except:
    pass

makedirs(PLOT_DIR, exist_ok=True)

# Discord client (passed from bot.py)
discord_client = None

def set_discord_client(client):
    global discord_client
    discord_client = client
    print(f"Discord client set: {client}")

async def send_plot_to_discord(filename, ticker, exp, greek):
    if discord_client is None:
        print("Discord client not initialized")
        return
    channel_key = f"{ticker}/{exp}/{greek}"
    channel_id = DISCORD_CHANNEL_IDS.get(channel_key)
    if not channel_id:
        print(f"No Discord channel found for {channel_key}")
        return
    channel = discord_client.get_channel(channel_id)
    if not channel:
        print(f"Channel ID {channel_id} not found")
        return
    
    # Check if the file exists before attempting to send
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return
    
    try:
        message = f"{ticker}/{exp}/{greek} at {datetime.now(ZoneInfo("America/New_York")).ctime()} EST"
        await channel.send(message)
        print(f"Sent message: {message} to Discord channel {channel_key}")
        # Let discord.File handle the file opening
        file = discord.File(filename)
        await channel.send(file=file)
        print(f"Sent {filename} to Discord channel {channel_key}")
    except Exception as e:
        print(f"Failed to send {filename} to {channel_key}: {type(e).__name__} - {e}")

def cleanup_timestamp_directory(timestamp):
    for ticker in TICKERS:
        for exp in EXPIRATIONS:
            for greek in GREEKS:
                timestamp_dir = os.path.join(PLOT_DIR, ticker, exp, greek, timestamp)
                try:
                    if os.path.exists(timestamp_dir):
                        shutil.rmtree(timestamp_dir)
                        print(f"Deleted timestamp directory {timestamp_dir}")
                except Exception as e:
                    print(f"Error deleting timestamp directory {timestamp_dir}: {e}")

@cached(cache)
def analyze_data(ticker, expir):
    #print(f"Fetching data for {ticker}/{expir}")
    result = get_options_data(
        ticker,
        expir,
        is_json=True,
        tz="Europe/Madrid",
    )
    return result if result else (None,) * 16

def sensor(select=None):
    #print(f"Executing sensor() at {datetime.now(ZoneInfo(TZ)).strftime('%Y-%m-%d %H:%M:%S')}")
    dwn_data(select, is_json=True)
    cache.clear()
    #print("sensor() completed")

async def generate_plots(specific_ticker=None, specific_exp=None, specific_greek=None):
    timestamp = datetime.now(ZoneInfo(TZ)).strftime("%Y%m%d_%H%M%S")
    #print(f"Generating plots at {timestamp}")
    sensor()

    tickers = [specific_ticker] if specific_ticker else TICKERS
    expirations = [specific_exp] if specific_exp else EXPIRATIONS
    greeks = [specific_greek] if specific_greek else GREEKS

    for ticker in tickers:
        for exp in expirations:
            if exp == "1dte":
                today = datetime.now(ZoneInfo(TZ)).date()
                tomorrow = today + timedelta(days=1)
                expir_param = tomorrow.strftime("%Y-%m-%d")
            else:
                expir_param = exp

            data = analyze_data(ticker.lower(), expir_param)
            if data[0] is None:
                #print(f"No data available for {ticker}/{exp}, skipping")
                #print(f"get_options_data output: {data}")
                continue
            (
                df,
                today_ddt,
                today_ddt_string,
                monthly_options_dates,
                spot_price,
                from_strike,
                to_strike,
                levels,
                totaldelta,
                totalgamma,
                totalvanna,
                totalcharm,
                zerodelta,
                zerogamma,
                call_ivs,
                put_ivs,
            ) = data

            if not isinstance(df, pd.DataFrame) or df.empty:
                #print(f"Invalid or empty DataFrame for {ticker}/{exp}, skipping")
                #print(f"get_options_data output: {data[0:7]}")
                #print(f"monthly_options_dates: {data[3]}")
                continue
            #print(f"df columns: {df.columns}, index type: {type(df.index)}")
            #print(f"from_strike: {from_strike}, to_strike: {to_strike}")
            #print(f"call_ivs: {call_ivs}, put_ivs: {put_ivs}")
            #print(f"totaldelta: {totaldelta}, totalgamma: {totalgamma}")

            for greek in greeks:
                for value in VISUALIZATIONS[greek]:
                    #print(f"Processing {ticker}/{exp}/{greek}/{value}")
                    if value == "Implied Volatility Average" and greek == "vanna" and (exp == "0dte" or exp=="1dte"):
                        continue

                    try:
                        date_condition = "Profile" not in value and value != "Implied Volatility Average"
                        if date_condition:
                            if not isinstance(from_strike, (int, float)) or not isinstance(to_strike, (int, float)):
                                #print(f"Invalid from_strike/to_strike for {ticker}/{exp}, skipping")
                                continue
                            df_agg = df.groupby(["strike_price"]).sum(numeric_only=True)
                            #print(f"df_agg index type: {type(df_agg.index)}, index values: {df_agg.index[:5]}")
                            lower_strike = max(int(spot_price - 300), df_agg.index.min())
                            upper_strike = min(int(spot_price + 300), df_agg.index.max())
                            strikes = np.arange(lower_strike, upper_strike + 5, 5)
                            df_agg = df_agg.reindex(strikes, method='ffill').fillna(0)
                            if df_agg.empty:
                                #print(f"Empty df_agg after slicing for {ticker}/{exp}, skipping")
                                continue
                        else:
                            df_agg = df.groupby(["expiration_date"]).sum(numeric_only=True)
                            #print(f"df_agg index type: {type(df_agg.index)}, index values: {df_agg.index[:5]}")
                            if df_agg.empty:
                                #print(f"Empty df_agg for {ticker}/{exp}, skipping")
                                continue

                        if "Calls/Puts" in value or value == "Implied Volatility Average":
                            key = "strike" if date_condition else "exp"
                            if not (isinstance(call_ivs, dict) and isinstance(put_ivs, dict) and
                                    key in call_ivs and key in put_ivs):
                                #print(f"Invalid call_ivs/put_ivs for {ticker}/{exp}/{value}, skipping")
                                continue
                            call_ivs_data, put_ivs_data = call_ivs[key], put_ivs[key]
                        else:
                            call_ivs_data, put_ivs_data = None, None

                        if "Profile" in value and exp == "0dte" and len(df_agg.index) <= 1:
                            #print(f"Skipping {ticker}/{exp}/{value}: insufficient expiration dates for Profile plot")
                            continue

                        name = value.split()[1] if "Absolute" in value else value.split()[0]
                        name_to_vals = {
                            "Delta": (f"per 1% {ticker} Move", f"{name} Exposure (price / 1% move)", zerodelta),
                            "Gamma": (f"per 1% {ticker} Move", f"{name} Exposure (delta / 1% move)", zerogamma),
                            "Vanna": (f"per 1% {ticker} IV Move", f"{name} Exposure (delta / 1% IV move)", 0),
                            "Charm": (f"a day til {ticker} Expiry", f"{name} Exposure (delta / day til expiry)", 0),
                            "Implied": ("", "Implied Volatility (IV) Average", 0),
                        }
                        description, y_title, zeroflip = name_to_vals[name]
                        scale = 10**9

                        plt.figure(figsize=(10, 6))
                        title = f"{ticker} {value}, {today_ddt_string} for {exp}"
                        plt.title(title.replace("<br>", " "))
                        plt.grid(True)

                        if "Absolute" in value:
                            plt.bar(
                                df_agg.index,
                                df_agg[f"total_{name.lower()}"],
                                width=4,
                                label=f"{name} Exposure",
                                alpha=0.8,
                                color="#2B5078",
                            )
                        elif "Calls/Puts" in value:
                            plt.bar(
                                df_agg.index,
                                df_agg[f"call_{name[:1].lower()}ex"] / scale,
                                width=4,
                                label=f"Call {name}",
                                alpha=0.8,
                                color="#2B5078",
                            )
                            plt.bar(
                                df_agg.index,
                                df_agg[f"put_{name[:1].lower()}ex"] / scale,
                                width=4,
                                label=f"Put {name}",
                                alpha=0.8,
                                color="#9B5C30",
                            )
                        elif value == "Implied Volatility Average":
                            plt.plot(
                                df_agg.index,
                                put_ivs_data * 100,
                                label="Put IV",
                                color="#C44E52",
                            )
                            plt.fill_between(df_agg.index, put_ivs_data * 100, alpha=0.3, color="#C44E52")
                            plt.plot(
                                df_agg.index,
                                call_ivs_data * 100,
                                label="Call IV",
                                color="#32A3A3",
                            )
                            plt.fill_between(df_agg.index, call_ivs_data * 100, alpha=0.3, color="#32A3A3")
                        else:
                            name_to_vals = {
                                "Delta": (totaldelta["all"], totaldelta["ex_next"], totaldelta["ex_fri"]),
                                "Gamma": (totalgamma["all"], totalgamma["ex_next"], totalgamma["ex_fri"]),
                                "Vanna": (totalvanna["all"], totalvanna["ex_next"], totalvanna["ex_fri"]),
                                "Charm": (totalcharm["all"], totalcharm["ex_next"], totalcharm["ex_fri"]),
                            }
                            all_ex, ex_next, ex_fri = name_to_vals[name]
                            if not (all_ex.size > 0 and ex_next.size > 0 and ex_fri.size > 0):
                                #print(f"Invalid profile data for {ticker}/{exp}/{value}: empty arrays")
                                continue
                            plt.plot(levels, all_ex, label="All Expiries")
                            plt.plot(levels, ex_fri, label="Next Monthly Expiry")
                            plt.plot(levels, ex_next, label="Next Expiry")
                            if name in ["Charm", "Vanna"]:
                                all_ex_min, all_ex_max = all_ex.min(), all_ex.max()
                                min_n = [all_ex_min, ex_fri.min() if ex_fri.size != 0 else all_ex_min, ex_next.min() if ex_next.size != 0 else all_ex_min]
                                max_n = [all_ex_max, ex_fri.max() if ex_fri.size != 0 else all_ex_max, ex_next.max() if ex_next.size != 0 else all_ex_max]
                                min_n.sort()
                                max_n.sort()
                                if min_n[0] < 0:
                                    plt.axhspan(0, min_n[0] * 1.5, facecolor="red", alpha=0.1)
                                if max_n[2] > 0:
                                    plt.axhspan(0, max_n[2] * 1.5, facecolor="green", alpha=0.1)
                                plt.axhline(y=0, color="dimgray", linestyle="--", label=f"{name} Flip")
                            elif zeroflip > 0:
                                plt.axvline(x=zeroflip, color="dimgray", linestyle="--", label=f"{name} Flip: {zeroflip:,.0f}")
                                plt.axvspan(from_strike, zeroflip, facecolor="red", alpha=0.1)
                                plt.axvspan(zeroflip, to_strike, facecolor="green", alpha=0.1)

                        if date_condition:
                            val = ((spot_price // 50) + 1) * 50
                            plt.axvline(x=spot_price, color="#707070", linestyle="--", label=f"{ticker} Spot: {spot_price:,.2f}")
                            plt.xlim(val - 300, val + 300)
                            x_ticks = np.arange(int(val - 300), int(val + 305), 50)
                            plt.xticks(x_ticks, [f"{int(x)}" for x in x_ticks])
                        else:
                            plt.xlim(today_ddt, today_ddt + timedelta(days=31))

                        plt.xlabel("Strike" if date_condition else "Date")
                        plt.ylabel(y_title)
                        plt.legend()
                        today = datetime.now(ZoneInfo(TZ)).date()
                        tomorrow = today + timedelta(days=1)
                        date_formats = {
                            "monthly": monthly_options_dates[0].strftime("%Y %b") if monthly_options_dates else "N/A",
                            "opex": monthly_options_dates[1].strftime("%Y %b %d") if len(monthly_options_dates) > 1 else "N/A",
                            "0dte": monthly_options_dates[0].strftime("%Y %b %d") if monthly_options_dates else "N/A",
                            "1dte": tomorrow.strftime("%Y %b %d"),
                            "all": "All Expirations",
                        }
                        plt.legend(title=date_formats.get(exp, "All Expirations"))

                        value = value.replace('Calls/Puts', 'Calls Puts')
                        filename = f"{PLOT_DIR}/{ticker}/{exp}/{greek}/{value.replace(' ', '_')}/{timestamp}.png"
                        makedirs(os.path.dirname(filename), exist_ok=True)
                        plt.savefig(filename, bbox_inches="tight")
                        plt.close()
                        print(f"Gráfico guardado: {filename}")

                        await send_plot_to_discord(filename, ticker, exp, greek)
                        shutil.rmtree(PLOT_DIR)

                    except Exception as e:
                        print(f"Error processing {ticker}/{exp}/{greek}/{value}: {e}")

    if not (specific_ticker or specific_exp or specific_greek):
        await asyncio.sleep(1)
        cleanup_timestamp_directory(timestamp)

def start_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(
        lambda: asyncio.run_coroutine_threadsafe(generate_plots(), discord_client.loop).result(),
        CronTrigger.from_crontab("0,5,10,15,20,25,30,35,40,45,50,55 8-17 * * 0-4", timezone=ZoneInfo("America/New_York")),
    )
    print("Scheduler started: Generating plots every minute for testing")
    sched.start()