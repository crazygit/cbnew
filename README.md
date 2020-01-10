## Convertible bond

Telegram打新债信息通知机器人

### 配置环境变量
```bash
# telegram机器人的token
$ echo 'BOT_TOKEN=xxxxxxxxxxxxxxx' >> .env
# telegram channel id
$ echo 'CHANNEL_ID=xxxxxxxxxxxxxxx' >> .env
```

### 环境初始化

```bash
$ python -V
Python 3.7.0

# 安装依赖
$ pip install -r requirements.txt

# 运行服务
$ python cb_bot.py
```

## 数据来源

* [集思录](https://www.jisilu.cn/data/cbnew/#pre)
* [东方财富](http://data.eastmoney.com/kzz/default.html)
