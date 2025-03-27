'''
依赖包：
1，mysqlclient==1.4.2.post1
2，DBUtils==3.0.3
'''

import json,pymysql  #mac环境下无法使用MYSQLdb
from dbutils.pooled_db import PooledDB

conf="config/db.conf"
with open(conf) as cf:
    confmidd = json.loads(cf.read())
    host = confmidd["mysql_host"]
    port = confmidd["mysql_port"]
    user = confmidd["mysql_user"]
    password = confmidd["mysql_password"]
    db = confmidd["mysql_db"]
    minsize = confmidd["mysql_min_size"]
    maxsize = confmidd["mysql_max_size"]
    timeout = confmidd["mysql_timeout"]
    heartbeat_interval = confmidd["heartbeat_interval"]


# Create a database connection pool
pool = PooledDB(
    pymysql,
    mincached=minsize,          #空闲连接数
    maxcached=minsize + 2,          #最大空闲连接数
    maxconnections=maxsize,     #全局最大连接数（包括空闲的）
    host=host,
    user=user,
    passwd=password,
    db=db,
    blocking=True,             #True为阻塞式，连接数达到最大后续连接等待，Fasle为直接断开
    charset='utf8'
)

# Function to execute a query
def execute_query(query, data=None):
    result={}
    connection = pool.connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, data)
        connection.commit()
        #print("Query executed successfully")
        result_tmp=cursor.fetchall()
        result['msg']='succeed'
        result['result']=result_tmp
    except Exception as error:
        # print("Error: {}".format(error))
        connection.rollback()
        # result_tmp=()
        result['msg'] = 'failed'
        result['result'] = error

    finally:
        cursor.close()
        connection.close()

    return result



