import logging
from typing import Dict
import hashlib
import requests
from requests import HTTPError
import json
from math import floor
from datetime import datetime, timedelta
from pytz import timezone

from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import (
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, Update
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

tempAccount = {}
loggedAccounts = []

ADD_ACC, ADD_MULTI, ENTER_PHONE, ENTER_PASS, ENTER_SERVER, LOGGED_IN, RE_LOGIN, COMPETITION, ORDER, RECORD, SET_BET_TIMER, UN_SET_BET_TIMER = range(12)
Q_INFO, Q_ORDER = range(2)

start_keyboard = [
    ["Add New Account", "Add Multi"],
    # ["Number of siblings", "Something else..."],
    # ["Done"],
]
start_markup = ReplyKeyboardMarkup(
    start_keyboard, input_field_placeholder="Choose the option...", one_time_keyboard=True, resize_keyboard=True)

logged_keyboard = [
    ["Balance", "Competition"],
    ["Bet record", "Login"],
    ["/SetBet 3600", "/UnSetBet"],
    ["Add New Account", "Add Multi"],
    ["Log out", "Done"]
]
logged_markup = ReplyKeyboardMarkup(
    logged_keyboard, input_field_placeholder="Choose the option...", resize_keyboard=True)

timer = 0.0

def facts_to_str(user_data: Dict[str, str]) -> str:
    """Helper function for formatting the gathered user info."""
    facts = [f"{key} - {value}" for key, value in user_data.items()]
    return "\n".join(facts).join(["\n", "\n"]).replace("'", '"')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global loggedAccounts

    """Start the conversation, display any stored data and ask user for input."""
    if "account" in context.user_data and len(context.user_data["account"]) > 0:
        loggedAccounts = context.user_data["account"]
        reply_text = "You're already added account.\nPlease tell what you want me to do."

        await update.message.reply_text(reply_text, reply_markup=logged_markup)
        return LOGGED_IN
    else:
        reply_text = "Hi! My name is Mr.OL_BOT.\nPlease choose the option!"

        await update.message.reply_text(reply_text, reply_markup=start_markup)
        return ADD_ACC

async def add_multi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "Please enter your accounts json:"
    await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())

    return ADD_MULTI

async def json_to_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(f"Add Multi: {update.message.text}")
    global loggedAccounts
    accounts = json.loads(update.message.text)
    oldAccount = []

    for account in accounts:
        phone = account["phone"]
        password = account["pass"]
        server = account["server"]
        url = (f"{server}/api/login")
        payload = {
            'mobile': phone,
            'password': password
        }

        try:
            r = requests.post(url, json=payload)
            r.raise_for_status()

            if context.user_data.get("account"):
                oldAccount = context.user_data["account"]

            oldAccount.append({"phone": phone, "pass": password, "server": server})
            context.user_data["account"] = oldAccount
            loggedAccounts = oldAccount

            re = json.loads(r.text) #response from server

            uid = re["uid"]
            nickname = re["nickname"]
            goldCoin = re["goldCoin"]
            vip = re["userLevel"]

            reply_text = (
                "Your account is successfully added!\n\n"
                f"UID: {uid}\n"
                f"Nickname: {nickname}\n"
                f"VIP: {vip}\n"
                f"Balance: ${roundDown(goldCoin, 4)}"
            )

            await update.message.reply_text(reply_text, reply_markup=logged_markup) 

        except HTTPError as ex:
            reply_text = f"{phone} ---> Error: {ex}"
            if context.user_data.get("account"):
                await update.message.reply_text(reply_text, reply_markup=logged_markup)
            else:
                await update.message.reply_text(reply_text, reply_markup=start_markup)

    return LOGGED_IN

async def add_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "Please enter your phone number:"
    await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())

    return ENTER_PHONE


async def enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return_value: int
    reply_text: str
    text = update.message.text

    if text.isdigit():
        tempAccount["phone"] = text
        reply_text = "Please enter your password:"

        return_value = ENTER_PASS
    else:
        reply_text = "Phone number is invalid!\nPlease Enter your phone number:"

        return_value = ENTER_PHONE

    await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())

    return return_value


async def enter_pass(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    tempAccount["pass"] = hashlib.md5((text+"GG").encode('utf-8')).hexdigest()

    reply_text = "Please enter server:"
    await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())
    await update.message.delete()

    return ENTER_SERVER


