import os,logging,json
from logging.handlers import RotatingFileHandler

# 设置日志级别和格式
class LogClass():
    def __init__(self):
        with open("config/applog.conf") as f:
            confj=json.loads(f.read())
        self.logger=None
        self.loglevel=confj["loglevel"].lower()
        self.logdir=confj["logdir"]
        self.logfile=confj["logfile"]
        self.maxBytes=confj["maxBytes"]
        self.backupCount=confj["backupCount"]
        self.encoding=confj["encoding"]
        self.logformat=confj["logformat"]
        self.levelmap={
            'info':logging.INFO,
            'error':logging.ERROR,
            'warning':logging.WARNING,
            'warn':logging.WARN,
            'critical':logging.CRITICAL,
            'debug':logging.DEBUG
        }

    def initialize(self):
        os.makedirs(self.logdir, exist_ok=True)
        logging.basicConfig(level=self.levelmap[self.loglevel])
        self.logger = logging.getLogger(__name__)
        # logger.setLevel(logging.INFO)     #可省略，因handler已继承basicConfig的级别

        # 创建文件处理器并设置日志格式和文件名
        file_handler = RotatingFileHandler("%s/%s" % (self.logdir,self.logfile) , maxBytes=self.maxBytes, backupCount=self.backupCount, encoding=self.encoding)
        formatter = logging.Formatter(self.logformat)
        file_handler.setFormatter(formatter)

        # 将处理器添加到日志记录器中
        self.logger.addHandler(file_handler)



