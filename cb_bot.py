# -*- coding: utf-8 -*-
import datetime
import logging
import time
from typing import Tuple, List, Dict

import requests
from environs import Env
from telegram.error import (
    TelegramError,
    Unauthorized,
    BadRequest,
    TimedOut,
    ChatMigrated,
    NetworkError,
)
from telegram.ext import (
    CallbackContext,
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
)
from telegram.ext.jobqueue import Days

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_cb_info() -> Tuple[List, List]:
    url = "https://www.jisilu.cn/data/cbnew/pre_list/"
    response = requests.post(
        url,
        data={"cb_type_Y": "Y", "progress": "", "rp": 22},
        headers={
            "Origin": "https://www.jisilu.cn",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.jisilu.cn/data/cbnew/",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        },
    )
    apply_cb = []
    listed_cb = []

    for row in response.json()["rows"]:
        cell = row["cell"]
        today = datetime.date.today().isoformat()
        # 当日可申购债券
        if cell["apply_date"] == today:
            apply_cb.append(cell)
        # 当日上市债券
        elif cell["list_date"] == today:
            listed_cb.append(cell)
    return apply_cb, listed_cb


def start(updater: Updater, context: CallbackContext) -> None:
    # context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")
    updater.message.reply_text("I'm a bot, please talk to me!")


def unknown(update: Updater, context: CallbackContext) -> None:
    # context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")
    update.message.reply_text("Sorry, I didn't understand that command.")


def format_cell(cell: Dict[str, str]) -> str:
    # text += f'证券代码: {cell["stock_id"]}, 债券代码: {cell["bond_id"]}, 申购代码: {cell["apply_cd"]}, 配售代码: {cell["ration_cd"]}, 名称: {cell["stock_nm"]}, 现价: {cell["price"]}, 发行规模（亿元）: {cell["amount"]}, 中签率: {cell["lucky_draw_rt"]}%, '
    # text += f'评级: {cell["rating_cd"]}, 申购建议: {cell["jsl_advise_text"]}, 单账户中签(定格): {cell["single_draw"]}\n\n'
    lucky_draw_rt = (
        escape_text(cell["lucky_draw_rt"]) + "%"
        if cell["lucky_draw_rt"]
        else escape_text("---")
    )
    return f"""
    名   称: {escape_text(cell["stock_nm"] + '(' + cell["bond_nm"] + ')')}
    债券代码: [{cell["bond_id"]}](https://www.jisilu.cn/data/convert_bond_detail/{cell["bond_id"]})
    证券代码: [{cell["stock_id"]}](https://www.jisilu.cn/data/stock/{cell["stock_id"]})
    现    价: {escape_text(cell["price"])}
    中签率: {lucky_draw_rt}
    评   级: {escape_text(cell["rating_cd"])}
    申购建议: {escape_text(cell["jsl_advise_text"])}
    """


def escape_text(text: str) -> str:
    if text:
        for keyword in [
            "_",
            "*",
            "[",
            "]",
            "(",
            ")",
            "~",
            "`",
            ">",
            "#",
            "+",
            "-",
            "=",
            "|",
            "{",
            "}",
            ".",
            "!",
        ]:
            text = text.replace(keyword, f"\\{keyword}")
        return text
    return ""


def get_message_text() -> str:
    today = datetime.date.today().isoformat()
    logger.info(f"get message at {today}")
    apply_cb, listed_cb = get_cb_info()
    text = ""
    text += f"*日期*: {escape_text(today)}\n\n"
    if apply_cb:
        text += "*当日可打新债*: \n"
        for cell in apply_cb:
            text += format_cell(cell)
    else:
        text += "*当日无可打新债*"
    text += "\n\n"
    if listed_cb:
        text += "*当日上市新债*: \n"
        for cell in listed_cb:
            text += format_cell(cell)
    else:
        text += "*当日无上市新债*\n\n"
    text += "\n_以上数据来源于互联网，仅供参考，不作为投资建议_ "
    return text


def get_cb_trade_data(context: CallbackContext) -> None:
    text = get_message_text()
    logger.info(text)
    retry_count = 0
    while True:
        try:
            context.bot.send_message(
                chat_id=context.job.context.get("channel_id"),
                # parse_mode=ParseMode.MARKDOWN,
                # note: hardcode, 当前SDK不支持MarkdwonV2模式
                parse_mode="MarkdownV2",
                text=text,
                disable_web_page_preview=True,
                timeout=5,
            )
            break
        except Exception as e:
            logger.exception(e)
            if retry_count >= 3:
                logger.info("Give up retrying...")
                break
            logger.info("Retrying after 10 seconds...")
            time.sleep(10)
            retry_count += 1


def error_callback(update: Updater, context: CallbackContext) -> None:
    try:
        raise context.error
    except Unauthorized as e:
        # remove update.message.chat_id from conversation list
        logger.error(e)
    except BadRequest as e:
        # handle malformed requests - read more below!
        logger.error(e)
    except TimedOut as e:
        # handle slow connection problems
        logger.error(e)
    except NetworkError as e:
        # handle other connection problems
        logger.error(e)
    except ChatMigrated as e:
        # the chat_id of a group has changed, use e.new_chat_id instead
        logger.error(e)
    except TelegramError as e:
        # handle all other telegram related errors
        logger.error(e)


def main() -> None:
    env = Env()
    # Read .env into os.environ
    env.read_env()

    token = env.str("BOT_TOKEN", None)
    channel_id = env.str("CHANNEL_ID", None)
    assert token is not None, "Please Set Bot Token"
    assert channel_id is not None, "Please Set Channel id"
    # channel_id必须以@符号开头
    if not channel_id.startswith("@"):
        channel_id = f"@{channel_id}"

    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher
    updater.job_queue.run_daily(
        get_cb_trade_data,
        # 北京时间9点触发
        time=datetime.time(9 - 8, 00),
        days=(Days.MON, Days.TUE, Days.WED, Days.THU, Days.FRI),
        context={"channel_id": channel_id},
    )
    start_handler = CommandHandler("start", start)
    dispatcher.add_handler(start_handler)

    # This handler must be added last. If you added it sooner, it would be triggered before the CommandHandlers had a chance to look at the update. Once an update is handled, all further handlers are ignored.
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)
    dispatcher.add_error_handler(error_callback)

    updater.start_polling()
    logger.info("Started Bot...")
    updater.idle()


if __name__ == "__main__":
    main()