async def enter_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tempAccount["server"] = update.message.text.lower()
    global loggedAccounts
    accounts = []

    url = (f"{update.message.text.lower()}/api/login")
    phone = tempAccount["phone"]
    password = tempAccount["pass"]
    payload = {
        'mobile': phone,
        'password': password
    }

    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()

        if context.user_data.get("account"):
            accounts = context.user_data["account"]
            print(f"context Accounts: {accounts}")
            
        print(f"Accounts: {accounts}")
        print(f"Temp Accounts: {tempAccount}")
        accounts.append({"phone": tempAccount["phone"], "pass": tempAccount["pass"], "server": tempAccount["server"]})
        context.user_data["account"] = accounts
        loggedAccounts = accounts

        re = json.loads(r.text) #response from server
        
        uid = re["uid"]
        nickname = re["nickname"]
        goldCoin = re["goldCoin"]
        vip = re["userLevel"]

        reply_text = (
            "Your account is successfully added!\n\n"
            f"UID: {uid}\n"
            f"Nickname: {nickname}\n"
            f"VIP: {vip}\n"
            f"Balance: ${roundDown(goldCoin, 4)}"
        )
        
        await update.message.reply_text(reply_text, reply_markup=logged_markup)

        return LOGGED_IN

    except HTTPError as ex:
        reply_text = f"{ex}"
        await update.message.reply_text(reply_text, reply_markup=logged_markup)

        return ADD_ACC

def roundDown(n, d=4):
    d = int('1' + ('0' * d))
    return floor(n * d) / d


async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    accounts = context.user_data.get("account")
    totalAmount = 0.0
    
    for acc in accounts:
        server = acc["server"]
        phone = acc["phone"]
        url = (f"{server}/api/info")

        try:
            r = requests.post(url, json={})
            r.raise_for_status()

            re = json.loads(r.text) #response from server

            # uid = re["uid"]
            # nickname = re["nickname"]
            goldCoin = re["goldCoin"]
            balance = roundDown(goldCoin)
            # vip = re["userLevel"]
            phone = re["phone"]
            ipAddress = re["ip_address"]

            totalAmount += balance

            reply_text = (
                f"{phone} --> {balance}\n"
                f"IP Address --> {ipAddress}"
            )

            await update.message.reply_text(reply_text, reply_markup=logged_markup)

        except HTTPError as ex:
            reply_text = f"{phone} --> ERROR: {ex}"
            await update.message.reply_text(reply_text, reply_markup=logged_markup)

    count = len(accounts)
    reply_text = f"All {count} accounts has been checked. Total Balance: {totalAmount}"
    await update.message.reply_text(reply_text, reply_markup=logged_markup)


async def re_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global loggedAccounts
    accounts = context.user_data.get("account")
    loggedAccounts = accounts
    
    for acc in accounts:
        server = acc["server"]
        phone = acc["phone"]
        password = acc["pass"]
        url = (f"{server}/api/login")
        payload = {
            'mobile': phone,
            'password': password
        }

        try:
            r = requests.post(url, json=payload)
            r.raise_for_status()

            re = json.loads(r.text) #response from server

            # uid = re["uid"]
            # nickname = re["nickname"]
            # goldCoin = re["goldCoin"]
            # vip = re["userLevel"]
            phone = re["phone"]

            reply_text = (
                f"{phone} --> Success"
            )

            await update.message.reply_text(reply_text, reply_markup=logged_markup)

        except HTTPError as ex:
            reply_text = f"{phone} --> ERROR: {ex}"
            await update.message.reply_text(reply_text, reply_markup=logged_markup)

    count = len(accounts)
    reply_text = f"All {count} accounts has been re-login"
    await update.message.reply_text(reply_text, reply_markup=logged_markup)


async def log_out(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"Last accounts json: {facts_to_str(context.user_data)}You use it next time!",
    )

    context.user_data.pop("account")
    reply_text = "You're successfully log out."

    await update.message.reply_text(reply_text, reply_markup=start_markup)
    return ADD_ACC

async def set_bet_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global timer
    global loggedAccounts
    """Add a job to the queue."""
    chat_id = update.effective_message.chat_id
    loggedAccounts = context.user_data.get("account")
    try:
        # args[0] should contain the time for the timer in seconds
        due = float(context.args[0])
        if due < 0:
            await update.effective_message.reply_text("Sorry we can not go back to pass!")
            return

        timer = due

        await showCompetition(update=update, context=context, isTimer=True)

        # job_removed = remove_job_if_exists(str(chat_id), context)
        # context.job_queue.run_once(alarm, due, chat_id=chat_id, name=str(chat_id), data=due)

        # text = "Timer successfully set!"
        # if job_removed:
        #     text += " Old one was removed."
        # await update.effective_message.reply_text(text)

    except (IndexError, ValueError):
        await update.effective_message.reply_text("Usage: /set <seconds>")


