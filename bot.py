import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
from plot_options import generate_plots, set_discord_client

load_dotenv()
DISCORD_TOKEN = ""

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="$", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    set_discord_client(bot)

@bot.command()
async def load(ctx, ticker: str, expiration: str, greek: str):
    ticker = ticker.upper()
    if ticker not in ["SPX", "NDX", "RUT"]:
        await ctx.send(f"Invalid ticker: {ticker}. Must be SPX, NDX, or RUT.")
        return
    ticker = f"^{ticker}"
    
    if expiration.lower() not in ["0dte", "1dte", "opex", "monthly", "all"]:
        await ctx.send(f"Invalid expiration: {expiration}. Must be 0dte, 1dte, opex, monthly, or all.")
        return
    if greek.lower() not in ["delta", "gamma", "vanna", "charm"]:
        await ctx.send(f"Invalid Greek: {greek}. Must be delta, gamma, vanna, or charm.")
        return
    await ctx.send(f"Generating plots for {ticker}/{expiration}/{greek.lower()}...")
    await generate_plots(specific_ticker=ticker, specific_exp=expiration, specific_greek=greek.lower())
    await ctx.send(f"Plots for {ticker}/{expiration}/{greek.lower()} sent to the respective channel.")

def run_bot():
    bot.run(DISCORD_TOKEN)