async def unset_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists((f"orderTimer{chat_id}"), context)
    text = "Timer successfully cancelled!" if job_removed else "You have no active timer."
    await update.message.reply_text(text)

async def alarm(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the alarm message."""
    print(context.user_data)
    job = context.job
    await context.bot.send_message(job.chat_id, text=f"Beep! {job.data} seconds are over!")


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True

async def showCompetition(update: Update, context: ContextTypes.DEFAULT_TYPE, isTimer: bool = False):
    accounts = context.user_data.get("account")
    if len(accounts) <= 0:
        reply_text = "No Account"
        await update.message.reply_text(reply_text, reply_markup=logged_markup)
        return

    account = accounts[0]
    server = account["server"]
    url = (f"{server}/api/competition")

    try:
        r = requests.get(url)
        r.raise_for_status()

        re = json.loads(r.text) #response from server
        
        competitions = list(re["competitionInfos"])

        if len(competitions) == 0:
            await update.message.reply_text("There is no competition!", reply_markup=logged_markup)
            return

        for competition in competitions:
            leagueName = competition["leagueNameEn"]
            homeTeamName = competition["homeTeamNameEn"]
            awayTeamName = competition["awayTeamNameEn"]
            scheduleTime = getTime(competition['scheduleTime'])
            cid = competition["cid"]
            option = "timer" if isTimer else "info"
            data = (f"{option}///"
                f"{cid}///"
                f"{server}"
            )

            betButton = [InlineKeyboardButton("Info", callback_data=data)]
            reply_markup = InlineKeyboardMarkup([betButton])

            reply_text = (
                f"{leagueName}\n{scheduleTime}\n\n"
                f"{homeTeamName} VS {awayTeamName}"
            )

            await update.message.reply_text(reply_text, reply_markup=reply_markup)

    except HTTPError as ex:
        reply_text = f"--> ERROR: {ex}"
        await update.message.reply_text(reply_text, reply_markup=logged_markup)

async def competition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await showCompetition(update=update, context=context)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    await query.answer()
    
    data = query.data.split("///")
    print(query.data)
    print(data)
    option = data[0]
    cid = data[1]
    
    if option == 'info' or option == 'timer':
        server = data[2]
        url = (f"{server}/api/competition/info")
        params = {
            'cid':cid
        }

        try:
            r = requests.get(url, params=params)
            r.raise_for_status()

            re = json.loads(r.text) #response from server

            leagueName = re["leagueEn"]
            homeTeamName = re["homeTeamEn"]
            awayTeamName = re["awayTeamEn"]
            time = re['scheduleTime']
            cid = re["cid"]
            quotaList = re['quotaList']
            keyboard = []

            orderOption = "orderTimer" if option == "timer" else "order"

            for quota in quotaList:
                rate = roundDown(quota['rate'] * 100, 2)
                score = quota['score']
                scoreStr = str(score).replace("H", "").replace("A", "-")
                
                data = (
                    f"{orderOption}///"
                    f"{cid}///"
                    f"{score}"
                )
                
                betButton = [InlineKeyboardButton(f"{scoreStr}  |   {rate}%", callback_data=data)]
                keyboard.append(betButton)
            
            reply_markup = InlineKeyboardMarkup(keyboard)

            text = (
                f"{leagueName}\n\n"
                f"{homeTeamName} VS {awayTeamName}"
            )

            await query.edit_message_text(text=text, reply_markup=reply_markup)

        except HTTPError as ex:
            reply_text = f"--> ERROR: {ex}"
            print(reply_text)
            await query.edit_message_text(reply_text, reply_markup=logged_markup)

        return

    if option == 'orderTimer':
        odds = data[2]
        chatID = update.effective_message.chat_id
        data = f"{cid}///{odds}"

        job_removed = remove_job_if_exists((f"orderTimer{chatID}"), context)
        context.job_queue.run_once(orderTimer, timer, chat_id=chatID, name=(f"orderTimer{chatID}"), data=data)

        text = f"Timer bet successfully set {timer}!"
        if job_removed:
            text += " Old one was removed."
    
        await query.edit_message_text(text)
        return

    if option == 'order':
        odds = data[2]
        score = str(odds).replace("H", "").replace("A", "-")
        accounts = []

        if not context.user_data.get('account'):
            await query.edit_message_text("No account!", reply_markup=logged_markup)
        else:
            accounts = context.user_data.get('account')

        text = f"Betting is in progress..."
        await query.edit_message_text(text=text)

        for account in accounts:
            server = account['server']
            phone = account['phone']
            url = (f"{server}/api/info")
            print(f"URL: {url}")

            try:
                r = requests.post(url, json={})
                r.raise_for_status()

                re = json.loads(r.text) #response from server

                goldCoin = re["goldCoin"]
                url = f"{server}/api/competition/order"
                payload = {
                    'cid':cid,
                    "amount": roundDown(goldCoin, 4),
                    "odds": odds
                } 

                try:
                    r = requests.post(url, json=payload)
                    r.raise_for_status()

                    re = json.loads(r.text) #response from server
                    # print(r.status_code)
                    # print(re)

                    if re['code'] != 200:
                        msg = re['msg']
                        reply_text = f"{phone} --> {msg}"
                        await context.bot.send_message(context._user_id, text=reply_text, reply_markup=logged_markup)
                    
                except HTTPError as ex:
                    reply_text = f"{phone} --> ERROR: {ex}"
                    await context.bot.send_message(context._user_id, text=reply_text, reply_markup=logged_markup)

            except HTTPError as ex:
                reply_text = f"{phone} --> ERROR: {ex}"
                await context.bot.send_message(context._user_id, text=reply_text, reply_markup=logged_markup)

        text = f"All {len(accounts)} accounts has been betted at {score}"
        await query.edit_message_text(text=text)
        return

async def orderTimer(context: ContextTypes.DEFAULT_TYPE):
    print("Order timer")
    job = context.job
    data = str(job.data).split("///")
    cid = data[0]
    odds = data[1]
    score = str(odds).replace("H", "").replace("A", "-")

    if len(loggedAccounts) <= 0:
        text = "No account, Retry in 5 minute"
        context.job_queue.run_once(orderTimer, (60*5), chat_id=job.chat_id, name=(f"orderTimer{job.chat_id}"), data=job.data)
        await context.bot.send_message(job.chat_id, text=text, reply_markup=logged_markup)
    else:
        accounts = loggedAccounts

        text = f"Timer Bet is in progress..."
        await context.bot.send_message(job.chat_id, text=text, reply_markup=logged_markup)

        for account in accounts:
            server = account['server']
            phone = account['phone']
            url = (f"{server}/api/info")
            print(f"URL: {url}")

            try:
                r = requests.post(url, json={})
                r.raise_for_status()

                re = json.loads(r.text) #response from server

                goldCoin = re["goldCoin"]
                url = f"{server}/api/competition/order"
                payload = {
                    'cid':cid,
                    "amount": roundDown(goldCoin, 4),
                    "odds": odds
                } 

                try:
                    r = requests.post(url, json=payload)
                    r.raise_for_status()

                    re = json.loads(r.text) #response from server
                    # print(r.status_code)
                    # print(re)

                    if re['code'] != 200:
                        msg = re['msg']
                        reply_text = f"{phone} --> {msg}"
                        await context.bot.send_message(job.chat_id, text=reply_text, reply_markup=logged_markup)
                    
                except HTTPError as ex:
                    reply_text = f"{phone} --> ERROR: {ex}"
                    await context.bot.send_message(job.chat_id, text=reply_text, reply_markup=logged_markup)

            except HTTPError as ex:
                reply_text = f"{phone} --> ERROR: {ex}"
                await context.bot.send_message(job.chat_id, text=reply_text, reply_markup=logged_markup)

        text = f"All {len(accounts)} accounts has been betted at {score}"
        await context.bot.send_message(job.chat_id, text=text, reply_markup=logged_markup)
    
    return

async def record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    accounts = context.user_data.get("account")
    totalProfit = 0.0
    
    for acc in accounts:
        server = acc["server"]
        phone = acc["phone"]
        today = datetime.today()
        tomorrow  = today - timedelta(days=-1)
        yesterday = today - timedelta(days=1)
        url = (f"{server}/api/order/record")
        startTime = yesterday.strftime("%Y-%m-%d") + "T17:00:00.000Z"
        endTime = tomorrow.strftime("%Y-%m-%d") + "T16:59:59.999Z"
        payload = {
            "startTime": startTime,
            "endTime": endTime
        }

        try:
            r = requests.post(url, json=payload)
            r.raise_for_status()

            re = json.loads(r.text) #response from server
            orders = re["competitionOrders"]

            for order in orders:
                if order["status"] != 0:
                    continue

                league = order["leagueEn"]
                homeTeam = order["homeTeamEn"]
                awayTeamEn = order["awayTeamEn"]
                fullHomeScore = order["fullHomeScore"]
                fullAwayScore = order["fullAwayScore"]
                orderNo = order["orderNo"]
                odds = str(order["odds"]).replace("H", "").replace("A", ":")
                rate = roundDown(order["rate"] * 100, 2)
                amount = order["amount"]
                income = roundDown(order["anticipatedIncome"], 4)
                scheduleTime = getTime(order['scheduleTime'])

                totalProfit += income
            
                reply_text = (
                    f"---------->>>>{phone}<<<<----------\n\n"
                    f"{league}\n{scheduleTime}\n\n"
                    f"{homeTeam}({fullHomeScore})   VS   {awayTeamEn}({fullAwayScore})\n"
                    f"Order number:     {orderNo}\n"
                    f"Betting options:  Correct Score {odds}@{rate}%\n"
                    f"Bet amount:       {amount}\n"
                    f"My profit:        {income}"
                )

                await update.message.reply_text(reply_text, reply_markup=logged_markup)

        except HTTPError as ex:
            reply_text = f"{phone} --> ERROR: {ex}"
            await update.message.reply_text(reply_text, reply_markup=logged_markup)

    count = len(accounts)
    reply_text = (f"All {count} accounts has been checked. Total Profit: {totalProfit}")
    await update.message.reply_text(reply_text, reply_markup=logged_markup)

def getTime(dateTime: str) -> str:
    datetime_str = dateTime.split('.')[0]

    datetime_object = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S').astimezone(timezone('Asia/Phnom_Penh'))

    return datetime_object.strftime('%B %d, %Y / %H:%M')

async def set_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    accounts = context.user_data.get("account")
    newUrl = context.args[0]
    payload = {
        "url": newUrl
    }
    
    for acc in accounts:
        server = acc["server"]
        url = (f"{server}/api/url")

        requests.put(url, json=payload)

    count = len(accounts)
    reply_text = (f"All {count} accounts has been updated.")
    await update.message.reply_text(reply_text, reply_markup=logged_markup)
    

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display the gathered info and end the conversation."""
    if "choice" in context.user_data:
        del context.user_data["choice"]

    await update.message.reply_text(
        f"Last accounts json: {facts_to_str(context.user_data)}You use it next time!",
        reply_markup=ReplyKeyboardRemove(),
    )

    context.user_data.pop("account")

    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    persistence = PicklePersistence(filepath="multi_acc_bot")
    application = Application.builder().token(
        "5629058980:AAF5gNsKvg26YmSMUYhEvkXTBGRpE7XDx5M").persistence(persistence).build()

    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ADD_MULTI: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, json_to_accounts
                )
            ],
            ADD_ACC: [
                MessageHandler(
                    # filters.Regex("^(Age|Favourite colour|Number of siblings)$"), regular_choice
                    filters.Regex("^(Add Multi)$"), add_multi
                ),
                MessageHandler(
                    # filters.Regex("^(Age|Favourite colour|Number of siblings)$"), regular_choice
                    filters.Regex("^(Add New Account)$"), add_account
                )
            ],
            ENTER_PHONE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, enter_phone
                )
            ],
            ENTER_PASS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, enter_pass
                )
            ],
            ENTER_SERVER: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, enter_server
                )
            ],
            LOGGED_IN: [
                MessageHandler(
                    filters.Regex("^Balance$"), check_balance
                ),
                MessageHandler(
                    filters.Regex("^Log out$"), log_out
                ),
                MessageHandler(
                    filters.Regex("^Competition$"), competition
                ),
                MessageHandler(
                    filters.Regex("^Bet record$"), record
                ),
                MessageHandler(
                    filters.Regex("^Login$"), re_login
                ),
                CommandHandler(
                    "SetBet", set_bet_timer
                ),
                CommandHandler(
                    "UnSetBet", unset_bet
                ),
                CommandHandler(
                    "SetUrl", set_url
                ),
                MessageHandler(
                    filters.Regex("^Add New Account$"), add_account
                ),
                MessageHandler(
                    filters.Regex("^Add Multi$"), add_multi
                )
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
        name="my_conversation",
        persistent=True,
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button))

    # show_data_handler = CommandHandler("show_data", show_data)
    # application.add_handler(show_data_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
